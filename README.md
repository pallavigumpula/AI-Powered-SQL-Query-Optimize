# ⚡ AI-Powered SQL Query Optimizer

An intelligent, full-stack SQL optimization and analysis suite built with **Python**, **Streamlit**, **FastAPI**, **MySQL**, and **AI (LLMs & NLP)**. 

The system automatically detects structural query bottlenecks, non-sargable functions, unindexed wildcards, Cartesian products, and subquery inefficiencies, generates optimized rewrites with step-by-step reasoning, recommends DDL indexes, benchmarks performance metrics, and exports audit reports.

---

## 🌟 Key Features

- **AST-Based Static Analysis Engine**:
  - Detects `SELECT *` unbounded column projections.
  - Flags non-sargable date and string functions (`YEAR(col) = 2024`, `UPPER()`, etc.) that invalidate B-Tree indexes.
  - Catches dangerous Cartesian products and unconstrained comma-separated joins.
  - Identifies suboptimal subqueries (`IN (SELECT ...)`) and unindexed leading wildcards (`LIKE '%term'`).
  - Warns on destructive statements (`UPDATE` / `DELETE`) missing `WHERE` filter clauses.
  - Scores query risk from 0 (Optimal) to 100 (Critical).

- **Automated Query Optimizer**:
  - Deterministically transforms non-sargable functions into high-performance indexed range boundaries.
  - Rewrites inefficient `IN (SELECT ...)` subqueries into correlated `EXISTS` or `INNER JOIN`.
  - Enforces result set safeguards (`LIMIT`) on large queries.
  - Automatically recommends targeted MySQL DDL composite and single-column indexes (`CREATE INDEX ...`).

- **AI-Powered Enhancements (LLMs & Smart NLP)**:
  - Supports **Google Gemini** (`gemini-1.5-flash`, `gemini-1.5-pro`) and **OpenAI** (`gpt-4o-mini`, `gpt-4o`).
  - Includes a **Built-in Smart Heuristic Engine** that runs offline with zero external API keys needed.
  - **Natural Language to Optimized SQL**: Converts plain English business queries into production-grade, index-friendly SQL queries.

- **Comparative Performance Metrics**:
  - Algorithmic query cost estimation and structural complexity score.
  - Calculates estimated latency and I/O reduction percentages.
  - Interactive side-by-side **Plotly** cost and complexity visual charts.

- **Live MySQL Benchmark Studio**:
  - Executes real MySQL `EXPLAIN` and execution timing comparisons side-by-side.
  - Compares rows examined, index keys used, and access scan types (`ALL` vs `range` / `ref`).

- **Audit Report Generator**:
  - One-click export of comprehensive Markdown (`.md`) audit reports with executive summaries, diff blocks, and index recommendations.

- **FastAPI REST API Service**:
  - High-performance programmatic endpoints for optimization, natural language translation, and history querying (`/docs` OpenAPI documentation).

- **Database Persistence & Query History**:
  - Logs all query optimization runs, inefficiencies, and metrics to **MySQL**.
  - Seamless automatic fallback to local **SQLite** (`sql_optimizer.db`) if MySQL is not yet configured.
  - Searchable history table with CSV export.

---

## 🛠️ Technology Stack

- **Frontend & Visualization**: [Streamlit](https://streamlit.io/), [Plotly](https://plotly.com/)
- **REST API**: [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/)
- **Core Logic & Parsing**: Python 3.11+, [sqlglot](https://github.com/tobymao/sqlglot), [sqlparse](https://github.com/andialbrecht/sqlparse)
- **Database**: MySQL 8.0 (with automatic SQLite fallback), [PyMySQL](https://github.com/PyMySQL/PyMySQL)
- **AI / LLMs**: Google Gemini API, OpenAI API, Rule-based NLP synthesis
- **Containerization**: Docker, Docker Compose

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
Copy the example environment file:
```bash
copy .env.example .env
```
Edit `.env` with your MySQL credentials or AI API keys (or configure directly inside the Streamlit sidebar).

### 3. Run the Streamlit Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 4. (Optional) Run the FastAPI REST Server
```bash
uvicorn api:app --reload --port 8000
```
Explore interactive Swagger API documentation at `http://localhost:8000/docs`.

### 5. (Optional) Deploy with Docker Compose
```bash
docker-compose up --build
```

---

## 🧪 Running Automated Tests

Run the full automated test suite (15 unit & integration tests):
```bash
python -m unittest discover tests -v
```

---

## 📂 Project Directory Structure

```
AI-Powered SQL-Query-Optimize/
├── app.py                      # Interactive Streamlit Web UI
├── api.py                      # FastAPI REST API Microservice
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Multi-container orchestration (UI + API + MySQL)
├── README.md                   # Project documentation
├── core/
│   ├── analyzer.py             # AST query parsing and antipattern detection
│   ├── optimizer.py            # Rule-based query rewriter & index advisor
│   ├── ai_engine.py            # Gemini / OpenAI / Built-in Smart NLP
│   ├── metrics.py              # Performance cost & live EXPLAIN evaluator
│   └── database.py             # MySQL and SQLite history persistence
├── utils/
│   └── sample_queries.py       # Pre-configured antipattern demo queries
├── sample_data/
│   └── init_sample_db.py       # Benchmark schema & mock dataset seeder
└── tests/
    ├── test_optimizer.py       # Core logic unit tests
    └── test_api.py             # REST API endpoint tests
```
