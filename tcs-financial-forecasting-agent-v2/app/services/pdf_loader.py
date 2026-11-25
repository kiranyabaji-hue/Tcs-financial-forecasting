from pathlib import Path
import fitz

def read_pdf_pages(path: Path) -> list[dict]:
    records = []
    try:
        with fitz.open(path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text", sort=True).strip()
                if text:
                    records.append({
                        "text": text,
                        "source": path.name,
                        "page": page_number,
                        "path": str(path.resolve()),
                    })
    except Exception as exc:
        raise RuntimeError(f"Could not read PDF {path}: {exc}") from exc
    return records

def load_folder(folder: str) -> list[dict]:
    directory = Path(folder)
    if not directory.exists():
        return []
    pages = []
    for pdf_path in sorted(directory.glob("*.pdf")):
        pages.extend(read_pdf_pages(pdf_path))
    return pages
