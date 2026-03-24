from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import json
import hashlib
import socket
import ipaddress
from urllib.parse import urlparse

from db.database import get_db, Agent, RSSSource

# Token 过期小时数（与服务端一致）
TOKEN_EXPIRE_HOURS = 720  # 30天

router = APIRouter()

# SSRF 防护：阻止的内网域名和 IP 段
BLOCKED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '::1',
]

def is_private_ip(url: str) -> bool:
    """检查 URL 是否指向内网 IP 或域名"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        
        if not hostname:
            return True
        
        # 检查是否在黑名单中
        if hostname.lower() in BLOCKED_HOSTS:
            return True
        
        # 检查是否为本地域名后缀
        if hostname.endswith('.local') or hostname.endswith('.internal') or hostname.endswith('.intra'):
            return True
        
        # 检查是否为 IP
        try:
            ip = ipaddress.ip_address(hostname)
            return ip.is_private
        except ValueError:
            pass
        
        # 解析域名获取 IP
        try:
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private
        except (socket.gaierror, OSError):
            # 无法解析时拒绝
            return True
            
    except Exception:
        # 任何异常都拒绝
        return True

def is_local_request(request: Request) -> bool:
    """检查请求是否来自本地/内网"""
    client_host = request.client.host if request.client else ""
    
    # 允许的内网 IP
    local_ips = ['127.0.0.1', 'localhost', '::1', '0.0.0.0']
    
    if client_host in local_ips:
        return True
    
    # 检查是否为内网 IP
    try:
        ip = ipaddress.ip_address(client_host)
        if ip.is_private:
            return True
    except ValueError:
        pass
    
    # 检查 X-Forwarded-For
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        first_ip = forwarded_for.split(',')[0].strip()
        try:
            ip = ipaddress.ip_address(first_ip)
            if ip.is_private:
                return True
        except ValueError:
            pass
    
    return False

# Schema
class SourceCreate(BaseModel):
    name: str
    url: str
    description: Optional[str] = None
    fetch_interval: int = 3600

class SourceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    fetch_interval: Optional[int] = None
    is_active: Optional[bool] = None

class SourceResponse(BaseModel):
    id: int
    agent_id: Optional[int]
    name: str
    url: str
    description: Optional[str]
    fetch_interval: int
    last_fetch_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

def get_current_agent(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """获取当前认证的 Agent，包含 token 过期检查"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    agent = db.query(Agent).filter(Agent.api_key == token).first()
    
    if agent is None:
        return None
    
    # 检查 token 是否过期 (updated_at + 30天)
    if agent.updated_at:
        expire_time = agent.updated_at + timedelta(hours=TOKEN_EXPIRE_HOURS)
        if datetime.now() > expire_time:
            # Token 已过期，返回特殊标记让前端知道
            return None
    
    return agent

# ============ RSS 源管理 API ============

