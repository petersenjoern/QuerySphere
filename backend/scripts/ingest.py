"""Load html from files, clean up, split, ingest into postgres vectors."""
import logging
import os

from bs4 import BeautifulSoup, SoupStrainer
from core.config import get_api_settings
from core.constants import DB_COLLECTION_NAME
from core.indexing import index
from core.parser import langchain_docs_extractor
from langchain.document_loaders import SitemapLoader
from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain.indexes import SQLRecordManager
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.pgvector import PGVector

logging.basicConfig(
    filename="ingest.log",
    format="%(asctime)s - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


settings = get_api_settings()


CONNECTION_STRING = PGVector.connection_string_from_db_params(
    driver=settings.pgvector.driver,
    host=settings.pgvector.host,
    port=settings.pgvector.port,
    database=settings.pgvector.database,
    user=settings.pgvector.user,
    password=settings.pgvector.password,
)


def get_embeddings_model(model_name: str):
    return HuggingFaceBgeEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


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


def load_langchain_docs():
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


def ingest_docs():
    docs_from_documentation = load_langchain_docs()
    logger.info(f"Loaded {len(docs_from_documentation)} docs from documentation")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)
    docs_transformed = text_splitter.split_documents(docs_from_documentation)

    # We try to return 'source' and 'title' metadata when querying vector store and
    # Weaviate will error at query time if one of the attributes is missing from a
    # retrieved document.
    for doc in docs_transformed:
        if "source" not in doc.metadata:
            doc.metadata["source"] = ""
        if "title" not in doc.metadata:
            doc.metadata["title"] = ""

    embedding = get_embeddings_model(settings.embed.name)
    vectorstore = PGVector(
        collection_name=DB_COLLECTION_NAME,
        connection_string=CONNECTION_STRING,
        embedding_function=embedding,
        logger=logger,
    )

    record_manager = SQLRecordManager(
        f"pgvector/{DB_COLLECTION_NAME}", db_url=CONNECTION_STRING
    )
    record_manager.create_schema()

    indexing_stats = index(
        docs_transformed,
        record_manager,
        vectorstore,
        cleanup="full",
        source_id_key="source",
        force_update=(os.environ.get("FORCE_UPDATE") or "false").lower() == "true",
    )

    logger.info(f"Indexing stats: {indexing_stats}")


if __name__ == "__main__":
    ingest_docs()
