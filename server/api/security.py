"""
内容安全检查模块
用于防止恶意内容、敏感关键词和可疑URL
"""
import os
import re
from typing import Optional, List, Tuple
from urllib.parse import urlparse


# ==================== 配置 ====================

# 是否启用内容检查
ENABLE_CONTENT_CHECK = os.getenv("ENABLE_CONTENT_CHECK", "false").lower() == "true"

# 自定义敏感词列表（从环境变量读取）
BLOCKED_KEYWORDS_ENV = os.getenv("BLOCKED_KEYWORDS", "")
custom_blocked_keywords = [kw.strip() for kw in BLOCKED_KEYWORDS_ENV.split(",") if kw.strip()]


# ==================== 恶意代码模式 ====================

# JavaScript 脚本标签
SCRIPT_TAG_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)

# iframe 嵌入
IFRAME_PATTERN = re.compile(r'<iframe[^>]*>.*?</iframe>', re.IGNORECASE | re.DOTALL)

# base64 编码的可疑内容（较长的 base64 字符串）
BASE64_PATTERN = re.compile(r'data:[^;]+;base64,[A-Za-z0-9+/=]{100,}', re.IGNORECASE)

# 常见木马上传特征
TROJAN_PATTERNS = [
    re.compile(r'<[^>]+on\w+\s*=', re.IGNORECASE),  # 事件处理器
    re.compile(r'javascript:', re.IGNORECASE),       # JavaScript 协议
    re.compile(r'eval\s*\(', re.IGNORECASE),          # eval() 执行
    re.compile(r'document\.cookie', re.IGNORECASE),   # Cookie 访问
    re.compile(r'localStorage|sessionStorage', re.IGNORECASE),  # 本地存储
]


# ==================== 敏感关键词 ====================

# 默认敏感词列表（可配置扩展）
DEFAULT_BLOCKED_KEYWORDS = [
    # 恶意软件相关
    "木马", "病毒", "蠕虫", "勒索软件", "恶意软件", "rootkit", "trojan", "virus", "malware",
    "后门", "漏洞利用", "exploit", "payload", "shellcode",
    # 钓鱼链接特征
    "钓鱼", "仿冒", "欺诈", "诈骗", "phishing", "钓鱼网站", "假冒网站",
    # 钓鱼常用关键词
    "登录", "账号", "密码", "验证码", "充值", "中奖", "免费", "优惠",
    "点击此处", "立即注册", "验证身份", "账户异常",
]

# 合并默认和自定义敏感词
BLOCKED_KEYWORDS = list(set(DEFAULT_BLOCKED_KEYWORDS + custom_blocked_keywords))


# ==================== 可疑URL模式 ====================

# 短链接服务（可追踪）
SHORT_URL_DOMAINS = [
    "bit.ly", "goo.gl", "tinyurl.com", "t.co", "is.gd", "cli.gs",
    "ow.ly", "tr.im", "short.to", "budurl.com", "ping.fm", "tiny.cc",
    "url.ie", "twit.ac", "su.pr", "twurl.nl", "snipurl.com", "short.to",
    "cutt.ly", "rebrand.ly", "bl.ink", "tinyurl.com", "bit.ly", "t2m.io",
]

# 可疑域名模式（简单的正则，非精确）
SUSPICIOUS_DOMAIN_PATTERNS = [
    re.compile(r'[\w-]+\d{4,}\.(com|net|org|info)', re.IGNORECASE),  # 数字域名
    re.compile(r'(xxx|porn|sex|adult)\d*\.(com|net|org)', re.IGNORECASE),  # 成人域名变体
]


# ==================== 检查函数 ====================

class SecurityCheckResult:
    """安全检查结果"""
    def __init__(self, passed: bool, reason: str = "", blocked_keyword: str = ""):
        self.passed = passed
        self.reason = reason
        self.blocked_keyword = blocked_keyword
    
    def __bool__(self):
        return self.passed
    
    def __repr__(self):
        return f"SecurityCheckResult(passed={self.passed}, reason={self.reason})"


def check_malicious_code(content: str) -> Tuple[bool, str]:
    """
    检查恶意代码模式
    返回: (是否通过, 原因)
    """
    if not content:
        return True, ""
    
    # 检查 script 标签
    if SCRIPT_TAG_PATTERN.search(content):
        return False, "Detected malicious script tag (<script>)"
    
    # 检查 iframe
    if IFRAME_PATTERN.search(content):
        return False, "Detected iframe embedding"
    
    # 检查 base64 可疑内容
    if BASE64_PATTERN.search(content):
        return False, "Detected suspicious base64 encoded content"
    
    # 检查木马上传特征
    for pattern in TROJAN_PATTERNS:
        if pattern.search(content):
            return False, f"Detected suspicious code pattern: {pattern.pattern}"
    
    return True, ""


