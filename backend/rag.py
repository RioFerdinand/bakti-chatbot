"""
rag.py
Mengelola vector store ChromaDB: membuat, menambah dokumen, dan
mengambil (retrieve) potongan teks paling relevan untuk sebuah pertanyaan.
"""
from typing import List

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

from config import CHROMA_DIR, EMBEDDING_MODEL, OLLAMA_HOST

_embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_HOST)

_vectorstore: Chroma | None = None


def get_vectorstore() -> Chroma:
    """Ambil instance ChromaDB (dibuat sekali, lalu dipakai ulang)."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            collection_name="rag_chatbot",
            embedding_function=_embeddings,
            persist_directory=CHROMA_DIR,
        )
    return _vectorstore


def add_documents(documents: List[Document]) -> int:
    """Tambahkan potongan dokumen baru ke ChromaDB. Return jumlah chunk yang masuk."""
    if not documents:
        return 0
    store = get_vectorstore()
    store.add_documents(documents)
    return len(documents)


def retrieve_context(question: str, k: int = 4) -> List[Document]:
    """Ambil k potongan dokumen paling relevan dengan pertanyaan."""
    store = get_vectorstore()
    return store.similarity_search(question, k=k)


def reset_vectorstore():
    """Hapus semua data di ChromaDB (berguna untuk re-index dari nol)."""
    global _vectorstore
    store = get_vectorstore()
    store.delete_collection()
    _vectorstore = None