@router.get("", response_model=dict)
def list_sources(
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """获取 RSS 源列表"""
    query = db.query(RSSSource)
    
    if is_active is not None:
        query = query.filter(RSSSource.is_active == is_active)
    
    sources = query.order_by(RSSSource.created_at.desc()).limit(limit).all()
    
    items = []
    for s in sources:
        items.append({
            "id": s.id,
            "agent_id": s.agent_id,
            "name": s.name,
            "url": s.url,
            "description": s.description,
            "fetch_interval": s.fetch_interval,
            "last_fetch_at": s.last_fetch_at.isoformat() if s.last_fetch_at else None,
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })
    
    return {
        "code": 0,
        "data": {
            "items": items,
            "total": len(items)
        }
    }

@router.post("", response_model=dict)
def create_source(
    source: SourceCreate,
    request: Request,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """添加 RSS 源"""
    # 系统源 (agent_id=null) 只能从本地/内网创建
    if agent is None and not is_local_request(request):
        raise HTTPException(status_code=401, detail="Authentication required for external source creation")
    
    url_hash = hashlib.sha256(source.url.strip().encode()).hexdigest()[:64]
    
    # 检查是否已存在
    existing = db.query(RSSSource).filter(
        (RSSSource.url == source.url) | (RSSSource.url_hash == url_hash)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Source already exists")
    
    new_source = RSSSource(
        agent_id=agent.id if agent else None,
        name=source.name,
        url=source.url,
        url_hash=url_hash,
        description=source.description,
        fetch_interval=source.fetch_interval
    )
    
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    
    return {
        "code": 0,
        "msg": "Source added",
        "data": {
            "id": new_source.id,
            "name": new_source.name,
            "url": new_source.url
        }
    }

@router.get("/{source_id}", response_model=dict)
def get_source(source_id: int, db: Session = Depends(get_db)):
    """获取单个 RSS 源"""
    source = db.query(RSSSource).filter(RSSSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    return {
        "code": 0,
        "data": {
            "id": source.id,
            "agent_id": source.agent_id,
            "name": source.name,
            "url": source.url,
            "description": source.description,
            "fetch_interval": source.fetch_interval,
            "last_fetch_at": source.last_fetch_at.isoformat() if source.last_fetch_at else None,
            "is_active": source.is_active,
            "created_at": source.created_at.isoformat() if source.created_at else None
        }
    }

@router.put("/{source_id}", response_model=dict)
def update_source(
    source_id: int,
    source: SourceUpdate,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """更新 RSS 源"""
    existing = db.query(RSSSource).filter(RSSSource.id == source_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # 只能修改自己创建的源（或者没有agent_id的系统源）
    if agent and existing.agent_id and existing.agent_id != agent.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if source.name is not None:
        existing.name = source.name
    if source.description is not None:
        existing.description = source.description
    if source.fetch_interval is not None:
        existing.fetch_interval = source.fetch_interval
    if source.is_active is not None:
        existing.is_active = source.is_active
    
    db.commit()
    db.refresh(existing)
    
    return {
        "code": 0,
        "msg": "Source updated",
        "data": {
            "id": existing.id,
            "name": existing.name
        }
    }

@router.delete("/{source_id}", response_model=dict)
def delete_source(
    source_id: int,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """删除 RSS 源"""
    existing = db.query(RSSSource).filter(RSSSource.id == source_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # 只能删除自己创建的源
    if agent and existing.agent_id and existing.agent_id != agent.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(existing)
    db.commit()
    
    return {
        "code": 0,
        "msg": "Source deleted"
    }

# ============ RSS 抓取功能 ============

def fetch_rss_feed(url: str) -> dict:
    """简单的 RSS 抓取，包含 SSRF 防护"""
    # SSRF 防护：检查是否为内网 IP
    if is_private_ip(url):
        return {
            "success": False,
            "error": "SSRF blocked: private IP not allowed",
            "items": [],
            "count": 0
        }
    
    try:
        import urllib.request
        import xml.etree.ElementTree as ET
        
        headers = {'User-Agent': 'Synapse/1.0'}
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req, timeout=30)
        content = response.read().decode('utf-8')
        
        # 解析 XML
        root = ET.fromstring(content)
        
        items = []
        # 尝试 RSS 2.0 格式
        channel = root.find('channel')
        if channel is not None:
            for item in channel.findall('item'):
                title = item.find('title')
                link = item.find('link')
                description = item.find('description')
                pubDate = item.find('pubDate')
                
                items.append({
                    "title": title.text if title is not None else "",
                    "link": link.text if link is not None else "",
                    "description": description.text if description is not None else "",
                    "pubDate": pubDate.text if pubDate is not None else ""
                })
        
        return {
            "success": True,
            "items": items,
            "count": len(items)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "items": [],
            "count": 0
        }

@router.post("/{source_id}/fetch", response_model=dict)
def fetch_source(
    source_id: int,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """手动抓取 RSS 源"""
    source = db.query(RSSSource).filter(RSSSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    if not source.is_active:
        raise HTTPException(status_code=400, detail="Source is inactive")
    
    result = fetch_rss_feed(source.url)
    
    # 更新最后抓取时间
    source.last_fetch_at = datetime.utcnow()
    db.commit()
    
    return {
        "code": 0,
        "msg": f"Fetched {result.get('count', 0)} items",
        "data": {
            "items": result.get("items", [])[:10],  # 返回前10条
            "count": result.get("count", 0)
        }
    }
