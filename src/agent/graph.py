"""Compiled LangGraph Workflow for SQL Analytics Agent."""

from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END

from config.settings import settings
from .state import AgentState
from .nodes import (
    inspect_schema_node,
    generate_sql_node,
    validate_sql_node,
    execute_query_node,
    reflection_node,
    response_node,
)


def route_after_validation(state: AgentState) -> Literal["execute_query", "response"]:
    """Conditional Edge: Route to execution if safe, or direct to response if blocked."""
    security = state.get("security_status", {})
    if security.get("status") == "BLOCKED":
        return "response"
    return "execute_query"


def route_after_execution(state: AgentState) -> Literal["reflection", "response"]:
    """Conditional Edge: Route to reflection if query failed and retries remain, else to response."""
    error = state.get("error_message")
    retry_count = state.get("retry_count", 0)

    if error and retry_count < settings.MAX_RETRIES:
        return "reflection"
    return "response"


def create_sql_agent_graph():
    """Construct and compile the LangGraph StateGraph workflow."""
    builder = StateGraph(AgentState)

    # 1. Register all nodes
    builder.add_node("inspect_schema", inspect_schema_node)
    builder.add_node("generate_sql", generate_sql_node)
    builder.add_node("validate_sql", validate_sql_node)
    builder.add_node("execute_query", execute_query_node)
    builder.add_node("reflection", reflection_node)
    builder.add_node("response", response_node)

    # 2. Add linear and conditional edges
    builder.add_edge(START, "inspect_schema")
    builder.add_edge("inspect_schema", "generate_sql")
    builder.add_edge("generate_sql", "validate_sql")

    # Conditional edge from validate_sql
    builder.add_conditional_edges(
        "validate_sql",
        route_after_validation,
        {
            "execute_query": "execute_query",
            "response": "response",
        },
    )

    # Conditional edge from execute_query
    builder.add_conditional_edges(
        "execute_query",
        route_after_execution,
        {
            "reflection": "reflection",
            "response": "response",
        },
    )

    # Edge from reflection routes back through validation before execution!
    builder.add_edge("reflection", "validate_sql")

    # Final edge to END
    builder.add_edge("response", END)

    # Compile the graph
    return builder.compile()


# Global compiled workflow instance
agent_workflow = create_sql_agent_graph()


def run_agent_workflow(user_query: str) -> AgentState:
    """Convenience helper to run user query through the compiled LangGraph workflow."""
    initial_state: AgentState = {
        "user_query": user_query,
        "generated_sql": "",
        "db_result": None,
        "error_message": None,
        "retry_count": 0,
        "schema_info": "",
        "execution_logs": [],
        "security_status": {"status": "INITIALIZED", "layer": None, "reason": None},
        "chart_type": None,
        "natural_response": None,
        "correction_history": [],
    }

    final_state = agent_workflow.invoke(initial_state)
    return final_state
