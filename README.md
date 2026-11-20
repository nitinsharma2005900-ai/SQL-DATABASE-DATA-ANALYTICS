# SQL & Database Analytics Agent with Self-Correction & Guardrails

An intelligent AI-powered SQL analytics agent featuring LangGraph state machine execution, self-correction reflection loops, dual-layer security (NeMo Guardrails & SQLGlot AST validation), and an interactive dark navy glassmorphic Streamlit dashboard with Plotly charts.

## Core Features

- **Automatic Text-to-SQL Generation**: Natural language translation into read-only SQL via Google Gemini (with deterministic simulation mode for offline/keyless use).
- **Dual-Layer Security Guardrails**:
  - *Layer A (NeMo Guardrails)*: Scans raw user input for malicious SQL injection patterns, destructive commands (`DROP`, `DELETE`, `UPDATE`, `INSERT`), prompt injections, and script tags.
  - *Layer B (SQLGlot AST Validator)*: Enforces AST-level read-only `SELECT` queries, rejects multi-statement stacking, and blocks dangerous system functions.
- **Self-Correction Reflection Loop**: Automatically catches database execution errors (e.g. invalid columns like `created_at` on the `orders` table), feeds schema context back to the reflection engine, and regenerates valid SQL (`order_date`), capped at 3 retries.
- **Interactive Dark Navy Glassmorphism Dashboard**: Streamlit interface with 6 tabs: Overview KPIs, AI SQL Chat, Interactive Plotly Visualizations, Execution Logs & Audit Trail, Database Schema Explorer, and Real-Time Security Monitor.
- **Automated Pytest Suite**: 22 automated tests verifying AST filtering, NeMo rails, database reflection, self-correction, retry limits, and Plotly visualizations.

---

## Quickstart & Installation

### 1. Clone & Configure Environment

```bash
# Copy example environment configuration
cp .env.example .env
```

Set your configuration in `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here  # Optional: runs in Demo Mode if left blank
GEMINI_MODEL=gemini-3.8-flash
DATABASE_URL=sqlite:///./data/analytics.db
MAX_RETRIES=3
READ_ONLY_MODE=true
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize & Seed Database (Optional - runs automatically on app start)

```bash
python -m src.db.seed
```

### 4. Run the Streamlit Dashboard

```bash
streamlit run app.py
```

### 5. Run Automated Tests

```bash
pytest
```

---

## Verification Test Workflows

### Test Case 1: SQL Self-Correction Recovery Loop
1. Ask the agent: `"Show orders sorted by date."`
2. The initial attempt generates `SELECT * FROM orders ORDER BY created_at;`.
3. The database execution node catches the error (`no such column: created_at`).
4. The reflection node diagnoses the schema for `orders`, discovers `order_date`, and rewrites the query to `SELECT * FROM orders ORDER BY order_date;`.
5. The corrected query passes AST validation and executes successfully.

### Test Case 2: Security Filter & SQL Injection Block
1. Enter query: `"DROP TABLE orders; --"` or `"SELECT * FROM orders; DROP TABLE customers;"`.
2. Intercepted by NeMo Guardrails or SQLGlot AST validator before database execution.
3. Execution is blocked, security incident is logged, and database tables remain untouched.
