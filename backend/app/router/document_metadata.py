from database import get_session
from dto import SourceAndTitle
from fastapi import APIRouter, Depends, status
from service import document_metadata as service_document_metadata
from sqlmodel import Session

router = APIRouter()


@router.get(
    "/doc-references",
    status_code=status.HTTP_200_OK,
)
def get_sources_and_titles(
    session: Session = Depends(get_session),
) -> list[SourceAndTitle]:
    sources_and_titles = service_document_metadata.get_doc_source_and_title(session)
    return sources_and_titles
