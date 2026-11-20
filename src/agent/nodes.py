"""LangGraph Node Implementations for SQL Analytics Agent."""

from typing import Any, Dict, List, Optional
from src.db.connection import get_db_manager
from src.db.schema import DatabaseInspector
from src.security.nemo_guard import NeMoInputGuard
from src.security.ast_validator import ASTSQLValidator
from .state import AgentState
from .llm import llm_service
from config.settings import settings


# Initialize security inspectors and validators
nemo_guard = NeMoInputGuard()
ast_validator = ASTSQLValidator()
db_inspector = DatabaseInspector()
db_manager = get_db_manager()


def inspect_schema_node(state: AgentState) -> Dict[str, Any]:
    """Node 1: Inspect database schema using SQLAlchemy reflection."""
    schema_info_obj = db_inspector.inspect_schema()
    schema_prompt = schema_info_obj.to_prompt_string()

    logs = list(state.get("execution_logs", []))
    logs.append({
        "step": "inspect_schema",
        "status": "COMPLETED",
        "message": f"Inspected database schema: {len(schema_info_obj.tables)} tables reflected ({', '.join(schema_info_obj.get_table_names())}).",
    })

    return {
        "schema_info": schema_prompt,
        "execution_logs": logs,
    }


def generate_sql_node(state: AgentState) -> Dict[str, Any]:
    """Node 2: Convert user query to SQL after passing Layer A (NeMo Guardrails)."""
    user_query = state.get("user_query", "").strip()
    logs = list(state.get("execution_logs", []))

    # Layer A: NeMo Guardrails Input Validation
    guard_res = nemo_guard.validate(user_query)
    if not guard_res.is_safe:
        logs.append({
            "step": "generate_sql",
            "status": "BLOCKED",
            "layer": "NeMo Guardrails",
            "category": guard_res.blocked_category,
            "message": guard_res.reason,
        })
        return {
            "generated_sql": "",
            "security_status": {
                "status": "BLOCKED",
                "layer": "NeMo Guardrails",
                "reason": guard_res.reason,
                "category": guard_res.blocked_category,
            },
            "error_message": guard_res.reason,
            "execution_logs": logs,
        }

    # Generate SQL via Gemini or deterministic fallback
    retry_count = state.get("retry_count", 0)
    sql_query = llm_service.generate_sql(
        user_query=user_query,
        schema_info=state.get("schema_info", ""),
        retry_count=retry_count,
    )

    if llm_service.last_provider_error:
        logs.append({
            "step": "llm_provider",
            "status": "FALLBACK",
            "message": (
                f"Gemini request failed ({llm_service.last_provider_error}); "
                "using deterministic SQL fallback."
            ),
        })

    logs.append({
        "step": "generate_sql",
        "status": "SUCCESS",
        "sql": sql_query,
        "message": f"Generated SQL query (Attempt {retry_count + 1}).",
    })

    return {
        "generated_sql": sql_query,
        "security_status": {
            "status": "PENDING_VALIDATION",
            "layer": "NeMo Guardrails",
            "reason": "Passed input guardrail filters.",
        },
        "execution_logs": logs,
    }


def validate_sql_node(state: AgentState) -> Dict[str, Any]:
    """Node 3: Validate generated SQL AST using SQLGlot (Layer B)."""
    logs = list(state.get("execution_logs", []))
    security = state.get("security_status", {})

    # If already blocked upstream by NeMo Guardrails, do not re-validate empty SQL
    if security.get("status") == "BLOCKED":
        return {
            "execution_logs": logs,
        }

    generated_sql = state.get("generated_sql", "").strip()

    # Build schema table/column mapping for AST verification
    schema_obj = db_inspector.inspect_schema()
    valid_tables = {tbl: schema_obj.get_column_names(tbl) for tbl in schema_obj.get_table_names()}

    ast_res = ast_validator.validate(generated_sql, valid_tables=valid_tables)

    if not ast_res.is_valid:
        logs.append({
            "step": "validate_sql",
            "status": "BLOCKED",
            "layer": "SQLGlot AST",
            "message": ast_res.error,
            "sql": generated_sql,
        })
        return {
            "security_status": {
                "status": "BLOCKED",
                "layer": "SQLGlot AST",
                "reason": ast_res.error,
            },
            "error_message": ast_res.error,
            "execution_logs": logs,
        }

    logs.append({
        "step": "validate_sql",
        "status": "PASSED",
        "layer": "SQLGlot AST",
        "message": "AST validation successful: Valid read-only SELECT query.",
        "sql": generated_sql,
    })

    return {
        "security_status": {
            "status": "PASSED",
            "layer": "SQLGlot AST",
            "reason": "Valid read-only SELECT query.",
        },
        "error_message": None,
        "execution_logs": logs,
    }


def execute_query_node(state: AgentState) -> Dict[str, Any]:
    """Node 4: Safely execute validated SQL on the database using SQLAlchemy."""
    logs = list(state.get("execution_logs", []))
    security = state.get("security_status", {})

    if security.get("status") == "BLOCKED":
        logs.append({
            "step": "execute_query",
            "status": "SKIPPED",
            "message": "Query execution skipped due to security block.",
        })
        return {
            "execution_logs": logs,
        }

    sql_query = state.get("generated_sql", "")
    query_result = db_manager.execute_query(sql_query, read_only=True)

    if not query_result.success:
        logs.append({
            "step": "execute_query",
            "status": "FAILED",
            "error": query_result.error,
            "duration_ms": query_result.execution_time_ms,
            "sql": sql_query,
            "message": f"Database execution error: {query_result.error}",
        })
        return {
            "error_message": query_result.error,
            "db_result": None,
            "execution_logs": logs,
        }

    logs.append({
        "step": "execute_query",
        "status": "SUCCESS",
        "row_count": query_result.row_count,
        "duration_ms": query_result.execution_time_ms,
        "sql": sql_query,
        "message": f"Query executed successfully in {query_result.execution_time_ms} ms. Returned {query_result.row_count} rows.",
    })

    return {
        "error_message": None,
        "db_result": {
            "columns": query_result.columns,
            "rows": query_result.rows,
            "row_count": query_result.row_count,
            "execution_time_ms": query_result.execution_time_ms,
        },
        "execution_logs": logs,
    }


