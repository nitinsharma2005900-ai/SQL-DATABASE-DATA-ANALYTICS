"""SQLAlchemy Database Connection & Execution Manager."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import sqlalchemy as sa
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import SQLAlchemyError

from config.settings import settings


@dataclass
class QueryResult:
    """Structured result returned from database query execution."""
    success: bool
    query: str
    columns: List[str] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    error: Optional[str] = None

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return self.rows


class DatabaseManager:
    """Manages database connection lifecycle, schema reflection, and safe query execution."""

    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url or settings.DATABASE_URL
        self._engine: Optional[Engine] = None
        self._init_engine()

    def _init_engine(self) -> None:
        """Initialize SQLAlchemy engine with connection pooling and dialect settings."""
        connect_args = {}
        if self.database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        self._engine = create_engine(
            self.database_url,
            connect_args=connect_args,
            pool_pre_ping=True,
            future=True,
        )

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._init_engine()
        return self._engine  # type: ignore

    def test_connection(self) -> bool:
        """Test if the database connection is active."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def execute_query(self, sql_query: str, read_only: bool = True) -> QueryResult:
        """Execute a SQL query safely, capturing timing and exceptions.
        
        Args:
            sql_query: The SQL query string to execute.
            read_only: Whether to enforce engine-level read-only protections.
        """
        start_time = time.perf_counter()
        clean_query = sql_query.strip().rstrip(";")

        try:
            with self.engine.connect() as conn:
                # Apply connection-level read-only lock if requested and supported
                if read_only:
                    if self.engine.dialect.name == "sqlite":
                        conn.execute(text("PRAGMA query_only = ON;"))
                    elif self.engine.dialect.name == "postgresql":
                        conn.execute(text("SET TRANSACTION READ ONLY;"))

                result = conn.execute(text(clean_query))
                
                # Fetch columns and records if result has returns_rows
                if result.returns_rows:
                    columns = list(result.keys())
                    raw_rows = result.fetchall()
                    rows = [dict(zip(columns, row)) for row in raw_rows]
                    row_count = len(rows)
                else:
                    columns = []
                    rows = []
                    row_count = result.rowcount or 0

                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

                return QueryResult(
                    success=True,
                    query=sql_query,
                    columns=columns,
                    rows=rows,
                    row_count=row_count,
                    execution_time_ms=elapsed_ms,
                    error=None,
                )

        except SQLAlchemyError as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            # Extract detailed error message
            error_msg = str(exc.orig) if hasattr(exc, "orig") and exc.orig else str(exc)
            return QueryResult(
                success=False,
                query=sql_query,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=elapsed_ms,
                error=error_msg,
            )
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return QueryResult(
                success=False,
                query=sql_query,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=elapsed_ms,
                error=str(exc),
            )

    def close(self) -> None:
        """Dispose of the engine connection pool."""
        if self._engine:
            self._engine.dispose()
            self._engine = None


# Global singleton instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(database_url: Optional[str] = None) -> DatabaseManager:
    """Get or create singleton DatabaseManager."""
    global _db_manager
    if _db_manager is None or (database_url and database_url != _db_manager.database_url):
        _db_manager = DatabaseManager(database_url)
    return _db_manager
