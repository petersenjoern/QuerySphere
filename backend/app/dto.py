from pydantic import BaseModel


class CMetaData(BaseModel):
    title: str
    source: str
    start_index: int


class SourceAndTitle(BaseModel):
    source: str
    title: str