def reflection_node(state: AgentState) -> Dict[str, Any]:
    """Node 5: Reflect on SQL execution failure, diagnose error, and self-correct query."""
    logs = list(state.get("execution_logs", []))
    retry_count = state.get("retry_count", 0) + 1
    failed_sql = state.get("generated_sql", "")
    error_msg = state.get("error_message", "Unknown error")
    user_query = state.get("user_query", "")
    schema_info = state.get("schema_info", "")

    corrected_sql = llm_service.reflect_and_correct(
        user_query=user_query,
        schema_info=schema_info,
        failed_sql=failed_sql,
        error_message=error_msg,
    )

    if llm_service.last_provider_error:
        logs.append({
            "step": "llm_provider",
            "status": "FALLBACK",
            "message": (
                f"Gemini correction failed ({llm_service.last_provider_error}); "
                "using deterministic SQL fallback."
            ),
        })

    history = list(state.get("correction_history", []))
    history.append({
        "attempt": retry_count,
        "failed_sql": failed_sql,
        "error": error_msg,
        "corrected_sql": corrected_sql,
    })

    logs.append({
        "step": "reflection",
        "status": "CORRECTION_PRODUCED",
        "attempt": retry_count,
        "failed_sql": failed_sql,
        "error": error_msg,
        "corrected_sql": corrected_sql,
        "message": f"Self-correction loop (Retry {retry_count}/{settings.MAX_RETRIES}): Caught '{error_msg}'. Regenerated SQL: {corrected_sql}",
    })

    return {
        "retry_count": retry_count,
        "generated_sql": corrected_sql,
        "error_message": None,  # Reset error for new attempt
        "correction_history": history,
        "execution_logs": logs,
    }


def _detect_chart_type(columns: List[str], rows: List[Dict[str, Any]]) -> Optional[str]:
    """Heuristic rule engine to detect optimal chart visualization."""
    if not rows or len(rows) == 0:
        return None

    if len(rows) == 1 and len(columns) <= 3:
        return "kpi"

    # Identify numeric and categorical columns
    numeric_cols = []
    categorical_cols = []
    first_row = rows[0]
    for col in columns:
        val = first_row.get(col)
        if isinstance(val, (int, float)):
            numeric_cols.append(col)
        elif isinstance(val, str):
            categorical_cols.append(col)

    if not numeric_cols:
        return "table"

    # Check for date or month columns -> line chart
    for cat in categorical_cols:
        cat_lower = cat.lower()
        if any(term in cat_lower for term in ("date", "month", "year", "time", "day", "period")):
            return "line"

    # Categorical + Numeric with 2-15 categories -> bar or pie
    if categorical_cols and numeric_cols:
        if 2 <= len(rows) <= 6:
            return "pie"
        return "bar"

    if len(numeric_cols) >= 1:
        return "bar"

    return "table"


def response_node(state: AgentState) -> Dict[str, Any]:
    """Node 6: Format query results, natural-language explanation, and chart recommendation."""
    logs = list(state.get("execution_logs", []))
    security = state.get("security_status", {})
    error_msg = state.get("error_message")
    db_result = state.get("db_result")
    user_query = state.get("user_query", "")

    if security.get("status") == "BLOCKED":
        natural_response = (
            f"🛡️ **Security Alert: Query Blocked**\n\n"
            f"Your request was intercepted by **{security.get('layer', 'Security System')}**.\n\n"
            f"**Reason:** {security.get('reason')}\n\n"
            f"*No database modifications or unauthorized operations are permitted.*"
        )
        chart_type = None
    elif error_msg:
        retry_count = state.get("retry_count", 0)
        natural_response = (
            f"⚠️ **Query Execution Failed**\n\n"
            f"The agent attempted self-correction {retry_count} time(s), but the query could not be resolved.\n\n"
            f"**Error Details:** `{error_msg}`"
        )
        chart_type = None
    elif db_result and db_result.get("rows") is not None:
        columns = db_result.get("columns", [])
        rows = db_result.get("rows", [])
        chart_type = _detect_chart_type(columns, rows)
        natural_response = llm_service.generate_summary(user_query, columns, rows)
    else:
        natural_response = "No data returned for this query."
        chart_type = None

    provider_fallbacks = [
        entry for entry in logs
        if entry.get("step") == "llm_provider" and entry.get("status") == "FALLBACK"
    ]
    if provider_fallbacks:
        natural_response = (
            f"⚠️ Gemini is unavailable ({provider_fallbacks[-1]['message']}). "
            "This response uses the limited deterministic fallback and may not match your question.\n\n"
            f"{natural_response}"
        )

    logs.append({
        "step": "response",
        "status": "COMPLETED",
        "message": "Final response and visualization payload generated.",
    })

    return {
        "natural_response": natural_response,
        "chart_type": chart_type,
        "execution_logs": logs,
    }
