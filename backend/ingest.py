"""
ingest.py
Membuat DUA vector store terpisah:

1. chroma_db_public  -> hanya dari documents/public/
                         (dipakai user yang BELUM login)
2. chroma_db_full     -> dari documents/public/ + documents/member/
                         (dipakai user yang SUDAH login, jadi otomatis
                         mencakup semua yang ada di public + tambahan
                         dokumen khusus member)

Bisa dijalankan lewat CLI (python ingest.py) ATAU dipanggil dari kode lain
(misal endpoint admin /admin/reingest) lewat fungsi build_all().
"""
import os
import shutil
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings

BASE_DIR = os.path.dirname(__file__)
PUBLIC_DIR = os.path.join(BASE_DIR, "documents", "public")
MEMBER_DIR = os.path.join(BASE_DIR, "documents", "member")

CHROMA_DIR_PUBLIC = os.path.join(BASE_DIR, "chroma_db_public")
CHROMA_DIR_FULL = os.path.join(BASE_DIR, "chroma_db_full")

EMBED_MODEL = "mxbai-embed-large"


def load_pdfs_from(folder: str):
    docs = []
    if not os.path.isdir(folder):
        return docs
    for filename in os.listdir(folder):
        if filename.lower().endswith(".pdf"):
            path = os.path.join(folder, filename)
            print(f"  Membaca: {filename}")
            loader = PyPDFLoader(path)
            docs.extend(loader.load())
    return docs


def build_vectorstore(documents, persist_dir: str, embeddings, label: str):
    # Hapus dulu vector store lama biar rebuild-nya BERSIH (bukan numpuk data
    # lama + baru). Penting terutama kalau admin baru saja MENGHAPUS dokumen --
    # tanpa ini, dokumen yang sudah dihapus filenya tetap "nyantol" di index lama.
    if os.path.isdir(persist_dir):
        shutil.rmtree(persist_dir)

    if not documents:
        print(f"[{label}] Tidak ada dokumen ditemukan, dilewati.")
        return

    print(f"[{label}] Total halaman terbaca: {len(documents)}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(documents)
    print(f"[{label}] Total chunk: {len(chunks)}")

    print(f"[{label}] Membuat vector store, mohon tunggu...")
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_dir,
    )
    print(f"[{label}] Selesai! Tersimpan di: {persist_dir}\n")


def build_all():
    """Bangun ulang kedua knowledge base dari isi folder documents/ saat ini."""
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)

    print("=== Membangun knowledge base PUBLIK (documents/public/) ===")
    public_docs = load_pdfs_from(PUBLIC_DIR)
    build_vectorstore(public_docs, CHROMA_DIR_PUBLIC, embeddings, "PUBLIC")

    print("=== Membangun knowledge base FULL (documents/public/ + documents/member/) ===")
    member_docs = load_pdfs_from(MEMBER_DIR)
    full_docs = public_docs + member_docs
    build_vectorstore(full_docs, CHROMA_DIR_FULL, embeddings, "FULL")

    if not member_docs:
        print(
            "Catatan: folder documents/member/ masih kosong, jadi knowledge base "
            "FULL isinya sama persis dengan PUBLIC untuk saat ini."
        )

    return {
        "public_pages": len(public_docs),
        "full_pages": len(public_docs) + len(member_docs),
    }


if __name__ == "__main__":
    build_all()
