import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from ..config import settings

logger = logging.getLogger("aegis_db")

Base = declarative_base()

def get_normalized_database_url(url: str) -> str:
    """Normalize database URL for async drivers."""
    if not url:
        return "sqlite+aiosqlite:///./data/clinical_ehr.db"
    
    # Supabase/Neon provide postgres:// or postgresql://
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    return url

DATABASE_URL = get_normalized_database_url(settings.DATABASE_URL)

# Configure engine with connection pooling and timeouts
is_sqlite = DATABASE_URL.startswith("sqlite")
if is_sqlite:
    db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    dir_name = os.path.dirname(db_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

connect_args = {"check_same_thread": False} if is_sqlite else {}
engine_kwargs = {
    "echo": settings.LOG_LEVEL.upper() == "DEBUG",
    "future": True,
}

if not is_sqlite:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    })

engine = create_async_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def init_db():
    """Initialize database schema and extensions."""
    logger.info(f"Connecting to database ({'SQLite' if is_sqlite else 'PostgreSQL'})...")
    
    async with engine.begin() as conn:
        if not is_sqlite:
            try:
                # Enable pgvector on PostgreSQL
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                logger.info("PostgreSQL pgvector extension verified.")
            except Exception as e:
                logger.warning(f"Could not enable pgvector extension (continuing): {e}")
        
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema synchronized.")

from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager providing transactional database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency providing transactional async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

