from config import get_api_settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine
from storage import get_pgvector_connection_str

settings = get_api_settings()
pg_connection_str = get_pgvector_connection_str(settings.pgvector, as_async=False)
engine = create_engine(pg_connection_str, echo=True)


def get_session() -> Session:
    with Session(engine) as session:
        yield session


async def get_async_session() -> AsyncSession:
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autocommit=False
    )
    async with async_session() as session:
        yield session
