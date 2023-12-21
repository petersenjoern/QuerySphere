"""Load html from files, clean up, split, ingest into postgres vectors."""
import logging
import os

from bs4 import BeautifulSoup, SoupStrainer
from core.config import get_api_settings
from core.constants import DB_COLLECTION_NAME, SQL_RECORD_MANAGAR_NAMESPACE
from core.embedding import get_embeddings_model
from core.indexing import index
from core.parser import langchain_docs_extractor
from core.storage import get_pgvector_connection_str, get_sql_record_manager
from langchain.document_loaders import SitemapLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.pgvector import PGVector
from langchain_core.documents import Document

FORCE_UPDATE = (os.environ.get("FORCE_UPDATE") or "false").lower() == "true"

logging.basicConfig(
    filename="ingest.log",
    format="%(asctime)s - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


def metadata_extractor(meta: dict, soup: BeautifulSoup) -> dict:
    title = soup.find("title")
    description = soup.find("meta", attrs={"name": "description"})
    html = soup.find("html")
    return {
        "source": meta["loc"],
        "title": title.get_text() if title else "",
        "description": description.get("content", "") if description else "",
        "language": html.get("lang", "") if html else "",
        **meta,
    }


def load_langchain_docs() -> list[Document]:
    return SitemapLoader(
        "https://python.langchain.com/sitemap.xml",
        filter_urls=["https://python.langchain.com/"],
        parsing_function=langchain_docs_extractor,
        default_parser="lxml",
        bs_kwargs={
            "parse_only": SoupStrainer(
                name=("article", "title", "html", "lang", "content")
            ),
        },
        meta_function=metadata_extractor,
    ).load()


def split_docs(
    docs: list[Document], chunk_size: int, chunk_overlap: int
) -> list[Document]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return text_splitter.split_documents(docs)


def add_missing_metadata(docs: list[Document]) -> None:
    for doc in docs:
        if "source" not in doc["metadata"]:
            doc["metadata"]["source"] = ""
        if "title" not in doc["metadata"]:
            doc["metadata"]["title"] = ""


def ingest_docs() -> None:
    settings = get_api_settings()
    logger.info("Loaded settings from environment variables")

    docs_from_documentation = load_langchain_docs()
    logger.info(f"Loaded {len(docs_from_documentation)} docs from documentation")

    docs_transformed = split_docs(
        docs_from_documentation,
        settings.parser.chunk_size,
        settings.parser.chunk_overlap,
    )
    add_missing_metadata(docs_transformed)

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
        docs_transformed,
        record_manager,
        vectorstore,
        cleanup="full",
        source_id_key="source",
        force_update=FORCE_UPDATE,
    )

    logger.info(f"Indexing stats: {indexing_stats}")

    # maybe to make SQL calls to check if data is in the DB.
    # import psycopg2.connect
    # connection = connect(
    #     dbname="mydb", user="myuser", password="mypassword"
    # )


if __name__ == "__main__":
    ingest_docs()
