from typing import List, Optional, Any, Literal
from pydantic import BaseModel, Field

WhitelistedField = Literal[
    "bank_name", "fdr_number", "institution_name",
    "principal_amount", "maturity_amount", "interest_rate",
    "trust_level", "status", "days_to_maturity", "risk_score"
]

FilterOperator = Literal[
    "eq", "neq", "gt", "gte", "lt", "lte", "contains"
]


class FieldFilter(BaseModel):
    field: WhitelistedField
    operator: FilterOperator
    value: Any


class AskSentinelRequest(BaseModel):
    question: str
    limit: int = Field(default=20, ge=1, le=100)


class AskSentinelResponse(BaseModel):
    original_question: str
    interpreted_filters: List[FieldFilter]
    summary_text: str
    results_count: int
    results: List[dict]
    execution_time_ms: float
    is_rule_fallback: bool = True
