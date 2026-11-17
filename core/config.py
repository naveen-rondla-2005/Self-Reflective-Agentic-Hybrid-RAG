import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    DOCS_DIR = os.getenv("DOCS_DIR", "./data/transit_docs")
    EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    LLM_MODEL = "gemini-3.1-flash-lite"
    TOP_K = 4
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 150

    @classmethod
    def validate(cls):
        if not cls.GOOGLE_API_KEY:
            raise ValueError("CRITICAL: GOOGLE_API_KEY is not set in your .env file.")