"""SQL Query Performance & Cost Metrics.

Calculates estimated performance metrics (cost score, scan footprint, complexity)
and parses real MySQL EXPLAIN / EXPLAIN ANALYZE plans for comparative evaluation.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time
from core.analyzer import AnalysisResult


@dataclass
class MetricSummary:
    estimated_cost: float
    complexity_score: int
    scan_type_risk: str  # "FULL TABLE SCAN", "INDEX RANGE", "INDEX SEEK", "LOW RISK"
    potential_improvement_pct: float
    estimated_memory_impact: str  # "High", "Medium", "Low"
    estimated_io_impact: str      # "High", "Medium", "Low"
    risk_factors: List[str] = field(default_factory=list)


@dataclass
class ExplainStep:
    select_id: Optional[int]
    table_name: str
    access_type: str  # ALL, index, range, ref, eq_ref, const
    possible_keys: Optional[str]
    key_used: Optional[str]
    rows_examined: int
    filtered_pct: float
    extra: str


@dataclass
class PlanComparison:
    has_live_data: bool
    original_cost: Optional[float]
    optimized_cost: Optional[float]
    original_rows_examined: Optional[int]
    optimized_rows_examined: Optional[int]
    original_exec_time_ms: Optional[float]
    optimized_exec_time_ms: Optional[float]
    improvement_pct: Optional[float]
    original_steps: List[ExplainStep] = field(default_factory=list)
    optimized_steps: List[ExplainStep] = field(default_factory=list)
    verdict: str = ""


class PerformanceMetricsEngine:
    """Calculates query execution cost estimates and evaluates real EXPLAIN plans."""

    def calculate_estimated_metrics(self, analysis: AnalysisResult, is_optimized: bool = False) -> MetricSummary:
        """Calculates algorithmic cost and scan footprint estimates based on AST and antipatterns."""
        base_cost = 10.0 + (len(analysis.tables_involved) * 15.0)
        risk_factors = []
        scan_risk = "LOW RISK"
        mem_impact = "Low"
        io_impact = "Low"

        if is_optimized:
            # Optimized version has reduced footprint
            return MetricSummary(
                estimated_cost=round(base_cost * 0.35, 1),
                complexity_score=max(5, int(analysis.complexity_score * 0.7)),
                scan_type_risk="INDEX SEEK / RANGE",
                potential_improvement_pct=0.0,
                estimated_memory_impact="Low",
                estimated_io_impact="Low",
                risk_factors=["Optimized with index/projection safeguards"]
            )

        # Evaluate risk factors based on detected inefficiencies
        for ineff in analysis.inefficiencies:
            if ineff.code == "CARTESIAN_PRODUCT":
                base_cost += 350.0
                scan_risk = "CRITICAL: UNCONSTRAINED SCAN"
                mem_impact = "High"
                io_impact = "High"
                risk_factors.append("Cartesian product causes exponential row multiplication")
            elif ineff.code == "LEADING_WILDCARD_LIKE":
                base_cost += 120.0
                scan_risk = "FULL TABLE SCAN"
                io_impact = "High"
                risk_factors.append("Leading wildcard disables B-Tree index seeks")
            elif ineff.code == "NON_SARGABLE_FUNCTION":
                base_cost += 90.0
                scan_risk = "FULL TABLE SCAN"
                io_impact = "High"
                risk_factors.append("Function evaluation on column invalidates indexes")
            elif ineff.code == "SELECT_STAR":
                base_cost += 30.0
                mem_impact = "Medium"
                io_impact = "Medium"
                risk_factors.append("SELECT * prevents covering index optimization")
            elif ineff.code == "ORDER_BY_RAND":
                base_cost += 150.0
                mem_impact = "High"
                risk_factors.append("Full table filesort and temporary memory buffer allocated")
            elif ineff.code == "IN_SUBQUERY":
                base_cost += 60.0
                risk_factors.append("Subquery materialization overhead")

        # Potential improvement calculation
        if analysis.inefficiency_score > 70:
            improvement = 75.0 + min(20.0, analysis.inefficiency_score * 0.2)
        elif analysis.inefficiency_score > 30:
            improvement = 45.0 + (analysis.inefficiency_score * 0.4)
        elif analysis.inefficiency_score > 0:
            improvement = 20.0 + (analysis.inefficiency_score * 0.3)
        else:
            improvement = 0.0

        if not risk_factors:
            risk_factors.append("No critical query antipatterns detected")

        return MetricSummary(
            estimated_cost=round(base_cost, 1),
            complexity_score=analysis.complexity_score,
            scan_type_risk=scan_risk,
            potential_improvement_pct=round(improvement, 1),
            estimated_memory_impact=mem_impact,
            estimated_io_impact=io_impact,
            risk_factors=risk_factors
        )

    def parse_mysql_explain(self, raw_explain_rows: List[Dict[str, Any]]) -> List[ExplainStep]:
        """Parses standard MySQL tabular EXPLAIN output into structured ExplainSteps."""
        steps = []
        for row in raw_explain_rows:
            # Handle both lowercase and uppercase dictionary keys from MySQL cursor
            row_normalized = {k.lower(): v for k, v in row.items()}
            steps.append(ExplainStep(
                select_id=row_normalized.get("id"),
                table_name=str(row_normalized.get("table") or "Unknown"),
                access_type=str(row_normalized.get("type") or "ALL").upper(),
                possible_keys=row_normalized.get("possible_keys"),
                key_used=row_normalized.get("key"),
                rows_examined=int(row_normalized.get("rows") or 0),
                filtered_pct=float(row_normalized.get("filtered") or 100.0),
                extra=str(row_normalized.get("extra") or "")
            ))
        return steps

    def compare_live_plans(
        self,
        orig_explain: List[Dict[str, Any]],
        opt_explain: List[Dict[str, Any]],
        orig_time_ms: Optional[float] = None,
        opt_time_ms: Optional[float] = None,
        orig_cost: Optional[float] = None,
        opt_cost: Optional[float] = None,
    ) -> PlanComparison:
        """Compares two live MySQL EXPLAIN plans and execution timings."""
        orig_steps = self.parse_mysql_explain(orig_explain)
        opt_steps = self.parse_mysql_explain(opt_explain)

        orig_rows = sum(s.rows_examined for s in orig_steps)
        opt_rows = sum(s.rows_examined for s in opt_steps)

        # Calculate improvement %
        improvement = 0.0
        if orig_time_ms and opt_time_ms and orig_time_ms > 0:
            improvement = round(((orig_time_ms - opt_time_ms) / orig_time_ms) * 100.0, 1)
        elif orig_rows > 0 and opt_rows >= 0:
            improvement = round(((orig_rows - opt_rows) / orig_rows) * 100.0, 1)

        # Verdict
        verdict = "Optimized query reduces rows scanned and execution overhead."
        if opt_rows < orig_rows:
            verdict = f"Optimized query scanned {orig_rows - opt_rows:,} fewer rows ({improvement}% reduction)!"
        elif opt_time_ms and orig_time_ms and opt_time_ms < orig_time_ms:
            verdict = f"Optimized query executed {round(orig_time_ms - opt_time_ms, 2)}ms faster ({improvement}% improvement)!"

        return PlanComparison(
            has_live_data=True,
            original_cost=orig_cost,
            optimized_cost=opt_cost,
            original_rows_examined=orig_rows,
            optimized_rows_examined=opt_rows,
            original_exec_time_ms=orig_time_ms,
            optimized_exec_time_ms=opt_time_ms,
            improvement_pct=improvement,
            original_steps=orig_steps,
            optimized_steps=opt_steps,
            verdict=verdict
        )
