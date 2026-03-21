from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import json

from db.database import get_db, Agent, Subscription

router = APIRouter()

def get_current_agent(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    agent = db.query(Agent).filter(Agent.api_key == token).first()
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid token")
    return agent

class SubscribeRequest(BaseModel):
    query: str
    domains: Optional[List[str]] = None

@router.post("")
def create_subscription(req: SubscribeRequest, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    """创建订阅"""
    sub = Subscription(
        agent_id=agent.id,
        query=req.query,
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
            "query": sub.query
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
