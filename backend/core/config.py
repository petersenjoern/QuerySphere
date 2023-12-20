"""Configuration for QuerySphere."""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Path where your env should be placed:
# /home/<user>/QuerySphere/.env
DOT_ENV_PATH = Path.cwd().joinpath(".env")


# Data handling related settings
class Parser(BaseModel):
    """Document/Node/Text parsing configurations"""

    chunk_size: int = Field(default=4000)
    chunk_overlap: int = Field(default=200)


class EmbedSettings(BaseModel):
    name: str = Field(default="BAAI/bge-small-en")


# LLM and prompting related settings
class LLMSettings(BaseModel):
    context_window: int = Field(default=3800)
    num_output: int = Field(default=256)
    temperature: float = Field(default=0.2)


## Database related settings
class PGVectorSettings(BaseModel):
    driver: str = Field(default="psycopg2")
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database: str = Field(default="app_db")
    user: str = Field(default="user")
    password: str = Field(default="password")


class Settings(BaseSettings, case_sensitive=False):
    """Configuration for QuerySphere"""

    model_config = SettingsConfigDict(
        env_file=DOT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    parser: Parser
    embed: EmbedSettings
    llm: LLMSettings
    pgvector: PGVectorSettings


@lru_cache()
def get_api_settings():
    """Get pydantic settings"""
    return Settings()
