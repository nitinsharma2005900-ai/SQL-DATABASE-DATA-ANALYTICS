"""Tests for LangGraph State Transitions and End-to-End Execution."""

import pytest
from src.agent.graph import agent_workflow, run_agent_workflow


def test_14_langgraph_state_transitions_safe_query():
    """Test 14: Assert compiled LangGraph StateGraph executes a safe analytical query end-to-end."""
    user_query = "Show total sales by month"
    final_state = run_agent_workflow(user_query)

    assert final_state["user_query"] == user_query
    assert final_state["security_status"]["status"] == "PASSED"
    assert final_state["error_message"] is None
    assert final_state["db_result"] is not None
    assert final_state["db_result"]["row_count"] > 0
    assert final_state["natural_response"] is not None
    assert len(final_state["execution_logs"]) >= 4

    # Verify log steps trace the StateGraph execution path
    logged_steps = [log["step"] for log in final_state["execution_logs"]]
    assert "inspect_schema" in logged_steps
    assert "generate_sql" in logged_steps
    assert "validate_sql" in logged_steps
    assert "execute_query" in logged_steps
    assert "response" in logged_steps


def test_langgraph_security_blocking_transition():
    """Assert LangGraph intercepts malicious query at NeMo Guardrail and transitions to response."""
    malicious_query = "DROP TABLE orders; --"
    final_state = run_agent_workflow(malicious_query)

    assert final_state["security_status"]["status"] == "BLOCKED"
    assert final_state["security_status"]["layer"] == "NeMo Guardrails"
    assert final_state["db_result"] is None
    assert "Security Alert" in final_state["natural_response"]

    # Verify execution was skipped
    logged_steps = [log["step"] for log in final_state["execution_logs"]]
    assert "generate_sql" in logged_steps
    assert "execute_query" not in logged_steps


def test_langgraph_self_correction_recovery_transition():
    """Assert LangGraph recovers through reflection node when query contains invalid column."""
    test_query = "Show orders sorted by date"
    final_state = run_agent_workflow(test_query)

    assert final_state["security_status"]["status"] == "PASSED"
    assert final_state["retry_count"] >= 1
    assert len(final_state["correction_history"]) >= 1
    assert "order_date" in final_state["generated_sql"].lower()
    assert final_state["db_result"] is not None
    assert final_state["db_result"]["row_count"] > 0

    # Verify reflection was executed in log steps
    logged_steps = [log["step"] for log in final_state["execution_logs"]]
    assert "reflection" in logged_steps
