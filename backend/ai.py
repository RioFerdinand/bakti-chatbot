import os
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

import qa_cache

BASE_DIR = os.path.dirname(__file__)
CHROMA_DIR_PUBLIC = os.path.join(BASE_DIR, "chroma_db_public")
CHROMA_DIR_FULL = os.path.join(BASE_DIR, "chroma_db_full")

EMBED_MODEL = "mxbai-embed-large"
LLM_MODEL = "llama3.1"  # sesuaikan dengan model yang sudah kamu pull di Ollama

_prompt = ChatPromptTemplate.from_template("""Kamu adalah Bakti AI, asisten virtual dari BAKTI Kominfo yang ramah, sopan, dan membantu.

Ikuti aturan ini saat menjawab:
1. Untuk obrolan dasar sehari-hari — sapaan (halo, hai, selamat pagi), basa-basi (apa kabar), 
   perkenalan (siapa kamu, kamu bisa apa), ucapan terima kasih, permintaan maaf, atau penutup 
   percakapan (sampai jumpa) — balas secara natural, hangat, dan ringkas seperti asisten AI 
   pada umumnya. Kamu TIDAK perlu bergantung pada konteks dokumen di bawah untuk jenis pesan ini.
2. Untuk pertanyaan seputar informasi BAKTI (sejarah, visi misi, struktur organisasi, layanan, 
   SOP, dan sejenisnya) — jawab HANYA berdasarkan konteks dokumen di bawah ini. Jika jawabannya 
   tidak ada di dalam konteks, katakan dengan jujur bahwa informasi tersebut tidak tersedia di 
   dokumen. Jangan mengarang jawaban di luar konteks untuk kategori ini.

Konteks dokumen (mungkin tidak relevan kalau pesan penggunanya cuma basa-basi):
{context}

Pertanyaan/pesan pengguna: {question}

Jawaban:""")

# Cache terpisah untuk masing-masing knowledge base, supaya tidak perlu
# reload vector store tiap kali ada pertanyaan.
_retrievers = {"public": None, "full": None}
_chains = {"public": None, "full": None}


def _format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def _get_chain(use_full: bool):
    """
    use_full=False -> knowledge base PUBLIK (chroma_db_public), dipakai
                       untuk user yang belum login.
    use_full=True  -> knowledge base FULL (chroma_db_full), dipakai untuk
                       user yang sudah login (mencakup dokumen member juga).
    """
    key = "full" if use_full else "public"
    chroma_dir = CHROMA_DIR_FULL if use_full else CHROMA_DIR_PUBLIC

    if _chains[key] is None:
        if not os.path.isdir(chroma_dir) or not os.listdir(chroma_dir):
            raise RuntimeError(
                f"Vector store '{key}' belum ada. Jalankan `python ingest.py` terlebih dahulu."
            )
        embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        vectordb = Chroma(persist_directory=chroma_dir, embedding_function=embeddings)
        _retrievers[key] = vectordb.as_retriever(search_kwargs={"k": 4})
        llm = OllamaLLM(model=LLM_MODEL, temperature=0.2)

        _chains[key] = (
            {"context": _retrievers[key] | _format_docs, "question": RunnablePassthrough()}
            | _prompt
            | llm
            | StrOutputParser()
        )
    return _chains[key]


def invalidate_cache():
    """
    Kosongkan cache chain/retriever yang sudah dimuat di memori. WAJIB
    dipanggil setelah re-index dokumen (lewat admin dashboard atau CLI),
    supaya server langsung pakai vector store yang baru -- tanpa ini,
    server bakal tetap pakai versi lama yang sudah kepegang di memori
    sampai proses-nya di-restart manual.
    """
    _retrievers["public"] = None
    _retrievers["full"] = None
    _chains["public"] = None
    _chains["full"] = None


def ask_question(question: str, use_full: bool = False):
    """
    Ajukan pertanyaan ke knowledge base yang sesuai.
    use_full=True dipakai kalau user sudah login (akses knowledge base lebih lengkap).

    Alur: cek cache (similarity search) dulu -> kalau ada pertanyaan yang mirip,
    langsung pakai jawaban lama (skip LLM). Kalau tidak ada, baru tanya LLM,
    lalu simpan hasilnya ke cache untuk pertanyaan berikutnya.
    """
    try:
        cached = qa_cache.get_cached_answer(question, use_full=use_full)
    except Exception:
        cached = None  # cache bermasalah -> anggap saja cache miss, lanjut ke LLM

    if cached is not None:
        return cached["answer"], cached["sources"]

    key = "full" if use_full else "public"
    chain = _get_chain(use_full)
    try:
        answer = chain.invoke(question)
        docs = _retrievers[key].invoke(question)
        sources = list({doc.metadata.get("source", "") for doc in docs})
    except Exception as e:
        # Biasanya ini terjadi kalau Ollama service belum jalan / model belum di-pull
        raise RuntimeError(f"Gagal menghubungi Ollama: {e}")

    try:
        qa_cache.save_to_cache(question, answer, sources, use_full=use_full)
    except Exception:
        # Gagal nyimpen ke cache TIDAK BOLEH bikin jawaban yang sudah didapat
        # jadi gagal ditampilkan -- cukup dilewati, cache tetap coba lagi
        # untuk pertanyaan berikutnya.
        pass

    return answer, sources
