from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings shared by every layer of ai-service."""

    APP_ENV: str
    APP_DEBUG: bool

    # Backend API Settings (data source for repository/)
    BACKEND_API_URL: str
    BACKEND_API_TIMEOUT_SECONDS: int = 10

    # LangGraph Checkpointer Settings (SQLite)
    CHECKPOINT_DB_PATH: str = "checkpoints.db"

    # Conversation History Settings (SQLite)
    CONVERSATION_DB_PATH: str = "conversations.db"
    CONVERSATION_HISTORY_LIMIT: int = 10

    # LLM Settings (Groq)
    GROQ_API_KEY: str
    LLM_MODEL: str
    LLM_TEMPERATURE: float = 0.0

    # Vector Store Settings (Qdrant)
    QDRANT_URL: str
    # No default: must match the collection the knowledge was ingested into.
    QDRANT_COLLECTION: str

    # Embedding & RAG Settings
    # No default: changing the model without re-ingesting breaks search (dimension mismatch).
    EMBEDDING_MODEL: str
    KNOWLEDGE_DIR: str = "./knowledge"
    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 120
    RAG_TOP_K: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
