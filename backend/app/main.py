import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db.database import init_db, is_sqlite
from .ehr.ehr_router import router as ehr_router
from .routers.chat_router import router as chat_router
from .routers.eval_router import router as eval_router
from .routers.auth_router import router as auth_router
from .routers.document_router import router as document_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("aegis_main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Aegis GI Clinical Backend...")
    try:
        await init_db()
        logger.info("Database schemas and vector extensions successfully verified.")
    except Exception as e:
        logger.error(f"Database initialization warning: {e}")
    yield
    logger.info("Aegis GI Backend shutting down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Outcome-Verified GI Prep & Booking Agent with Independent EHR State Verification",
    lifespan=lifespan
)

# Production CORS configuration
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://*.vercel.app",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(chat_router)
app.include_router(ehr_router)
app.include_router(eval_router)
app.include_router(auth_router)
app.include_router(document_router)

@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database_engine": "SQLite" if is_sqlite else "PostgreSQL",
        "pgvector_enabled": settings.USE_PGVECTOR or not is_sqlite,
        "llm_provider": settings.LLM_PROVIDER,
        "gemini_model": settings.GEMINI_MODEL
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
