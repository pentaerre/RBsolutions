from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Atrium"
    api_prefix: str = "/api"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "qwen2.5:7b"
    ollama_embed_model: str = ""
    documents_dir: str = "/data/documents"
    qdrant_url: str = "memory"
    qdrant_collection: str = "documents"
    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = "atriumpass"
    llm_provider: str = "ollama"
    anthropic_api_key: str = ""
    chunk_size: int = 1000
    chunk_overlap: int = 150
    rag_top_k: int = 5
    watch_documents: bool = True
    embedding_backend: str = "hash"
    database_url: str = "sqlite:////tmp/atrium.db"
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    workspace_url: str = "http://localhost:3000"
    admin_url: str = "http://localhost:3001"
    imap_host: str = ""
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    imap_folder: str = "INBOX"
    imap_poll_seconds: int = 0
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_poll_seconds: int = 0
    teams_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_to: str = ""
    docs_root: str = ""
    sync_docs: bool = True
    taxonomy_cadence: str = "hour"
    extract_with_llm: bool = True
    file_llm: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
