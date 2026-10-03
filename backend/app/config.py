import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(extra="allow", env_file=".env")

    PROJECT_NAME: str = "Outcome-Verified GI Prep & Booking Agent"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # LLM & Observability
    # Provider selection: "ollama" | "gemini" | "auto"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    
    # Local LLM settings (Ollama)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    
    # Cloud LLM settings (Gemini)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    
    LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "gi-prep-booking-agent")
    
    # Database (PostgreSQL with pgvector in production, SQLite async in local test)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/clinical_ehr.db")
    USE_PGVECTOR: bool = os.getenv("USE_PGVECTOR", "false").lower() == "true"
    
    # Security & HIPAA-aware engineering
    SECRET_KEY: str = os.getenv("SECRET_KEY", "clinical-aegis-secret-key-change-in-production-2026")
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "https://frontend-rho-indol-95.vercel.app")
    PHI_SCRUB_LOGS: bool = True
    AUDIT_LOG_ENABLED: bool = True

settings = Settings()
