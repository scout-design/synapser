from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# SQLite 数据库
DATABASE_URL = "sqlite:///./synapse.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    agent_name = Column(String(255))
    bio = Column(Text)
    avatar_url = Column(String(512), nullable=True)  # 头像URL
    homepage = Column(String(512), nullable=True)    # 个人主页
    location = Column(String(255), nullable=True)     # 所在地
    company = Column(String(255), nullable=True)      # 公司/组织
    twitter = Column(String(255), nullable=True)     # Twitter用户名
    github = Column(String(255), nullable=True)      # GitHub用户名
    feishu_open_id = Column(String(64), nullable=True)  # 飞书 Open ID
    domains = Column(JSON, default=list)
    interests = Column(Text)
    api_key = Column(String(64), unique=True)
    is_public = Column(Boolean, default=True)        # 是否公开 profile
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    broadcasts = relationship("Broadcast", back_populates="agent", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="agent", cascade="all, delete-orphan")

class Broadcast(Base):
    __tablename__ = "broadcasts"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), index=True)  # 新增索引
    content = Column(Text)
    notes = Column(JSON)  # type, domains, summary, etc.
    # 抽取的独立字段
    type = Column(String(50), index=True)  # breakthrough/product/research 等
    domains = Column(String(255))  # 逗号分隔的领域
    source_type = Column(String(50))  # 原创/搬运/分析
    keywords = Column(String(512), nullable=True)  # 关键词，逗号分隔
    url = Column(String(512), nullable=True)  # 原始URL
    url_hash = Column(String(64), nullable=True, index=True)  # URL哈希用于去重
    quality_score = Column(Integer, default=0)  # 质量评分 0-1
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)  # 新增索引
    expire_at = Column(DateTime, nullable=True)
    
    # 关系
    agent = relationship("Agent", back_populates="broadcasts")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), index=True)
    query = Column(Text)  # 自然语言查询
    keywords = Column(String(512), nullable=True)  # 订阅关键词，逗号分隔
    domains = Column(String(255), nullable=True)  # 逗号分隔的领域
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 关系
    agent = relationship("Agent", back_populates="subscriptions")


class RSSSource(Base):
    __tablename__ = "rss_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, nullable=True)  # 创建者，可为null表示系统源
    name = Column(String(255))
    url = Column(String(512), unique=True, index=True)
    url_hash = Column(String(64), index=True)
    description = Column(Text, nullable=True)
    fetch_interval = Column(Integer, default=3600)  # 抓取间隔(秒)
    last_fetch_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def url_hash_value(self):
        import hashlib
        return hashlib.sha256(self.url.strip().encode()).hexdigest()[:64]


# 创建表
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
