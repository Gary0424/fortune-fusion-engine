"""
数据模型 - SQLAlchemy ORM 定义
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean, Text, 
    JSON, Index, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=True)
    gender = Column(String(10), nullable=True)
    birth_year = Column(Integer, nullable=True)
    birth_month = Column(Integer, nullable=True)
    birth_day = Column(Integer, nullable=True)
    birth_hour = Column(Integer, nullable=True)
    birth_minute = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    calibration_data = Column(JSON, default=dict)  # 个性化校准数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    queries = relationship("QueryModel", back_populates="user", lazy="dynamic")


class QueryModel(Base):
    """查询记录表"""
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(16), unique=True, nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=True, index=True)
    scene = Column(String(32), nullable=False, index=True)
    
    # 请求参数
    birth_info = Column(JSON, nullable=False)
    gender = Column(String(10), nullable=False)
    name = Column(String(128), nullable=True)
    
    # 融合结果
    fusion_score = Column(Float, nullable=False)
    fusion_trend = Column(String(16), nullable=False)
    fusion_risk_level = Column(String(16), nullable=False)
    fusion_reliability = Column(String(16), nullable=False)
    fusion_uncertainty = Column(Float, nullable=False)
    fusion_details = Column(JSON, nullable=True)  # 完整融合结果 JSON
    
    # 各体系详细结果
    system_results = Column(JSON, nullable=True)
    
    # 性能指标
    calculation_time_ms = Column(Integer, nullable=False)
    cached = Column(Boolean, default=False)
    
    # 用户反馈
    accuracy_feedback = Column(Integer, nullable=True)  # 1-5 星
    feedback_comment = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 关系
    user = relationship("UserModel", back_populates="queries")


class SystemAccuracyModel(Base):
    """体系准确率统计表"""
    __tablename__ = "system_accuracy"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    system = Column(String(32), unique=True, nullable=False, index=True)
    total_predictions = Column(Integer, default=0)
    accurate_predictions = Column(Integer, default=0)
    rolling_accuracy = Column(Float, default=0.8)  # 滚动准确率
    avg_confidence = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DailyStatsModel(Base):
    """每日统计表"""
    __tablename__ = "daily_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), unique=True, nullable=False, index=True)  # YYYY-MM-DD
    total_queries = Column(Integer, default=0)
    avg_calculation_time_ms = Column(Float, default=0.0)
    avg_fusion_score = Column(Float, default=0.0)
    cache_hit_rate = Column(Float, default=0.0)
    error_count = Column(Integer, default=0)
    
    # 各场景统计
    scene_distribution = Column(JSON, default=dict)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============== 索引 ==============

Index("idx_queries_user_scene", QueryModel.user_id, QueryModel.scene)
Index("idx_queries_created", QueryModel.created_at)


# ============== 数据库管理 ==============

def get_database_url(async_mode: bool = True) -> str:
    """获取数据库连接 URL"""
    import os
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fortune")
    if async_mode:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    return db_url


def create_engine_pool():
    """创建异步数据库引擎"""
    url = get_database_url(async_mode=True)
    engine = create_async_engine(url, pool_size=10, max_overflow=20, pool_pre_ping=True)
    return engine


def get_session_factory(engine=None):
    """获取会话工厂"""
    if engine is None:
        engine = create_engine_pool()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
