"""AI-Powered SQL Query Optimizer - Streamlit Application.

Interactive interface for SQL query static analysis, rule-based & AI-driven optimizations,
performance metric comparisons, and history tracking with MySQL/SQLite persistence.
"""

import os
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sqlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from core.analyzer import SQLAnalyzer
from core.optimizer import SQLOptimizer
from core.ai_engine import AIEngine
from core.metrics import PerformanceMetricsEngine
from core.database import DatabaseManager
from utils.sample_queries import SAMPLE_QUERIES, CATEGORIZED_QUERIES

# Page Configuration
st.set_page_config(
    page_title="AI-Powered SQL Query Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1e2130;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        margin-bottom: 12px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        margin-top: 4px;
    }
    .badge-critical {
        background-color: #e53e3e;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    .badge-high {
        background-color: #dd6b20;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    .badge-medium {
        background-color: #d69e2e;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    .badge-low {
        background-color: #3182ce;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    .stCodeBlock {
        border-radius: 6px;
    }
/* MySQL Workbench-style Row Limit Dropdown */
div[data-testid="stSelectbox"] {
    min-width: 180px;
}

div[data-testid="stSelectbox"] [role="combobox"] {
    min-height: 32px;
    padding: 0px 8px;
    font-size: 13px;
    border-radius: 2px;
}

/* Compact dropdown options */
div[role="listbox"] [role="option"] {
    min-height: 30px;
    padding: 5px 10px;
    font-size: 13px;
}

