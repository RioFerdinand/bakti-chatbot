"""
ocr.py
Ekstrak teks dari foto (papan tulis, slide yang difoto, atau catatan
tulisan tangan/ketikan) memakai Tesseract OCR (bukan model vision LLM,
jauh lebih ringan karena Tesseract cuma OCR biasa, gak butuh model
Ollama tambahan yang berat).

PENTING: pytesseract cuma wrapper Python. Tesseract OCR engine-nya
sendiri harus diinstal terpisah di sistem (bukan lewat pip):
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Setelah install, kalau tesseract.exe gak otomatis kedetek, set manual
  path-nya lewat TESSERACT_CMD di bawah atau environment variable.
"""
import io
import os

import pytesseract
from PIL import Image

# Kalau Tesseract gak otomatis ketemu di PATH (umum kejadian di Windows),
# set path instalasinya secara manual lewat environment variable ini.
_custom_path = os.getenv("TESSERACT_CMD")
if _custom_path:
    pytesseract.pytesseract.tesseract_cmd = _custom_path


def extract_text_from_image(image_bytes: bytes, lang: str = "ind+eng") -> str:
    """
    Baca teks dari foto pakai Tesseract OCR.
    lang: kode bahasa Tesseract, default Indonesia+Inggris digabung
    (butuh language pack 'ind' terinstal, lihat catatan di README).
    """
    if not image_bytes:
        raise ValueError("File gambar kosong")

    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise ValueError(f"File bukan gambar yang valid: {e}")

    try:
        text = pytesseract.image_to_string(image, lang=lang)
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract OCR belum terinstal atau tidak ditemukan di sistem. "
            "Install dulu dari https://github.com/UB-Mannheim/tesseract/wiki "
            "(Windows), lalu set TESSERACT_CMD di .env kalau perlu."
        )
    except Exception as e:
        # Bahasa 'ind' mungkin belum ada language pack-nya, coba fallback ke default
        try:
            text = pytesseract.image_to_string(image)
        except Exception:
            raise RuntimeError(f"Gagal membaca teks dari gambar: {e}")

    text = text.strip()
    if not text:
        raise RuntimeError(
            "Tidak ada teks yang terbaca dari foto ini. Coba foto yang lebih "
            "jelas/terang, atau pastikan tulisannya cukup kontras."
        )
    return text
