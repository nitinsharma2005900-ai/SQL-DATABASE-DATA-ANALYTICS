"""SQL & Database Analytics AI Agent - Streamlit Dashboard.

Features:
- Dark Navy Glassmorphism UI
- LangGraph State Machine Integration
- NeMo Guardrails & SQLGlot AST Security Layers
- Self-Correction Reflection Loop & Telemetry
- Automatic Plotly Analytics Visualizations
- Database Explorer & Live Security Monitor
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from config.settings import settings
from src.agent.graph import run_agent_workflow
from src.agent.state import AgentState
from src.db.connection import get_db_manager
from src.db.schema import DatabaseInspector
from src.db.seed import seed_database
from src.visualization.charts import (
    auto_generate_chart,
    create_bar_chart,
    create_line_chart,
    create_pie_chart,
    get_column_types,
)

# Initialize Database and Seed if necessary
db_manager = get_db_manager()
seed_database(db_manager, force=False)
inspector = DatabaseInspector(db_manager)

# Streamlit Page Setup
st.set_page_config(
    page_title="SQL Analytics AI Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Glassmorphism & Dark Navy CSS
st.markdown(
    """
    <style>
    /* Dark Navy Base Theme */
    .stApp {
        background: linear-gradient(135deg, #090d16 0%, #0f172a 50%, #111827 100%);
        color: #f1f5f9;
        font-family: 'Segoe UI', Inter, -apple-system, sans-serif;
    }
    
    /* Header gradient text */
    .gradient-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #c084fc 0%, #818cf8 50%, #60a5fa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    
    .sub-header-text {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    
    /* Glassmorphic Metric Cards */
    .glass-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(139, 92, 246, 0.18);
        border-radius: 12px;
        padding: 1.1rem;
        box-shadow: 0 4px 24px 0 rgba(0, 0, 0, 0.25);
    }
    
    .metric-title {
        color: #94a3b8;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    
    .metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0.35rem 0;
    }
    
    .metric-subtitle {
        color: #64748b;
        font-size: 0.78rem;
    }
    
    /* Badges */
    .badge-safe {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.35);
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .badge-blocked {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.35);
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .badge-correction {
        background: rgba(168, 85, 247, 0.15);
        color: #c084fc;
        border: 1px solid rgba(168, 85, 247, 0.35);
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .badge-demo {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.35);
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "history" not in st.session_state:
    st.session_state.history = []
if "latest_state" not in st.session_state:
    st.session_state.latest_state = None
if "safe_count" not in st.session_state:
    st.session_state.safe_count = 0
if "blocked_count" not in st.session_state:
    st.session_state.blocked_count = 0
if "security_events" not in st.session_state:
    st.session_state.security_events = []
if "prompt_input" not in st.session_state:
    st.session_state.prompt_input = ""

# Sidebar: System Status & Configuration
with st.sidebar:
    st.markdown("### ⚡ Agent Control Hub")

    # LLM Provider Status
    if settings.is_demo_mode:
        st.markdown(
            """
            <div class='glass-card'>
                <span class='badge-demo'>🟡 Demo / Simulation Mode</span>
                <p style='font-size: 0.8rem; color: #94a3b8; margin-top: 0.5rem;'>
                    Deterministic local reasoning active. Set <code>GEMINI_API_KEY</code> in <code>.env</code> to connect live Google Gemini.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class='glass-card'>
                <span class='badge-safe'>🟢 Gemini Configured</span>
                <p style='font-size: 0.8rem; color: #94a3b8; margin-top: 0.5rem;'>
                    Model: <b>{settings.GEMINI_MODEL}</b>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Database Info
    st.markdown("#### 🗄️ Database Connection")
    db_connected = db_manager.test_connection()
    if db_connected:
        st.markdown("<span class='badge-safe'>Connected • Online</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='badge-blocked'>Connection Failed</span>", unsafe_allow_html=True)
    
    st.caption(f"Dialect: `{db_manager.engine.dialect.name.upper()}`")
    st.caption(f"Read-Only Protection: `{'Enabled' if settings.READ_ONLY_MODE else 'Disabled'}`")

    if st.button("🔄 Reset & Re-Seed Database", use_container_width=True):
        with st.spinner("Re-seeding database with realistic sample records..."):
            seed_database(db_manager, force=True)
            st.success("Database re-seeded successfully!")
            st.rerun()

    st.markdown("---")

    # Security Stats Mini Widget
    st.markdown("#### 🛡️ Security Guardrails")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.metric("Safe Queries", st.session_state.safe_count)
    with col_s2:
        st.metric("Blocked", st.session_state.blocked_count)
    st.caption("Layer A: NeMo Colang Rules")
    st.caption("Layer B: SQLGlot AST Inspector")


# Main Header
st.markdown("<div class='gradient-header'>SQL & Database Analytics AI Agent</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-header-text'>Intelligent text-to-SQL analytics powered by LangGraph with self-correction reflection loops, NeMo Guardrails, and AST validation.</div>",
    unsafe_allow_html=True,
)

# Navigation Tabs
tab_overview, tab_chat, tab_analytics, tab_logs, tab_explorer, tab_security = st.tabs([
    "📊 Overview",
    "💬 AI SQL Chat",
    "📈 Analytics Dashboard",
    "📜 Execution Logs",
    "🗄️ Database Explorer",
    "🛡️ Security Monitor",
])


# ==============================================================================
# SECTION A: DASHBOARD OVERVIEW
# ==============================================================================
with tab_overview:
    st.markdown("### 📊 Business Intelligence Overview")
    
    # Query KPIs from Database
    total_customers = 0
    total_orders = 0
    total_revenue = 0.0
    avg_order_value = 0.0

    try:
        res_cust = db_manager.execute_query("SELECT COUNT(*) as c FROM customers")
        if res_cust.success and res_cust.rows:
            total_customers = res_cust.rows[0]["c"]

        res_orders = db_manager.execute_query("SELECT COUNT(*) as c, SUM(total_amount) as r, AVG(total_amount) as a FROM orders")
        if res_orders.success and res_orders.rows:
            total_orders = res_orders.rows[0]["c"]
            total_revenue = round(res_orders.rows[0]["r"] or 0.0, 2)
            avg_order_value = round(res_orders.rows[0]["a"] or 0.0, 2)
    except Exception as e:
        st.warning(f"Could not load KPI summary: {e}")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(
            f"""
            <div class='glass-card'>
                <div class='metric-title'>Total Customers</div>
                <div class='metric-value'>{total_customers:,}</div>
                <div class='metric-subtitle'>Across 10 metropolitan regions</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi2:
        st.markdown(
            f"""
            <div class='glass-card'>
                <div class='metric-title'>Total Orders</div>
                <div class='metric-value'>{total_orders:,}</div>
                <div class='metric-subtitle'>Lifetime recorded transactions</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi3:
        st.markdown(
            f"""
            <div class='glass-card'>
                <div class='metric-title'>Total Revenue</div>
                <div class='metric-value'>${total_revenue:,.2f}</div>
                <div class='metric-subtitle'>Gross sales volume</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi4:
        st.markdown(
            f"""
            <div class='glass-card'>
                <div class='metric-title'>Avg Order Value</div>
                <div class='metric-value'>${avg_order_value:,.2f}</div>
                <div class='metric-subtitle'>Per completed transaction</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("#### 🕒 Recent Database Activity")
    recent_res = db_manager.execute_query(
        """
        SELECT o.id AS order_id, c.name AS customer, o.order_date, o.total_amount, o.status
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        ORDER BY o.order_date DESC
        LIMIT 6;
        """
    )
    if recent_res.success and recent_res.rows:
        df_recent = pd.DataFrame(recent_res.rows)
        df_recent["total_amount"] = df_recent["total_amount"].apply(lambda v: f"${v:,.2f}")
        st.dataframe(df_recent, use_container_width=True, hide_index=True)


# ==============================================================================
# SECTION B: AI SQL CHAT
# ==============================================================================
with tab_chat:
    st.markdown("### 💬 Natural Language SQL Assistant")

    def process_query(query_text: str) -> None:
        """Execute query through LangGraph and update session state."""
        st.session_state.prompt_input = query_text
        with st.spinner(f"Running LangGraph agent on '{query_text}'..."):
            agent_state = run_agent_workflow(query_text)
            st.session_state.latest_state = agent_state
            st.session_state.history.append(agent_state)

            sec_status = agent_state.get("security_status", {})
            if sec_status.get("status") == "BLOCKED":
                st.session_state.blocked_count += 1
                st.session_state.security_events.append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "query": query_text,
                    "layer": sec_status.get("layer", "Security"),
                    "category": sec_status.get("category", "BLOCKED"),
                    "reason": sec_status.get("reason", "Violation detected"),
                })
            else:
                st.session_state.safe_count += 1
        st.rerun()

    # Suggested Example Questions (Immediate 1-Click Execution)
    st.markdown("##### 💡 Suggested Questions (Click any button to run instantly):")
    col_ex1, col_ex2, col_ex3 = st.columns(3)
    col_ex4, col_ex5, col_ex6 = st.columns(3)

    sample_questions = [
        ("Show all orders", col_ex1),
        ("Show total sales by month", col_ex2),
        ("Find the top 5 customers", col_ex3),
        ("Show orders sorted by date", col_ex4),
        ("Calculate total revenue", col_ex5),
        ("Compare sales across different products", col_ex6),
    ]

    for q_text, col in sample_questions:
        if col.button(f"📌 {q_text}", use_container_width=True, key=f"btn_{q_text}"):
            process_query(q_text)

    # Adversarial test button
    if st.button("🚨 Test Security Block: DROP TABLE orders; --", key="btn_sec_test", use_container_width=True):
        process_query("DROP TABLE orders; --")

    st.markdown("---")
    st.markdown("##### ✍️ Or Type Your Own Question:")
    c_in, c_btn = st.columns([4, 1])
    with c_in:
        custom_input = st.text_input(
            "Query input",
            value=st.session_state.prompt_input,
            placeholder="e.g., Calculate total revenue, or Show all orders",
            label_visibility="collapsed",
            key="custom_query_input",
        )
    with c_btn:
        custom_submit = st.button("🚀 Ask AI Agent", use_container_width=True)

    if custom_submit and custom_input:
        process_query(custom_input)

    # Render Current / Latest State
    curr_state = st.session_state.latest_state
    if curr_state:
        st.markdown("---")
        sec = curr_state.get("security_status", {})
        retry_cnt = curr_state.get("retry_count", 0)
        history = curr_state.get("correction_history", [])

        # 1. Status Badges Header
        status_cols = st.columns([1, 1, 3])
        with status_cols[0]:
            if sec.get("status") == "BLOCKED":
                st.markdown(f"<span class='badge-blocked'>🛡️ BLOCKED by {sec.get('layer')}</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='badge-safe'>✅ PASSED AST & NeMo Rails</span>", unsafe_allow_html=True)
        with status_cols[1]:
            if retry_cnt > 0:
                st.markdown(f"<span class='badge-correction'>🔄 Self-Corrected ({retry_cnt} retries)</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='badge-safe'>⚡ First-Pass Success</span>", unsafe_allow_html=True)

        # 2. Self-Correction Banner
        if retry_cnt > 0 and history:
            st.info(
                f"**Self-Correction Demonstration Active:**\n\n"
                f"• **Initial Error Caught:** `{history[0]['error']}`\n"
                f"• **Initial Faulty SQL:** `{history[0]['failed_sql']}`\n"
                f"• **Reflection Diagnosis:** Reflection node detected invalid column, referenced database schema, and rewrote SQL to `{history[0]['corrected_sql']}`\n"
                f"• **Resolution:** Corrected query passed SQLGlot AST validation and executed successfully!"
            )

        # 3. Natural Language Explanation
        st.markdown(f"#### 🤖 AI Assistant Answer for: *\"{curr_state.get('user_query', '')}\"*")
        st.info(curr_state.get("natural_response", "No response generated."))

        # 4. Generated SQL Code Panel
        if curr_state.get("generated_sql"):
            st.markdown("#### 📝 Validated SQL Query")
            st.code(curr_state["generated_sql"], language="sql")

        # 5. Query Result Table & KPI Summaries
        db_res = curr_state.get("db_result")
        if db_res and db_res.get("rows"):
            st.markdown(f"#### 📋 Query Results ({db_res.get('row_count')} record{'s' if db_res.get('row_count') != 1 else ''} in {db_res.get('execution_time_ms')} ms)")
            df_results = pd.DataFrame(db_res["rows"])

            # Highlight 1-row summary queries (like total revenue) with metric cards
            if len(df_results) == 1 and len(df_results.columns) <= 5:
                metric_cols = st.columns(len(df_results.columns))
                for idx, col_name in enumerate(df_results.columns):
                    val = df_results.iloc[0][col_name]
                    if isinstance(val, (int, float)) and any(term in col_name.lower() for term in ("revenue", "sales", "amount", "price", "val")):
                        val_str = f"${val:,.2f}"
                    elif isinstance(val, (int, float)):
                        val_str = f"{val:,}"
                    else:
                        val_str = str(val)
                    with metric_cols[idx]:
                        st.metric(label=col_name.replace("_", " ").title(), value=val_str)

            st.dataframe(df_results, use_container_width=True)


# ==============================================================================
# SECTION C: ANALYTICS DASHBOARD (PLOTLY)
# ==============================================================================
with tab_analytics:
    st.markdown("### 📈 Interactive Visualizations")
    curr_state = st.session_state.latest_state

    if not curr_state or not curr_state.get("db_result") or not curr_state["db_result"].get("rows"):
        st.info("Execute an analytics query in the AI SQL Chat tab to generate interactive charts.")
    else:
        df_chart = pd.DataFrame(curr_state["db_result"]["rows"])
        cat_cols, num_cols = get_column_types(df_chart)

        st.markdown(f"**Visualizing results for:** *\"{curr_state['user_query']}\"*")

        # Interactive Chart Controls
        c_ctrl1, c_ctrl2, c_ctrl3 = st.columns(3)
        with c_ctrl1:
            chart_type_choice = st.selectbox(
                "Chart Type",
                options=["Auto-Detect", "Bar Chart", "Line Chart", "Pie / Donut Chart"],
                index=0,
            )
        with c_ctrl2:
            default_x = cat_cols[0] if cat_cols else df_chart.columns[0]
            x_axis = st.selectbox("X-Axis (Category / Dimension)", options=df_chart.columns.tolist(), index=df_chart.columns.tolist().index(default_x))
        with c_ctrl3:
            if num_cols:
                default_y = num_cols[0]
                y_axis = st.selectbox("Y-Axis (Numeric Metric)", options=num_cols, index=0)
            else:
                y_axis = None
                st.warning("No numeric columns found for Y-axis.")

        # Render Chart
        if y_axis:
            mapped_type = "auto"
            if chart_type_choice == "Bar Chart":
                mapped_type = "bar"
            elif chart_type_choice == "Line Chart":
                mapped_type = "line"
            elif chart_type_choice == "Pie / Donut Chart":
                mapped_type = "pie"

            fig = auto_generate_chart(
                data=curr_state["db_result"]["rows"],
                chart_type=mapped_type,
                x_col=x_axis,
                y_col=y_axis,
            )
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Could not automatically generate chart from selected dimensions.")
        else:
            st.dataframe(df_chart, use_container_width=True)


# ==============================================================================
# SECTION D: EXECUTION LOGS & TELEMETRY
# ==============================================================================
with tab_logs:
    st.markdown("### 📜 LangGraph Execution Logs & Audit Trail")
    curr_state = st.session_state.latest_state

    if not curr_state:
        st.info("No execution telemetry recorded yet. Run a query in the chat.")
    else:
        st.markdown("#### ⏱️ Latest Workflow Step Breakdown")
        logs = curr_state.get("execution_logs", [])
        
        for idx, step_log in enumerate(logs, 1):
            status = step_log.get("status", "INFO")
            step_name = step_log.get("step", f"Step {idx}")
            message = step_log.get("message", "")
            
            with st.expander(f"Step {idx}: {step_name} [{status}]", expanded=(status in ["BLOCKED", "FAILED", "CORRECTION_PRODUCED"])):
                st.write(f"**Status:** {status}")
                st.write(f"**Details:** {message}")
                for k, v in step_log.items():
                    if k not in ["step", "status", "message"]:
                        st.write(f"**{k}:** `{v}`")

        # Telemetry Summary Cards
        st.markdown("#### 📊 Execution Metrics")
        t_col1, t_col2, t_col3, t_col4 = st.columns(4)
        db_res = curr_state.get("db_result")
        with t_col1:
            duration = db_res.get("execution_time_ms", 0.0) if db_res else 0.0
            st.metric("Database Execution Time", f"{duration} ms")
        with t_col2:
            st.metric("Retry / Correction Count", curr_state.get("retry_count", 0))
        with t_col3:
            st.metric("Security Status", curr_state.get("security_status", {}).get("status", "N/A"))
        with t_col4:
            st.metric("Total Graph Steps", len(logs))


# ==============================================================================
# SECTION E: DATABASE EXPLORER
# ==============================================================================
with tab_explorer:
    st.markdown("### 🗄️ Database Schema & Table Explorer")

    schema_info = inspector.inspect_schema()
    tables = schema_info.get_table_names()

    selected_table = st.selectbox("Select Table to Inspect:", options=tables, index=0)

    if selected_table and selected_table in schema_info.tables:
        t_meta = schema_info.tables[selected_table]
        st.markdown(f"#### Table: `{selected_table}` (Approx. {t_meta.row_count} records)")

        # Display Schema Metadata Table
        cols_data = []
        for col in t_meta.columns:
            cols_data.append({
                "Column Name": col.name,
                "Data Type": col.data_type,
                "Primary Key": "🔑 Yes" if col.primary_key else "No",
                "Nullable": "Yes" if col.nullable else "No",
                "Default": col.default or "None",
            })
        st.dataframe(pd.DataFrame(cols_data), use_container_width=True, hide_index=True)

        # Sample Records
        st.markdown("##### Sample Records (Top 10)")
        sample_res = inspector.get_sample_rows(selected_table, limit=10)
        if sample_res.success and sample_res.rows:
            st.dataframe(pd.DataFrame(sample_res.rows), use_container_width=True, hide_index=True)


# ==============================================================================
# SECTION F: SECURITY MONITOR
# ==============================================================================
with tab_security:
    st.markdown("### 🛡️ Real-Time Security Monitor")

    sec1, sec2, sec3 = st.columns(3)
    with sec1:
        st.metric("Total Safe Queries", st.session_state.safe_count)
    with sec2:
        st.metric("Blocked Adversarial Attacks", st.session_state.blocked_count)
    with sec3:
        total_q = st.session_state.safe_count + st.session_state.blocked_count
        pass_rate = round((st.session_state.safe_count / total_q) * 100, 1) if total_q > 0 else 100.0
        st.metric("Security Pass Rate", f"{pass_rate}%")

    st.markdown("#### 🔒 Security Architecture Layers")
    sec_layer_col1, sec_layer_col2 = st.columns(2)
    with sec_layer_col1:
        st.markdown(
            """
            <div class='glass-card'>
                <div class='metric-title'>Layer A: NeMo Guardrails</div>
                <p style='color: #cbd5e1; font-size: 0.85rem; margin-top: 0.5rem;'>
                    Scans raw user input before reaching the LLM. Blocks destructive commands (DROP, DELETE, UPDATE, INSERT, ALTER), SQL injections, comment expansions, tautologies (1=1), prompt overrides, and malicious script tags.
                </p>
                <span class='badge-safe'>Colang Policies Active</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with sec_layer_col2:
        st.markdown(
            """
            <div class='glass-card'>
                <div class='metric-title'>Layer B: SQLGlot AST Validator</div>
                <p style='color: #cbd5e1; font-size: 0.85rem; margin-top: 0.5rem;'>
                    Parses generated SQL into an Abstract Syntax Tree. Enforces read-only SELECT queries, disallows statement chaining, forbids dangerous system functions (xp_cmdshell, load_file, sleep), and verifies authorized schema tables.
                </p>
                <span class='badge-safe'>AST Analysis Active</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("#### 🚨 Security Incident & Event History")
    if not st.session_state.security_events:
        st.success("No security violations detected in this session. All queries conform to security policies.")
    else:
        st.dataframe(pd.DataFrame(st.session_state.security_events), use_container_width=True, hide_index=True)