/* Compact dropdown menu */
div[data-baseweb="popover"] {
    font-size: 13px;
}
""", unsafe_allow_html=True)


# Initialize Session State
if "db_manager" not in st.session_state:
    st.session_state.db_manager = DatabaseManager()
if "analyzer" not in st.session_state:
    st.session_state.analyzer = SQLAnalyzer(dialect="mysql")
if "optimizer" not in st.session_state:
    st.session_state.optimizer = SQLOptimizer(dialect="mysql")
if "metrics_engine" not in st.session_state:
    st.session_state.metrics_engine = PerformanceMetricsEngine()
if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None
if "last_optimization" not in st.session_state:
    st.session_state.last_optimization = None
if "last_metrics" not in st.session_state:
    st.session_state.last_metrics = None
if "query_input_val" not in st.session_state:
    st.session_state.query_input_val = SAMPLE_QUERIES["[Date & Sargability] Non-Sargable YEAR() Function"]["sql"]


# -------------------------------------------------------------
# SIDEBAR CONFIGURATION
# -------------------------------------------------------------
with st.sidebar:
    st.title("⚡ SQL Optimizer")
    st.markdown("*Intelligent SQL Performance Studio*")
    st.divider()

    # 1. Preset Queries
    st.subheader("📚 Antipattern Presets")
    selected_preset = st.selectbox(
        "Load Example Antipattern Query:",
        options=list(SAMPLE_QUERIES.keys()),
        index=0
    )
    if st.button("📥 Load Preset Query", use_container_width=True):
        st.session_state.query_input_val = SAMPLE_QUERIES[selected_preset]["sql"]
        st.success(f"Loaded: {SAMPLE_QUERIES[selected_preset]['title']}")

    st.divider()

    # 2. Database Connection Settings
    st.subheader("🗄️ MySQL Database")
    db_host = st.text_input("Host", value=os.getenv("MYSQL_HOST", "localhost"))
    db_port = st.number_input("Port", value=int(os.getenv("MYSQL_PORT", 3306)), step=1)
    db_user = st.text_input("User", value=os.getenv("MYSQL_USER", "root"))
    db_pass = st.text_input("Password", value=os.getenv("MYSQL_PASSWORD", ""), type="password")
    db_name = st.text_input("Database", value=os.getenv("MYSQL_DATABASE", "sql_optimizer"))

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔌 Connect", use_container_width=True):
            st.session_state.db_manager = DatabaseManager(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_pass,
                database=db_name
            )
            success, msg, db_type = st.session_state.db_manager.test_connection()
            if success:
                st.success(msg)
            else:
                st.warning(f"Using SQLite fallback. {msg}")

    with col_btn2:
        is_conn, msg, db_type = st.session_state.db_manager.test_connection()
        if is_conn:
            st.markdown("🟢 **MySQL 8.0**")
        else:
            st.markdown("🟡 **SQLite Mode**")

    # Seed benchmark DB button
    if st.button("🌱 Init Benchmark Schema", use_container_width=True, help="Creates sample customers & orders tables for live EXPLAIN testing"):
        from sample_data.init_sample_db import setup_sample_database
        with st.spinner("Seeding benchmark data..."):
            ok = setup_sample_database(host=db_host, port=db_port, user=db_user, password=db_pass, db_name="sql_optimizer_bench")
            if ok:
                st.success("Benchmark schema & 4,000+ mock records ready in 'sql_optimizer_bench'!")
            else:
                st.error("Failed to seed MySQL. Ensure credentials are correct.")

    st.divider()

    # 3. AI Engine Settings
    st.subheader("🤖 AI Engine")
    ai_provider = st.selectbox(
        "AI Provider",
        options=["Built-in Smart Engine (No Key)", "Google Gemini", "OpenAI"],
        index=0
    )

    gemini_key = ""
    openai_key = ""
    ai_model = "gemini-1.5-flash"

    if ai_provider == "Google Gemini":
        gemini_key = st.text_input(
            "Gemini API Key",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            help="Get your key from Google AI Studio (aistudio.google.com)"
        )
        ai_model = st.selectbox("Model", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"])
    elif ai_provider == "OpenAI":
        openai_key = st.text_input(
            "OpenAI API Key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password"
        )
        ai_model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"])
    else:
        st.caption("✨ Using built-in rule-based NLP optimizer. No external API key required.")


# Initialize AI Engine instance
ai_engine = AIEngine(
    provider="gemini" if ai_provider == "Google Gemini" else ("openai" if ai_provider == "OpenAI" else "built-in"),
    gemini_api_key=gemini_key,
    openai_api_key=openai_key,
    model_name=ai_model
)


# -------------------------------------------------------------
# MAIN DASHBOARD TABS
# -------------------------------------------------------------
tab_optimizer, tab_nl_to_sql, tab_live_bench, tab_history = st.tabs([
    "🔍 Query Optimizer",
    "🤖 Natural Language to SQL",
    "📊 Live MySQL Benchmark Studio",
    "📜 Optimization History & Analytics"
])


# =============================================================
# TAB 1: QUERY OPTIMIZER
# =============================================================
with tab_optimizer:
    st.subheader("MySQL Workbench Style Query Studio & Optimizer")
    st.caption("Inspect queries with professional IDE controls, row limit constraints, and intelligent AST optimizations.")

    # 1. Categorized Query Tabs (Matching Top Header in Screenshot)
    cat_tab1, cat_tab2, cat_tab3, cat_tab4, cat_tab5 = st.tabs([
        "🛒 Flipkart", "🔢 Numerical Functions", "🔗 Subqueries", "📅 Date & Sargability", "⭐ Starred Queries"
    ])

    with cat_tab1:
        f_cols = st.columns([3, 1])
        with f_cols[0]:
            sel_f = st.selectbox("Flipkart E-Commerce Queries:", list(CATEGORIZED_QUERIES["Flipkart (E-Commerce)"].keys()), key="sel_flipkart")
            st.caption(CATEGORIZED_QUERIES["Flipkart (E-Commerce)"][sel_f]["description"])
        with f_cols[1]:
            st.write("")
            if st.button("📥 Load Flipkart Query", use_container_width=True, key="btn_load_flipkart"):
                st.session_state.query_input_val = CATEGORIZED_QUERIES["Flipkart (E-Commerce)"][sel_f]["sql"]
                st.rerun()

    with cat_tab2:
        n_cols = st.columns([3, 1])
        with n_cols[0]:
            sel_n = st.selectbox("Numerical & Mathematical Queries:", list(CATEGORIZED_QUERIES["Numerical Functions"].keys()), key="sel_numerical")
            st.caption(CATEGORIZED_QUERIES["Numerical Functions"][sel_n]["description"])
        with n_cols[1]:
            st.write("")
            if st.button("📥 Load Numerical Query", use_container_width=True, key="btn_load_numerical"):
                st.session_state.query_input_val = CATEGORIZED_QUERIES["Numerical Functions"][sel_n]["sql"]
                st.rerun()

    with cat_tab3:
        s_cols = st.columns([3, 1])
        with s_cols[0]:
            sel_s = st.selectbox("Subqueries & Nested Queries:", list(CATEGORIZED_QUERIES["Subqueries"].keys()), key="sel_subqueries")
            st.caption(CATEGORIZED_QUERIES["Subqueries"][sel_s]["description"])
        with s_cols[1]:
            st.write("")
            if st.button("📥 Load Subquery", use_container_width=True, key="btn_load_subquery"):
                st.session_state.query_input_val = CATEGORIZED_QUERIES["Subqueries"][sel_s]["sql"]
                st.rerun()

    with cat_tab4:
        d_cols = st.columns([3, 1])
        with d_cols[0]:
            sel_d = st.selectbox("Date & Sargability Queries:", list(CATEGORIZED_QUERIES["Date & Sargability"].keys()), key="sel_date")
            st.caption(CATEGORIZED_QUERIES["Date & Sargability"][sel_d]["description"])
        with d_cols[1]:
            st.write("")
            if st.button("📥 Load Date Query", use_container_width=True, key="btn_load_date"):
                st.session_state.query_input_val = CATEGORIZED_QUERIES["Date & Sargability"][sel_d]["sql"]
                st.rerun()

    with cat_tab5:
        fav_list = st.session_state.db_manager.get_favorites()
        if not fav_list:
            st.info("No starred queries yet! Click the ⭐ button in the toolbar below to save custom queries to your personal library.")
        else:
            fav_map = {f"#{f['id']} - {f['title']} ({f['category']})": f for f in fav_list}
            sel_fav_key = st.selectbox("Your Saved Queries:", list(fav_map.keys()), key="sel_starred")
            fav_act1, fav_act2 = st.columns([1, 1])
            with fav_act1:
                if st.button("📥 Load Starred Query", use_container_width=True, key="btn_load_fav"):
                    st.session_state.query_input_val = fav_map[sel_fav_key]["query"]
                    st.rerun()
            with fav_act2:
                if st.button("🗑️ Delete from Starred", use_container_width=True, key="btn_del_fav"):
                    st.session_state.db_manager.delete_favorite(fav_map[sel_fav_key]["id"])
                    st.success("Deleted from favorites.")
                    st.rerun()

    st.markdown("---")

    # 2. Workbench Query Toolbar (Matching Screenshot)
    tb_c1, tb_c2, tb_c3, tb_c4, tb_c5, tb_c6 = st.columns([0.6, 0.8, 2.2, 1.2, 0.8, 1.2])

    with tb_c1:
        clear_btn = st.button("❌", help="Clear / Reset SQL Editor", use_container_width=True)
        if clear_btn:
            st.session_state.query_input_val = ""
            st.rerun()

    with tb_c2:
        optimize_btn = st.button("⚡", help="Execute & Optimize Query", type="primary", use_container_width=True)

    with tb_c3:
        row_limit_options = [
            "Limit to 1000 rows",
            "Don't Limit",
            "Limit to 10 rows",
            "Limit to 50 rows",
            "Limit to 100 rows",
            "Limit to 200 rows",
            "Limit to 300 rows",
            "Limit to 400 rows",
            "Limit to 500 rows",
            "Limit to 1000 rows",
            "Limit to 2000 rows",
            "Limit to 5000 rows",
            "Limit to 10000 rows",
            "Limit to 50000 rows"
        ]
        selected_limit_str = st.selectbox(
            "Limit:",
            options=row_limit_options,
            index=0,
            label_visibility="collapsed",
            help="Row limit to enforce in query optimizer and execution"
        )
        if selected_limit_str == "Don't Limit":
            chosen_row_limit = None
        else:
            chosen_row_limit = int(selected_limit_str.replace("Limit to ", "").replace(" rows", ""))

    with tb_c4:
        with st.popover("⭐ Bookmark", use_container_width=True):
            st.markdown("**⭐ Save Query to Favorites**")
            new_fav_title = st.text_input("Query Title:", value="Custom Optimized Query", key="input_fav_title")
            new_fav_cat = st.selectbox("Category:", ["Flipkart", "Numerical Functions", "Subqueries", "Date & Sargability", "General"], key="input_fav_cat")
            if st.button("Save to Starred", key="btn_confirm_save_fav"):
                if st.session_state.query_input_val.strip():
                    st.session_state.db_manager.save_favorite(
                        title=new_fav_title,
                        query=st.session_state.query_input_val,
                        category=new_fav_cat
                    )
                    st.success("Query saved to ⭐ Starred Queries tab!")
                    st.rerun()

    with tb_c5:
        format_btn = st.button("🧹", help="Beautify / Format SQL", use_container_width=True)

    with tb_c6:
        sql_dialect = st.selectbox("Dialect", ["MySQL", "Generic SQL", "PostgreSQL"], index=0, label_visibility="collapsed")

    # SQL Editor Text Area
    query_input = st.text_area(
        "SQL Query:",
        value=st.session_state.query_input_val,
        height=200,
        label_visibility="collapsed",
        help="Type or paste your SQL query here"
    )

    if format_btn and query_input.strip():
        st.session_state.query_input_val = sqlparse.format(
            query_input, reindent=True, keyword_case="upper", identifier_case="lower"
        )
        st.rerun()

    with st.expander("⚙️ Optional Schema Context / DDL", expanded=False):
        schema_context = st.text_area(
            "Table Schema / DDL:",
            placeholder="CREATE TABLE orders (\n  id INT PRIMARY KEY,\n  customer_id INT,\n  status VARCHAR(20),\n  order_date DATETIME\n);",
            height=110
        )

    if optimize_btn and query_input.strip():
        with st.spinner("Analyzing query AST and applying Workbench constraints..."):
            analyzer = SQLAnalyzer(dialect=sql_dialect)
            analysis = analyzer.analyze(query_input)

            if not analysis.is_valid:
                st.error(f"Analysis Error: {analysis.error_message}")
            else:
                st.session_state.last_analysis = analysis

                # Run rule-based optimizer with user's selected row limit
                rule_optimizer = SQLOptimizer(dialect=sql_dialect)
                opt_res = rule_optimizer.optimize(query_input, analysis, row_limit=chosen_row_limit)

                # If user selected an active AI provider (Gemini / OpenAI), complement with LLM
                ai_mode_label = "Rule-Based + Heuristic"
                if ai_provider in ["Google Gemini", "OpenAI"]:
                    try:
                        ai_res = ai_engine.optimize_with_ai(
                            query_input,
                            schema_context=schema_context,
                            detected_inefficiencies=[i.title for i in analysis.inefficiencies]
                        )
                        opt_res.optimized_query = ai_res.optimized_sql
                        opt_res.optimizations_applied.extend(ai_res.optimizations_applied)
                        if ai_res.explanation:
                            opt_res.explanations.append(ai_res.explanation)
                        opt_res.index_recommendations.extend(ai_res.recommended_indexes)
                        ai_mode_label = ai_res.model_used
                    except Exception as e:
                        st.warning(f"AI engine note: {str(e)}. Used rule-based optimization.")

                st.session_state.last_optimization = opt_res

                # Calculate metrics
                metrics = st.session_state.metrics_engine.calculate_estimated_metrics(analysis, is_optimized=False)
                opt_metrics = st.session_state.metrics_engine.calculate_estimated_metrics(analysis, is_optimized=True)
                st.session_state.last_metrics = {
                    "orig": metrics,
                    "opt": opt_metrics
                }

                # Save run to database
                st.session_state.db_manager.save_history(
                    original_query=query_input,
                    optimized_query=opt_res.optimized_query,
                    statement_type=analysis.statement_type,
                    inefficiency_score=analysis.inefficiency_score,
                    complexity_score=analysis.complexity_score,
                    inefficiencies=[{
                        "code": i.code, "title": i.title, "severity": i.severity, "desc": i.description, "sugg": i.suggestion
                    } for i in analysis.inefficiencies],
                    metrics={
                        "estimated_cost": metrics.estimated_cost,
                        "scan_type": metrics.scan_type_risk,
                        "improvement_pct": metrics.potential_improvement_pct
                    },
                    optimizations=opt_res.optimizations_applied,
                    explanations=opt_res.explanations,
                    index_recommendations=opt_res.index_recommendations,
                    mode=ai_mode_label
                )

    # Render Analysis & Optimization Results if available
    if st.session_state.last_analysis and st.session_state.last_optimization:
        analysis = st.session_state.last_analysis
        opt_res = st.session_state.last_optimization
        metrics_dict = st.session_state.last_metrics
        orig_m = metrics_dict["orig"]
        opt_m = metrics_dict["opt"]

        st.divider()

        # Scorecard Row
        score_cols = st.columns(4)
        with score_cols[0]:
            score_color = "red" if analysis.inefficiency_score > 60 else ("orange" if analysis.inefficiency_score > 25 else "green")
            st.metric(
                label="Inefficiency Risk Score",
                value=f"{analysis.inefficiency_score} / 100",
                delta=f"-{analysis.inefficiency_score}" if analysis.inefficiency_score > 0 else "Optimal",
                delta_color="inverse"
            )
        with score_cols[1]:
            st.metric(
                label="Structural Complexity",
                value=f"{analysis.complexity_score} / 100",
                help="Based on number of joined tables, subqueries, conditions, and groupings."
            )
        with score_cols[2]:
            st.metric(
                label="Potential Speedup / Savings",
                value=f"+{orig_m.potential_improvement_pct}%",
                delta="Estimated Latency & I/O Reduction",
                delta_color="normal"
            )
        with score_cols[3]:
            st.metric(
                label="Estimated Scan Risk",
                value=orig_m.scan_type_risk,
                help="Identifies full table scans vs indexed lookups."
            )

        # Side-by-Side SQL Comparison
        st.subheader("Query Comparison")
        col_orig, col_opt = st.columns(2)
        with col_orig:
            st.markdown("#### ❌ Original Query")
            st.code(analysis.formatted_query, language="sql")
        with col_opt:
            st.markdown("#### ✅ Optimized Query")
            st.code(opt_res.optimized_query, language="sql")

        # Inefficiencies Detected
        st.subheader(f"Detected Inefficiencies ({len(analysis.inefficiencies)})")
        if not analysis.inefficiencies:
            st.success("🎉 No major antipatterns detected! Query adheres to SQL best practices.")
        else:
            for item in analysis.inefficiencies:
                badge_class = f"badge-{item.severity.lower()}"
                with st.container():
                    st.markdown(f"""
                        <div style="border: 1px solid #374151; border-radius: 8px; padding: 12px; margin-bottom: 10px; background-color: #111827;">
                            <span class="{badge_class}">{item.severity}</span>
                            <strong style="margin-left: 10px; font-size: 16px;">{item.title}</strong>
                            <p style="margin-top: 8px; margin-bottom: 4px; color: #d1d5db;">{item.description}</p>
                            <p style="margin-bottom: 0px; color: #60a5fa;">💡 <strong>Fix:</strong> {item.suggestion}</p>
                        </div>
                    """, unsafe_allow_html=True)

        # Optimization Explanations
        st.subheader("💡 Optimization Breakdown & Reasoning")
        if opt_res.explanations:
            for exp in opt_res.explanations:
                st.markdown(f"- {exp}")
        else:
            st.info("No query structure modifications were necessary.")

        # Performance Comparison Chart & Table
        st.subheader("📊 Performance Footprint Comparison")
        tab_chart, tab_metrics_table = st.tabs(["Cost Chart", "Detailed Metrics"])

        with tab_chart:
            fig = go.Figure(data=[
                go.Bar(name="Original Query", x=["Estimated Cost Units", "Complexity Score"], y=[orig_m.estimated_cost, orig_m.complexity_score], marker_color="#ef4444"),
                go.Bar(name="Optimized Query", x=["Estimated Cost Units", "Complexity Score"], y=[opt_m.estimated_cost, opt_m.complexity_score], marker_color="#10b981")
            ])
            fig.update_layout(
                barmode="group",
                height=320,
                margin=dict(l=20, r=20, t=30, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f3f4f6"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab_metrics_table:
            metrics_df = pd.DataFrame({
                "Metric": ["Estimated Cost Score", "Access Scan Type", "Memory Footprint", "Disk I/O Impact", "Tables Involved"],
                "Original": [orig_m.estimated_cost, orig_m.scan_type_risk, orig_m.estimated_memory_impact, orig_m.estimated_io_impact, ", ".join(analysis.tables_involved) or "None"],
                "Optimized": [opt_m.estimated_cost, opt_m.scan_type_risk, opt_m.estimated_memory_impact, opt_m.estimated_io_impact, ", ".join(analysis.tables_involved) or "None"]
            })
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)

        # Index Recommendations
        if opt_res.index_recommendations:
            st.subheader("⚡ Recommended Indexing Strategy (DDL)")
            st.caption("Apply these indexes to your database schema to maximize search argument speeds:")
            for idx in set(opt_res.index_recommendations):
                st.code(idx, language="sql")

        # Downloadable Audit Report
        st.divider()
        report_md = f"""# SQL Optimization & Performance Audit Report

