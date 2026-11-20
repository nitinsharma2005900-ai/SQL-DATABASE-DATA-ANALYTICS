"""Database Schema Inspection & Metadata Extraction."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from .connection import DatabaseManager, QueryResult, get_db_manager


@dataclass
class ColumnMeta:
    """Metadata for a single column."""
    name: str
    data_type: str
    nullable: bool
    primary_key: bool
    default: Optional[str] = None


@dataclass
class TableMeta:
    """Metadata for a single table."""
    name: str
    columns: List[ColumnMeta] = field(default_factory=list)
    foreign_keys: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0


@dataclass
class SchemaInfo:
    """Comprehensive database schema representation."""
    tables: Dict[str, TableMeta] = field(default_factory=dict)
    dialect: str = "sqlite"

    def get_table_names(self) -> List[str]:
        return list(self.tables.keys())

    def get_column_names(self, table_name: str) -> List[str]:
        table = self.tables.get(table_name)
        if not table:
            return []
        return [col.name for col in table.columns]

    def to_prompt_string(self) -> str:
        """Format schema into clean, LLM-digestible markdown representation."""
        lines = [f"Database Dialect: {self.dialect.upper()}", "Available Tables & Columns:"]
        for table_name, table in self.tables.items():
            col_strs = []
            for col in table.columns:
                pk_flag = " [PRIMARY KEY]" if col.primary_key else ""
                col_strs.append(f"    - {col.name} ({col.data_type}){pk_flag}")
            
            lines.append(f"Table: {table_name} (approx {table.row_count} rows)")
            lines.extend(col_strs)
            
            if table.foreign_keys:
                lines.append("  Foreign Keys:")
                for fk in table.foreign_keys:
                    constrained = ", ".join(fk.get("constrained_columns", []))
                    referred = f"{fk.get('referred_table')}({', '.join(fk.get('referred_columns', []))})"
                    lines.append(f"    - ({constrained}) -> {referred}")
            lines.append("")
        return "\n".join(lines).strip()


class DatabaseInspector:
    """Inspects database schema dynamically using SQLAlchemy reflection."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or get_db_manager()

    def inspect_schema(self) -> SchemaInfo:
        """Reflect entire schema and return structured SchemaInfo."""
        inspector = inspect(self.db.engine)
        table_names = inspector.get_table_names()
        dialect = self.db.engine.dialect.name
        schema_info = SchemaInfo(dialect=dialect)

        for table_name in table_names:
            columns_raw = inspector.get_columns(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols = set(pk_constraint.get("constrained_columns", [])) if pk_constraint else set()
            fks_raw = inspector.get_foreign_keys(table_name)

            col_metas = []
            for col in columns_raw:
                col_name = col["name"]
                col_type = str(col["type"])
                is_pk = col_name in pk_cols or col.get("primary_key", False)
                col_metas.append(
                    ColumnMeta(
                        name=col_name,
                        data_type=col_type,
                        nullable=col.get("nullable", True),
                        primary_key=bool(is_pk),
                        default=str(col.get("default", "")) if col.get("default") else None,
                    )
                )

            # Query row count safely
            row_count = 0
            try:
                count_res = self.db.execute_query(f"SELECT COUNT(*) as count FROM {table_name}", read_only=True)
                if count_res.success and count_res.rows:
                    row_count = int(list(count_res.rows[0].values())[0])
            except Exception:
                row_count = 0

            schema_info.tables[table_name] = TableMeta(
                name=table_name,
                columns=col_metas,
                foreign_keys=fks_raw,
                row_count=row_count,
            )

        return schema_info

    def get_sample_rows(self, table_name: str, limit: int = 5) -> QueryResult:
        """Fetch sample records for a table."""
        return self.db.execute_query(f"SELECT * FROM {table_name} LIMIT {limit}", read_only=True)
