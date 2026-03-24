"""
飞书通知模块 - 推送广播通知到用户的飞书
"""
import asyncio
import httpx
from sqlalchemy.orm import Session
from typing import Optional

from db.database import Agent, Subscription, Broadcast

# 飞书应用配置（留空则跳过通知）
FEISHU_APP_ID = ""
FEISHU_APP_SECRET = ""

# Scout 的飞书 ID（用于测试）
SCOUT_FEISHU_OPEN_ID = "ou_1046564380d7e144e6429e7627a0a3f9"


async def get_feishu_access_token() -> Optional[str]:
    """获取飞书应用访问令牌"""
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        return None  # 未配置飞书，跳过
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10)
            data = response.json()
            if data.get("code") == 0:
                return data.get("tenant_access_token")
    except Exception as e:
        print(f"Failed to get Feishu access token: {e}")
    return None


async def send_feishu_message(
    open_id: str,
    content: str,
    msg_type: str = "text"
) -> bool:
    """发送飞书消息"""
    token = await get_feishu_access_token()
    if not token:
        print("Failed to get Feishu access token")
        return False
    
    # receive_id_type 是 URL 查询参数，不是 body 字段
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    # 构建消息内容
    if msg_type == "text":
        payload = {
            "receive_id": open_id,
            "msg_type": "text",
            "content": '{"text": "' + content.replace('"', '\\"') + '"}'
        }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10)
            data = response.json()
            if data.get("code") == 0:
                return True
            else:
                print(f"Failed to send Feishu message: {data}")
    except Exception as e:
        print(f"Error sending Feishu message: {e}")
    
    return False


async def notify_agent_of_match(
    agent_id: int,
    broadcast_content: str,
    broadcast_id: int,
    db: Session
):
    """通知用户有匹配的广播（异步，不阻塞响应）"""
    
    # 获取用户的飞书 ID
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        return
    
    # 从 agent 的 extra_info 或其他字段获取飞书 ID
    # 这里暂时使用模拟逻辑，实际应该存在数据库中
    feishu_open_id = getattr(agent, "feishu_open_id", None)
    
    if not feishu_open_id:
        # 如果没有绑定飞书 ID，跳过
        print(f"Agent {agent_id} has no Feishu Open ID, skipping notification")
        return
    
    # 截取内容摘要
    content_preview = broadcast_content[:100] + "..." if len(broadcast_content) > 100 else broadcast_content
    
    # 构建消息
    message = f"🔔 您有新的广播匹配！\n\n{content_preview}\n\n点击查看详情 →"
    
    # 异步发送（不阻塞主流程）
    try:
        await send_feishu_message(feishu_open_id, message)
        print(f"📨 Sent Feishu notification to agent {agent_id}")
    except Exception as e:
        print(f"Failed to send notification: {e}")


async def notify_subscribers(
    broadcast: Broadcast,
    matched_subscriptions: list,
    db: Session
):
    """
    批量通知订阅者
    
    Args:
        broadcast: 广播对象
        matched_subscriptions: 匹配的订阅列表
        db: 数据库会话
    """
    if not matched_subscriptions:
        return
    
    # 为每个匹配的订阅者发送通知
    tasks = []
    for sub in matched_subscriptions:
        task = notify_agent_of_match(
            agent_id=sub.agent_id,
            broadcast_content=broadcast.content,
            broadcast_id=broadcast.id,
            db=db
        )
        tasks.append(task)
    
    # 并发执行（不阻塞）
    await asyncio.gather(*tasks, return_exceptions=True)


async def test_send_to_scout():
    """测试发送消息给 Scout"""
    message = "🔗 Synapse 测试消息 - 您的 AI 广播网络已连接！"
    return await send_feishu_message(SCOUT_FEISHU_OPEN_ID, message)


# 简单的同步版本（用于直接调用）
def send_notification_sync(
    agent_id: int,
    broadcast_content: str,
    broadcast_id: int,
    db: Session
):
    """同步版本的通知（内部使用）"""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # 如果在异步环境中，创建新任务
        asyncio.create_task(
            notify_agent_of_match(agent_id, broadcast_content, broadcast_id, db)
        )
    else:
        # 如果不在异步环境，同步执行
        loop.run_until_complete(
            notify_agent_of_match(agent_id, broadcast_content, broadcast_id, db)
        )
