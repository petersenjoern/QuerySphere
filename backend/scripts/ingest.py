"""Load html from files, clean up, split, ingest into postgres vectors."""
import logging
import os
import re
from pathlib import Path
from typing import Callable, ClassVar
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
from pydantic import BaseModel

FORCE_UPDATE = (os.environ.get("FORCE_UPDATE") or "false").lower() == "true"
WEBSITE_LANGCHAIN = "https://python.langchain.com/"
LOCAL_GITHUB_REPOS = "./data/github_repos"


class UnsupportedSchemeError(Exception):
    pass


class RepoPath(str):
    """A local file path for a GitHub repository."""

    _LOCAL_REPO_ROOT: ClassVar[str] = LOCAL_GITHUB_REPOS

    @classmethod
    def from_clone_url(cls, clone_url: str) -> "RepoPath":
        parsed = urlparse(clone_url)
        if parsed.scheme != "https":
            raise UnsupportedSchemeError("Only HTTPS clones are supported")
        path = parsed.path.lstrip("/")
        org, repo = path.split("/")
        local_path = Path(cls._LOCAL_REPO_ROOT).joinpath(org, repo).resolve()
        return cls(str(local_path))


class GitHubRepositoryHolder(BaseModel):
    clone_url: str
    local_path: str


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


def add_missing_metadata(source: str, docs: list[Document]) -> None:
    for doc in docs:
        if "source" not in doc.metadata:
            doc.metadata["source"] = source
        if "title" not in doc.metadata:
            doc.metadata["title"] = ""


class GitRepository:
    def __init__(self, repo_path: Path, branch: git.Head):
        self.repo_path = repo_path
        self._branch = branch

    @staticmethod
    def clone_or_pull(repository: GitHubRepositoryHolder) -> "GitRepository":
        repo_path = repository.local_path
        try:
            repo = git.Repo(repo_path)
            repo.remotes.origin.pull()
        except (git.NoSuchPathError, git.GitCommandError):
            repo = git.Repo.clone_from(repository.clone_url, repository.local_path)
        return GitRepository(repo_path, repo.head.reference)

    def load_docs(self, file_filter: callable) -> list[Document]:
        loader = GitLoader(
            repo_path=self.repo_path,
            branch=self._branch,
            file_filter=file_filter,
        )
        return loader.load()


def get_github_files_as_docs(clone_url: str, file_extension: str) -> list[Document]:
    repository_holder = _create_github_repository_holder(clone_url)
    git_repo = GitRepository.clone_or_pull(repository_holder)
    return git_repo.load_docs(_file_ends_with_extension(file_extension))


def _create_github_repository_holder(clone_url: str) -> GitHubRepositoryHolder:
    return GitHubRepositoryHolder(
        clone_url=clone_url, local_path=RepoPath.from_clone_url(clone_url)
    )


def _file_ends_with_extension(file_extension: str) -> Callable[[Path], bool]:
    return lambda file_path: file_path.endswith(file_extension)


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


def load_and_transform_docs(
    sources: list[str],
    en_splitter: RecursiveCharacterTextSplitter,
    code_splitter: RecursiveCharacterTextSplitter,
) -> list[Document]:
    transformed_docs = []
    for source in sources:
        docs = _load_docs(source)
        logger.info(f"Loaded {len(docs)} docs from {source}")
        if source.startswith("https://github.com"):
            transformed_docs.extend(code_splitter.split_documents(docs))
        else:
            transformed_docs.extend(en_splitter.split_documents(docs))
    add_missing_metadata(source, transformed_docs)
    return transformed_docs


def _load_docs(source: str) -> list[str]:
    if source.startswith("https://python.langchain.com"):
        return load_langchain_docs()
    elif source.startswith("https://github.com"):
        docs = get_github_files_as_docs(clone_url=source, file_extension=".py")
        _add_absolute_path_to_repo(source, docs)
        return docs
    elif source.startswith("https://arxiv.org"):
        docs = get_arxiv_files_as_docs(source)
        _add_entry_id_as_source(docs)
        return docs
    else:
        raise ValueError(f"This source: {source} cannot be parsed.")


def _add_absolute_path_to_repo(source: str, docs: list[Document]) -> None:
    repository = _create_github_repository_holder(source)
    for doc in docs:
        file_path_abs = Path(repository.local_path) / doc.metadata["file_path"]
        doc.metadata["source"] = str(file_path_abs)


def _add_entry_id_as_source(docs: list[Document]) -> None:
    for doc in docs:
        doc.metadata["source"] = doc.metadata["entry_id"]
        doc.metadata["title"] = doc.metadata["Title"]


def ingest_docs() -> None:
    settings = get_api_settings()
    logger.info("Loaded settings from environment variables")

    en_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.parser.chunk_size,
        chunk_overlap=settings.parser.chunk_overlap,
        add_start_index=True,
        length_function=len,
    )
    code_splitter = RecursiveCharacterTextSplitter.from_language(
        chunk_size=settings.parser.chunk_size,
        chunk_overlap=settings.parser.chunk_overlap,
        add_start_index=True,
        length_function=len,
        language=Language.PYTHON.value,
    )

    logger.info("Loading docs from sources...")
    all_docs = load_and_transform_docs(
        [
            # "https://github.com/langchain-ai/langchain",
            "https://arxiv.org/abs/2401.01814",
            "https://arxiv.org/abs/2308.04889",
            "https://arxiv.org/abs/2304.01373",
            "https://arxiv.org/abs/2307.09288",
            # WEBSITE_LANGCHAIN,
        ],
        en_splitter,
        code_splitter,
    )

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
