from pydantic import BaseModel, Field
from typing import Literal

class ForecastRequest(BaseModel):
    company: str = "Tata Consultancy Services"
    ticker: str = "TCS"
    horizon: str = "upcoming quarter"
    question: str = (
        "Analyze financial trends, management outlook, opportunities and risks "
        "and provide a qualitative business forecast."
    )

class MetricEvidence(BaseModel):
    metric: str
    value: str | None = None
    period: str | None = None
    unit: str | None = None
    source: str
    page: int | None = None
    evidence_text: str | None = None

class ForecastResponse(BaseModel):
    company: str
    horizon: str
    executive_outlook: str
    financial_trends: list[str] = Field(default_factory=list)
    outlook_by_dimension: dict[str, str] = Field(default_factory=dict)
    management_outlook: list[str] = Field(default_factory=list)
    recurring_themes: list[str] = Field(default_factory=list)
    positive_drivers: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    financial_metrics: list[MetricEvidence] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)
    confidence: Literal["Low", "Medium", "High"] = "Low"
    limitations: list[str] = Field(default_factory=list)
