"""
app.py
Server FastAPI untuk RAG Chatbot berbasis Llama (Ollama) + ChromaDB.

Jalankan dengan:
    uvicorn app:app --reload --port 8000
(dijalankan dari dalam folder backend/)
"""
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import PDF_DIR, WORD_DIR
from loader import load_and_split_single, load_and_split_all
from rag import add_documents, reset_vectorstore
from chatbot import ask

app = FastAPI(title="RAG Chatbot API", version="1.0.0")

# Izinkan frontend (Streamlit/React) mengakses API ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    k: int = 4


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


@app.get("/health")
def health():
    """Cek apakah server backend hidup."""
    return {"status": "ok"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload satu file PDF atau Word, lalu langsung index ke ChromaDB
    supaya bisa langsung ditanyakan.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix == ".pdf":
        dest_dir = PDF_DIR
    elif suffix in (".docx", ".doc"):
        dest_dir = WORD_DIR
    else:
        raise HTTPException(status_code=400, detail="Hanya file .pdf, .docx, atau .doc yang didukung")

    dest_path = dest_dir / file.filename
    content = await file.read()
    dest_path.write_bytes(content)

    chunks = load_and_split_single(dest_path)
    jumlah = add_documents(chunks)

    return {"filename": file.filename, "chunks_indexed": jumlah}


@app.post("/reindex")
def reindex_all():
    """Index ulang SEMUA file yang ada di data/pdf dan data/word dari nol."""
    reset_vectorstore()
    chunks = load_and_split_all()
    jumlah = add_documents(chunks)
    return {"chunks_indexed": jumlah}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Ajukan pertanyaan ke chatbot RAG."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Pertanyaan tidak boleh kosong")

    answer, sources = ask(req.question, k=req.k)
    return ChatResponse(answer=answer, sources=sources)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
