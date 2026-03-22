"""
日志脱敏工具模块
用于过滤日志中的敏感信息
"""
import re
import json
from typing import Any, Dict, Union
from datetime import datetime


# ==================== 敏感字段列表 ====================

# 需要脱敏的字段名
SENSITIVE_FIELDS = {
    "password",
    "token",
    "api_key",
    "apikey",
    "apiKey",
    "email",
    "code",
    "secret",
    "secret_key",
    "access_token",
    "refresh_token",
    "session_id",
    "session",
    "cookie",
    "authorization",
    "auth",
    "private_key",
    "public_key",
    "credit_card",
    "card_number",
    "cvv",
    "pin",
    "phone",
    "mobile",
    "address",
    "ssn",
    "national_id",
}

# 敏感值替换符
MASK = "***"


# ==================== 脱敏函数 ====================

def sanitize_value(value: Any) -> Any:
    """
    对单个值进行脱敏处理
    如果值是字符串且长度 > 3，则替换为 MASK
    否则直接返回原值
    """
    if isinstance(value, str):
        if len(value) > 3:
            return MASK
        return value
    elif isinstance(value, dict):
        return sanitize_dict(value)
    elif isinstance(value, list):
        return sanitize_list(value)
    return value


def sanitize_dict(data: Dict) -> Dict:
    """
    对字典进行脱敏处理
    过滤敏感字段，替换敏感值
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        # 检查字段名是否敏感
        key_lower = key.lower()
        if key_lower in SENSITIVE_FIELDS:
            result[key] = MASK
        else:
            result[key] = sanitize_value(value)
    
    return result


def sanitize_list(data: list) -> list:
    """对列表进行脱敏处理"""
    if not isinstance(data, list):
        return data
    return [sanitize_value(item) for item in data]


def sanitize_object(obj: Any) -> Any:
    """
    对任意对象进行脱敏处理
    支持 dict, list, str, int, float, bool, None
    """
    if obj is None:
        return None
    elif isinstance(obj, dict):
        return sanitize_dict(obj)
    elif isinstance(obj, list):
        return sanitize_list(obj)
    elif isinstance(obj, str):
        return sanitize_value(obj)
    else:
        # 基本类型直接返回
        return obj


def sanitize_json_string(json_str: str) -> str:
    """
    对 JSON 字符串进行脱敏处理
    """
    if not json_str:
        return json_str
    
    try:
        # 尝试解析为 JSON
        data = json.loads(json_str)
        sanitized = sanitize_object(data)
        return json.dumps(sanitized, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        # 如果不是有效 JSON，尝试当作普通字符串处理
        return sanitize_value(json_str)


# ==================== 日志格式化 ====================

def format_log_data(**kwargs) -> Dict:
    """
    格式化日志数据，自动脱敏
    用法: log_data = format_log_data(user="test", password="secret", data={"token": "abc"})
    """
    result = {}
    for key, value in kwargs.items():
        key_lower = key.lower()
        if key_lower in SENSITIVE_FIELDS:
            result[key] = MASK
        else:
            result[key] = sanitize_value(value)
    return result


def log_with_sanitization(logger, level: str, message: str, **kwargs):
    """
    带自动脱敏的日志记录
    用法: log_with_sanitization(logger, "info", "User login", username="test", password="secret")
    """
    log_data = format_log_data(**kwargs)
    
    if level.lower() == "debug":
        logger.debug(message, extra=log_data)
    elif level.lower() == "info":
        logger.info(message, extra=log_data)
    elif level.lower() == "warning":
        logger.warning(message, extra=log_data)
    elif level.lower() == "error":
        logger.error(message, extra=log_data)
    elif level.lower() == "critical":
        logger.critical(message, extra=log_data)


# ==================== 便捷函数 ====================

def mask_sensitive_data(data: Union[Dict, str, list]) -> Union[Dict, str, list]:
    """
    统一的脱敏入口函数
    """
    if isinstance(data, str):
        # 尝试解析 JSON
        if data.strip().startswith(("{", "[")):
            return sanitize_json_string(data)
        return sanitize_value(data)
    return sanitize_object(data)


def sanitize_request_body(body: Any) -> Any:
    """
    对请求体进行脱敏
    常用于日志记录请求体
    """
    return mask_sensitive_data(body)


def sanitize_response_body(body: Any) -> Any:
    """
    对响应体进行脱敏
    常用于日志记录响应体
    """
    return mask_sensitive_data(body)


# ==================== 特定场景辅助 ====================

def sanitize_user_info(user_info: Dict) -> Dict:
    """
    专门对用户信息进行脱敏
    """
    sensitive_keys = {"password", "token", "api_key", "email", "phone", "address", "ssn"}
    
    result = {}
    for key, value in user_info.items():
        if key.lower() in sensitive_keys:
            result[key] = MASK
        else:
            result[key] = sanitize_value(value)
    
    return result


def sanitize_auth_request(data: Dict) -> Dict:
    """
    专门对认证请求进行脱敏
    如 login, register, reset password 等
    """
    return sanitize_dict(data)
