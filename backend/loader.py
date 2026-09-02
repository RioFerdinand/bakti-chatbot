"""
loader.py
Bertugas membaca file PDF/Word dan memecahnya menjadi potongan (chunks)
teks yang siap di-embed ke ChromaDB.
"""
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from config import PDF_DIR, WORD_DIR


def load_single_file(file_path: Path) -> List[Document]:
    """Load satu file (pdf atau docx) menjadi list of Document."""
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        loader = PyPDFLoader(str(file_path))
    elif suffix in (".docx", ".doc"):
        loader = Docx2txtLoader(str(file_path))
    else:
        raise ValueError(f"Format file tidak didukung: {suffix}")

    docs = loader.load()
    for doc in docs:
        doc.metadata["source"] = file_path.name
    return docs


def load_all_documents() -> List[Document]:
    """Load semua file PDF di data/pdf dan Word di data/word."""
    all_docs: List[Document] = []

    for pdf_file in PDF_DIR.glob("*.pdf"):
        all_docs.extend(load_single_file(pdf_file))

    for word_file in list(WORD_DIR.glob("*.docx")) + list(WORD_DIR.glob("*.doc")):
        all_docs.extend(load_single_file(word_file))

    return all_docs


def split_documents(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> List[Document]:
    """Pecah dokumen panjang menjadi chunk kecil agar cocok untuk embedding."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)


def load_and_split_all() -> List[Document]:
    """Fungsi gabungan: load semua file lalu langsung split jadi chunks."""
    docs = load_all_documents()
    return split_documents(docs)


def load_and_split_single(file_path: Path) -> List[Document]:
    """Load dan split satu file saja (dipakai saat upload file baru)."""
    docs = load_single_file(file_path)
    return split_documents(docs)
