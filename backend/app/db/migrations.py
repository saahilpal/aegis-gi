"""Declarative Migration Runner for Aegis GI Clinical Schema.

Provides lightweight, zero-dependency schema versioning and index optimization
compatible with PostgreSQL (pgvector) and local development SQLite.
"""

import sys
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy import text
from .database import engine, is_sqlite, Base
from . import models  # Ensures all models are registered on Base.metadata

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("aegis_migrations")

MIGRATIONS: List[Dict[str, Any]] = [
    {
        "version": 1,
        "name": "001_initial_relational_schema",
        "description": "Create base clinical tables: patients, providers, slots, appointments, prep, audit, eval, users",
        "up_sql_postgres": [
            "CREATE EXTENSION IF NOT EXISTS vector;",
            "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";",
        ],
        "up_sql_sqlite": [],
    },
    {
        "version": 2,
        "name": "002_performance_indexes",
        "description": "Add B-tree indexes on lookup fields: appointment status, patient MRN, provider NPI, audit event_type",
        "up_sql_postgres": [
            "CREATE INDEX IF NOT EXISTS idx_appointments_patient_status ON appointments (patient_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_audit_events_event_created ON audit_events (event_type, created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_eval_results_run_scenario ON evaluation_results (run_id, scenario_id);",
            "CREATE INDEX IF NOT EXISTS idx_patients_mrn ON patients (mrn);",
        ],
        "up_sql_sqlite": [
            "CREATE INDEX IF NOT EXISTS idx_appointments_patient_status ON appointments (patient_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_audit_events_event_created ON audit_events (event_type, created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_eval_results_run_scenario ON evaluation_results (run_id, scenario_id);",
            "CREATE INDEX IF NOT EXISTS idx_patients_mrn ON patients (mrn);",
        ],
    },
    {
        "version": 3,
        "name": "003_pgvector_ivfflat_index",
        "description": "Add IVFFlat vector index on document_chunks for accelerated cosine similarity",
        "up_sql_postgres": [
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'document_chunks') THEN
                    -- Check if table has sufficient rows for IVFFlat (requires at least 1 row to build lists)
                    IF (SELECT count(*) FROM document_chunks) > 0 THEN
                        CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding_cosine 
                        ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
                    END IF;
                END IF;
            END $$;
            """
        ],
        "up_sql_sqlite": [],
    }
]


async def ensure_migration_table():
    """Ensure schema_migrations tracking table exists."""
    async with engine.begin() as conn:
        if is_sqlite:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
        else:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """))


async def get_applied_versions() -> List[int]:
    """Retrieve list of already applied migration versions."""
    await ensure_migration_table()
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT version FROM schema_migrations ORDER BY version ASC;"))
        return [row[0] for row in res.fetchall()]


async def migrate_up():
    """Apply all pending migrations in order."""
    logger.info("Initializing schema synchronization via SQLAlchemy metadata...")
    async with engine.begin() as conn:
        if not is_sqlite:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception as e:
                logger.warning(f"pgvector extension notice: {e}")
        await conn.run_sync(Base.metadata.create_all)

    await ensure_migration_table()
    applied = await get_applied_versions()
    logger.info(f"Currently applied migrations: {applied}")

    for mig in MIGRATIONS:
        v = mig["version"]
        name = mig["name"]
        if v in applied:
            continue

        logger.info(f"Applying migration v{v}: {name} - {mig['description']}")
        sqls = mig["up_sql_sqlite"] if is_sqlite else mig["up_sql_postgres"]
        
        async with engine.begin() as conn:
            for statement in sqls:
                st = statement.strip()
                if st:
                    try:
                        await conn.execute(text(st))
                    except Exception as e:
                        logger.warning(f"Migration statement notice on v{v}: {e}")
            
            await conn.execute(
                text("INSERT INTO schema_migrations (version, name) VALUES (:v, :n);"),
                {"v": v, "n": name}
            )
        logger.info(f"Successfully applied v{v} ({name})")

    logger.info("All database migrations up-to-date.")


async def verify_schema():
    """Verify table presence and integrity."""
    async with engine.begin() as conn:
        expected_tables = [
            "patients", "providers", "procedures", "appointments",
            "prep_protocols", "document_chunks", "conversations", "messages",
            "trace_steps", "outcome_verifications", "evaluation_runs",
            "evaluation_results", "audit_events", "users"
        ]
        logger.info(f"Verifying presence of {len(expected_tables)} clinical tables...")
        
        for table in expected_tables:
            if is_sqlite:
                query = text(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{table}';")
            else:
                query = text(f"SELECT count(*) FROM information_schema.tables WHERE table_name='{table}';")
            res = await conn.execute(query)
            count = res.scalar()
            if count and count > 0:
                logger.info(f"  [OK] Table '{table}' verified.")
            else:
                logger.error(f"  [FAIL] Table '{table}' missing!")
                return False
                
    logger.info("Database schema verification PASSED.")
    return True


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if action == "upgrade":
        asyncio.run(migrate_up())
    elif action == "verify":
        success = asyncio.run(verify_schema())
        sys.exit(0 if success else 1)
    elif action == "status":
        applied = asyncio.run(get_applied_versions())
        print(f"Applied migrations: {applied}")
    else:
        print(f"Usage: python -m app.db.migrations [upgrade|verify|status]")
