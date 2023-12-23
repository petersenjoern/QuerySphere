"""Load html from files, clean up, split, ingest into postgres vectors."""
import logging
import os
import re
from typing import Callable, Optional
from urllib.parse import urlparse

import git
from bs4 import BeautifulSoup, SoupStrainer
from core.config import get_api_settings
from core.constants import DB_COLLECTION_NAME, SQL_RECORD_MANAGAR_NAMESPACE
from core.embedding import get_embeddings_model
from core.indexing import index
from core.parser import langchain_docs_extractor
from core.storage import get_pgvector_connection_str, get_sql_record_manager
from langchain.document_loaders import ArxivLoader, GitLoader, SitemapLoader
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter
from langchain.vectorstores.pgvector import PGVector
from langchain_core.documents import Document
from pydantic import BaseModel, Field

FORCE_UPDATE = (os.environ.get("FORCE_UPDATE") or "false").lower() == "true"
WEBSITE_LANGCHAIN = "https://python.langchain.com"


class TextSplitterConfig(BaseModel):
    chunk_size: int
    chunk_overlap: int
    add_start_index: bool = Field(default=True)
    length_function: Callable[[str], int] = Field(default=len)
    language: Optional[str] = Field(default=Language.PYTHON)


class GitHubRepositoryHolder(BaseModel):
    clone_url: str
    repo_path: str
    file_extension: Optional[str] = Field(default=".py")


logging.basicConfig(
    filename="ingest.log",
    format="%(asctime)s - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


def load_langchain_docs() -> list[Document]:
    return SitemapLoader(
        f"{WEBSITE_LANGCHAIN}sitemap.xml",
        filter_urls=[WEBSITE_LANGCHAIN],
        parsing_function=langchain_docs_extractor,
        default_parser="lxml",
        bs_kwargs={
            "parse_only": SoupStrainer(
                name=("article", "title", "html", "lang", "content")
            ),
        },
        meta_function=_metadata_extractor,
    ).load()


def _metadata_extractor(meta: dict, soup: BeautifulSoup) -> dict:
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


def add_missing_metadata(docs: list[Document]) -> None:
    for doc in docs:
        if "source" not in doc["metadata"]:
            doc["metadata"]["source"] = ""
        if "title" not in doc["metadata"]:
            doc["metadata"]["title"] = ""


def get_files_from_github_repos(
    repositories: list[GitHubRepositoryHolder],
) -> list[Document]:
    all_code_files = []
    for repo_info in repositories:
        code: list[Document] = _get_github_files_as_docs(
            repo_info.clone_url, repo_info.repo_path, repo_info.file_extension
        )
        all_code_files.extend(code)
    return all_code_files


def _get_github_files_as_docs(
    clone_url: str, repo_path: str, file_extension: str = ".py"
) -> list[Document]:
    # TODO: if repo already exists, fetch and pull?
    repo = git.Repo.clone_from(clone_url, to_path=repo_path)
    branch = repo.head.reference
    loader = GitLoader(
        repo_path=repo_path,
        branch=branch,
        file_filter=lambda file_path: file_path.endswith(file_extension),
    )
    # TODO: add meta_function to extract not only the relative file path but the absolute (so I can load the code later)
    # TODO: add source so I can filter
    return loader.load()


# TODO: wrap this for list of queries, could be just a list comph.
def get_arxiv_files_as_docs(query: str) -> list[Document]:
    """
    Get arxiv files transformed to langchain Document.
    query can be either search terms, arxiv url or a paper ID
    """
    # TODO: add metadata source (arxiv), so I can filter on it.
    return ArxivLoader(
        query=_get_arxiv_id(query),
        load_max_docs=10,
        load_all_available_meta=True,
    ).load()


def _get_arxiv_id(potential_url: str) -> str:
    parsed_url = urlparse(potential_url)
    if parsed_url.netloc == "arxiv.org":
        return re.search(r"abs\/(.+)$", potential_url).group(1)
    return potential_url


def load_and_transform_docs(source, config, **kwargs):
    docs = _load_docs(source, kwargs)
    logger.info(f"Loaded {len(docs)} docs from {source}")
    transformed_docs = _split_documents_by_config(docs, config)
    return transformed_docs


def _load_docs(source: str, config: dict) -> list[str]:
    if source == "documentation":
        return load_langchain_docs()
    elif source == "github":
        return get_files_from_github_repos(
            [GitHubRepositoryHolder.model_validate(config)]
        )
    elif source == "arxiv":
        return get_arxiv_files_as_docs(query=config)
    else:
        raise ValueError(f"Invalid source: {source}")


def _split_documents_by_config(
    documents: list[Document], splitter_config: TextSplitterConfig
) -> list[Document]:
    text_splitter = _create_text_splitter(splitter_config)
    return text_splitter.split_documents(documents)


def _create_text_splitter(
    splitter_config: TextSplitterConfig,
) -> RecursiveCharacterTextSplitter:
    if splitter_config.language is not None:
        return RecursiveCharacterTextSplitter.from_language(
            chunk_size=splitter_config.chunk_size,
            chunk_overlap=splitter_config.chunk_overlap,
            add_start_index=splitter_config.add_start_index,
            length_function=splitter_config.length_function,
            language=splitter_config.language,
        )
    return RecursiveCharacterTextSplitter(
        chunk_size=splitter_config.chunk_size,
        chunk_overlap=splitter_config.chunk_overlap,
        length_function=splitter_config.length_function,
        add_start_index=splitter_config.add_start_index,
    )


def ingest_docs() -> None:
    settings = get_api_settings()
    logger.info("Loaded settings from environment variables")

    logger.info("Loading docs from sources...")

    docs_from_documentation = load_and_transform_docs(
        "documentation",
        TextSplitterConfig(
            chunk_size=settings.parser.chunk_size,
            chunk_overlap=settings.parser.chunk_overlap,
            language=None,
        ),
    )
    add_missing_metadata(docs_from_documentation)

    docs_from_code = load_and_transform_docs(
        "github",
        TextSplitterConfig(
            chunk_size=settings.parser.chunk_size,
            chunk_overlap=settings.parser.chunk_overlap,
            language=Language.PYTHON.value,
        ),
        clone_url="https://github.com/langchain-ai/langchain",
        repo_path="./data/github_repos/langchain-ai/langchain",
        file_extension=".py",
    )

    docs_from_arxiv = load_and_transform_docs(
        "arxiv",
        TextSplitterConfig(
            chunk_size=settings.parser.chunk_size,
            chunk_overlap=settings.parser.chunk_overlap,
            language=None,
        ),
        query="https://arxiv.org/abs/1605.08386",
    )

    all_docs = docs_from_documentation + docs_from_code + docs_from_arxiv

    pg_connection_str = get_pgvector_connection_str(settings.pgvector)
    embedding = get_embeddings_model(settings.embed.name)
    vectorstore = PGVector(
        collection_name=DB_COLLECTION_NAME,
        connection_string=pg_connection_str,
        embedding_function=embedding,
        logger=logger,
    )

    record_manager = get_sql_record_manager(
        settings.pgvector, SQL_RECORD_MANAGAR_NAMESPACE
    )
    record_manager.create_schema()

    indexing_stats = index(
        all_docs,
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
