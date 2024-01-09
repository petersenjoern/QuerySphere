from typing import Set

from dto import SourceAndTitle
from repository import document_metadata as repository_document_metadata
from sqlmodel import Session


def get_doc_source_and_title(session: Session) -> list[SourceAndTitle]:
    metadata = repository_document_metadata.get_all_doc_metadata(session)

    duplicate_source_titles: Set[str] = set()
    source_and_titles: list[SourceAndTitle] = []

    for meta in metadata:
        key = f"{meta.source}:{meta.title}"
        if key not in duplicate_source_titles:
            duplicate_source_titles.add(key)
            source_and_titles.append(
                SourceAndTitle(source=meta.source, title=meta.title)
            )

    return source_and_titles
