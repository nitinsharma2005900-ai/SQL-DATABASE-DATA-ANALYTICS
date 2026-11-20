"""Plotly Interactive Visualization Engine with Dark Navy & Glassmorphic Styling."""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# Theme Palette: Dark Navy background with Purple/Blue gradient accents
THEME_BG = "#0f172a"
THEME_PLOT_BG = "rgba(15, 23, 42, 0.7)"
THEME_FONT_COLOR = "#f8fafc"
THEME_GRID_COLOR = "rgba(51, 65, 85, 0.4)"
COLOR_SEQUENCE = [
    "#8b5cf6",  # Vibrant Purple
    "#3b82f6",  # Royal Blue
    "#06b6d4",  # Cyan
    "#6366f1",  # Indigo
    "#a855f7",  # Violet
    "#ec4899",  # Pink
    "#10b981",  # Emerald
    "#f59e0b",  # Amber
]


def apply_custom_layout(fig: go.Figure, title: Optional[str] = None) -> go.Figure:
    """Apply unified dark navy and glassmorphic styling to Plotly figures."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=THEME_PLOT_BG,
        font=dict(color=THEME_FONT_COLOR, family="Segoe UI, Inter, sans-serif", size=13),
        title=dict(
            text=f"<b>{title}</b>" if title else "",
            font=dict(size=16, color="#f1f5f9"),
            x=0.02,
            y=0.96,
        ),
        margin=dict(l=40, r=30, t=50, b=40),
        xaxis=dict(
            showgrid=True,
            gridcolor=THEME_GRID_COLOR,
            zeroline=False,
            color="#cbd5e1",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=THEME_GRID_COLOR,
            zeroline=False,
            color="#cbd5e1",
        ),
        hoverlabel=dict(
            bgcolor="#1e293b",
            font_size=12,
            font_family="Segoe UI, Inter, sans-serif",
            bordercolor="#6366f1",
        ),
        legend=dict(
            bgcolor="rgba(15, 23, 42, 0.6)",
            bordercolor="rgba(99, 102, 241, 0.3)",
            borderwidth=1,
            font=dict(color="#e2e8f0"),
        ),
    )
    return fig


def get_column_types(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    """Partition DataFrame columns into categorical/text and numeric types."""
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=["number"]).columns.tolist()
    return categorical_cols, numeric_cols


def create_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: Optional[str] = None,
    color: Optional[str] = None,
) -> go.Figure:
    """Generate styled interactive bar chart."""
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color or x,
        color_discrete_sequence=COLOR_SEQUENCE,
        text_auto=".2s" if df[y].dtype in ["float64", "float32"] else True,
    )
    fig.update_traces(
        marker=dict(line=dict(width=1, color="rgba(255,255,255,0.2)")),
        opacity=0.92,
    )
    return apply_custom_layout(fig, title or f"{y.replace('_', ' ').title()} by {x.replace('_', ' ').title()}")


def create_line_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: Optional[str] = None,
) -> go.Figure:
    """Generate styled interactive line chart."""
    fig = px.line(
        df,
        x=x,
        y=y,
        markers=True,
        color_discrete_sequence=[COLOR_SEQUENCE[1]],
    )
    fig.update_traces(
        line=dict(width=3, color="#3b82f6"),
        marker=dict(size=8, color="#8b5cf6", line=dict(width=2, color="#ffffff")),
    )
    return apply_custom_layout(fig, title or f"{y.replace('_', ' ').title()} Over Time")


def create_pie_chart(
    df: pd.DataFrame,
    names: str,
    values: str,
    title: Optional[str] = None,
) -> go.Figure:
    """Generate styled interactive donut / pie chart."""
    fig = px.pie(
        df,
        names=names,
        values=values,
        hole=0.45,
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        marker=dict(line=dict(color="#0f172a", width=2)),
    )
    return apply_custom_layout(fig, title or f"Distribution of {values.replace('_', ' ').title()} by {names.replace('_', ' ').title()}")


def auto_generate_chart(
    data: List[Dict[str, Any]],
    chart_type: Optional[str] = None,
    x_col: Optional[str] = None,
    y_col: Optional[str] = None,
) -> Optional[go.Figure]:
    """Automatically determine and render the optimal Plotly chart for query results."""
    if not data:
        return None

    df = pd.DataFrame(data)
    if df.empty:
        return None

    cat_cols, num_cols = get_column_types(df)

    # Allow explicit overrides
    chosen_x = x_col or (cat_cols[0] if cat_cols else (df.columns[0] if len(df.columns) > 0 else None))
    chosen_y = y_col or (num_cols[0] if num_cols else None)

    if not chosen_x or not chosen_y:
        return None

    target_type = chart_type or "auto"
    if target_type == "auto":
        # Heuristic: Check if x looks like a date or month
        if any(term in chosen_x.lower() for term in ("date", "month", "year", "day", "time")):
            target_type = "line"
        elif 2 <= len(df) <= 6 and len(num_cols) >= 1:
            target_type = "pie"
        else:
            target_type = "bar"

    if target_type == "line":
        return create_line_chart(df, chosen_x, chosen_y)
    elif target_type == "pie":
        return create_pie_chart(df, chosen_x, chosen_y)
    elif target_type == "bar":
        return create_bar_chart(df, chosen_x, chosen_y)

    return create_bar_chart(df, chosen_x, chosen_y)
