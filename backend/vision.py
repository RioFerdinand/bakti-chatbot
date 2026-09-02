"""
vision.py
Modul untuk fitur "kamera / unggah file": membaca teks dari gambar (OCR)
maupun dari dokumen (PDF/DOCX) yang dikirim user lewat chat, lalu
meringkas atau menjawab pertanyaan berdasarkan isinya menggunakan LLM (Ollama).

Alur:
1. User kirim gambar (mis. foto notulensi rapat, papan tulis, screenshot,
   struk, dsb.) atau file dokumen lewat tombol kamera / lampirkan.
2. Kita ekstrak teksnya:
   - Gambar (png/jpg/jpeg/webp/bmp) -> OCR pakai pytesseract.
   - PDF/DOCX -> pakai loader yang sudah ada (PyPDFLoader / Docx2txtLoader).
3. Teks hasil ekstraksi + pertanyaan/instruksi user (opsional) dikirim ke LLM
   (Ollama) untuk diringkas atau dijawab.
"""
import io
import os
import tempfile
from pathlib import Path
from typing import Tuple

from PIL import Image
import pytesseract

from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

try:
    from ai import LLM_MODEL  # pakai model yang sama persis dengan fitur chat teks biasa
except ImportError:
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc"}

# Bahasa OCR: Indonesia + Inggris. Kalau paket bahasa "ind" belum ter-install
# di Tesseract, otomatis fallback ke "eng" saja supaya tidak error.
_OCR_LANG_CANDIDATES = ["ind+eng", "eng"]

_analysis_prompt = ChatPromptTemplate.from_template(
    """Kamu adalah Bakti AI, asisten yang membantu membaca dan meringkas isi
gambar atau dokumen yang dikirim oleh pengguna (misalnya notulensi rapat,
foto papan tulis, screenshot, atau dokumen PDF/Word).

Berikut teks yang berhasil diekstrak dari file/gambar tersebut:
---
{content}
---

Instruksi dari pengguna: {question}

Tugasmu:
- Jika instruksi pengguna adalah pertanyaan spesifik, jawab berdasarkan isi teks di atas.
- Jika tidak ada instruksi spesifik (kosong atau umum seperti "ringkas ini"),
  buatkan ringkasan yang rapi dan mudah dibaca. Kalau isinya notulensi rapat,
  strukturkan menjadi: Topik/Agenda, Poin-poin pembahasan, dan Tindak lanjut/Action item (jika ada).
- Jawab HANYA berdasarkan teks yang tersedia. Jika teksnya kosong/tidak terbaca,
  katakan bahwa gambar/dokumen tidak bisa dibaca dan minta pengguna mengirim ulang
  dengan kualitas lebih jelas.
- Gunakan bahasa Indonesia yang natural.

Jawaban:"""
)

_llm = None
_chain = None


def _get_chain():
    global _llm, _chain
    if _chain is None:
        _llm = OllamaLLM(model=LLM_MODEL, base_url=OLLAMA_HOST, temperature=0.2)
        _chain = _analysis_prompt | _llm | StrOutputParser()
    return _chain


def _ocr_image_bytes(image_bytes: bytes) -> str:
    """Ekstrak teks dari gambar (bytes) pakai Tesseract OCR."""
    image = Image.open(io.BytesIO(image_bytes))
    # Konversi ke RGB dulu supaya aman untuk semua format (mis. PNG dengan alpha)
    if image.mode != "RGB":
        image = image.convert("RGB")

    last_error = None
    for lang in _OCR_LANG_CANDIDATES:
        try:
            text = pytesseract.image_to_string(image, lang=lang)
            if text.strip():
                return text.strip()
            # kalau kosong tapi tidak error, tetap coba bahasa berikutnya
        except pytesseract.TesseractError as e:
            last_error = e
            continue

    if last_error and not _OCR_LANG_CANDIDATES:
        raise RuntimeError(f"OCR gagal: {last_error}")

    return ""  # tidak ada teks yang terbaca


def _extract_from_document(file_bytes: bytes, filename: str) -> str:
    """Ekstrak teks dari PDF/DOCX pakai loader yang sudah ada di loader.py."""
    from loader import load_single_file  # import lokal agar tidak circular

    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        docs = load_single_file(tmp_path)
        return "\n\n".join(doc.page_content for doc in docs).strip()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def extract_text(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """
    Ekstrak teks dari file (gambar atau dokumen).
    Return (extracted_text, file_type) dengan file_type: "image" | "document".
    Raise ValueError kalau format tidak didukung.
    """
    suffix = Path(filename).suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        return _ocr_image_bytes(file_bytes), "image"

    if suffix in DOCUMENT_EXTENSIONS:
        return _extract_from_document(file_bytes, filename), "document"

    raise ValueError(
        f"Format file '{suffix}' belum didukung. Gunakan gambar (jpg/png/webp) "
        "atau dokumen (pdf/docx)."
    )


def analyze_content(question: str, extracted_text: str) -> str:
    """Ringkas atau jawab pertanyaan berdasarkan teks hasil ekstraksi."""
    chain = _get_chain()

    if not extracted_text.strip():
        return (
            "Maaf, saya tidak berhasil membaca teks dari gambar/file yang dikirim. "
            "Coba kirim ulang dengan foto yang lebih jelas, pencahayaan cukup, "
            "dan tidak buram."
        )

    q = question.strip() if question and question.strip() else "Ringkas isi dokumen/gambar ini."

    return chain.invoke({"content": extracted_text, "question": q})