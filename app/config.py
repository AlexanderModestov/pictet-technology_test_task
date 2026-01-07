"""Configuration management using Pydantic Settings"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # LLM Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    llm_model: str = Field(default="gpt-4o-mini", description="LLM model to use")
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model")

    # Database Configuration
    sqlite_db_path: str = Field(default="./data/stocks.db", description="SQLite database path")
    chroma_persist_path: str = Field(default="./data/chroma", description="ChromaDB persistence path")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    debug: bool = Field(default=False, description="Debug mode")

    # Processing Configuration
    chunk_size: int = Field(default=512, description="Chunk size in tokens")
    chunk_overlap: int = Field(default=50, description="Chunk overlap in tokens")
    top_k_results: int = Field(default=5, description="Number of results to retrieve")
    similarity_threshold: float = Field(default=0.7, description="Minimum similarity score")
    max_context_tokens: int = Field(default=3000, description="Maximum context tokens for LLM")

    # Retry Configuration
    llm_max_retries: int = Field(default=3, description="Maximum LLM API retries")
    llm_retry_delay: int = Field(default=1, description="Delay between retries in seconds")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def sqlite_db_path_absolute(self) -> Path:
        """Get absolute path to SQLite database"""
        return Path(self.sqlite_db_path).resolve()

    @property
    def chroma_persist_path_absolute(self) -> Path:
        """Get absolute path to ChromaDB persistence directory"""
        return Path(self.chroma_persist_path).resolve()


# Global settings instance
settings = Settings()
