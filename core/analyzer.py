"""SQL Query Analyzer.

Parses SQL queries using AST (sqlglot / sqlparse) and detects structural
inefficiencies, antipatterns, and performance bottlenecks.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Comparison
from sqlparse.tokens import Keyword, DML, Wildcard

try:
    import sqlglot
    from sqlglot import exp
    HAS_SQLGLOT = True
except ImportError:
    HAS_SQLGLOT = False


@dataclass
class Inefficiency:
    code: str
    title: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    description: str
    suggestion: str
    rule_category: str  # e.g., "Indexing", "Projection", "Join", "Predicate"
    snippet: Optional[str] = None


@dataclass
class AnalysisResult:
    is_valid: bool
    query: str
    formatted_query: str
    statement_type: str
    inefficiencies: List[Inefficiency] = field(default_factory=list)
    complexity_score: int = 0  # 1 - 100
    inefficiency_score: int = 0  # 0 - 100 (0 = clean, 100 = critical)
    tables_involved: List[str] = field(default_factory=list)
    has_joins: bool = False
    has_subqueries: bool = False
    has_aggregations: bool = False
    error_message: Optional[str] = None


class SQLAnalyzer:
    """Analyzes SQL queries for anti-patterns and performance risks."""

    def __init__(self, dialect: str = "mysql"):
        self.dialect = dialect.lower()

    def analyze(self, query: str) -> AnalysisResult:
        query_clean = query.strip().rstrip(";")
        if not query_clean:
            return AnalysisResult(
                is_valid=False,
                query=query,
                formatted_query="",
                statement_type="EMPTY",
                error_message="Query cannot be empty."
            )

        formatted = sqlparse.format(
            query_clean,
            reindent=True,
            keyword_case="upper",
            identifier_case="lower"
        )

        statement_type = self._detect_statement_type(query_clean)
        inefficiencies: List[Inefficiency] = []
        tables: List[str] = []
        has_joins = False
        has_subqueries = False
        has_aggregations = False

        # Attempt sqlglot AST parsing
        glot_parsed = None
        if HAS_SQLGLOT:
            try:
                glot_dialect = "mysql" if self.dialect in ["mysql", "mariadb"] else "postgres"
                expressions = sqlglot.parse(query_clean, read=glot_dialect)
                if expressions and expressions[0] is not None:
                    glot_parsed = expressions[0]
            except Exception:
                glot_parsed = None

        if glot_parsed is not None:
            self._analyze_with_sqlglot(
                glot_parsed, inefficiencies, tables
            )
            has_joins = bool(list(glot_parsed.find_all(exp.Join)))
            has_subqueries = bool(list(glot_parsed.find_all(exp.Subquery))) or bool(list(glot_parsed.find_all(exp.Select))[1:])
            has_aggregations = bool(list(glot_parsed.find_all(exp.AggFunc))) or bool(glot_parsed.find(exp.Group))
        else:
            # Fallback to sqlparse & regex-based analysis
            self._analyze_with_sqlparse(
                query_clean, inefficiencies, tables
            )
            upper_q = query_clean.upper()
            has_joins = " JOIN " in upper_q or ("," in upper_q and "FROM" in upper_q)
            has_subqueries = "(SELECT" in upper_q.replace(" ", "")
            has_aggregations = any(f"{fn}(" in upper_q for fn in ["COUNT", "SUM", "AVG", "MAX", "MIN"]) or "GROUP BY" in upper_q

        # Add regex-based heuristics that complement AST
        self._analyze_heuristic_patterns(query_clean, inefficiencies)

        # Deduplicate inefficiencies by code
        unique_inefficiencies = []
        seen_codes = set()
        for item in inefficiencies:
            if item.code not in seen_codes:
                seen_codes.add(item.code)
                unique_inefficiencies.append(item)

        # Calculate scores
        inefficiency_score = self._calculate_inefficiency_score(unique_inefficiencies)
        complexity_score = self._calculate_complexity_score(
            query_clean, tables, has_joins, has_subqueries, has_aggregations
        )

        return AnalysisResult(
            is_valid=True,
            query=query_clean,
            formatted_query=formatted,
            statement_type=statement_type,
            inefficiencies=unique_inefficiencies,
            complexity_score=complexity_score,
            inefficiency_score=inefficiency_score,
            tables_involved=list(set(tables)),
            has_joins=has_joins,
            has_subqueries=has_subqueries,
            has_aggregations=has_aggregations
        )

    def _detect_statement_type(self, query: str) -> str:
        first_token = query.strip().split()[0].upper() if query.strip() else "UNKNOWN"
        return first_token

    def _analyze_with_sqlglot(self, root: Any, inefficiencies: List[Inefficiency], tables: List[str]):
        # Extract tables
        for table in root.find_all(exp.Table):
            if table.name:
                tables.append(table.name)

        # 1. Detect SELECT *
        for star in root.find_all(exp.Star):
            inefficiencies.append(Inefficiency(
                code="SELECT_STAR",
                title="Unbounded Column Projection (SELECT *)",
                severity="MEDIUM",
                description="Using 'SELECT *' retrieves all columns from the table, increasing disk I/O, memory cache eviction, and network payload. It also prevents index-only covering scans.",
                suggestion="Specify only the columns explicitly needed by your application (e.g., SELECT id, username, email).",
                rule_category="Projection",
                snippet=str(star)
            ))
            break

        # 2. Missing WHERE in UPDATE or DELETE
        if isinstance(root, (exp.Update, exp.Delete)):
            if not root.find(exp.Where):
                inefficiencies.append(Inefficiency(
                    code="MISSING_WHERE_MODIFY",
                    title="Destructive Statement Missing WHERE Clause",
                    severity="CRITICAL",
                    description=f"This {root.key.upper()} statement has no WHERE clause, meaning it will affect every single row in the target table.",
                    suggestion="Add a specific WHERE clause with indexed primary or foreign keys to limit affected rows.",
                    rule_category="Safety / Data Integrity"
                ))

        # 3. Missing LIMIT on non-aggregated SELECT
        if isinstance(root, exp.Select):
            has_limit = root.find(exp.Limit) is not None
            has_group = root.find(exp.Group) is not None
            has_agg = bool(list(root.find_all(exp.AggFunc)))
            if not has_limit and not has_group and not has_agg:
                inefficiencies.append(Inefficiency(
                    code="MISSING_LIMIT",
                    title="Unbounded Result Set (Missing LIMIT)",
                    severity="LOW",
                    description="The SELECT query fetches records without a LIMIT clause, which can cause excessive memory consumption if the table scales.",
                    suggestion="Add a LIMIT clause (e.g. LIMIT 50 or pagination) if only a subset or preview of data is required.",
                    rule_category="Pagination & Scans"
                ))

        # 4. Cartesian Product / Joins without ON
        for join in root.find_all(exp.Join):
            if join.kind == "CROSS" or (not join.args.get("on") and not join.args.get("using")):
                inefficiencies.append(Inefficiency(
                    code="CARTESIAN_PRODUCT",
                    title="Cartesian Product / Unconstrained JOIN",
                    severity="CRITICAL",
                    description="A JOIN occurs without an ON or USING condition, producing an M x N Cartesian product that can severely exhaust server CPU and RAM.",
                    suggestion="Explicitly define the relationship using 'INNER JOIN table ON a.id = b.a_id'.",
                    rule_category="Joins",
                    snippet=str(join)
                ))

        # 5. Non-Sargable function on column in WHERE
        where_node = root.find(exp.Where)
        if where_node:
            for func in where_node.find_all(exp.Func):
                # Check if function wraps a column
                has_column_arg = bool(list(func.find_all(exp.Column)))
                func_name = func.key.upper()
                if has_column_arg and func_name in ["YEAR", "MONTH", "DAY", "DATE", "UPPER", "LOWER", "SUBSTR", "SUBSTRING", "DATE_FORMAT", "CONCAT"]:
                    inefficiencies.append(Inefficiency(
                        code="NON_SARGABLE_FUNCTION",
                        title="Non-Sargable Function on Predicate Column",
                        severity="HIGH",
                        description=f"Function {func_name}() is applied directly to a table column in the WHERE clause, preventing database B-Tree index lookups and forcing a full table scan.",
                        suggestion=f"Rewrite the expression to compare the column directly against a calculated range (e.g., date_col >= '2024-01-01' AND date_col < '2025-01-01').",
                        rule_category="Indexing & Sargability",
                        snippet=str(func)
                    ))

        # 6. IN (SELECT ...) Subquery
        if where_node:
            for in_expr in where_node.find_all(exp.In):
                if in_expr.find(exp.Select):
                    inefficiencies.append(Inefficiency(
                        code="IN_SUBQUERY",
                        title="Suboptimal IN (SELECT ...) Subquery",
                        severity="MEDIUM",
                        description="Subqueries inside IN (...) often evaluate repeatedly or materialize unnecessary intermediate result sets.",
                        suggestion="Rewrite using 'EXISTS (SELECT 1 FROM ... WHERE ...)' or convert into an 'INNER JOIN'.",
                        rule_category="Subqueries",
                        snippet=str(in_expr)[:80] + "..."
                    ))

    def _analyze_with_sqlparse(self, query: str, inefficiencies: List[Inefficiency], tables: List[str]):
        parsed = sqlparse.parse(query)
        if not parsed:
            return
        stmt = parsed[0]

        # Extract table names
        from_seen = False
        for token in stmt.tokens:
            if token.is_keyword and token.value.upper() == "FROM":
                from_seen = True
                continue
            if from_seen:
                if isinstance(token, IdentifierList):
                    for id_ in token.get_identifiers():
                        tables.append(id_.get_real_name() or str(id_))
                elif isinstance(token, Identifier):
                    tables.append(token.get_real_name() or str(token))
                elif token.is_keyword and token.value.upper() in ["WHERE", "GROUP", "ORDER", "LIMIT", "INNER", "LEFT", "RIGHT", "JOIN"]:
                    break

        # Check for SELECT *
        if re.search(r"SELECT\s+(\*|[\w\.]+\.\*)\s+FROM", query, re.IGNORECASE):
            inefficiencies.append(Inefficiency(
                code="SELECT_STAR",
                title="Unbounded Column Projection (SELECT *)",
                severity="MEDIUM",
                description="Using 'SELECT *' retrieves all columns, causing extra I/O and preventing covering index scans.",
                suggestion="Explicitly name only the columns required.",
                rule_category="Projection"
            ))

    def _analyze_heuristic_patterns(self, query: str, inefficiencies: List[Inefficiency]):
        # 1. Leading wildcard LIKE
        leading_like_match = re.search(r"\bLIKE\s+['\"]%[^'\"]*['\"]", query, re.IGNORECASE)
        if leading_like_match:
            inefficiencies.append(Inefficiency(
                code="LEADING_WILDCARD_LIKE",
                title="Leading Wildcard in LIKE Condition",
                severity="HIGH",
                description="LIKE conditions starting with a wildcard (e.g. LIKE '%pattern') cannot utilize standard B-Tree indexes, triggering a full table scan.",
                suggestion="Use trailing wildcard search (LIKE 'pattern%'), equality, or implement Full-Text Indexing (MATCH ... AGAINST).",
                rule_category="Indexing & Sargability",
                snippet=leading_like_match.group(0)
            ))

        # 2. ORDER BY RAND()
        if re.search(r"ORDER\s+BY\s+RAND\s*\(\s*\)", query, re.IGNORECASE):
            inefficiencies.append(Inefficiency(
                code="ORDER_BY_RAND",
                title="Extremely Inefficient ORDER BY RAND()",
                severity="HIGH",
                description="ORDER BY RAND() assigns a random float to every row, sorting the entire dataset in a temporary table with a filesort.",
                suggestion="Retrieve a random ID through application logic or join on a precomputed random index instead.",
                rule_category="Sorting & Temp Tables",
                snippet="ORDER BY RAND()"
            ))

        # 3. Disjunctive OR in WHERE clause across disparate fields
        if re.search(r"\bWHERE\b.*?\bOR\b", query, re.IGNORECASE):
            # Check if OR is present in WHERE clause
            inefficiencies.append(Inefficiency(
                code="DISJUNCTIVE_OR",
                title="Potential Index Invalidation with Disjunctive 'OR'",
                severity="MEDIUM",
                description="Using 'OR' across different columns often prevents standard single-column B-Tree index scans and may cause index merge or full table scans.",
                suggestion="Consider rewriting multiple OR predicates using 'UNION ALL' or composite/covering indexes.",
                rule_category="Predicates"
            ))

        # 4. Redundant DISTINCT with GROUP BY
        if re.search(r"\bSELECT\s+DISTINCT\b", query, re.IGNORECASE) and re.search(r"\bGROUP\s+BY\b", query, re.IGNORECASE):
            inefficiencies.append(Inefficiency(
                code="REDUNDANT_DISTINCT",
                title="Redundant DISTINCT with GROUP BY",
                severity="LOW",
                description="GROUP BY already aggregates rows by the group keys; adding DISTINCT forces an additional sorting/hashing pass.",
                suggestion="Remove DISTINCT when GROUP BY already ensures unique output rows.",
                rule_category="Aggregation"
            ))

        # 5. Implicit Cartesian joins via comma separation in FROM
        from_comma_match = re.search(r"\bFROM\s+([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)", query, re.IGNORECASE)
        if from_comma_match and "WHERE" not in query.upper():
            inefficiencies.append(Inefficiency(
                code="IMPLICIT_CROSS_JOIN",
                title="Implicit Comma Cross Join without WHERE Filter",
                severity="CRITICAL",
                description=f"Tables '{from_comma_match.group(1)}' and '{from_comma_match.group(2)}' are joined using comma syntax without explicit join conditions or WHERE filters.",
                suggestion="Use explicit ANSI JOIN syntax: 'FROM table1 JOIN table2 ON table1.id = table2.table1_id'.",
                rule_category="Joins",
                snippet=from_comma_match.group(0)
            ))

        # 6. NOT IN with NULL risk
        if re.search(r"\bNOT\s+IN\s*\(", query, re.IGNORECASE):
            inefficiencies.append(Inefficiency(
                code="NOT_IN_NULL_RISK",
                title="Suboptimal NOT IN Predicate",
                severity="MEDIUM",
                description="'NOT IN' returns empty/NULL if any element in the subquery or set contains NULL, and is notoriously slow on unindexed sets.",
                suggestion="Use 'NOT EXISTS' or a 'LEFT JOIN ... WHERE right_table.id IS NULL' which are safer with NULLs and optimize better.",
                rule_category="Predicates",
                snippet="NOT IN"
            ))

    def _calculate_inefficiency_score(self, inefficiencies: List[Inefficiency]) -> int:
        """Calculates an overall inefficiency risk score from 0 (clean) to 100 (critical)."""
        if not inefficiencies:
            return 0
        severity_weights = {
            "CRITICAL": 40,
            "HIGH": 25,
            "MEDIUM": 15,
            "LOW": 5
        }
        raw_score = sum(severity_weights.get(i.severity, 10) for i in inefficiencies)
        return min(100, raw_score)

    def _calculate_complexity_score(
        self, query: str, tables: List[str], has_joins: bool, has_subqueries: bool, has_aggregations: bool
    ) -> int:
        """Calculates a query structural complexity score from 1 to 100."""
        score = 10
        score += len(set(tables)) * 10
        if has_joins:
            # Count occurrences of join
            joins_count = len(re.findall(r"\bJOIN\b", query, re.IGNORECASE)) or 1
            score += joins_count * 12
        if has_subqueries:
            subquery_count = len(re.findall(r"\bSELECT\b", query, re.IGNORECASE)) - 1
            score += max(1, subquery_count) * 15
        if has_aggregations:
            score += 10
        if "GROUP BY" in query.upper():
            score += 10
        if "ORDER BY" in query.upper():
            score += 5
        if "HAVING" in query.upper():
            score += 10
        return min(100, max(1, score))
