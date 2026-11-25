from app.database.db import init_db
from app.tools.financial_extractor import FinancialDataExtractorTool
from app.tools.qualitative_analysis import QualitativeAnalysisTool

def main():
    init_db()
    metrics = FinancialDataExtractorTool().run()
    chunks = QualitativeAnalysisTool().ingest()
    print(f"Extracted {len(metrics)} financial metric records.")
    print(f"Indexed {chunks} transcript chunks.")
    print("Review metric source/page references against original PDFs.")

if __name__ == "__main__":
    main()
