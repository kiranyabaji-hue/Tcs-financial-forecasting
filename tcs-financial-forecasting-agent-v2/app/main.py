from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import ForecastRequest
from app.database.db import init_db, get_db
from app.database.models import ForecastLog
from app.agent import ForecastingAgent
from app.tools.financial_extractor import FinancialDataExtractorTool
from app.tools.qualitative_analysis import QualitativeAnalysisTool
from app.services.document_discovery import discover_pdf_links, download_pdf

app = FastAPI(
    title="TCS Financial Forecasting Agent",
    version="2.0.0",
    description="TCS outlook using financial report extraction and earnings-call transcript RAG."
)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok", "service": "tcs-financial-forecasting-agent"}

@app.get("/api/v1/documents/discover")
def discover_documents():
    """Find candidate PDF links from configured TCS investor relations page."""
    try:
        return {"documents": discover_pdf_links()}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Document discovery failed: {exc}")

@app.post("/api/v1/ingest")
def ingest():
    try:
        metrics = FinancialDataExtractorTool().run()
        chunks = QualitativeAnalysisTool().ingest()
        return {
            "status": "completed",
            "financial_metrics_extracted": len(metrics),
            "transcript_chunks_indexed": chunks,
            "note": "Verify extracted figures against original PDF pages."
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")

@app.post("/api/v1/forecast")
def forecast(payload: ForecastRequest, db: Session = Depends(get_db)):
    log = ForecastLog(
        company=payload.company,
        request_json=payload.model_dump(),
        status="processing"
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    try:
        output = ForecastingAgent().generate(payload)
        log.response_json = output
        log.status = "completed"
        db.commit()
        return {"request_id": log.id, "result": output}
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)[:4000]
        db.commit()
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {exc}")
