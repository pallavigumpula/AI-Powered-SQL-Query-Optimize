"""FastAPI REST API for AI-Powered SQL Query Optimizer.

Exposes endpoints for programmatic query optimization, natural language translation,
and history inspection.
"""

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.analyzer import SQLAnalyzer
from core.optimizer import SQLOptimizer
from core.ai_engine import AIEngine
from core.metrics import PerformanceMetricsEngine
from core.database import DatabaseManager

app = FastAPI(
    title="AI SQL Query Optimizer API",
    description="REST API for automated SQL query analysis, optimization, and metric scoring.",
    version="1.0.0"
)

# Enable CORS for external frontend or microservice integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core singletons
analyzer = SQLAnalyzer(dialect="mysql")
optimizer = SQLOptimizer(dialect="mysql")
ai_engine = AIEngine(provider="built-in")
metrics_engine = PerformanceMetricsEngine()
db_manager = DatabaseManager()


# Request / Response Schemas
class OptimizeRequest(BaseModel):
    query: str = Field(..., example="SELECT * FROM orders WHERE YEAR(order_date) = 2024;")
    dialect: str = Field(default="mysql", example="mysql")
    schema_context: Optional[str] = Field(default=None, example="CREATE TABLE orders (id INT, order_date DATETIME);")
    use_ai: bool = Field(default=False, description="Whether to invoke advanced LLM optimization")


class InefficiencyModel(BaseModel):
    code: str
    title: str
    severity: str
    description: str
    suggestion: str
    snippet: Optional[str] = None


class MetricsModel(BaseModel):
    estimated_cost: float
    complexity_score: int
    scan_type_risk: str
    potential_improvement_pct: float
    estimated_memory_impact: str
    estimated_io_impact: str
    risk_factors: List[str]


class OptimizeResponse(BaseModel):
    is_valid: bool
    statement_type: str
    inefficiency_score: int
    complexity_score: int
    original_query: str
    optimized_query: str
    inefficiencies: List[InefficiencyModel]
    optimizations_applied: List[str]
    explanations: List[str]
    recommended_indexes: List[str]
    original_metrics: MetricsModel
    optimized_metrics: MetricsModel
    logged_id: Optional[int] = None


class NLRequest(BaseModel):
    prompt: str = Field(..., example="Find customers who spent over $500 last month")
    schema_context: Optional[str] = Field(default=None)


class NLResponse(BaseModel):
    sql_query: str
    explanation: str
    assumed_schema: str
    optimization_highlights: List[str]
    model_used: str


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "AI-Powered SQL Query Optimizer API",
        "docs_url": "/docs",
        "database_mode": db_manager.db_type.upper()
    }


@app.post("/api/optimize", response_model=OptimizeResponse)
def optimize_query(req: OptimizeRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # 1. Analyze AST
    custom_analyzer = SQLAnalyzer(dialect=req.dialect)
    analysis = custom_analyzer.analyze(req.query)

    if not analysis.is_valid:
        raise HTTPException(status_code=400, detail=analysis.error_message or "Invalid SQL query.")

    # 2. Rule-based optimization
    custom_optimizer = SQLOptimizer(dialect=req.dialect)
    opt_res = custom_optimizer.optimize(req.query, analysis)

    # 3. Optional AI Optimization
    ai_mode_label = "Rule-Based Engine"
    if req.use_ai:
        try:
            ai_res = ai_engine.optimize_with_ai(
                req.query,
                schema_context=req.schema_context,
                detected_inefficiencies=[i.title for i in analysis.inefficiencies]
            )
            opt_res.optimized_query = ai_res.optimized_sql
            opt_res.optimizations_applied.extend(ai_res.optimizations_applied)
            if ai_res.explanation:
                opt_res.explanations.append(ai_res.explanation)
            opt_res.index_recommendations.extend(ai_res.recommended_indexes)
            ai_mode_label = ai_res.model_used
        except Exception:
            pass

    # 4. Metrics
    orig_m = metrics_engine.calculate_estimated_metrics(analysis, is_optimized=False)
    opt_m = metrics_engine.calculate_estimated_metrics(analysis, is_optimized=True)

    # 5. Persist to History
    logged_id = db_manager.save_history(
        original_query=req.query,
        optimized_query=opt_res.optimized_query,
        statement_type=analysis.statement_type,
        inefficiency_score=analysis.inefficiency_score,
        complexity_score=analysis.complexity_score,
        inefficiencies=[{
            "code": i.code, "title": i.title, "severity": i.severity, "desc": i.description, "sugg": i.suggestion
        } for i in analysis.inefficiencies],
        metrics={"cost": orig_m.estimated_cost, "improvement_pct": orig_m.potential_improvement_pct},
        optimizations=opt_res.optimizations_applied,
        explanations=opt_res.explanations,
        index_recommendations=opt_res.index_recommendations,
        mode=ai_mode_label
    )

    return OptimizeResponse(
        is_valid=True,
        statement_type=analysis.statement_type,
        inefficiency_score=analysis.inefficiency_score,
        complexity_score=analysis.complexity_score,
        original_query=analysis.formatted_query,
        optimized_query=opt_res.optimized_query,
        inefficiencies=[InefficiencyModel(
            code=i.code,
            title=i.title,
            severity=i.severity,
            description=i.description,
            suggestion=i.suggestion,
            snippet=i.snippet
        ) for i in analysis.inefficiencies],
        optimizations_applied=opt_res.optimizations_applied,
        explanations=opt_res.explanations,
        recommended_indexes=list(set(opt_res.index_recommendations)),
        original_metrics=MetricsModel(**orig_m.__dict__),
        optimized_metrics=MetricsModel(**opt_m.__dict__),
        logged_id=logged_id
    )


@app.post("/api/natural-language", response_model=NLResponse)
def natural_language_to_sql(req: NLRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    resp = ai_engine.natural_language_to_sql(req.prompt, req.schema_context)
    return NLResponse(
        sql_query=resp.sql_query,
        explanation=resp.explanation,
        assumed_schema=resp.assumed_schema,
        optimization_highlights=resp.optimization_highlights,
        model_used=resp.model_used
    )


@app.get("/api/history")
def get_query_history(limit: int = 50):
    df = db_manager.get_history(limit=limit)
    return df.to_dict(orient="records")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
