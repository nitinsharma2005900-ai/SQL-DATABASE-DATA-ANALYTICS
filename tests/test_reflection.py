"""Tests for Self-Correction, Reflection Node, and Retry Enforcement."""

from unittest.mock import Mock, patch
import pytest
from src.agent.llm import LLMService
from src.agent.nodes import reflection_node, execute_query_node
from src.agent.state import AgentState
from src.db.connection import QueryResult


def test_10_invalid_column_error_detection(db_manager):
    """Test 10: Assert execution node detects invalid column error from database."""
    # Query orders with created_at which does not exist in orders
    query = "SELECT * FROM orders ORDER BY created_at;"
    res = db_manager.execute_query(query, read_only=True)

    assert res.success is False
    assert res.error is not None
    assert "no such column: created_at" in res.error.lower()


def test_11_self_correction_workflow():
    """Test 11: Assert reflection node diagnoses column error and successfully corrects SQL."""
    llm = LLMService()
    user_query = "Show orders sorted by date."
    schema_info = "Table: orders\n    - id (INTEGER)\n    - order_date (DATE)\n    - total_amount (FLOAT)"
    failed_sql = "SELECT * FROM orders ORDER BY created_at;"
    error_msg = "no such column: created_at"

    corrected_sql = llm.reflect_and_correct(
        user_query=user_query,
        schema_info=schema_info,
        failed_sql=failed_sql,
        error_message=error_msg,
    )

    assert "order_date" in corrected_sql.lower()
    assert "created_at" not in corrected_sql.lower()


def test_gemini_failure_is_logged_before_deterministic_fallback(caplog):
    """Make live-provider failures visible instead of silently masking them."""
    llm = LLMService()
    llm._gemini_llm = Mock()
    llm._gemini_llm.invoke.side_effect = RuntimeError("provider unavailable")

    sql = llm.generate_sql("Calculate total revenue", "Table: orders")

    assert "SUM(total_amount)" in sql
    assert "Gemini SQL generation failed (RuntimeError)" in caplog.text
    assert llm.last_provider_error == "RuntimeError"


def test_12_maximum_3_retries_enforcement():
    """Test 12: Assert workflow enforces a maximum of 3 retries without looping infinitely."""
    from src.agent.graph import agent_workflow

    # Patch db_manager.execute_query to simulate persistent failure
    with patch("src.agent.nodes.db_manager.execute_query") as mock_exec:
        mock_exec.return_value = QueryResult(
            success=False,
            query="SELECT * FROM orders",
            error="OperationalError: database locked or table corrupted",
        )

        initial_state: AgentState = {
            "user_query": "Show orders sorted by date",
            "generated_sql": "",
            "db_result": None,
            "error_message": None,
            "retry_count": 0,
            "schema_info": "",
            "execution_logs": [],
            "security_status": {"status": "INIT"},
            "chart_type": None,
            "natural_response": None,
            "correction_history": [],
        }

        final_state = agent_workflow.invoke(initial_state)

        # Retries must cap at 3
        assert final_state["retry_count"] == 3
        assert len(final_state["correction_history"]) == 3
        assert final_state["db_result"] is None
        assert "attempted self-correction 3 time(s)" in final_state["natural_response"]
