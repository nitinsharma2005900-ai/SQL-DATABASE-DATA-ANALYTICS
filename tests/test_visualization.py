"""Tests for Plotly Chart Generation Engine."""

import pytest
import plotly.graph_objects as go
from src.visualization.charts import (
    auto_generate_chart,
    create_bar_chart,
    create_line_chart,
    create_pie_chart,
    get_column_types,
)
import pandas as pd


def test_13_plotly_chart_generation():
    """Test 13: Assert Plotly chart generation for bar, line, and pie charts."""
    sample_data = [
        {"month": "2024-01", "sales": 1500.50},
        {"month": "2024-02", "sales": 2300.00},
        {"month": "2024-03", "sales": 3100.25},
    ]

    # Test auto line chart for temporal data
    fig_line = auto_generate_chart(sample_data, chart_type="line")
    assert isinstance(fig_line, go.Figure)
    assert len(fig_line.data) > 0

    # Test auto bar chart for category data
    category_data = [
        {"category": "Electronics", "revenue": 12500},
        {"category": "Furniture", "revenue": 8400},
        {"category": "Accessories", "revenue": 6200},
        {"category": "Software", "revenue": 9500},
    ]
    fig_bar = auto_generate_chart(category_data, chart_type="bar")
    assert isinstance(fig_bar, go.Figure)
    assert len(fig_bar.data) > 0

    # Test auto pie chart
    fig_pie = auto_generate_chart(category_data, chart_type="pie")
    assert isinstance(fig_pie, go.Figure)
    assert len(fig_pie.data) > 0


def test_column_type_extraction():
    """Assert helper correctly partitions numeric and categorical columns."""
    df = pd.DataFrame({
        "name": ["Alice", "Bob"],
        "age": [25, 30],
        "salary": [75000.0, 90000.0],
        "department": ["IT", "HR"],
    })
    cat_cols, num_cols = get_column_types(df)
    assert "name" in cat_cols
    assert "department" in cat_cols
    assert "age" in num_cols
    assert "salary" in num_cols
