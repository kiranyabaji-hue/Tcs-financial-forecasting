import json
import re
from langchain_openai import ChatOpenAI
from app.config import settings
from app.services.pdf_loader import load_folder

METRIC_TERMS = (
    "revenue from operations", "total revenue", "revenue", "net profit",
    "profit for the year", "profit after tax", "operating margin",
    "operating profit", "ebit", "ebit margin", "net margin"
)

class FinancialDataExtractorTool:
    """
    Extract financial facts with source provenance.
    Quarterly result PDFs should be placed in data/financial_reports.
    Annual reports are also supported but remain labelled as annual.
    """
    name = "FinancialDataExtractorTool"
    description = "Extract revenue, net profit, operating margin and related metrics from TCS reports."

    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=0,
        )

    @staticmethod
    def _candidate_pages(pages: list[dict]) -> list[dict]:
        candidates = []
        for page in pages:
            lower = page["text"].lower()
            hits = sum(1 for term in METRIC_TERMS if term in lower)
            if hits >= 2:
                candidates.append(page)
        return candidates

    def run(self) -> list[dict]:
        pages = load_folder("data/financial_reports")
        candidates = self._candidate_pages(pages)
        extracted = []
        # One page per model call limits context and makes page provenance reliable.
        for page in candidates:
            excerpt = page["text"][:10000]
            prompt = f"""
Extract explicitly stated TCS consolidated financial metrics from this single report page.
Return ONLY a JSON array. Each object must have:
metric, value, period, unit, source, page, evidence_text.
Extract only values actually present on this page. Do not calculate or infer.
Keep annual periods annual and quarterly periods quarterly. Never relabel annual as quarterly.
If the page contains standalone table values without clear metric/period mapping, omit them.
Prefer Total Revenue/Revenue from Operations, Net Profit/PAT, Operating Profit/EBIT,
Operating Margin/EBIT Margin and Net Margin. Preserve units exactly.
source must be {page['source']!r}; page must be {page['page']}.

PAGE TEXT:
{excerpt}
"""
            content = self.llm.invoke(prompt).content
            raw = content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            try:
                items = json.loads(raw)
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            item["source"] = page["source"]
                            item["page"] = page["page"]
                            extracted.append(item)
            except json.JSONDecodeError:
                continue
        # Deduplicate repeated metric/page outputs.
        unique = {}
        for item in extracted:
            key = (item.get("metric"), item.get("period"), item.get("source"), item.get("page"))
            unique[key] = item
        return list(unique.values())
