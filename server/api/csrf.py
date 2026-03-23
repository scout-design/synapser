"""
CSRF 防护模块
对于使用 Bearer Token 的 API，CSRF 风险较低
但我们提供可选的 CSRF Token 机制
"""
import secrets
from typing import Optional, Tuple

# CSRF Token 存储（生产环境建议用 Redis）
_csrf_tokens = {}

# CSRF Token 有效期（秒）
CSRF_TOKEN_EXPIRE = 3600  # 1小时


def generate_csrf_token(agent_id: int) -> str:
    """
    为指定 Agent 生成 CSRF Token
    """
    token = secrets.token_urlsafe(32)
    _csrf_tokens[token] = {
        'agent_id': agent_id,
        'created_at': __import__('time').time()
    }
    return token


def verify_csrf_token(token: str, agent_id: int) -> bool:
    """
    验证 CSRF Token
    返回 True 如果有效，否则返回 False
    """
    if not token or token not in _csrf_tokens:
        return False
    
    stored = _csrf_tokens[token]
    
    # 检查 agent_id 是否匹配
    if stored['agent_id'] != agent_id:
        return False
    
    # 检查是否过期
    if __import__('time').time() - stored['created_at'] > CSRF_TOKEN_EXPIRE:
        del _csrf_tokens[token]
        return False
    
    # Token 只能使用一次（用完删除）
    del _csrf_tokens[token]
    return True


def get_csrf_token_for_agent(agent_id: int) -> Optional[str]:
    """
    获取最新的未使用的 CSRF Token
    如果没有或已过期，返回 None
    """
    for token, data in list(_csrf_tokens.items()):
        if data['agent_id'] == agent_id:
            if __import__('time').time() - data['created_at'] <= CSRF_TOKEN_EXPIRE:
                return token
            else:
                del _csrf_tokens[token]
    return None


def cleanup_expired_tokens():
    """
    清理过期的 CSRF Token
    应该定期调用
    """
    now = __import__('time').time()
    expired = [t for t, d in _csrf_tokens.items() 
               if now - d['created_at'] > CSRF_TOKEN_EXPIRE]
    for t in expired:
        del _csrf_tokens[t]
