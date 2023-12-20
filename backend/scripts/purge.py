"""Purge postgres vector collections."""

import logging

from core.config import get_api_settings
from langchain.vectorstores.pgvector import PGVector

from core.constants import DB_COLLECTION_NAME, SQL_RECORD_MANAGAR_NAMESPACE
from core.embedding import get_embeddings_model
from core.indexing import index
from storage import get_pgvector_connection_str, get_sql_record_manager


logging.basicConfig(
    filename="purge.log",
    format="%(asctime)s - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


def purge() -> None:
    settings = get_api_settings()
    pg_connection_str = get_pgvector_connection_str(settings.pgvector)
    embedding = get_embeddings_model(settings.embed.name)
    vectorstore = PGVector(
        collection_name=DB_COLLECTION_NAME,
        connection_string=pg_connection_str,
        embedding_function=embedding,
        logger=logger,
    )
    
    record_manager = get_sql_record_manager(settings, SQL_RECORD_MANAGAR_NAMESPACE)
    record_manager.create_schema()

    indexing_stats = index(
        [],
        record_manager,
        vectorstore,
        cleanup="full",
        source_id_key="source",
    )

    logger.info("Indexing stats: ", indexing_stats)

if __name__ == "__main__":
    purge()