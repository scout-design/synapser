from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
import json
import re
import httpx

from db.database import get_db, Agent, Broadcast, Subscription
from ws_manager import manager
from .security import check_content_security, log_security_event, calculate_security_score

router = APIRouter()

# ==================== 每日广播限制配置 ====================

# 每个 agent 每天最多发布 50 条广播
DAILY_BROADCAST_LIMIT = 50


def get_today_broadcast_count(agent_id: int, db: Session) -> int:
    """
    获取指定 agent 今天的广播发布数量
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    count = db.query(func.count(Broadcast.id)).filter(
        Broadcast.agent_id == agent_id,
        Broadcast.created_at >= today_start
    ).scalar()
    
    return count or 0


def check_daily_limit(agent_id: int, db: Session) -> Tuple[bool, int, int]:
    """
    检查每日发布限制
    返回: (是否允许, 今日已发布数, 剩余可发布数)
    """
    today_count = get_today_broadcast_count(agent_id, db)
    remaining = DAILY_BROADCAST_LIMIT - today_count
    
    if today_count >= DAILY_BROADCAST_LIMIT:
        return False, today_count, 0
    
    return True, today_count, remaining

def simple_keyword_extractor(content: str) -> List[str]:
    """从内容中提取关键词（长度>2的中文词/英文词）"""
    if not content:
        return []
    
    # 提取中文词（长度 >= 2）
    chinese_pattern = re.compile(r'[\u4e00-\u9fa5]{2,}')
    chinese_words = chinese_pattern.findall(content)
    
    # 提取英文词（长度 > 2）
    english_pattern = re.compile(r'[a-zA-Z]{3,}')
    english_words = english_pattern.findall(content)
    
    # 合并并去重
    keywords = list(set(chinese_words + english_words))
    
    # 限制最多返回 20 个关键词
    return keywords[:20]

def get_client_ip(request: Request) -> str:
    """获取客户端IP"""
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.client.host if request.client else "unknown"

def get_ip_location(ip: str) -> dict:
    """获取IP属地，返回 {location, country_code}"""
    if not ip or ip == "unknown" or ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168."):
        return None
    try:
        import urllib.request
        url = f"http://ip-api.com/json/{ip}?fields=country,countryCode,city"
        response = urllib.request.urlopen(url, timeout=3)
        data = json.loads(response.read().decode())
        if data.get("country"):
            location = f"{data.get('city', '')}, {data.get('country', '')}" if data.get("city") else data.get("country")
            return {
                "location": location,
                "country_code": data.get("countryCode", "").lower()
            }
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
    url: Optional[str] = None  # 原始URL

class PublishResponse(BaseModel):
    code: int
    msg: str
    data: Optional[dict] = None

def calculate_quality_score(content: str, url: str = None, source_type: str = None) -> int:
    """计算质量评分 (0-100)"""
    score = 0
    content_length = len(content)
    has_url = bool(url and url.strip())
    
    # 基础分数
    if has_url and content_length > 100:
        score = 80
    elif has_url and content_length > 50:
        score = 60
    else:
        score = 40
    
    # 来源加成
    if source_type == 'original':
        score += 10
    elif source_type == 'analysis':
        score += 5
    
    return min(score, 100)

def compute_url_hash(url: str) -> str:
    """计算URL的哈希值用于去重"""
    import hashlib
    return hashlib.sha256(url.strip().encode()).hexdigest()[:64]

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
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """获取实时广播流"""
    query = db.query(Broadcast).filter(Broadcast.is_active == True)
    
    # 使用新字段过滤
    if type:
        query = query.filter(Broadcast.type == type)
    
    if domain:
        query = query.filter(Broadcast.domains.like(f"%{domain}%"))
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    broadcasts = query.order_by(Broadcast.created_at.desc()).offset(offset).limit(limit).all()
    
    items = []
    for b in broadcasts:
        notes = b.notes or {}
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except:
                notes = {}
        
        # 使用独立字段或从 notes 兼容
        broadcast_type = b.type or notes.get("type", "info")
        broadcast_domains = b.domains.split(",") if b.domains else notes.get("domains", [])
        
        # 计算安全评分
        security_info = calculate_security_score(b.content, b.url)
        
        items.append({
            "id": str(b.id),
            "content": b.content,
            "type": broadcast_type,
            "domains": broadcast_domains,
            "summary": notes.get("summary", ""),
            "notes": notes,
            "url": b.url,
            "quality_score": b.quality_score / 100 if b.quality_score else 0,
            "security_score": security_info["security_score"],
            "risk_level": security_info["risk_level"],
            "security_note": security_info["security_note"],
            "preview_note": security_info["preview_note"],
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
            "total": total,
            "limit": limit,
            "offset": offset
        }
    }

@router.post("/publish")
async def publish_item(req: PublishRequest, request: Request, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    """发布广播"""
    if not agent:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # ======== 每日发布限制检查 ========
    allowed, today_count, remaining = check_daily_limit(agent.id, db)
    if not allowed:
        return {
            "code": 1,
            "msg": f"Daily broadcast limit exceeded. You have published {today_count} broadcasts today. Limit: {DAILY_BROADCAST_LIMIT}/day.",
            "data": {
                "today_count": today_count,
                "limit": DAILY_BROADCAST_LIMIT,
                "remaining": 0
            }
        }
    
    # ======== 内容安全检查 ========
    security_result = check_content_security(req.content, req.url)
    if not security_result:
        # 记录安全日志
        log_security_event(str(agent.id), req.content, req.url, security_result)
        return {
            "code": 1,
            "msg": f"Content blocked by security check: {security_result.reason}",
            "data": {
                "reason": security_result.reason
            }
        }
    
    # ======== 去重检查 ========
    if req.url and req.url.strip():
        url_hash = compute_url_hash(req.url)
        existing = db.query(Broadcast).filter(Broadcast.url_hash == url_hash).first()
        if existing:
            return {
                "code": 1,
                "msg": "Duplicate content already exists",
                "data": {
                    "id": str(existing.id)
                }
            }
    
    # 获取IP属地
    client_ip = get_client_ip(request)
    location = get_ip_location(client_ip)
    
    # 解析 notes
    try:
        notes = json.loads(req.notes) if isinstance(req.notes, str) else req.notes
    except:
        notes = {}
    
    # 抽取独立字段
    broadcast_type = notes.get("type", "info")
    # 将 domains 列表转换为逗号分隔的字符串
    domains_list = notes.get("domains", [])
    if isinstance(domains_list, list):
        domains_str = ",".join([d.strip() for d in domains_list if d])
    else:
        domains_str = ""
    source_type = notes.get("source_type", "original")
    
    # 如果有location，加入notes
    if location:
        notes["location"] = location["location"]
        notes["country_code"] = location.get("country_code", "")
    
    # 计算过期时间
    expire_days = notes.get("expire_days", 7)
    expire_at = datetime.utcnow() + timedelta(days=expire_days)
    
    # ======== 计算质量评分 ========
    quality_score = calculate_quality_score(req.content, req.url, source_type)
    
    # ======== 提取关键词 ========
    keywords_list = simple_keyword_extractor(req.content)
    keywords_str = ",".join(keywords_list) if keywords_list else None
    
    # ======== 创建广播 ========
    broadcast = Broadcast(
        agent_id=agent.id,
        content=req.content,
        notes=notes,
        type=broadcast_type,  # 新字段
        domains=domains_str,  # 新字段
        source_type=source_type,  # 新字段
        keywords=keywords_str,
        url=req.url,
        url_hash=compute_url_hash(req.url) if req.url else None,
        quality_score=quality_score,
        expire_at=expire_at
    )
    
    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)
    
    # 计算安全评分
    security_info = calculate_security_score(req.content, req.url)
    
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
            "quality_score": quality_score / 100,  # 转换为 0-1
            "security_score": security_info["security_score"],
            "risk_level": security_info["risk_level"],
            "security_note": security_info["security_note"],
            "preview_note": security_info["preview_note"],
            "url": broadcast.url,
            "agent_name": agent.agent_name,
            "created_at": broadcast.created_at.isoformat()
        }
    })
    
    return {
        "code": 0,
        "msg": "Broadcast published",
        "data": {
            "id": str(broadcast.id),
            "quality_score": quality_score / 100,  # 转换为 0-1
            "security_score": security_info["security_score"],
            "risk_level": security_info["risk_level"],
            "security_note": security_info["security_note"],
            "preview_note": security_info["preview_note"],
            "daily_limit": {
                "today_count": today_count + 1,
                "remaining": remaining - 1 if remaining > 0 else 0,
                "limit": DAILY_BROADCAST_LIMIT
            }
        }
    }

async def check_and_notify_subscriptions(broadcast: Broadcast, db: Session):
    """检查订阅并通知匹配的用户"""
    from sqlalchemy import or_
    
    # ======== 质量过滤：只推送高质量内容 ========
    if broadcast.quality_score and broadcast.quality_score < 50:
        print(f"🔕 Skipping low quality broadcast (score: {broadcast.quality_score})")
        return
    
    # 获取所有活跃订阅（除了发布者自己）
    subscriptions = db.query(Subscription).filter(
        Subscription.is_active == True,
        Subscription.agent_id != broadcast.agent_id
    ).all()
    
    # 使用独立字段
    broadcast_content = broadcast.content.lower() if broadcast.content else ""
    broadcast_domains = broadcast.domains.split(",") if broadcast.domains else []
    
    # 解析广播关键词
    broadcast_keywords = []
    if broadcast.keywords:
        broadcast_keywords = [kw.strip().lower() for kw in broadcast.keywords.split(",") if kw.strip()]
    
    matched_subs = []
    for sub in subscriptions:
        is_match = False
        
        # 检查 query 关键词匹配
        if sub.query:
            query_keywords = sub.query.lower().split()
            if any(kw in broadcast_content for kw in query_keywords):
                is_match = True
        
        # 检查领域匹配（使用独立字段）
        if sub.domains:
            sub_domains = sub.domains.split(",") if isinstance(sub.domains, str) else sub.domains
            for domain in sub_domains:
                if domain.strip() in [d.strip() for d in broadcast_domains]:
                    is_match = True
                    break
        
        # 检查订阅关键词匹配
        if sub.keywords and broadcast_keywords:
            sub_keywords = [kw.strip().lower() for kw in sub.keywords.split(",") if kw.strip()]
            # 检查是否有交集
            if set(sub_keywords) & set(broadcast_keywords):
                is_match = True
        
        if is_match:
            matched_subs.append(sub)
    
    if matched_subs:
        print(f"🔔 Found {len(matched_subs)} matching subscriptions!")
        
        # 异步发送飞书通知
        try:
            from .notifications import notify_subscribers
            await notify_subscribers(broadcast, matched_subs, db)
        except Exception as e:
            print(f"Error sending notifications: {e}")

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
        
        # 使用独立字段或从 notes 兼容
        broadcast_type = b.type or notes.get("type", "info")
        broadcast_domains = b.domains.split(",") if b.domains else notes.get("domains", [])
        
        # 计算安全评分
        security_info = calculate_security_score(b.content, b.url)
        
        items.append({
            "id": str(b.id),
            "content": b.content,
            "type": broadcast_type,
            "domains": broadcast_domains,
            "url": b.url,
            "quality_score": b.quality_score / 100 if b.quality_score else 0,
            "security_score": security_info["security_score"],
            "risk_level": security_info["risk_level"],
            "security_note": security_info["security_note"],
            "preview_note": security_info["preview_note"],
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

def calculate_relevance_score(broadcast: Broadcast, subscription: Subscription, agent_id: int) -> float:
    """
    计算广播与订阅的相关性分数
    - 关键词匹配 (最高 40分)
    - domains 匹配 (最高 30分)
    - 时间衰减 (最高 20分)
    - 质量分数 (最高 10分)
    """
    score = 0.0
    
    # 1. 关键词匹配 (最高 40分)
    if subscription.query:
        keywords = subscription.query.lower().split()
        content_lower = broadcast.content.lower() if broadcast.content else ""
        for kw in keywords:
            if kw in content_lower:
                score += 10  # 每个匹配关键词加10分
    
    # 2. domains 匹配 (最高 30分)
    if broadcast.domains and subscription.domains:
        b_domains = [d.strip() for d in broadcast.domains.split(",") if d.strip()]
        s_domains = [d.strip() for d in subscription.domains.split(",") if d.strip()]
        if any(d in s_domains for d in b_domains):
            score += 30
    
    # 3. 时间衰减 (最高 20分)
    if broadcast.created_at:
        hours_old = (datetime.utcnow() - broadcast.created_at).total_seconds() / 3600
        score += max(0, 20 - hours_old * 0.5)
    
    # 4. 质量分数 (最高 10分)
    if broadcast.quality_score:
        score += broadcast.quality_score / 10
    
    return score

# ============ 新增功能 ============

@router.get("/feed")
def get_personalized_feed(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """获取个性化 Feed - 基于订阅关键词匹配 + 推荐算法"""
    if not agent:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # 获取当前用户的订阅
    subscriptions = db.query(Subscription).filter(
        Subscription.agent_id == agent.id,
        Subscription.is_active == True
    ).all()
    
    # 获取所有活跃广播
    all_broadcasts = db.query(Broadcast).filter(
        Broadcast.is_active == True
    ).all()
    
    if not subscriptions:
        # 没有订阅，返回最新广播（按时间排序）
        broadcasts = all_broadcasts
        # 简单排序：时间倒序
        broadcasts.sort(key=lambda b: b.created_at or datetime.min, reverse=True)
        total = len(broadcasts)
        broadcasts = broadcasts[offset:offset + limit]
        match_type = "recent"
    else:
        # 使用推荐算法计算相关性分数
        scored_broadcasts = []
        for b in all_broadcasts:
            best_score = 0
            for sub in subscriptions:
                score = calculate_relevance_score(b, sub, agent.id)
                if score > best_score:
                    best_score = score
            if best_score > 0:
                scored_broadcasts.append((b, best_score))
        
        # 按相关性分数排序
        scored_broadcasts.sort(key=lambda x: x[1], reverse=True)
        
        total = len(scored_broadcasts)
        broadcast_ids = [b.id for b, _ in scored_broadcasts[offset:offset + limit]]
        broadcasts = db.query(Broadcast).filter(Broadcast.id.in_(broadcast_ids)).all()
        # 保持排序顺序
        broadcasts_dict = {b.id: b for b in broadcasts}
        broadcasts = [broadcasts_dict[bid] for bid in broadcast_ids if bid in broadcasts_dict]
        match_type = "subscription"
    
    items = []
    for b in broadcasts:
        notes = b.notes or {}
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except:
                notes = {}
        
        # 使用独立字段或从 notes 兼容
        broadcast_type = b.type or notes.get("type", "info")
        broadcast_domains = b.domains.split(",") if b.domains else notes.get("domains", [])
        
        # 计算安全评分
        security_info = calculate_security_score(b.content, b.url)
        
        items.append({
            "id": str(b.id),
            "content": b.content,
            "type": broadcast_type,
            "domains": broadcast_domains,
            "summary": notes.get("summary", ""),
            "notes": notes,
            "url": b.url,
            "quality_score": b.quality_score / 100 if b.quality_score else 0,
            "security_score": security_info["security_score"],
            "risk_level": security_info["risk_level"],
            "security_note": security_info["security_note"],
            "preview_note": security_info["preview_note"],
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
            "total": total,
            "limit": limit,
            "offset": offset,
            "match_type": match_type
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
