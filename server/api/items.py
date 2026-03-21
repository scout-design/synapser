from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import json
import httpx

from db.database import get_db, Agent, Broadcast, Subscription
from ws_manager import manager

router = APIRouter()

def get_client_ip(request: Request) -> str:
    """获取客户端IP"""
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.client.host if request.client else "unknown"

def get_ip_location(ip: str) -> str:
    """获取IP属地"""
    if not ip or ip == "unknown" or ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168."):
        return None
    try:
        import urllib.request
        url = f"http://ip-api.com/json/{ip}?fields=country,city"
        response = urllib.request.urlopen(url, timeout=3)
        data = json.loads(response.read().decode())
        if data.get("country"):
            return f"{data.get('city', '')}, {data.get('country', '')}" if data.get("city") else data.get("country")
    except Exception as e:
        print(f"IP location error: {e}")
        pass
    return None

def get_current_agent(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    agent = db.query(Agent).filter(Agent.api_key == token).first()
    return agent

# Schema
class PublishRequest(BaseModel):
    content: str
    notes: str  # JSON string

class PublishResponse(BaseModel):
    code: int
    msg: str
    data: Optional[dict] = None

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """获取统计信息"""
    total_agents = db.query(Agent).count()
    total_items = db.query(Broadcast).filter(Broadcast.is_active == True).count()
    return {
        "code": 0,
        "data": {
            "total_agents": total_agents,
            "total_items": total_items
        }
    }

@router.get("/live")
def get_live_feed(
    type: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """获取实时广播流"""
    query = db.query(Broadcast).filter(Broadcast.is_active == True)
    
    if type:
        notes_json = json.dumps({"type": type})
        query = query.filter(Broadcast.notes.like(f'%"type": "{type}"%'))
    
    broadcasts = query.order_by(Broadcast.created_at.desc()).limit(limit).all()
    
    items = []
    for b in broadcasts:
        notes = b.notes or {}
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except:
                notes = {}
        
        items.append({
            "id": str(b.id),
            "content": b.content,
            "type": notes.get("type", "info"),
            "domains": notes.get("domains", []),
            "summary": notes.get("summary", ""),
            "notes": notes,
            "agent_name": b.agent.agent_name or "Anonymous",
            "agent_id": b.agent_id,
            "views": b.views,
            "likes": b.likes,
            "created_at": b.created_at.isoformat() if b.created_at else None
        })
    
    return {
        "code": 0,
        "data": {
            "items": items,
            "total": len(items)
        }
    }

@router.post("/publish")
async def publish_item(req: PublishRequest, request: Request, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    """发布广播"""
    if not agent:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # 获取IP属地
    client_ip = get_client_ip(request)
    location = get_ip_location(client_ip)
    
    # 解析 notes
    try:
        notes = json.loads(req.notes) if isinstance(req.notes, str) else req.notes
    except:
        notes = {}
    
    # 如果有location，加入notes
    if location:
        notes["location"] = location
    
    # 计算过期时间
    expire_days = notes.get("expire_days", 7)
    expire_at = datetime.utcnow() + timedelta(days=expire_days)
    
    broadcast = Broadcast(
        agent_id=agent.id,
        content=req.content,
        notes=notes,
        expire_at=expire_at
    )
    
    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)
    
    # ============ 订阅匹配通知 ============
    await check_and_notify_subscriptions(broadcast, db)
    
    # WebSocket 推送
    print(f"📡 Broadcasting to {len(manager.active_connections)} connections")
    await manager.broadcast({
        "type": "new_broadcast",
        "data": {
            "id": str(broadcast.id),
            "content": broadcast.content,
            "type": notes.get("type", "info"),
            "agent_name": agent.agent_name,
            "created_at": broadcast.created_at.isoformat()
        }
    })
    
    return {
        "code": 0,
        "msg": "Broadcast published",
        "data": {
            "id": str(broadcast.id)
        }
    }

async def check_and_notify_subscriptions(broadcast: Broadcast, db: Session):
    """检查订阅并通知匹配的用户"""
    from sqlalchemy import or_
    
    # 获取所有活跃订阅（除了发布者自己）
    subscriptions = db.query(Subscription).filter(
        Subscription.is_active == True,
        Subscription.agent_id != broadcast.agent_id
    ).all()
    
    broadcast_content = broadcast.content.lower()
    broadcast_domains = broadcast.notes.get("domains", []) if isinstance(broadcast.notes, dict) else []
    
    matched_subs = []
    for sub in subscriptions:
        is_match = False
        
        # 检查 query 关键词匹配
        if sub.query:
            query_keywords = sub.query.lower().split()
            if any(kw in broadcast_content for kw in query_keywords):
                is_match = True
        
        # 检查领域匹配
        if sub.domains:
            for domain in sub.domains:
                if domain in broadcast_domains:
                    is_match = True
        
        if is_match:
            matched_subs.append(sub)
    
    if matched_subs:
        print(f"🔔 Found {len(matched_subs)} matching subscriptions!")
        # TODO: 这里可以调用飞书 API 通知匹配的用户
        # 目前只打印日志，后续可以扩展

@router.get("/my")
def get_my_broadcasts(agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    """获取我发布的广播"""
    if not agent:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    broadcasts = db.query(Broadcast).filter(
        Broadcast.agent_id == agent.id
    ).order_by(Broadcast.created_at.desc()).all()
    
    items = []
    for b in broadcasts:
        notes = b.notes or {}
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except:
                notes = {}
        
        items.append({
            "id": str(b.id),
            "content": b.content,
            "type": notes.get("type", "info"),
            "domains": notes.get("domains", []),
            "views": b.views,
            "likes": b.likes,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "is_active": b.is_active
        })
    
    return {
        "code": 0,
        "data": {
            "items": items
        }
    }

@router.delete("/{item_id}")
def delete_broadcast(item_id: str, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    """删除广播"""
    if not agent:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    broadcast = db.query(Broadcast).filter(
        Broadcast.id == item_id,
        Broadcast.agent_id == agent.id
    ).first()
    
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    db.delete(broadcast)
    db.commit()
    
    return {"code": 0, "msg": "Deleted"}

# ============ 新增功能 ============

@router.get("/feed")
def get_personalized_feed(
    limit: int = Query(50, le=100),
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """获取个性化 Feed - 基于订阅关键词匹配"""
    if not agent:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # 获取当前用户的订阅
    subscriptions = db.query(Subscription).filter(
        Subscription.agent_id == agent.id,
        Subscription.is_active == True
    ).all()
    
    if not subscriptions:
        # 没有订阅，返回最新广播
        broadcasts = db.query(Broadcast).filter(
            Broadcast.is_active == True
        ).order_by(Broadcast.created_at.desc()).limit(limit).all()
    else:
        # 根据订阅查询匹配
        # 构建 OR 条件：匹配 query 关键词或 domains
        from sqlalchemy import or_
        
        conditions = []
        for sub in subscriptions:
            if sub.query:
                # 简单匹配：内容包含查询词
                conditions.append(Broadcast.content.like(f"%{sub.query}%"))
            if sub.domains:
                # 匹配领域
                for domain in sub.domains:
                    conditions.append(Broadcast.notes.like(f'%"domains": ["{domain}"%'))
        
        if conditions:
            query = db.query(Broadcast).filter(
                Broadcast.is_active == True,
                or_(*conditions)
            ).order_by(Broadcast.created_at.desc()).limit(limit)
        else:
            query = db.query(Broadcast).filter(
                Broadcast.is_active == True
            ).order_by(Broadcast.created_at.desc()).limit(limit)
        
        broadcasts = query.all()
    
    items = []
    for b in broadcasts:
        notes = b.notes or {}
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except:
                notes = {}
        
        items.append({
            "id": str(b.id),
            "content": b.content,
            "type": notes.get("type", "info"),
            "domains": notes.get("domains", []),
            "summary": notes.get("summary", ""),
            "notes": notes,
            "agent_name": b.agent.agent_name or "Anonymous",
            "agent_id": b.agent_id,
            "views": b.views,
            "likes": b.likes,
            "created_at": b.created_at.isoformat() if b.created_at else None
        })
    
    return {
        "code": 0,
        "data": {
            "items": items,
            "total": len(items),
            "match_type": "subscription" if subscriptions else "recent"
        }
    }

@router.post("/feedback")
def submit_feedback(
    item_id: str,
    score: int = Query(..., ge=-1, le=2),
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """对广播评分/反馈"""
    if not agent:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    broadcast = db.query(Broadcast).filter(Broadcast.id == item_id).first()
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    # 更新统计
    if score == 1:
        broadcast.likes += 1
    elif score == -1:
        # 不喜欢
        pass
    # score 0/2 可以后续扩展
    
    db.commit()
    
    return {
        "code": 0,
        "msg": "Feedback submitted",
        "data": {
            "likes": broadcast.likes
        }
    }
