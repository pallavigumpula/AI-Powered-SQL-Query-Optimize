"""Database persistence layer for SQL Query Optimizer.

Supports MySQL (with automatic SQLite fallback) for logging query history,
storing optimization analytics, and executing live EXPLAIN queries.
"""

import os
import json
import sqlite3
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd

try:
    import pymysql
    from pymysql.cursors import DictCursor
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False


class DatabaseManager:
    """Handles MySQL connections and query history logging with SQLite fallback."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 3306,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        use_sqlite_fallback: bool = True
    ):
        self.host = host or os.getenv("MYSQL_HOST", "localhost")
        self.port = int(port or os.getenv("MYSQL_PORT", 3306))
        self.user = user or os.getenv("MYSQL_USER", "root")
        self.password = password or os.getenv("MYSQL_PASSWORD", "")
        self.database = database or os.getenv("MYSQL_DATABASE", "sql_optimizer")
        self.use_sqlite_fallback = use_sqlite_fallback
        self.sqlite_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sql_optimizer.db")

        self.db_type = "unknown"
        self._init_storage()

    def _get_mysql_connection(self, create_db_if_missing: bool = True):
        if not HAS_PYMYSQL:
            raise ImportError("PyMySQL is not installed.")

        # Connect without database first to ensure database exists if needed
        if create_db_if_missing:
            conn_admin = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                cursorclass=DictCursor,
                connect_timeout=3
            )
            try:
                with conn_admin.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database}`;")
                conn_admin.commit()
            finally:
                conn_admin.close()

        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            cursorclass=DictCursor,
            connect_timeout=3
        )

    def _get_sqlite_connection(self):
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def test_connection(self) -> Tuple[bool, str, str]:
        """Tests connection to MySQL, returning (success, message, db_type)."""
        if not HAS_PYMYSQL:
            return False, "PyMySQL is not installed.", "sqlite"
        try:
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                cursorclass=DictCursor,
                connect_timeout=2
            )
            with conn.cursor() as cursor:
                cursor.execute("SELECT VERSION() as ver;")
                res = cursor.fetchone()
                version = res.get("ver", "unknown") if res else "unknown"
            conn.close()
            return True, f"Successfully connected to MySQL {version} at {self.host}:{self.port}", "mysql"
        except Exception as e:
            return False, f"MySQL connection failed: {str(e)}", "sqlite"

    def _init_storage(self):
        """Initializes tables in either MySQL or SQLite."""
        is_mysql, _, _ = self.test_connection()
        if is_mysql:
            self.db_type = "mysql"
            try:
                conn = self._get_mysql_connection()
                with conn.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS query_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            original_query TEXT NOT NULL,
                            optimized_query TEXT NOT NULL,
                            statement_type VARCHAR(50),
                            inefficiency_score INT,
                            complexity_score INT,
                            inefficiencies_json JSON,
                            metrics_json JSON,
                            optimizations_json JSON,
                            explanations_text TEXT,
                            index_recommendations_text TEXT,
                            mode VARCHAR(50) DEFAULT 'Rule-Based',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS favorite_queries (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            title VARCHAR(150) NOT NULL,
                            category VARCHAR(100) DEFAULT 'General',
                            query TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                conn.commit()
                conn.close()
                return
            except Exception:
                pass

        # Fallback to SQLite
        self.db_type = "sqlite"
        conn = self._get_sqlite_connection()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_query TEXT NOT NULL,
                    optimized_query TEXT NOT NULL,
                    statement_type TEXT,
                    inefficiency_score INTEGER,
                    complexity_score INTEGER,
                    inefficiencies_json TEXT,
                    metrics_json TEXT,
                    optimizations_json TEXT,
                    explanations_text TEXT,
                    index_recommendations_text TEXT,
                    mode TEXT DEFAULT 'Rule-Based',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS favorite_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category TEXT DEFAULT 'General',
                    query TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.close()

    def save_history(
        self,
        original_query: str,
        optimized_query: str,
        statement_type: str,
        inefficiency_score: int,
        complexity_score: int,
        inefficiencies: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        optimizations: List[str],
        explanations: List[str],
        index_recommendations: List[str],
        mode: str = "Rule-Based"
    ) -> int:
        """Saves an optimization run into history."""
        ineff_json = json.dumps(inefficiencies)
        metrics_json = json.dumps(metrics)
        opt_json = json.dumps(optimizations)
        expl_text = "\n\n".join(explanations)
        idx_text = "\n".join(index_recommendations)

        if self.db_type == "mysql":
            try:
                conn = self._get_mysql_connection()
                with conn.cursor() as cursor:
                    sql = """
                        INSERT INTO query_history (
                            original_query, optimized_query, statement_type,
                            inefficiency_score, complexity_score, inefficiencies_json,
                            metrics_json, optimizations_json, explanations_text,
                            index_recommendations_text, mode
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """
                    cursor.execute(sql, (
                        original_query, optimized_query, statement_type,
                        inefficiency_score, complexity_score, ineff_json,
                        metrics_json, opt_json, expl_text, idx_text, mode
                    ))
                    new_id = cursor.lastrowid
                conn.commit()
                conn.close()
                return new_id
            except Exception:
                # If MySQL fails on write, fallback to SQLite
                self.db_type = "sqlite"

        # SQLite insert
        conn = self._get_sqlite_connection()
        with conn:
            cursor = conn.execute("""
                INSERT INTO query_history (
                    original_query, optimized_query, statement_type,
                    inefficiency_score, complexity_score, inefficiencies_json,
                    metrics_json, optimizations_json, explanations_text,
                    index_recommendations_text, mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                original_query, optimized_query, statement_type,
                inefficiency_score, complexity_score, ineff_json,
                metrics_json, opt_json, expl_text, idx_text, mode
            ))
            new_id = cursor.lastrowid
        conn.close()
        return new_id

    def get_history(self, limit: int = 50) -> pd.DataFrame:
        """Retrieves past query optimizations as a pandas DataFrame."""
        if self.db_type == "mysql":
            try:
                conn = self._get_mysql_connection()
                query = f"SELECT * FROM query_history ORDER BY id DESC LIMIT {limit};"
                df = pd.read_sql_query(query, conn)
                conn.close()
                return df
            except Exception:
                self.db_type = "sqlite"

        conn = self._get_sqlite_connection()
        query = f"SELECT * FROM query_history ORDER BY id DESC LIMIT {limit};"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def clear_history(self) -> bool:
        """Clears all records in query_history."""
        if self.db_type == "mysql":
            try:
                conn = self._get_mysql_connection()
                with conn.cursor() as cursor:
                    cursor.execute("TRUNCATE TABLE query_history;")
                conn.commit()
                conn.close()
                return True
            except Exception:
                pass

        conn = self._get_sqlite_connection()
        with conn:
            conn.execute("DELETE FROM query_history;")
        conn.close()
        return True

    def run_explain(self, query: str) -> Tuple[List[Dict[str, Any]], Optional[float], Optional[str]]:
        """Executes EXPLAIN on MySQL. Returns (explain_rows, execution_time_ms, error)."""
        clean_q = query.strip().rstrip(";")
        if not clean_q.upper().startswith("SELECT"):
            return [], None, "EXPLAIN is only supported for SELECT statements."

        if self.db_type != "mysql":
            return [], None, "Live EXPLAIN requires an active MySQL connection."

        try:
            conn = self._get_mysql_connection()
            explain_query = f"EXPLAIN {clean_q};"
            t0 = time.perf_counter()
            with conn.cursor() as cursor:
                cursor.execute(explain_query)
                rows = cursor.fetchall()
            exec_time_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            conn.close()
            return rows, exec_time_ms, None
        except Exception as e:
            return [], None, f"EXPLAIN error: {str(e)}"

    def get_database_tables(self) -> List[str]:
        """Lists tables in the active database."""
        if self.db_type == "mysql":
            try:
                conn = self._get_mysql_connection()
                with conn.cursor() as cursor:
                    cursor.execute("SHOW TABLES;")
                    rows = cursor.fetchall()
                conn.close()
                tables = []
                for r in rows:
                    tables.append(list(r.values())[0])
                return tables
            except Exception:
                return []
        return []

    # ---------------- FAVORITE QUERIES ----------------
    def save_favorite(self, title: str, query: str, category: str = "General") -> int:
        """Saves a query to favorite_queries."""
        if self.db_type == "mysql":
            try:
                conn = self._get_mysql_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO favorite_queries (title, category, query) VALUES (%s, %s, %s);",
                        (title, category, query)
                    )
                    fav_id = cursor.lastrowid
                conn.commit()
                conn.close()
                return fav_id
            except Exception:
                self.db_type = "sqlite"

        conn = self._get_sqlite_connection()
        with conn:
            cursor = conn.execute(
                "INSERT INTO favorite_queries (title, category, query) VALUES (?, ?, ?);",
                (title, category, query)
            )
            fav_id = cursor.lastrowid
        conn.close()
        return fav_id

    def get_favorites(self) -> List[Dict[str, Any]]:
        """Retrieves all bookmarked favorite queries."""
        if self.db_type == "mysql":
            try:
                conn = self._get_mysql_connection()
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM favorite_queries ORDER BY id DESC;")
                    rows = cursor.fetchall()
                conn.close()
                return rows
            except Exception:
                self.db_type = "sqlite"

        conn = self._get_sqlite_connection()
        with conn:
            rows = [dict(r) for r in conn.execute("SELECT * FROM favorite_queries ORDER BY id DESC;").fetchall()]
        conn.close()
        return rows

    def delete_favorite(self, fav_id: int) -> bool:
        """Deletes a bookmarked favorite query."""
        if self.db_type == "mysql":
            try:
                conn = self._get_mysql_connection()
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM favorite_queries WHERE id = %s;", (fav_id,))
                conn.commit()
                conn.close()
                return True
            except Exception:
                self.db_type = "sqlite"

        conn = self._get_sqlite_connection()
        with conn:
            conn.execute("DELETE FROM favorite_queries WHERE id = ?;", (fav_id,))
        conn.close()
        return True

    def execute_query(self, query: str, limit: Optional[int] = 1000) -> Tuple[List[Dict[str, Any]], Optional[str], float]:
        """Executes a SELECT query and returns (rows, error_message, exec_time_ms)."""
        clean_q = query.strip().rstrip(";")
        if not clean_q.upper().startswith("SELECT"):
            return [], "Only SELECT queries can be executed in the Results Grid.", 0.0

        # Enforce limit if specified and query has no limit
        if limit and "LIMIT" not in clean_q.upper():
            clean_q = f"{clean_q} LIMIT {limit}"

        t0 = time.perf_counter()
        if self.db_type == "mysql":
            try:
                conn = self._get_mysql_connection()
                with conn.cursor() as cursor:
                    cursor.execute(clean_q)
                    rows = cursor.fetchall()
                conn.close()
                exec_time_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                return rows, None, exec_time_ms
            except Exception as e:
                return [], str(e), 0.0

        # SQLite fallback execution (using mock or local benchmark database)
        try:
            conn = self._get_sqlite_connection()
            rows = [dict(r) for r in conn.execute(clean_q).fetchall()]
            conn.close()
            exec_time_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return rows, None, exec_time_ms
        except Exception as e:
            return [], str(e), 0.0