**Generated on:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Statement Type:** {analysis.statement_type}  
**Inefficiency Risk Score:** {analysis.inefficiency_score}/100  
**Structural Complexity:** {analysis.complexity_score}/100  
**Estimated Speedup:** +{orig_m.potential_improvement_pct}%  
**Scan Risk:** {orig_m.scan_type_risk}  

---

## 1. Executive Summary
- **Original Cost Estimate:** {orig_m.estimated_cost} units
- **Optimized Cost Estimate:** {opt_m.estimated_cost} units
- **Identified Issues:** {len(analysis.inefficiencies)}

---

## 2. Detected Inefficiencies
| Severity | Issue | Description | Recommended Fix |
|---|---|---|---|
""" + "\n".join([f"| **{i.severity}** | {i.title} | {i.description} | {i.suggestion} |" for i in analysis.inefficiencies]) + f"""

---

## 3. Query Comparison

### Original Query
```sql
{analysis.formatted_query}
```

### Optimized Query
```sql
{opt_res.optimized_query}
```

---

## 4. Technical Reasoning & Changes Applied
""" + "\n".join([f"- {e}" for e in opt_res.explanations]) + f"""

---

## 5. Recommended Indexes (DDL)
```sql
""" + "\n".join(set(opt_res.index_recommendations) if opt_res.index_recommendations else ["-- No additional indexes required"]) + """
```
"""
        st.download_button(
            label="📄 Download Optimization Audit Report (.md)",
            data=report_md,
            file_name=f"sql_optimization_report_{analysis.statement_type.lower()}.md",
            mime="text/markdown"
        )

        # 6. Live Query Results Grid (Workbench Data Output)
        st.divider()
        st.subheader("📋 Workbench Results Grid")
        st.caption(f"Execute and preview data rows (constrained by selected: {selected_limit_str})")
        col_exec_grid1, col_exec_grid2 = st.columns([1, 4])
        with col_exec_grid1:
            exec_grid_btn = st.button("▶️ Execute & Fetch Rows", type="secondary", use_container_width=True)

        if exec_grid_btn:
            with st.spinner("Executing query on active database..."):
                target_q = opt_res.optimized_query if opt_res.optimized_query else query_input
                rows, err_msg, exec_ms = st.session_state.db_manager.execute_query(target_q, limit=chosen_row_limit)
                if err_msg:
                    st.warning(f"Database response: {err_msg}")
                    st.info("Tip: Ensure your MySQL database has the relevant tables or click 'Init Benchmark Schema' in the sidebar!")
                elif not rows:
                    st.info("Query executed successfully: 0 rows returned.")
                else:
                    st.success(f"Fetched {len(rows)} rows in {exec_ms} ms (Row Limit: {chosen_row_limit or 'Unlimited'})")
                    res_df = pd.DataFrame(rows)
                    st.dataframe(res_df, use_container_width=True)




# =============================================================
# TAB 2: NATURAL LANGUAGE TO SQL
# =============================================================
with tab_nl_to_sql:
    st.subheader("🤖 Natural Language to Optimized SQL")
    st.caption("Describe what data you want to retrieve in plain English. The AI engine will produce an optimized, production-grade SQL query.")

    nl_presets = [
        "Find customers who placed orders over $500 in the last 30 days ordered by total spent",
        "List all active user accounts that logged in during the past 7 days",
        "Get top 10 products by gross sales revenue with units sold in 2024",
        "Find customers who have never placed any order"
    ]

    selected_nl_example = st.selectbox("Quick Prompt Templates:", ["Select or type below..."] + nl_presets)

    default_nl_text = selected_nl_example if selected_nl_example != "Select or type below..." else "Find customers who placed orders over $500 in the last 30 days ordered by total spent"
    nl_input = st.text_area("Your Request in Plain English:", value=default_nl_text, height=90)

    col_nl_gen, col_nl_space = st.columns([1, 4])
    with col_nl_gen:
        gen_sql_btn = st.button("🪄 Generate SQL", type="primary", use_container_width=True)

    if gen_sql_btn and nl_input.strip():
        with st.spinner("Translating intent into optimized SQL..."):
            nl_resp = ai_engine.natural_language_to_sql(nl_input)

            st.markdown("#### Generated Optimized SQL")
            st.code(nl_resp.sql_query, language="sql")

            col_send, _ = st.columns([2, 5])
            with col_send:
                if st.button("📤 Load into Optimizer Tab", use_container_width=True):
                    st.session_state.query_input_val = nl_resp.sql_query
                    st.success("Query loaded into Optimizer tab!")

            st.markdown("#### 💡 Architectural Highlights")
            for h in nl_resp.optimization_highlights:
                st.markdown(f"- **{h}**")

            st.info(f"**Assumed Schema Context:** {nl_resp.assumed_schema}")
            st.caption(f"Generated via: {nl_resp.model_used}")


# =============================================================
# TAB 3: LIVE MYSQL BENCHMARK STUDIO
# =============================================================
with tab_live_bench:
    st.subheader("📊 Live MySQL Benchmark Studio")
    st.caption("Execute real EXPLAIN plans and compare actual query execution performance against your local MySQL server.")

    is_mysql_active, bench_msg, _ = st.session_state.db_manager.test_connection()

    if not is_mysql_active:
        st.warning("⚠️ Live EXPLAIN requires a direct MySQL connection. Currently running in SQLite fallback mode.")
        st.markdown("""
        **To enable live MySQL benchmarks:**
        1. Ensure your local MySQL 8.0 service is running.
        2. Enter your MySQL username and password in the sidebar and click **Connect**.
        3. Click **Init Benchmark Schema** to automatically seed test tables (`customers`, `orders`, `products`) with 4,000+ mock records.
        """)
    else:
        st.success(bench_msg)

        bench_col1, bench_col2 = st.columns(2)
        with bench_col1:
            q_original = st.text_area(
                "Original SQL Query to EXPLAIN:",
                value="SELECT * FROM orders WHERE status = 'COMPLETED';",
                height=130
            )
        with bench_col2:
            q_optimized = st.text_area(
                "Optimized SQL Query to EXPLAIN:",
                value="SELECT id, customer_id, total_amount FROM orders WHERE status = 'COMPLETED' LIMIT 100;",
                height=130
            )

        if st.button("⚡ Run Live EXPLAIN Comparison", type="primary"):
            with st.spinner("Executing MySQL EXPLAIN plans..."):
                orig_rows, orig_time, orig_err = st.session_state.db_manager.run_explain(q_original)
                opt_rows, opt_time, opt_err = st.session_state.db_manager.run_explain(q_optimized)

                if orig_err:
                    st.error(f"Original Query Error: {orig_err}")
                elif opt_err:
                    st.error(f"Optimized Query Error: {opt_err}")
                else:
                    comparison = st.session_state.metrics_engine.compare_live_plans(
                        orig_rows, opt_rows, orig_time, opt_time
                    )

                    st.markdown(f"### 🎯 Benchmark Verdict: **{comparison.verdict}**")

                    bench_metric_cols = st.columns(3)
                    with bench_metric_cols[0]:
                        st.metric("Original Rows Examined", f"{comparison.original_rows_examined:,}")
                    with bench_metric_cols[1]:
                        st.metric("Optimized Rows Examined", f"{comparison.optimized_rows_examined:,}", delta=f"-{comparison.original_rows_examined - comparison.optimized_rows_examined:,}" if comparison.original_rows_examined > comparison.optimized_rows_examined else None, delta_color="inverse")
                    with bench_metric_cols[2]:
                        st.metric("Execution Time", f"{opt_time} ms", delta=f"{round(orig_time - opt_time, 2)} ms" if orig_time and opt_time else None)

                    st.markdown("#### Original EXPLAIN Plan")
                    st.dataframe(pd.DataFrame(orig_rows), use_container_width=True)

                    st.markdown("#### Optimized EXPLAIN Plan")
                    st.dataframe(pd.DataFrame(opt_rows), use_container_width=True)


# =============================================================
# TAB 4: QUERY HISTORY & ANALYTICS
# =============================================================
with tab_history:
    st.subheader("📜 Optimization History & Analytics")
    st.caption("Track past queries, structural improvements, and learning analytics.")

    history_df = st.session_state.db_manager.get_history(limit=100)

    if history_df.empty:
        st.info("No query optimization history recorded yet. Run queries in the Optimizer tab to build your log!")
    else:
        # History Action Controls
        col_hist_summary, col_hist_clear = st.columns([4, 1])
        with col_hist_summary:
            st.markdown(f"**Total Queries Logged:** `{len(history_df)}` | **Database:** `{st.session_state.db_manager.db_type.upper()}`")
        with col_hist_clear:
            if st.button("🗑️ Clear History", use_container_width=True):
                st.session_state.db_manager.clear_history()
                st.success("History cleared!")
                st.rerun()

        # Display history table
        display_cols = ["id", "statement_type", "inefficiency_score", "complexity_score", "mode", "created_at"]
        available_cols = [c for c in display_cols if c in history_df.columns]
        st.dataframe(history_df[available_cols], use_container_width=True, hide_index=True)

        # Expandable inspection of past query
        selected_hist_id = st.selectbox("Inspect Past Optimization Details:", options=history_df["id"].tolist())
        selected_row = history_df[history_df["id"] == selected_hist_id].iloc[0]

        with st.expander(f"🔍 Details for Query #{selected_hist_id}", expanded=True):
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                st.markdown("**Original Query:**")
                st.code(selected_row["original_query"], language="sql")
            with col_h2:
                st.markdown("**Optimized Query:**")
                st.code(selected_row["optimized_query"], language="sql")

            st.markdown("**Explanations & Findings:**")
            st.write(selected_row["explanations_text"] or "No notes recorded.")

            if selected_row["index_recommendations_text"]:
                st.markdown("**Recommended Indexes:**")
                st.code(selected_row["index_recommendations_text"], language="sql")

        # Download History as CSV
        csv_data = history_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download History CSV",
            data=csv_data,
            file_name="sql_optimization_history.csv",
            mime="text/csv"
        )
