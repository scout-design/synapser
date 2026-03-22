"""
Rate Limiting Module
基于 IP + API 路径的请求频率限制
"""
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, Tuple
from fastapi import HTTPException, Request, Response


# ==================== 限制规则配置 ====================

# 限制规则: 路径 -> (请求数, 时间窗口秒数)
RATE_LIMIT_RULES = {
    "/api/auth/login": (5, 60),        # 5次/分钟
    "/api/items": (10, 60),           # POST /api/items: 10次/分钟
    # 其他写操作: 30次/分钟 (默认)
    # 读操作: 60次/分钟 (默认)
}

# 默认限制
DEFAULT_WRITE_LIMIT = (30, 60)   # 30次/分钟
DEFAULT_READ_LIMIT = (60, 60)    # 60次/分钟


# ==================== 内存存储 ====================

class RateLimitStore:
    """内存级限流存储"""
    def __init__(self):
        # 结构: { "ip_path": [(timestamp, count), ...] }
        self._store: Dict[str, list] = defaultdict(list)
        # 定期清理过期记录
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # 每60秒清理一次
    
    def _make_key(self, ip: str, path: str) -> str:
        return f"{ip}:{path}"
    
    def _cleanup_expired(self):
        """清理过期记录"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        current_time = int(now)
        for key in list(self._store.keys()):
            # 清理超过2分钟的记录
            self._store[key] = [
                ts for ts in self._store[key]
                if current_time - ts < 120
            ]
            # 删除空列表
            if not self._store[key]:
                del self._store[key]
        
        self._last_cleanup = now
    
    def check(self, ip: str, path: str, method: str = "GET") -> Tuple[bool, int]:
        """
        检查是否超限
        返回: (是否允许, 剩余请求数)
        """
        self._cleanup_expired()
        
        now = int(time.time())
        key = self._make_key(ip, path)
        
        # 确定限制规则
        limit, window = self._get_limit_rule(path, method)
        
        # 获取当前窗口内的请求记录
        requests = self._store[key]
        
        # 统计当前窗口内的请求数
        current_count = sum(1 for ts in requests if now - ts < window)
        
        if current_count >= limit:
            return False, 0
        
        # 记录本次请求
        self._store[key].append(now)
        
        return True, limit - current_count - 1
    
    def _get_limit_rule(self, path: str, method: str) -> Tuple[int, int]:
        """获取路径的限制规则"""
        # 精确匹配
        if path in RATE_LIMIT_RULES:
            return RATE_LIMIT_RULES[path]
        
        # 前缀匹配
        for rule_path, rule_limit in RATE_LIMIT_RULES.items():
            if path.startswith(rule_path):
                return rule_limit
        
        # 根据方法默认
        if method.upper() in ("POST", "PUT", "DELETE", "PATCH"):
            return DEFAULT_WRITE_LIMIT
        else:
            return DEFAULT_READ_LIMIT


# 全局存储实例
_rate_limit_store = RateLimitStore()


# ==================== 依赖项 ====================

async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI 中间件形式的限流检查
    """
    # 获取客户端IP
    client_ip = get_client_ip(request)
    
    # 排除 WebSocket 和健康检查
    if request.url.path in ("/ws", "/api/health", "/"):
        return await call_next(request)
    
    # 获取路径和方法
    path = request.url.path
    method = request.method
    
    # 检查是否超限
    allowed, remaining = _rate_limit_store.check(client_ip, path, method)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    
    # 添加速率限制响应头
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(_rate_limit_store._get_limit_rule(path, method)[0])
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    return response


def get_client_ip(request: Request) -> str:
    """获取客户端IP"""
    # 优先从 X-Forwarded-For 获取
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    
    # 其次从 X-Real-IP 获取
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()
    
    # 最后使用客户端host
    if request.client:
        return request.client.host
    
    return "unknown"


# ==================== 便捷函数 ====================

def check_rate_limit(ip: str, path: str, method: str = "GET") -> Tuple[bool, int]:
    """
    手动检查限流（用于特定端点的精细控制）
    返回: (是否允许, 剩余请求数)
    """
    return _rate_limit_store.check(ip, path, method)
