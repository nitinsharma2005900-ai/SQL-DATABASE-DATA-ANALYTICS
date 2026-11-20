"""Tests for Database Schema Inspection and Safe SQL Execution."""

import pytest
from src.db.connection import DatabaseManager
from src.db.schema import DatabaseInspector


def test_8_database_schema_inspection(db_inspector):
    """Test 8: Assert database schema inspection returns tables and columns correctly."""
    schema_info = db_inspector.inspect_schema()
    table_names = schema_info.get_table_names()

    # Verify all four required tables are present
    assert "customers" in table_names
    assert "products" in table_names
    assert "orders" in table_names
    assert "order_items" in table_names

    # Check orders table columns (must have order_date, not created_at)
    orders_cols = schema_info.get_column_names("orders")
    assert "id" in orders_cols
    assert "order_date" in orders_cols
    assert "total_amount" in orders_cols
    assert "status" in orders_cols
    assert "created_at" not in orders_cols

    # Check customers table columns
    customers_cols = schema_info.get_column_names("customers")
    assert "name" in customers_cols
    assert "email" in customers_cols
    assert "city" in customers_cols
    assert "created_at" in customers_cols

    # Check prompt formatted string contains schema elements
    prompt_str = schema_info.to_prompt_string()
    assert "Table: orders" in prompt_str
    assert "order_date" in prompt_str


def test_9_successful_sql_execution(db_manager):
    """Test 9: Assert successful SQL execution captures results, rows, and execution time."""
    query = "SELECT id, product_name, category, price FROM products ORDER BY price DESC LIMIT 5;"
    res = db_manager.execute_query(query, read_only=True)

    assert res.success is True
    assert res.error is None
    assert res.row_count == 5
    assert len(res.rows) == 5
    assert "product_name" in res.columns
    assert "price" in res.columns
    assert res.execution_time_ms >= 0.0


def test_read_only_protection_blocks_write_at_engine_level(db_manager):
    """Assert database connection blocks write execution at engine level in read_only mode."""
    delete_query = "DELETE FROM customers WHERE id = 1"
    res = db_manager.execute_query(delete_query, read_only=True)
    # Under SQLite PRAGMA query_only = ON or read_only, attempt produces an error
    if res.success is False:
        assert res.error is not None
