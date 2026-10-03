import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
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

# Production-Hardened CORS Configuration
if settings.ENVIRONMENT.lower() == "production":
    raw_origins = settings.CORS_ORIGINS or "https://frontend-rho-indol-95.vercel.app"
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip() and o.strip() != "*"]
    if not allowed_origins:
        allowed_origins = ["https://frontend-rho-indol-95.vercel.app"]
else:
    # Development / local test origins only
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://frontend-rho-indol-95.vercel.app"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Requested-With"],
)

# Global Unhandled Exception Handler (Prevents stack trace leaks to clients)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log sanitized error internally
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please try again or contact clinic support.",
            "error_code": "INTERNAL_SERVER_ERROR"
        }
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
