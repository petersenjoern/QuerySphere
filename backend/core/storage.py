"""Module to organize storage related functionality"""

from core.config import PGVectorSettings
from langchain.indexes import SQLRecordManager


def get_pgvector_connection_str(
    settings: PGVectorSettings, as_async: bool = False
) -> str:
    if as_async:
        return f"postgresql+asyncpg://{settings.user}:{settings.password}@{settings.host}:{settings.port}/{settings.database}"
    return f"postgresql://{settings.user}:{settings.password}@{settings.host}:{settings.port}/{settings.database}"


def get_sql_record_manager(
    settings: PGVectorSettings, namespace: str
) -> SQLRecordManager:
    return SQLRecordManager(
        namespace=namespace, db_url=get_pgvector_connection_str(settings)
    )
