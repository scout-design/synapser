from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import json

from db.database import get_db, Agent, Subscription

router = APIRouter()

# Token 过期小时数
TOKEN_EXPIRE_HOURS = 720  # 30天

def get_current_agent(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    agent = db.query(Agent).filter(Agent.api_key == token).first()
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # 检查 token 是否过期 (updated_at + 30天)
    if agent.updated_at:
        expire_time = agent.updated_at + timedelta(hours=TOKEN_EXPIRE_HOURS)
        if datetime.now() > expire_time:
            raise HTTPException(status_code=401, detail="Token expired")
    
    return agent

# 每个 Agent 最多订阅数量
MAX_SUBSCRIPTIONS_PER_AGENT = 10

class SubscribeRequest(BaseModel):
    query: str
    domains: Optional[List[str]] = None
    keywords: Optional[str] = None  # 逗号分隔的关键词

@router.post("")
def create_subscription(req: SubscribeRequest, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    """创建订阅"""
    # 检查订阅数量限制
    current_count = db.query(Subscription).filter(Subscription.agent_id == agent.id).count()
    if current_count >= MAX_SUBSCRIPTIONS_PER_AGENT:
        raise HTTPException(
            status_code=400, 
            detail=f"订阅数量已达上限 ({MAX_SUBSCRIPTIONS_PER_AGENT}个)，请先删除不需要的订阅"
        )
    
    sub = Subscription(
        agent_id=agent.id,
        query=req.query,
        keywords=req.keywords,
        domains=req.domains or []
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    
    return {
        "code": 0,
        "msg": "Subscription created",
        "data": {
            "id": str(sub.id),
            "query": sub.query,
            "keywords": sub.keywords
        }
    }

@router.get("")
def get_subscriptions(agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    """获取我的订阅"""
    subs = db.query(Subscription).filter(
        Subscription.agent_id == agent.id,
        Subscription.is_active == True
    ).all()
    
    return {
        "code": 0,
        "data": {
            "subscriptions": [
                {
                    "id": str(s.id),
                    "query": s.query,
                    "keywords": s.keywords,
                    "domains": s.domains or [],
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
                for s in subs
            ]
        }
    }

@router.delete("/{sub_id}")
def delete_subscription(sub_id: str, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    """删除订阅"""
    sub = db.query(Subscription).filter(
        Subscription.id == sub_id,
        Subscription.agent_id == agent.id
    ).first()
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    db.delete(sub)
    db.commit()
    
    return {"code": 0, "msg": "Deleted"}
