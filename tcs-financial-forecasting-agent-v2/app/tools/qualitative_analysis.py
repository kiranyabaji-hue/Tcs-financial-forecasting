from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.config import settings
from app.services.pdf_loader import load_folder

class QualitativeAnalysisTool:
    """RAG over 2–3 TCS earnings-call transcript PDFs."""

    name = "QualitativeAnalysisTool"
    description = "Retrieve transcript evidence about themes, management sentiment and forward outlook."

    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        self.vectorstore = Chroma(
            collection_name="tcs_earnings_call_transcripts",
            embedding_function=self.embeddings,
            persist_directory=settings.chroma_db_path,
        )

    def ingest(self) -> int:
        pages = load_folder("data/transcripts")
        if not pages:
            return 0
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=160)
        documents, ids = [], []
        for page in pages:
            chunks = splitter.split_text(page["text"])
            for index, chunk in enumerate(chunks):
                documents.append(Document(
                    page_content=chunk,
                    metadata={"source": page["source"], "page": page["page"]}
                ))
                ids.append(f"{page['source']}::p{page['page']}::c{index}")
        # Chroma upsert prevents duplicate records when the same PDFs are re-ingested.
        self.vectorstore.add_documents(documents, ids=ids)
        return len(documents)

    def search(self, question: str, k: int = 10) -> list[dict]:
        results = self.vectorstore.similarity_search(question, k=k)
        return [
            {"text": doc.page_content, "source": doc.metadata.get("source"), "page": doc.metadata.get("page")}
            for doc in results
        ]
