import json
from langchain_openai import ChatOpenAI
from app.config import settings
from app.schemas import ForecastResponse
from app.tools.financial_extractor import FinancialDataExtractorTool
from app.tools.qualitative_analysis import QualitativeAnalysisTool

class ForecastingAgent:
    """Master workflow: financial extraction + transcript RAG + grounded synthesis."""

    def __init__(self):
        self.llm = ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_model, temperature=0)
        self.financial_tool = FinancialDataExtractorTool()
        self.qualitative_tool = QualitativeAnalysisTool()

    def generate(self, request) -> dict:
        metrics = self.financial_tool.run()
        if not metrics:
            raise ValueError(
                "No financial metrics were extracted. Add quarterly results PDFs to "
                "data/financial_reports and check that the PDFs contain selectable text."
            )
        transcript_query = (
            f"{request.company} management outlook demand trends client spending "
            "revenue growth margins deal wins order book AI services hiring attrition "
            "risks opportunities guidance forward-looking statements"
        )
        passages = self.qualitative_tool.search(transcript_query, k=12)
        if not passages:
            raise ValueError("No transcript passages found. Run POST /api/v1/ingest first.")

        prompt = f"""
You are a financial research analyst preparing a qualitative business outlook.
Company: {request.company}; ticker: {request.ticker}; horizon: {request.horizon}.
Question: {request.question}

Use only the evidence supplied below. Do not invent figures, quotes, events, guidance or causal claims.
Clearly distinguish reported financial facts, management statements, and your analysis.
Never treat annual report metrics as quarterly results. Compare periods only when their
period definitions and units make the comparison valid. If evidence is insufficient, say so.
Every factual financial metric must retain its source filename, page, period and unit.
Cite transcript themes with source filename and page.
Return ONLY a JSON object matching this schema:
{{
 "company": string, "horizon": string, "executive_outlook": string,
 "financial_trends": [string], "outlook_by_dimension": {{string:string}},
 "management_outlook": [string], "recurring_themes": [string],
 "positive_drivers": [string], "risks": [string],
 "financial_metrics": [{{"metric":string,"value":string|null,"period":string|null,
 "unit":string|null,"source":string,"page":integer|null,"evidence_text":string|null}}],
 "evidence_references": [string], "confidence": "Low"|"Medium"|"High",
 "limitations": [string]
}}
Confidence is evidence coverage, not a probability. Use Low if evidence is sparse or source coverage incomplete.

FINANCIAL METRICS:
{json.dumps(metrics, ensure_ascii=False)}

RETRIEVED TRANSCRIPT EVIDENCE:
{json.dumps(passages, ensure_ascii=False)}
"""
        raw = self.llm.invoke(prompt).content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = json.loads(raw)
        result = ForecastResponse.model_validate(data)
        return result.model_dump()