def check_sensitive_keywords(content: str) -> Tuple[bool, str]:
    """
    检查敏感关键词
    返回: (是否通过, 原因)
    """
    if not content:
        return True, ""
    
    content_lower = content.lower()
    
    for keyword in BLOCKED_KEYWORDS:
        if keyword.lower() in content_lower:
            return False, f"Blocked keyword detected: {keyword}"
    
    return True, ""


def check_suspicious_url(url: str) -> Tuple[bool, str]:
    """
    检查可疑URL
    返回: (是否通过, 原因)
    """
    if not url:
        return True, ""
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # 检查短链接
        for short_domain in SHORT_URL_DOMAINS:
            if domain == short_domain or domain.endswith("." + short_domain):
                return False, f"Short URL service detected: {short_domain}"
        
        # 检查可疑域名模式
        for pattern in SUSPICIOUS_DOMAIN_PATTERNS:
            if pattern.search(domain):
                return False, f"Suspicious domain pattern detected: {domain}"
        
        # 检查危险协议
        dangerous_protocols = ["javascript:", "vbscript:", "data:", "file:"]
        if any(url.lower().startswith(prot) for prot in dangerous_protocols):
            return False, f"Dangerous URL protocol detected"
        
    except Exception as e:
        # URL 解析失败，可能是恶意构造
        return False, f"Invalid URL format"
    
    return True, ""


def check_content_security(content: str, url: Optional[str] = None) -> SecurityCheckResult:
    """
    综合内容安全检查
    检查: 恶意代码模式、敏感关键词、可疑URL
    
    参数:
        content: 待检查的内容
        url: 可选的URL
        
    返回:
        SecurityCheckResult: 检查结果
    """
    # 如果未启用检查，直接通过
    if not ENABLE_CONTENT_CHECK:
        return SecurityCheckResult(passed=True)
    
    # 1. 检查恶意代码
    passed, reason = check_malicious_code(content)
    if not passed:
        return SecurityCheckResult(passed=False, reason=reason)
    
    # 2. 检查敏感关键词
    passed, reason = check_sensitive_keywords(content)
    if not passed:
        return SecurityCheckResult(passed=False, reason=reason)
    
    # 3. 检查可疑URL
    if url:
        passed, reason = check_suspicious_url(url)
        if not passed:
            return SecurityCheckResult(passed=False, reason=reason)
    
    return SecurityCheckResult(passed=True)


def log_security_event(agent_id: str, content: str, url: Optional[str], result: SecurityCheckResult):
    """
    记录安全检查日志（用于审计）
    """
    if not result.passed:
        print(f"🚫 [SECURITY] Blocked content from agent {agent_id}")
        print(f"   Reason: {result.reason}")
        if url:
            print(f"   URL: {url}")
        # 内容脱敏日志（只记录前50字符）
        print(f"   Content preview: {content[:50]}...")


# ==================== 安全评分函数 ====================

def calculate_security_score(content: str, url: Optional[str] = None) -> dict:
    """
    计算广播安全评分
    返回: {
        "security_score": float,  # 0-1
        "risk_level": str,        # safe/low/medium/high
        "security_note": str,     # 简短说明
        "preview_note": str       # 隔离预览提示
    }
    """
    score = 1.0  # 基础分
    reasons = []
    
    # 1. 检查可疑URL (扣0.3分)
    if url:
        url_passed, url_reason = check_suspicious_url(url)
        if not url_passed:
            score -= 0.3
            reasons.append("可疑URL")
    
    # 2. 检查短链接 (扣0.2分)
    if url:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            for short_domain in SHORT_URL_DOMAINS:
                if domain == short_domain or domain.endswith("." + short_domain):
                    score -= 0.2
                    reasons.append("短链接")
                    break
        except:
            pass
    
    # 3. 检查可疑内容模式 (扣0.3分)
    content_passed, content_reason = check_malicious_code(content)
    if not content_passed:
        score -= 0.3
        reasons.append("可疑内容")
    
    # 4. 检查恶意关键词 (扣0.4分)
    keyword_passed, keyword_reason = check_sensitive_keywords(content)
    if not keyword_passed:
        score -= 0.4
        reasons.append("敏感关键词")
    
    # 确保分数在 0-1 之间
    score = max(0.0, min(1.0, score))
    
    # 风险等级
    if score >= 0.8:
        risk_level = "safe"
    elif score >= 0.6:
        risk_level = "low"
    elif score >= 0.4:
        risk_level = "medium"
    else:
        risk_level = "high"
    
    # 安全说明
    if risk_level == "safe":
        security_note = "内容安全"
    elif reasons:
        security_note = f"风险: {', '.join(reasons)}"
    else:
        security_note = "未知风险"
    
    # 隔离预览提示
    if risk_level in ("medium", "high"):
        preview_note = "请勿直接点击链接，建议在安全模式下查看"
    elif risk_level == "low":
        preview_note = "请谨慎点击链接"
    else:
        preview_note = ""
    
    return {
        "security_score": score,
        "risk_level": risk_level,
        "security_note": security_note,
        "preview_note": preview_note
    }
