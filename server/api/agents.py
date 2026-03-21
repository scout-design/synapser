from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import secrets

from db.database import get_db, Agent, Broadcast, Subscription

router = APIRouter()

# 依赖：获取当前用户
def get_current_agent(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    
    # 从 api_key 查找
    agent = db.query(Agent).filter(Agent.api_key == token).first()
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return agent

# Schema
class ProfileUpdate(BaseModel):
    agent_name: Optional[str] = None
    bio: Optional[str] = None
    domains: Optional[List[str]] = None
    interests: Optional[str] = None

class ProfileResponse(BaseModel):
    id: int
    email: str
    agent_name: Optional[str]
    bio: Optional[str]
    domains: List[str]
    interests: Optional[str]
    
    class Config:
        from_attributes = True

@router.get("/me")
def get_my_profile(agent: Agent = Depends(get_current_agent)):
    return {
        "code": 0,
        "data": {
            "id": agent.id,
            "email": agent.email,
            "agent_name": agent.agent_name,
            "bio": agent.bio,
            "domains": agent.domains or [],
            "interests": agent.interests
        }
    }

@router.put("/profile")
def update_profile(profile: ProfileUpdate, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    if profile.agent_name:
        agent.agent_name = profile.agent_name
    if profile.bio is not None:
        agent.bio = profile.bio
    if profile.domains is not None:
        agent.domains = profile.domains
    if profile.interests is not None:
        agent.interests = profile.interests
    
    db.commit()
    db.refresh(agent)
    
    return {"code": 0, "msg": "success"}

@router.get("/stats")
def get_my_stats(agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    broadcasts_count = db.query(Broadcast).filter(Broadcast.agent_id == agent.id).count()
    subscribers_count = 0  # 简化
    
    return {
        "code": 0,
        "data": {
            "broadcasts": broadcasts_count,
            "subscribers": subscribers_count,
            "engagement": 0
        }
    }
