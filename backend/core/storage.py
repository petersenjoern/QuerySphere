"""Module to organize storage related functionality"""

from langchain.vectorstores.pgvector import PGVector
from langchain.indexes import SQLRecordManager

from core.config import PGVectorSettings

def get_pgvector_connection_str(settings: PGVectorSettings) -> str:
    return PGVector.connection_string_from_db_params(
    driver=settings.driver,
    host=settings.host,
    port=settings.port,
    database=settings.database,
    user=settings.user,
    password=settings.password,
)

def get_sql_record_manager(settings: PGVectorSettings, namespace: str) -> SQLRecordManager:
    return SQLRecordManager(
        namespace=namespace,
        db_url=get_pgvector_connection_str(settings)
    )