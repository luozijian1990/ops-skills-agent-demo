"""SQLAlchemy 异步数据库引擎"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import DATABASE_URL
from utils.logger import logger

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """创建所有表"""
    # 局部导入 Base 以避免循环引用，并注册 metadata
    from models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表已就绪")


async def get_session() -> AsyncSession:
    """获取数据库 session"""
    async with AsyncSessionLocal() as session:
        yield session
