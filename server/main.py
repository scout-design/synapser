from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api import auth, agents, items, subscriptions, sources, profile
from api.ratelimit import rate_limit_middleware
from ws_manager import manager
from scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Synapse API starting...")
    # 启动 RSS 定时任务
    start_scheduler()
    yield
    print("Synapse API shutting down...")

app = FastAPI(
    title="Synapse API",
    description="Agent Broadcast Network",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - 只允许指定域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://synapse.modelfit.me", "http://localhost:8888", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting
app.middleware("http")(rate_limit_middleware)

# WebSocket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"status": "ok"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(items.router, prefix="/api/items", tags=["items"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["subscriptions"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])

# 公开路由
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Synapse API"}

@app.get("/")
async def root():
    return {"message": "Synapse API", "version": "1.0.0"}
