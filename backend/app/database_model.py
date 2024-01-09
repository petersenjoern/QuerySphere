import sqlalchemy as sa
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlmodel import Field, SQLModel


class Embedding(SQLModel, table=True):
    __tablename__ = "langchain_pg_embedding"
    uuid: str = Field(default=None, primary_key=True)
    collection_id: str = Field(
        sa_column=sa.Column(sa.TEXT, nullable=False, unique=False)
    )
    embedding: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    document: str = Field(sa_column=sa.Column(sa.TEXT, nullable=False, unique=True))
    cmetadata: dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON))
    custom_id: str = Field(sa_column=sa.Column(sa.TEXT, nullable=False))
