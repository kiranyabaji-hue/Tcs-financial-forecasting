# TCS Financial Forecasting Agent

FastAPI application for generating a source-grounded qualitative business outlook for
Tata Consultancy Services (TCS). Stack: Python 3.10+, FastAPI, LangChain, OpenAI,
ChromaDB, local Sentence Transformers embeddings, PyMuPDF and MySQL 8.x.

## Important scope and source-data warning

The current source set described by the project owner is:
- TCS Annual Reports FY2026, FY2025 and FY2024
- Earnings-call transcripts for October, July and April

These reports provide annual financial context; they do **not** replace recent
quarterly financial statements. The assignment specifically expects recent quarterly
reports and metrics such as total revenue, net profit and operating margin. For a
valid quarterly trend analysis, also place the latest 1–2 quarterly results/fact-sheet
PDFs in `data/financial_reports/`. The application labels periods and must not treat
annual metrics as quarterly figures.

The discovery endpoint is a lightweight best-effort link scanner. TCS website
structure and PDF links can change. Inspect discovered links before downloading;
the reliable fallback is to download official PDFs yourself and put them in the
specified folders. This project does not claim that every latest document is
automatically discovered.

## Architecture

```text
Client
  |
  v
FastAPI POST /api/v1/forecast
  |
  +--> Persist incoming request in MySQL
  |
  +--> FinancialDataExtractorTool
  |      PyMuPDF page extraction -> OpenAI structured extraction
  |      output: metric/value/period/unit/source/page/evidence
  |
  +--> QualitativeAnalysisTool
  |      transcript PDFs -> page metadata -> chunking
  |      -> local Sentence Transformers embeddings -> ChromaDB
  |      -> semantic retrieval with source/page provenance
  |
  +--> OpenAI synthesis (LangChain ChatOpenAI)
  |      -> Pydantic response validation
  |
  +--> Persist final JSON in MySQL and return response
```

## Tools and AI stack

### FinancialDataExtractorTool

Reads PDFs from `data/financial_reports/`, extracts page-level text with PyMuPDF,
selects pages containing relevant financial terms, and asks OpenAI to return only
explicitly stated metrics. Each metric retains source filename, PDF page, period,
unit and a short evidence excerpt. It does not calculate values or silently infer
missing figures. Financial tables may extract imperfectly; manually verify important
numbers against the original PDF.

### QualitativeAnalysisTool

Reads PDFs from `data/transcripts/`, splits page text into overlapping chunks,
creates embeddings locally using `sentence-transformers/all-MiniLM-L6-v2`, and
stores them in ChromaDB. Similarity search retrieves passages relevant to demand,
client spending, order book, AI, margins, hiring, risks and management outlook.
Retrieved passages retain transcript filename and page number.

### Master forecasting workflow

The `ForecastingAgent` calls both tools, then sends the evidence to OpenAI through
LangChain `ChatOpenAI`. The prompt requires separation of reported facts, management
statements and analysis; it forbids invented metrics and annual-to-quarterly
relabeling. The response is parsed as JSON and validated with Pydantic before storage.

OpenAI model is configurable through `OPENAI_MODEL` and defaults to `gpt-4o-mini`.
Model availability and account limits can change.

## Project structure

```text
app/
  main.py
  config.py
  schemas.py
  agent.py
  ingest.py
  tools/
    financial_extractor.py
    qualitative_analysis.py
  services/
    pdf_loader.py
    document_discovery.py
  database/
    db.py
    models.py
data/
  financial_reports/
  transcripts/
  chroma_db/
tests/
  test_api.py
.env.example
requirements.txt
README.md
```

## Setup: Windows 10/11 PowerShell

### 1. Install prerequisites

- Python 3.10 or newer
- MySQL Server 8.0.x (the requested 8.0.46 is compatible with this SQLAlchemy/PyMySQL setup)
- MySQL Workbench (optional, useful for creating/verifying the database)
- An OpenAI API key

### 2. Create database

Start the MySQL service. In MySQL Workbench, open a SQL tab and run:

```sql
CREATE DATABASE tcs_forecast
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 3. Configure environment

In the project root:

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=mysql+pymysql://root:YOUR_URL_ENCODED_PASSWORD@localhost:3306/tcs_forecast?charset=utf8mb4
CHROMA_DB_PATH=./data/chroma_db
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
TCS_DOCUMENTS_URL=https://www.tcs.com/investor-relations
```

