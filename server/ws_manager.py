import asyncio
from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.agent_connections: Dict[str, WebSocket] = {}  # agent_id -> websocket
    
    async def connect(self, websocket: WebSocket, agent_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if agent_id:
            self.agent_connections[agent_id] = websocket
        
        # 启动心跳任务
        asyncio.create_task(self.keep_alive(websocket, agent_id))
    
    async def keep_alive(self, websocket: WebSocket, agent_id: str = None):
        """心跳保活 - 每30秒发送一次ping"""
        try:
            while True:
                await asyncio.sleep(30)
                try:
                    await websocket.send_json({"type": "ping"})
                except:
                    # 连接已断开
                    break
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
    
    def disconnect(self, websocket: WebSocket, agent_id: str = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if agent_id and agent_id in self.agent_connections:
            del self.agent_connections[agent_id]
    
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.active_connections.remove(conn)

    async def send_to_agent(self, agent_id: str, message: dict):
        """向特定 agent 发送消息"""
        if agent_id in self.agent_connections:
            websocket = self.agent_connections[agent_id]
            try:
                await websocket.send_json(message)
                return True
            except:
                del self.agent_connections[agent_id]
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
        return False


manager = ConnectionManager()


# 客户端重连指引（添加到 WebSocket 端点）
# 客户端应处理：
# 1. 监听 "type": "ping" 消息，回复 {"type": "pong"}
# 2. 如果发送消息后3秒内无响应，自动重连
# 3. 重连时携带上次的 agent_id 以恢复订阅
