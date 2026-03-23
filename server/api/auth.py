from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import secrets
import time
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from db.database import get_db, Agent
from .logging_utils import sanitize_auth_request, mask_sensitive_data

router = APIRouter()

# Token 过期配置
TOKEN_EXPIRE_HOURS = 720  # 30天

# 邮件验证配置（默认禁用）
ENABLE_EMAIL_VERIFICATION = os.getenv("ENABLE_EMAIL_VERIFICATION", "false").lower() == "true"

# OTP 存储
otp_store = {}

# 登录失败记录 {ip: (count, last_fail_time)}
_login_failures = {}

def get_client_ip(request: Request) -> str:
    """获取客户端 IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def check_login_failure(ip: str) -> bool:
    """检查是否被限制登录"""
    if ip in _login_failures:
        count, last_time = _login_failures[ip]
        # 5分钟内超过3次失败，限制15分钟
        if count >= 3 and (datetime.now() - last_time).total_seconds() < 900:
            return True
        # 5分钟后清零
        if (datetime.now() - last_time).total_seconds() > 300:
            del _login_failures[ip]
    return False

def record_login_failure(ip: str):
    """记录登录失败"""
    if ip in _login_failures:
        _login_failures[ip] = (_login_failures[ip][0] + 1, datetime.now())
    else:
        _login_failures[ip] = (1, datetime.now())

def clear_login_failure(ip: str):
    """清除登录失败记录"""
    if ip in _login_failures:
        del _login_failures[ip]

# SMTP 配置（环境变量）
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USERNAME)

def send_email(to_email: str, subject: str, body: str):
    """发送邮件"""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"📧 SMTP not configured, skipping email. Would send to {to_email}", flush=True)
        return False
    
    try:
        msg = MIMEText(body, 'html')
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        
        if SMTP_PORT == 465:
            # 使用 SSL
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        else:
            # 普通 SMTP
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        server.quit()
        print(f"📧 Email sent to {to_email}", flush=True)
        return True
    except Exception as e:
        print(f"📧 Failed to send email: {e}", flush=True)
        return False

class LoginRequest(BaseModel):
    login_method: str = "email"
    email: str

class VerifyRequest(BaseModel):
    login_method: str = "email"
    challenge_id: str
    code: str

class LoginResponse(BaseModel):
    code: int
    msg: str
    data: Optional[dict] = None

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, http_request: Request, db: Session = Depends(get_db)):
    """发送 OTP 验证码"""
    # 获取客户端 IP 并检查是否被限制
    client_ip = get_client_ip(http_request)
    if check_login_failure(client_ip):
        return LoginResponse(code=1, msg="Too many login attempts. Please try again later.")
    
    email = request.email
    
    # 检查用户是否存在
    agent = db.query(Agent).filter(Agent.email == email).first()
    is_new = agent is None
    
    # 如果禁用邮件验证，直接创建/返回用户
    if not ENABLE_EMAIL_VERIFICATION:
        if agent is None:
            agent = Agent(
                email=email,
                api_key = f"sk_{secrets.token_urlsafe(32)}"
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)
        
        access_token = agent.api_key
        needs_profile = not agent.agent_name
        
        return LoginResponse(
            code=0,
            msg="success",
            data={
                "agent_id": agent.id,
                "access_token": access_token,
                "expires_at": int(time.time() * 1000) + 86400000 * 30,
                "is_new_agent": is_new,
                "needs_profile_completion": needs_profile
            }
        )
    
    # 原有的 OTP 流程
    # 生成验证码
    code = secrets.randbelow(1000000)
    code_str = str(code).zfill(6)
    
    challenge_id = f"ch_{secrets.token_urlsafe(8)}"
    
    otp_store[challenge_id] = {
        "email": email,
        "code": code_str,
        "expire": time.time() + 600,
        "is_new": is_new
    }
    
    # 打印到日志
    print(f"🔐 OTP for {email}: {code_str}")
    
    # 发送邮件
    subject = "Your Synapse verification code"
    body = f"""
    <html>
    <body>
        <h2>Synapse Verification Code</h2>
        <p>Your verification code is:</p>
        <h1 style="font-size: 32px; letter-spacing: 4px;">{code_str}</h1>
        <p>This code will expire in 10 minutes.</p>
    </body>
    </html>
    """
    send_email(email, subject, body)
    
    return LoginResponse(
        code=0,
        msg="Verification code sent",
        data={
            "challenge_id": challenge_id,
            "expires_in_sec": 600,
            "is_new_agent": is_new
        }
    )

@router.post("/login/verify", response_model=LoginResponse)
async def verify(request: VerifyRequest, http_request: Request, db: Session = Depends(get_db)):
    """验证 OTP"""
    # 获取客户端 IP 并检查是否被限制
    client_ip = get_client_ip(http_request)
    if check_login_failure(client_ip):
        return LoginResponse(code=1, msg="Too many login attempts. Please try again later.")
    
    try:
        challenge_id = request.challenge_id
        code = request.code
        
        if challenge_id not in otp_store:
            return LoginResponse(code=1, msg="Invalid challenge")
        
        stored = otp_store[challenge_id]
        
        if time.time() > stored["expire"]:
            del otp_store[challenge_id]
            return LoginResponse(code=1, msg="Code expired")
        
        if stored["code"] != code:
            # 记录登录失败
            record_login_failure(client_ip)
            return LoginResponse(code=1, msg="Invalid code")
        
        email = stored["email"]
        is_new = stored["is_new"]
        
        # 查找或创建用户
        agent = db.query(Agent).filter(Agent.email == email).first()
        
        # 如果用户已存在，使用已有账号
        if agent is None:
            agent = Agent(
                email=email,
                api_key = f"sk_{secrets.token_urlsafe(32)}"
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)
        
        # 生成 access_token（使用 api_key）
        access_token = agent.api_key
        
        # 删除 OTP
        del otp_store[challenge_id]
        
        # 清除登录失败记录
        clear_login_failure(client_ip)
        
        needs_profile = not agent.agent_name
        
        return LoginResponse(
            code=0,
            msg="success",
            data={
                "agent_id": agent.id,
                "access_token": access_token,
                "expires_at": int(time.time() * 1000) + 86400000 * 30,  # 30天
                "is_new_agent": is_new and agent is None,
                "needs_profile_completion": needs_profile
            }
        )
    except Exception as e:
        print(f"❌ Verify error: {e}")
        return LoginResponse(code=1, msg="Server error")
