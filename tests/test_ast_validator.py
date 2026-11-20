"""Tests for Layer B: SQLGlot AST Validation."""

import pytest
from src.security.ast_validator import ASTSQLValidator


def test_1_safe_select_query_acceptance(ast_validator):
    """Test 1: Assert safe SELECT queries are accepted."""
    query = "SELECT id, name, city FROM customers WHERE city = 'New York' ORDER BY name LIMIT 10;"
    result = ast_validator.validate(query)
    assert result.is_valid is True
    assert result.error is None
    assert result.statement_type == "SELECT"
    assert "customers" in result.tables_referenced


def test_safe_select_with_cte(ast_validator):
    """Assert safe SELECT queries using CTEs are accepted."""
    cte_query = """
    WITH monthly_sales AS (
        SELECT strftime('%Y-%m', order_date) AS month, SUM(total_amount) AS revenue
        FROM orders
        GROUP BY month
    )
    SELECT month, revenue FROM monthly_sales ORDER BY revenue DESC;
    """
    result = ast_validator.validate(cte_query)
    assert result.is_valid is True
    assert result.error is None


def test_2_delete_query_rejection(ast_validator):
    """Test 2: Assert DELETE query is rejected."""
    query = "DELETE FROM customers WHERE id = 1;"
    result = ast_validator.validate(query)
    assert result.is_valid is False
    assert "delete" in result.error.lower()
    assert result.statement_type == "DELETE"


def test_3_drop_table_query_rejection(ast_validator):
    """Test 3: Assert DROP TABLE query is rejected."""
    query = "DROP TABLE orders;"
    result = ast_validator.validate(query)
    assert result.is_valid is False
    assert "drop" in result.error.lower()
    assert result.statement_type == "DROP"


def test_4_update_query_rejection(ast_validator):
    """Test 4: Assert UPDATE query is rejected."""
    query = "UPDATE orders SET total_amount = 0 WHERE id = 5;"
    result = ast_validator.validate(query)
    assert result.is_valid is False
    assert "update" in result.error.lower()
    assert result.statement_type == "UPDATE"


def test_5_multiple_sql_statements_rejection(ast_validator):
    """Test 5: Assert multiple SQL statements / query stacking is rejected."""
    query = "SELECT * FROM orders; DROP TABLE customers;"
    result = ast_validator.validate(query)
    assert result.is_valid is False
    assert "multiple sql statements detected" in result.error.lower()


def test_insert_and_truncate_rejection(ast_validator):
    """Assert INSERT and TRUNCATE queries are rejected."""
    insert_q = "INSERT INTO products (product_name, category, price) VALUES ('Hacked', 'Bug', 0);"
    res_ins = ast_validator.validate(insert_q)
    assert res_ins.is_valid is False

    trunc_q = "TRUNCATE TABLE order_items;"
    res_trunc = ast_validator.validate(trunc_q)
    assert res_trunc.is_valid is False


def test_dangerous_function_rejection(ast_validator):
    """Assert dangerous functions like load_file and sleep are rejected."""
    sleep_q = "SELECT * FROM orders WHERE sleep(5) = 0;"
    res = ast_validator.validate(sleep_q)
    assert res.is_valid is False
    assert "dangerous function" in res.error.lower()
