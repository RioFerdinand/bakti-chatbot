"""
pdf_text.py
Ekstrak teks mentah dari file PDF yang diupload user (misal notulen rapat
lama yang mau diringkas ulang) - beda dari RAG document store (loader.py),
ini cuma buat baca isi PDF apa adanya, bukan buat di-index ke ChromaDB.
"""
import io

from pypdf import PdfReader


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Baca semua teks dari file PDF (semua halaman digabung)."""
    if not pdf_bytes:
        raise ValueError("File PDF kosong")

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as e:
        raise ValueError(f"File bukan PDF yang valid: {e}")

    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages_text.append(text.strip())

    full_text = "\n\n".join(pages_text).strip()

    if not full_text:
        raise RuntimeError(
            "Tidak ada teks yang bisa dibaca dari PDF ini. Kemungkinan PDF-nya "
            "berupa hasil scan/gambar (bukan teks asli), coba upload sebagai "
            "foto lewat fitur OCR sebagai gantinya."
        )
    return full_text
