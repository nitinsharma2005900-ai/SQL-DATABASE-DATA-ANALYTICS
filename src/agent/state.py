"""LangGraph State Definitions for SQL Analytics Agent."""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """Typed state dictionary tracked across LangGraph nodes."""
    user_query: str
    generated_sql: str
    db_result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: int
    schema_info: str
    execution_logs: List[Dict[str, Any]]
    security_status: Dict[str, Any]
    chart_type: Optional[str]
    natural_response: Optional[str]
    correction_history: List[Dict[str, Any]]