If the MySQL password contains reserved URL characters (`@`, `#`, `/`, `:`), URL-encode it.
Never commit `.env`.

### 4. Add source PDFs

Use clear names. Example:

```text
data/financial_reports/
  TCS_Annual_Report_FY2026.pdf
  TCS_Annual_Report_FY2025.pdf
  TCS_Annual_Report_FY2024.pdf
  TCS_Q1_FY27_Results.pdf
  TCS_Q2_FY27_Results.pdf

data/transcripts/
  TCS_Concall_Oct_2026.pdf
  TCS_Concall_Jul_2026.pdf
  TCS_Concall_Apr_2026.pdf
```

Put quarterly results PDFs in `financial_reports` if available. Put only earnings-call
transcript PDFs (not summaries or slide decks) in `transcripts`.

### 5. Ingest documents and initialize MySQL tables

```powershell
python -m app.ingest
```

This creates the MySQL table and extracts financial evidence/builds the transcript
vector index. First embedding-model use downloads the model and can take time.

### 6. Run API

```powershell
uvicorn app.main:app --reload
```

Swagger UI: http://127.0.0.1:8000/docs

## API endpoints

- `GET /health` — health check
- `GET /api/v1/documents/discover` — best-effort scan for candidate PDF links on the
  configured TCS investor-relations page
- `POST /api/v1/ingest` — process financial PDFs and index transcript PDFs
- `POST /api/v1/forecast` — generate outlook and persist request/response JSON

Example request:

```json
{
  "company": "Tata Consultancy Services",
  "ticker": "TCS",
  "horizon": "upcoming quarter",
  "question": "Analyze recent financial trends, management outlook, opportunities and risks."
}
```

The response contains executive outlook, financial trends, outlook by dimension,
management outlook, recurring themes, drivers, risks, financial metrics with
provenance, evidence references, confidence and limitations.

## MySQL logging

`forecast_logs` stores:
- request ID and company
- incoming request JSON
- final response JSON
- status (`processing`, `completed` or `failed`)
- error message for failed generation
- creation timestamp

The API commits the request before running the agent and updates the same row with
the final JSON or failure status.

## Guardrails and evaluation

- No metric should be included without its original source filename and page.
- Annual and quarterly periods must remain distinct.
- Model is instructed to omit unclear values rather than infer them.
- Transcript claims should be traceable to transcript filename/page.
- Pydantic validates the final JSON contract.
- Confidence is an evidence-coverage label, not a calibrated probability.
- Manual evaluation: compare at least 5 extracted figures with the original report;
  check that 3–5 recurring themes are supported by multiple transcript excerpts;
  inspect whether risks and opportunities are actually mentioned in source material.

## Limitations and trade-offs

- This is a take-home prototype, not an audited financial data pipeline.
- PDF tables, scanned PDFs and unusual layouts may require OCR or manual review.
- The discovery scanner depends on the public website's HTML and may not find all
  documents; use manually downloaded official PDFs as the deterministic source set.
- The current metric extraction is LLM-assisted page-level extraction, not a
  financial-statement parser with fully deterministic table reconstruction.
- Annual reports alone cannot support last-quarter growth/margin calculations.
- No live market data, frontend, authentication, background task queue or deployment
  configuration is included; MarketDataTool is optional in the assignment.

## Troubleshooting

- **Access denied / MySQL connection error:** check MySQL service, root password,
  port 3306, database name and URL encoding.
- **OpenAI API error:** verify that `OPENAI_API_KEY` is valid, your account has
  API access, and `OPENAI_MODEL` names a model available to your account.
- **No financial metrics:** add text-based quarterly/annual PDFs to
  `data/financial_reports/`; check PDF text extraction and verify pages manually.
- **No transcript retrieval:** put transcript PDFs in `data/transcripts/` and run
  `python -m app.ingest`.
- **Scanned PDF:** run OCR separately or use a text-based official PDF.

## Tests

```powershell
pytest -q
```

The health test does not require a live OpenAI request. A full end-to-end test requires
working OpenAI credentials, MySQL and source PDFs.
