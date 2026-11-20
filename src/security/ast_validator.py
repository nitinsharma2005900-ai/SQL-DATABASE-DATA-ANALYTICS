"""SQLGlot AST Security Validation Engine (Layer B)."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError


@dataclass
class ASTValidationResult:
    """Outcome of SQLGlot AST validation."""
    is_valid: bool
    error: Optional[str] = None
    statement_type: Optional[str] = None
    tables_referenced: List[str] = field(default_factory=list)
    columns_referenced: List[str] = field(default_factory=list)


# Destructive / Write operations strictly disallowed in AST
DISALLOWED_EXPRESSION_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.TruncateTable,
    exp.Command,
    exp.Pragma,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
    exp.Merge,
    exp.Copy,
)

# Dangerous SQL functions (file access, command execution, DoS timing attacks)
DANGEROUS_FUNCTIONS = {
    "load_file",
    "into_outfile",
    "into_dumpfile",
    "sys_eval",
    "sys_exec",
    "xp_cmdshell",
    "benchmark",
    "sleep",
    "pg_sleep",
    "sp_executesql",
    "system",
    "delay",
}


class ASTSQLValidator:
    """Layer B Security: Validates generated SQL through SQLGlot AST parsing."""

    def __init__(self, dialect: str = "sqlite") -> None:
        self.dialect = dialect

    def validate(
        self,
        sql_query: str,
        valid_tables: Optional[Dict[str, List[str]]] = None,
    ) -> ASTValidationResult:
        """Parse and validate SQL query against strict read-only security policies.
        
        Args:
            sql_query: Raw SQL query string to parse.
            valid_tables: Optional dictionary mapping table names to lists of column names.
        """
        if not sql_query or not sql_query.strip():
            return ASTValidationResult(is_valid=False, error="SQL query is empty.")

        clean_sql = sql_query.strip().rstrip(";")

        # 1. Parse into AST statements
        try:
            statements = sqlglot.parse(clean_sql, read=self.dialect)
        except ParseError as exc:
            return ASTValidationResult(
                is_valid=False,
                error=f"SQL Syntax Error: Unable to parse query AST ({str(exc)})",
            )
        except Exception as exc:
            return ASTValidationResult(
                is_valid=False,
                error=f"SQL Parsing Failure: {str(exc)}",
            )

        if not statements:
            return ASTValidationResult(is_valid=False, error="No valid SQL statement found.")

        # 2. Reject multiple SQL statements (SQL Injection / statement stacking)
        if len(statements) > 1:
            return ASTValidationResult(
                is_valid=False,
                error="Security Violation: Multiple SQL statements detected. Stacking queries is strictly prohibited.",
            )

        stmt = statements[0]

        # 3. Reject any write or destructive AST node anywhere in the parse tree
        for node in stmt.walk():
            if isinstance(node, DISALLOWED_EXPRESSION_TYPES):
                stmt_name = node.__class__.__name__.replace("exp.", "").upper()
                return ASTValidationResult(
                    is_valid=False,
                    statement_type=stmt_name,
                    error=f"Security Violation: Write or destructive operation '{stmt_name}' detected. Only read-only SELECT queries are allowed.",
                )

        # 4. Verify Root Statement is a SELECT or SELECT with CTE
        is_select = isinstance(stmt, (exp.Select, exp.Union))
        if not is_select:
            # Check for CTE (WITH ... SELECT)
            if isinstance(stmt, exp.Query) or hasattr(stmt, "this") and isinstance(stmt.this, exp.Select):
                is_select = True
            elif isinstance(stmt, exp.Expression) and stmt.find(exp.Select):
                # Ensure the main query body is a select
                is_select = True

        if not is_select:
            return ASTValidationResult(
                is_valid=False,
                statement_type=stmt.__class__.__name__,
                error=f"Security Violation: Non-SELECT root statement type '{stmt.__class__.__name__}' is not permitted.",
            )

        # 5. Check for Dangerous SQL Functions
        for func in stmt.find_all((exp.Anonymous, exp.Func)):
            func_name = func.name.lower() if hasattr(func, "name") and func.name else ""
            if func_name in DANGEROUS_FUNCTIONS:
                return ASTValidationResult(
                    is_valid=False,
                    error=f"Security Violation: Call to dangerous function '{func_name}' is forbidden.",
                )

        # 6. Extract CTE definitions so they aren't falsely flagged as missing tables
        cte_names: Set[str] = set()
        for with_node in stmt.find_all(exp.With):
            for cte in with_node.expressions:
                if hasattr(cte, "alias") and cte.alias:
                    cte_names.add(cte.alias.lower())

        # 7. Extract Referenced Tables
        tables: Set[str] = set()
        for table in stmt.find_all(exp.Table):
            t_name = table.name.lower()
            if t_name and t_name not in cte_names:
                tables.add(t_name)

        # 8. Extract Referenced Columns and Column Aliases
        columns: Set[str] = set()
        column_aliases: Set[str] = set()
        for alias_node in stmt.find_all(exp.Alias):
            if alias_node.alias:
                column_aliases.add(alias_node.alias.lower())

        for col in stmt.find_all(exp.Column):
            c_name = col.name.lower()
            if c_name and c_name != "*":
                columns.add(c_name)

        # 9. Table Validation (ensure query only targets known business tables)
        if valid_tables:
            valid_table_names_lower = {k.lower(): [c.lower() for c in v] for k, v in valid_tables.items()}

            # Check that every referenced table exists in schema
            for tbl in tables:
                if tbl not in valid_table_names_lower:
                    return ASTValidationResult(
                        is_valid=False,
                        statement_type="SELECT",
                        tables_referenced=list(tables),
                        columns_referenced=list(columns),
                        error=f"Security Violation: Referenced table '{tbl}' does not exist in the authorized schema.",
                    )

        return ASTValidationResult(
            is_valid=True,
            error=None,
            statement_type="SELECT",
            tables_referenced=list(tables),
            columns_referenced=list(columns),
        )
