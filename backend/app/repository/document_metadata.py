from database_model import Embedding
from dto import CMetaData
from sqlmodel import Session, select


def get_all_doc_metadata(session: Session) -> list[CMetaData]:
    query = select(Embedding.cmetadata)
    metadata = session.exec(query).fetchall()
    return [CMetaData(**meta) for meta in metadata]
