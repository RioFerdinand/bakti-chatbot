"""
Konfigurasi terpusat untuk backend RAG Chatbot.
Semua nilai bisa diubah lewat file .env di root project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv


# Cari .env di root project (satu folder di atas backend/)
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
CHROMA_DIR = str(ROOT_DIR / os.getenv("CHROMA_DIR", "chroma_db"))
DATA_DIR = ROOT_DIR / os.getenv("DATA_DIR", "data")
PDF_DIR = DATA_DIR / "pdf"
WORD_DIR = DATA_DIR / "word"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
CHROMA_DIR = "./chroma_db"

# Pastikan folder yang dibutuhkan ada
PDF_DIR.mkdir(parents=True, exist_ok=True)
WORD_DIR.mkdir(parents=True, exist_ok=True)

REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
