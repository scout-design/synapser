"""
数据加密模块 - 用于敏感字段加密存储
"""
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend

# 加密密钥（生产环境应从环境变量或配置文件读取）
# 这里使用简单的派生方式，实际部署建议使用固定的密钥
ENCRYPTION_KEY = os.environ.get('SYNAPSE_ENCRYPTION_KEY', '')

_backend = None
_fernet = None


def _get_fernet():
    """获取 Fernet 实例（懒加载）"""
    global _fernet, _backend
    
    if _fernet is None:
        if not ENCRYPTION_KEY:
            # 如果没有配置密钥，使用默认密钥（仅用于开发，生产环境应设置）
            # 实际应该使用固定的 Fernet 密钥
            _fernet = None
            return None
        
        # 使用 PBKDF2 派生密钥
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'synapse_salt',  # 生产环境应使用随机盐
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(ENCRYPTION_KEY.encode()))
        _fernet = Fernet(key)
    
    return _fernet


def encrypt(plaintext: str) -> str:
    """
    加密字符串
    返回 base64 编码的密文
    """
    if not plaintext:
        return plaintext
    
    fernet = _get_fernet()
    if fernet is None:
        # 未配置加密密钥，返回原文（仅开发模式）
        return plaintext
    
    encrypted = fernet.encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt(ciphertext: str) -> str:
    """
    解密字符串
    输入 base64 编码的密文
    """
    if not ciphertext:
        return ciphertext
    
    fernet = _get_fernet()
    if fernet is None:
        # 未配置加密密钥，返回原文
        return ciphertext
    
    try:
        encrypted = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted = fernet.decrypt(encrypted)
        return decrypted.decode()
    except Exception:
        # 解密失败，可能是未加密的数据
        return ciphertext


def encrypt_email(email: str) -> str:
    """加密邮箱"""
    return encrypt(email)


def decrypt_email(encrypted_email: str) -> str:
    """解密邮箱"""
    return decrypt(encrypted_email)
