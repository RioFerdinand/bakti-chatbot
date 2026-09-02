"""
qa_cache.py
Cache jawaban berbasis SIMILARITY SEARCH (bukan exact match teks).

Alurnya persis seperti diagram:
    User -> Cek database (cache) -> Ada (mirip)?  -> Tampilkan jawaban lama
                                  -> Tidak ada?    -> Kirim ke LLM
                                                        -> Simpan Q&A ke cache
                                                        -> Tampilkan jawaban baru

Cache disimpan sebagai koleksi ChromaDB terpisah (bukan tabel SQL), karena
kita butuh SIMILARITY search (pertanyaan baru dibandingkan makna/embedding-nya
dengan pertanyaan yang sudah pernah ditanya sebelumnya), bukan pencocokan
teks persis.

Cache dipisah per knowledge base (public vs full) karena jawaban yang benar
bisa saja beda antara mode umum dan mode login (mode login punya sumber
dokumen lebih banyak).
"""
import os
import json

from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings

BASE_DIR = os.path.dirname(__file__)
CACHE_DIR_PUBLIC = os.path.join(BASE_DIR, "qa_cache_public")
CACHE_DIR_FULL = os.path.join(BASE_DIR, "qa_cache_full")

EMBED_MODEL = "mxbai-embed-large"  # sama dengan yang dipakai ai.py, biar konsisten

# Seberapa mirip dua pertanyaan dianggap "pertanyaan yang sama".
# Skornya 0-1 (relevance score dari langchain, makin tinggi makin mirip).
# 0.93 artinya harus SANGAT mirip -- longgar dikit soal typo/susunan kata,
# tapi tidak akan menyamakan pertanyaan yang beda maksud.
SIMILARITY_THRESHOLD = 0.93

_embeddings = None
_stores = {"public": None, "full": None}


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    return _embeddings


def _get_store(use_full: bool):
    key = "full" if use_full else "public"
    cache_dir = CACHE_DIR_FULL if use_full else CACHE_DIR_PUBLIC

    if _stores[key] is None:
        _stores[key] = Chroma(
            persist_directory=cache_dir,
            embedding_function=_get_embeddings(),
            collection_name="qa_cache",
        )
    return _stores[key]


def get_cached_answer(question: str, use_full: bool = False):
    """
    Cari pertanyaan yang MIRIP di cache. Kalau ada yang cukup mirip
    (>= SIMILARITY_THRESHOLD), return dict {"answer", "sources"}.
    Kalau tidak ada yang cukup mirip (atau cache masih kosong), return None.
    """
    store = _get_store(use_full)

    try:
        results = store.similarity_search_with_relevance_scores(question, k=1)
    except Exception:
        # Koleksi masih kosong / belum ada apa-apa di cache -> anggap cache miss
        return None

    if not results:
        return None

    doc, score = results[0]
    if score < SIMILARITY_THRESHOLD:
        return None

    metadata = doc.metadata
    try:
        sources = json.loads(metadata.get("sources", "[]"))
    except json.JSONDecodeError:
        sources = []

    return {"answer": metadata.get("answer", ""), "sources": sources}


def save_to_cache(question: str, answer: str, sources: list, use_full: bool = False):
    """Simpan pasangan pertanyaan-jawaban baru ke cache untuk knowledge base terkait."""
    store = _get_store(use_full)
    store.add_texts(
        texts=[question],
        metadatas=[{"answer": answer, "sources": json.dumps(sources)}],
    )
