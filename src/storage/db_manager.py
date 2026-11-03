"""Database Manager for EcoSyn telemetry logging and retrieval."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session

from src.storage.models import Base, InvocationLog, BenchmarkRun


class DatabaseManager:
    """Handles database connections, schema creation, and telemetry persistence."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        db_cfg = config.get("database", {})
        db_type = db_cfg.get("type", "sqlite").lower()

        if db_type == "mysql":
            mysql_cfg = db_cfg.get("mysql", {})
            user = mysql_cfg.get("user", "root")
            password = mysql_cfg.get("password", "")
            host = mysql_cfg.get("host", "localhost")
            port = mysql_cfg.get("port", 3306)
            database = mysql_cfg.get("database", "ecosyn_db")
            db_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        else:
            # Default to SQLite
            sqlite_path = db_cfg.get("sqlite_path", "data/ecosyn.db")
            # Ensure parent directory exists
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{sqlite_path}"

        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.create_tables()

    def create_tables(self) -> None:
        """Creates database tables if they do not already exist."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Returns a new database session."""
        return self.SessionLocal()

    def log_invocation(self, record_data: Dict[str, Any]) -> InvocationLog:
        """Persists a single invocation log entry."""
        session = self.get_session()
        try:
            log_entry = InvocationLog(**record_data)
            session.add(log_entry)
            session.commit()
            session.refresh(log_entry)
            return log_entry
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def log_batch(self, records: List[Dict[str, Any]]) -> None:
        """Persists a batch of invocation logs inside a single transaction."""
        if not records:
            return
        session = self.get_session()
        try:
            log_entries = [InvocationLog(**rec) for rec in records]
            session.bulk_save_objects(log_entries)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def save_benchmark_run(self, run_data: Dict[str, Any]) -> BenchmarkRun:
        """Persists benchmark run summary statistics."""
        session = self.get_session()
        try:
            run_entry = BenchmarkRun(**run_data)
            session.merge(run_entry)
            session.commit()
            return run_entry
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_invocation_logs(
        self,
        policy: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Queries recent invocation logs, optionally filtered by router policy."""
        session = self.get_session()
        try:
            query = session.query(InvocationLog)
            if policy:
                query = query.filter(InvocationLog.router_policy == policy)
            records = query.order_by(desc(InvocationLog.id)).limit(limit).all()

            results = []
            for r in records:
                results.append({
                    "id": r.id,
                    "request_id": r.request_id,
                    "timestamp": r.timestamp,
                    "router_policy": r.router_policy,
                    "client_region": r.client_region,
                    "selected_region": r.selected_region,
                    "function_name": r.function_name,
                    "total_latency_ms": r.total_latency_ms,
                    "sla_deadline_ms": r.sla_deadline_ms,
                    "sla_violated": r.sla_violated,
                    "carbon_intensity": r.carbon_intensity,
                    "energy_kwh": r.energy_kwh,
                    "carbon_emissions_g": r.carbon_emissions_g,
                    "cost_usd": r.cost_usd,
                    "decision_notes": r.decision_notes,
                })
            return results
        finally:
            session.close()

