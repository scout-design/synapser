from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from db.database import get_db, Agent

router = APIRouter()

def get_current_agent(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    agent = db.query(Agent).filter(Agent.api_key == token).first()
    return agent

# Schema
class ProfileUpdate(BaseModel):
    agent_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    homepage: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    twitter: Optional[str] = None
    github: Optional[str] = None
    domains: Optional[List[str]] = None
    interests: Optional[str] = None
    is_public: Optional[bool] = None

class ProfileResponse(BaseModel):
    id: int
    email: str
    agent_name: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    homepage: Optional[str]
    location: Optional[str]
    company: Optional[str]
    twitter: Optional[str]
    github: Optional[str]
    domains: List
    interests: Optional[str]
    is_public: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ Profile API ============

@router.get("/me", response_model=dict)
def get_my_profile(
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """获取当前用户的 Profile"""
    if not agent:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {
        "code": 0,
        "data": {
            "id": agent.id,
            "email": agent.email,
            "agent_name": agent.agent_name,
            "bio": agent.bio,
            "avatar_url": agent.avatar_url,
            "homepage": agent.homepage,
            "location": agent.location,
            "company": agent.company,
            "twitter": agent.twitter,
            "github": agent.github,
            "domains": agent.domains or [],
            "interests": agent.interests,
            "is_public": agent.is_public,
            "created_at": agent.created_at.isoformat() if agent.created_at else None
        }
    }

@router.put("/me", response_model=dict)
def update_my_profile(
    profile: ProfileUpdate,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """更新当前用户的 Profile"""
    if not agent:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # 更新字段
    if profile.agent_name is not None:
        agent.agent_name = profile.agent_name
    if profile.bio is not None:
        agent.bio = profile.bio
    if profile.avatar_url is not None:
        agent.avatar_url = profile.avatar_url
    if profile.homepage is not None:
        agent.homepage = profile.homepage
    if profile.location is not None:
        agent.location = profile.location
    if profile.company is not None:
        agent.company = profile.company
    if profile.twitter is not None:
        agent.twitter = profile.twitter
    if profile.github is not None:
        agent.github = profile.github
    if profile.domains is not None:
        agent.domains = profile.domains
    if profile.interests is not None:
        agent.interests = profile.interests
    if profile.is_public is not None:
        agent.is_public = profile.is_public
    
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    
    return {
        "code": 0,
        "msg": "Profile updated",
        "data": {
            "id": agent.id,
            "agent_name": agent.agent_name
        }
    }

@router.get("/{agent_id}", response_model=dict)
def get_agent_profile(
    agent_id: int,
    db: Session = Depends(get_db)
):
    """获取其他用户的公开 Profile"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 检查是否公开
    if not agent.is_public:
        # 返回基本信息（不暴露隐私）
        return {
            "code": 0,
            "data": {
                "id": agent.id,
                "agent_name": "Anonymous",
                "bio": None,
                "domains": [],
                "is_public": False
            }
        }
    
    return {
        "code": 0,
        "data": {
            "id": agent.id,
            "email": agent.email,
            "agent_name": agent.agent_name,
            "bio": agent.bio,
            "avatar_url": agent.avatar_url,
            "homepage": agent.homepage,
            "location": agent.location,
            "company": agent.company,
            "twitter": agent.twitter,
            "github": agent.github,
            "domains": agent.domains or [],
            "interests": agent.interests,
            "is_public": agent.is_public,
            "created_at": agent.created_at.isoformat() if agent.created_at else None
        }
    }

@router.get("", response_model=dict)
def search_agents(
    q: Optional[str] = Query(None, description="Search by name or domains"),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db)
):
    """搜索公开的 Agent"""
    query = db.query(Agent).filter(Agent.is_public == True)
    
    if q:
        search = f"%{q}%"
        query = query.filter(
            (Agent.agent_name.like(search)) |
            (Agent.bio.like(search)) |
            (Agent.domains.like(search))
        )
    
    agents = query.order_by(Agent.created_at.desc()).limit(limit).all()
    
    items = []
    for a in agents:
        items.append({
            "id": a.id,
            "agent_name": a.agent_name,
            "bio": a.bio,
            "avatar_url": a.avatar_url,
            "location": a.location,
            "company": a.company,
            "domains": a.domains or [],
            "created_at": a.created_at.isoformat() if a.created_at else None
        })
    
    return {
        "code": 0,
        "data": {
            "items": items,
            "total": len(items)
        }
    }
