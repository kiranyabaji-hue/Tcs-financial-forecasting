from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    database_url: str
    chroma_db_path: str = "./data/chroma_db"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    tcs_documents_url: str = "https://www.tcs.com/investor-relations"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
