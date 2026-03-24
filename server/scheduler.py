"""
定时任务调度器 - RSS 自动抓取
"""
import asyncio
import hashlib
import logging
import socket
import ipaddress
from datetime import datetime, timedelta
from typing import List, Dict, Any
from urllib.parse import urlparse

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from db.database import SessionLocal, Broadcast, RSSSource
from ws_manager import manager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 调度器实例
_scheduler = None

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


def hash_title(title: str) -> str:
    """对标题进行哈希用于去重"""
    return hashlib.sha256(title.strip().encode()).hexdigest()[:64]


async def fetch_single_rss_source(source: RSSSource, db) -> List[Dict]:
    """抓取单个 RSS 源，包含 SSRF 防护"""
    # SSRF 防护：检查是否为内网 IP
    if is_private_ip(source.url):
        logger.warning(f"SSRF blocked: private IP not allowed for {source.url}")
        return []
    
    try:
        import urllib.request
        import xml.etree.ElementTree as ET
        
        headers = {'User-Agent': 'Synapse/1.0 (RSS Fetcher)'}
        req = urllib.request.Request(source.url, headers=headers)
        response = urllib.request.urlopen(req, timeout=30)
        content = response.read().decode('utf-8')
        
        root = ET.fromstring(content)
        items = []
        
        channel = root.find('channel')
        if channel is not None:
            for item in channel.findall('item'):
                title = item.find('title')
                link = item.find('link')
                description = item.find('description')
                pubDate = item.find('pubDate')
                
                title_text = title.text if title is not None else ""
                link_text = link.text if link is not None else ""
                desc_text = description.text if description is not None else ""
                
                items.append({
                    "title": title_text,
                    "link": link_text,
                    "description": desc_text[:200] if desc_text else "",  # 截取前200字符
                    "pubDate": pubDate.text if pubDate is not None else ""
                })
        
        return items
        
    except Exception as e:
        logger.error(f"抓取 RSS 源失败 {source.url}: {e}")
        return []


async def publish_rss_item_as_broadcast(item: Dict, source: RSSSource, db) -> bool:
    """将 RSS 项发布为广播"""
    try:
        # 生成内容
        content = f"【{source.name}】{item['title']}"
        if item['description']:
            content += f"\n\n{item['description']}"
        if item['link']:
            content += f"\n\n链接: {item['link']}"
        
        # 标题哈希去重（RSS 可能没有 URL）
        title_hash = hash_title(item['title'])
        
        # 检查是否已存在相同标题的广播（最近24小时内）
        yesterday = datetime.now() - timedelta(hours=24)
        existing = db.query(Broadcast).filter(
            Broadcast.content.like(f"%{item['title'][:50]}%"),
            Broadcast.created_at >= yesterday
        ).first()
        
        if existing:
            logger.info(f"跳过重复: {item['title'][:30]}...")
            return False
        
        # 创建广播
        # type 根据来源判断，domains 使用源名称
        new_broadcast = Broadcast(
            agent_id=source.agent_id or 1,  # 系统源用 agent_id=1
            content=content,
            notes={"source": "rss", "source_name": source.name},
            type="info",
            domains=source.name,
            source_type="aggregated",
            url=item['link'] if item['link'] else None,
            url_hash=title_hash if not item['link'] else None,
            quality_score=60,  # RSS 来源默认 0.6
            views=0,
            likes=0,
            is_active=True,
            created_at=datetime.now()
        )
        
        db.add(new_broadcast)
        db.commit()
        
        # WebSocket 广播通知所有客户端
        await manager.broadcast({
            "type": "new_broadcast",
            "data": {
                "id": str(new_broadcast.id),
                "content": new_broadcast.content,
                "type": new_broadcast.type,
                "agent_name": "System",
                "agent_id": new_broadcast.agent_id,
                "created_at": new_broadcast.created_at.isoformat() if new_broadcast.created_at else None
            }
        })
        
        logger.info(f"发布 RSS 广播: {item['title'][:30]}...")
        return True
        
    except Exception as e:
        logger.error(f"发布 RSS 广播失败: {e}")
        db.rollback()
        return False


async def fetch_rss_sources():
    """定时抓取所有活跃的 RSS 源"""
    logger.info("开始 RSS 定时抓取...")
    
    db = SessionLocal()
    try:
        # 查找所有活跃且该抓取的源
        now = datetime.now()
        sources = db.query(RSSSource).filter(
            RSSSource.is_active == True
        ).all()
        
        new_count = 0
        for source in sources:
            # 检查是否到了抓取时间
            if source.last_fetch_at:
                next_fetch = source.last_fetch_at + timedelta(seconds=source.fetch_interval)
                if now < next_fetch:
                    continue  # 还没到时间
            
            # 抓取
            items = await fetch_single_rss_source(source, db)
            
            if items:
                # 发布新项
                for item in items[:10]:  # 最多处理10条
                    if await publish_rss_item_as_broadcast(item, source, db):
                        new_count += 1
            
            # 更新最后抓取时间
            source.last_fetch_at = now
            db.commit()
        
        if new_count > 0:
            logger.info(f"RSS 抓取完成，新增 {new_count} 条广播")
        else:
            logger.info("RSS 抓取完成，无新内容")
            
    except Exception as e:
        logger.error(f"RSS 定时任务失败: {e}")
    finally:
        db.close()


def start_scheduler():
    """启动调度器"""
    global _scheduler
    
    if _scheduler is not None:
        logger.warning("调度器已启动，忽略重复调用")
        return
    
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        fetch_rss_sources,
        IntervalTrigger(seconds=60),  # 每分钟检查一次
        id='rss_fetch',
        name='RSS 定时抓取'
    )
    _scheduler.start()
    logger.info("RSS 调度器已启动")


def stop_scheduler():
    """停止调度器"""
    global _scheduler
    
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("RSS 调度器已停止")
