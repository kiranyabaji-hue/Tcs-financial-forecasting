"""
Lightweight PDF discovery/downloader.
It scans a configured public TCS investor-relations page for PDF links and
downloads links whose visible URL/text matches quarterly-results or earnings-call
keywords. Website markup can change; manual PDF placement remains supported.
"""
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from app.config import settings

KEYWORDS = (
    "quarter", "q1", "q2", "q3", "q4", "result", "concall",
    "earnings", "transcript", "financial"
)

def discover_pdf_links(page_url: str | None = None) -> list[dict]:
    url = page_url or settings.tcs_documents_url
    response = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    found = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(url, anchor["href"])
        label = " ".join(anchor.get_text(" ", strip=True).split())
        if urlparse(href).path.lower().endswith(".pdf"):
            searchable = f"{label} {href}".lower()
            if any(word in searchable for word in KEYWORDS):
                found.append({"title": label or Path(urlparse(href).path).name, "url": href})
    # Preserve order while removing duplicate URLs.
    unique = {}
    for item in found:
        unique[item["url"]] = item
    return list(unique.values())

def download_pdf(url: str, destination_folder: str) -> Path:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS document URLs are accepted.")
    filename = Path(parsed.path).name or "source_document.pdf"
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    folder = Path(destination_folder)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / filename
    response = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    if not response.content.startswith(b"%PDF"):
        raise ValueError(f"URL did not return a PDF: {url}")
    destination.write_bytes(response.content)
    return destination
