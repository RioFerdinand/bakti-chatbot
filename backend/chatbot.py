"""
chatbot.py
Menyusun prompt dari konteks hasil retrieval + pertanyaan user,
lalu mengirimkannya ke model Llama lewat Ollama untuk mendapat jawaban.
"""
from typing import List, Tuple

import ollama

from config import LLM_MODEL, OLLAMA_HOST
from rag import retrieve_context

_client = ollama.Client(host=OLLAMA_HOST)

SYSTEM_PROMPT = (
    "Kamu adalah asisten AI yang menjawab pertanyaan HANYA berdasarkan "
    "konteks dokumen yang diberikan. Jika jawaban tidak ada di dalam "
    "konteks, katakan dengan jujur bahwa kamu tidak menemukan informasi "
    "tersebut di dokumen. Jawab dengan bahasa yang sama dengan pertanyaan "
    "pengguna, singkat, dan jelas."
)


def build_prompt(question: str, contexts: List[str]) -> str:
    context_text = "\n\n---\n\n".join(contexts) if contexts else "(tidak ada konteks ditemukan)"
    return (
        f"Konteks dokumen:\n{context_text}\n\n"
        f"Pertanyaan: {question}\n\n"
        "Jawablah berdasarkan konteks di atas."
    )


def ask(question: str, k: int = 4) -> Tuple[str, List[str]]:
    """
    Jalankan pipeline RAG lengkap:
    1. Ambil potongan dokumen relevan dari ChromaDB
    2. Susun prompt gabungan konteks + pertanyaan
    3. Kirim ke model Llama lewat Ollama
    Return: (jawaban, daftar_sumber)
    """
    docs = retrieve_context(question, k=k)
    contexts = [d.page_content for d in docs]
    sources = sorted({d.metadata.get("source", "unknown") for d in docs})

    prompt = build_prompt(question, contexts)

    response = _client.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    answer = response["message"]["content"]
    return answer, sources
