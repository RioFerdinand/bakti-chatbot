"""
document_export.py

FITUR (tambahkan file ini ke folder backend/, sejajar dengan main.py, ai.py, dll):

1. Ekstrak teks dari file/foto yang dikirim user (PDF, Word, atau gambar/OCR)
2. Ringkas teks tersebut lewat model Llama (Ollama) menjadi notulensi TERSTRUKTUR (JSON)
3. Deteksi otomatis kalau user mengirim teks notulensi rapat
4. Generate file Word (.docx) memakai template resmi Bakti (letterhead/header/footer)
   dengan layout PERSIS seperti contoh: judul, I. INFORMASI RAPAT, II. TUJUAN RAPAT,
   III. AGENDA RAPAT, IV. HASIL PEMBAHASAN (tabel TOPIK / HASIL PEMBAHASAN), V. TINDAK LANJUT
5. Convert file Word tersebut ke PDF

File ini TIDAK mengubah kode yang sudah ada, hanya dipakai (di-import) dari main.py.

CATATAN MIGRASI DARI VERSI LAMA:
- summarize_text(text) -> dipakai untuk ringkasan bebas (non-notulensi).
- summarize_meeting_minutes(text, kegiatan_title=None) -> BARU, mengembalikan dict
  terstruktur yang siap dipakai generate_docx(data).
- generate_docx(title, content, bab_label=...) -> BERUBAH menjadi generate_docx(data: dict).
  Jadi kalau main.py masih memanggil generate_docx(title, content), sesuaikan pemanggilannya
  menjadi generate_docx(data) dengan data dari summarize_meeting_minutes().
- save_pending_export(chat_id, title, content, is_meeting) -> BERUBAH menjadi
  save_pending_export(chat_id, data, is_meeting) di mana `data` adalah dict notulensi.
"""
import io
import json
import uuid
from pathlib import Path
from typing import Optional

from docx2pdf import convert

import ollama
from pypdf import PdfReader
from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image
import pytesseract

from config import LLM_MODEL, OLLAMA_HOST

BACKEND_DIR = Path(__file__).resolve().parent

# Taruh salinan Template_DOCS_Bakti.docx di sini: backend/templates/Template_DOCS_Bakti.docx
# (Template ini yang menyediakan letterhead KOMDIGI + logo BAKTI di header, dan footer
# "Halaman X dari Y" -- generate_docx() TIDAK menyentuh header/footer, hanya body-nya.)
TEMPLATE_PATH = BACKEND_DIR / "templates" / "Template_DOCS_Bakti.docx"

import tempfile as _tempfile  # tambahkan import ini di bagian atas file (dekat import tempfile yang sudah ada)

# Folder PERMANEN (bukan folder temp sistem) supaya file hasil export tetap ada
# dan bisa diunduh ulang kapan saja lewat endpoint GET /files/{file_id} di main.py,
# termasuk setelah server di-restart atau chat lama dibuka kembali.
EXPORT_DIR = BACKEND_DIR / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

_client = ollama.Client(host=OLLAMA_HOST)

# Menyimpan sementara notulensi terstruktur yang menunggu dipilih formatnya (word/pdf).
# key = chat_id -> {"data": dict, "is_meeting": bool}
_pending_exports: dict[int, dict] = {}

NAVY = RGBColor(0, 51, 153)
HEADER_FILL = "1F3864"  # navy gelap untuk header tabel Hasil Pembahasan
FONT_NAME = "Times New Roman"


# ================= EKSTRAKSI TEKS DARI FILE / FOTO =================

def extract_text_from_file(filename: str, content: bytes) -> str:
    """Ambil teks mentah dari file yang diupload user (PDF, Word, atau gambar)."""
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if suffix in (".docx", ".doc"):
        tmp_path = EXPORT_DIR / f"tmp_{uuid.uuid4().hex}{suffix}"
        tmp_path.write_bytes(content)
        try:
            doc = DocxDocument(tmp_path)
            return "\n".join(p.text for p in doc.paragraphs)
        finally:
            tmp_path.unlink(missing_ok=True)

    if suffix in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        image = Image.open(io.BytesIO(content))
        return pytesseract.image_to_string(image, lang="ind+eng")

    raise ValueError(f"Tipe file '{suffix}' belum didukung untuk fitur ringkasan")


# ================= RINGKASAN BEBAS VIA LLM (Ollama) =================

def summarize_text(text: str, instruksi: Optional[str] = None) -> str:
    """Minta model Llama meringkas teks yang diberikan (ringkasan bebas, non-notulensi)."""
    instruksi = instruksi or (
        "Ringkas dokumen berikut dengan bahasa Indonesia yang rapi dan jelas. "
        "Tulis dalam bentuk paragraf ringkas, lalu tambahkan poin-poin penting "
        "sebagai bullet list (diawali tanda '-') jika ada."
    )
    prompt = f"{instruksi}\n\nDokumen:\n{text[:12000]}"

    response = _client.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "Kamu adalah asisten yang ahli meringkas dokumen dalam bahasa Indonesia."},
            {"role": "user", "content": prompt},
        ],
    )
    return response["message"]["content"].strip()


# ================= RINGKASAN NOTULENSI TERSTRUKTUR (JSON) VIA LLM =================

_MEETING_JSON_INSTRUCTION = """\
Kamu akan menerima teks rapat/diskusi. Ubah menjadi notulensi rapat resmi dalam format JSON MURNI
(TANPA markdown, TANPA ```, TANPA penjelasan tambahan di luar JSON). Struktur JSON harus PERSIS seperti ini:

{
  "kegiatan": "<nama/judul rapat, misal 'Rapat Koordinasi Sistem Informasi BAKTI Kominfo'>",
  "tanggal": "<tanggal rapat jika disebutkan, kalau tidak ada isi string kosong>",
  "lokasi": "<lokasi rapat jika disebutkan, kalau tidak ada isi string kosong>",
  "penyusun": "<nama penyusun notulen jika disebutkan, kalau tidak ada isi string kosong>",
  "tujuan": "<satu paragraf ringkas tujuan rapat>",
  "agenda": ["poin agenda 1", "poin agenda 2", "..."],
  "hasil_pembahasan": [
    {"topik": "<nama topik/klaster pembahasan>", "poin": ["poin pembahasan 1", "poin pembahasan 2"]}
  ],
  "tindak_lanjut": ["poin tindak lanjut 1", "poin tindak lanjut 2", "..."]
}

Semua isi WAJIB berbahasa Indonesia baku, ringkas, dan rapi. Kelompokkan hasil_pembahasan menjadi
2-4 topik yang masuk akal (jangan terlalu banyak topik kecil-kecil). Jangan menambahkan teks apapun
di luar objek JSON tersebut.
"""


def summarize_meeting_minutes(text: str, kegiatan_title: Optional[str] = None) -> dict:
    """Minta model Llama membuat notulensi rapat TERSTRUKTUR (dict) dari teks rapat.

    Dict yang dikembalikan siap dipakai langsung sebagai argumen generate_docx(data).
    """
    prompt = f"{_MEETING_JSON_INSTRUCTION}\n\nTeks rapat:\n{text[:12000]}"

    response = _client.chat(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Kamu adalah asisten yang ahli menyusun notulensi rapat resmi dalam bahasa "
                    "Indonesia, dan SELALU menjawab dalam format JSON murni sesuai instruksi."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    raw = response["message"]["content"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback kalau model tidak disiplin mengembalikan JSON murni:
        # taruh semua isi mentah sebagai "tujuan" supaya tidak hilang.
        data = {
            "kegiatan": kegiatan_title or "Notulensi Rapat",
            "tanggal": "",
            "lokasi": "",
            "penyusun": "",
            "tujuan": raw,
            "agenda": [],
            "hasil_pembahasan": [],
            "tindak_lanjut": [],
        }

    if kegiatan_title and not data.get("kegiatan"):
        data["kegiatan"] = kegiatan_title

    # Pastikan semua key ada supaya generate_docx tidak perlu cek None di banyak tempat.
    data.setdefault("kegiatan", kegiatan_title or "Notulensi Rapat")
    data.setdefault("tanggal", "")
    data.setdefault("lokasi", "")
    data.setdefault("penyusun", "")
    data.setdefault("tujuan", "")
    data.setdefault("agenda", [])
    data.setdefault("hasil_pembahasan", [])
    data.setdefault("tindak_lanjut", [])

    return data


# ================= DETEKSI TEKS NOTULENSI RAPAT =================

_MEETING_KEYWORDS = [
    "notulensi", "notulen rapat", "hasil rapat", "agenda rapat",
    "peserta rapat", "pembahasan rapat", "risalah rapat", "minutes of meeting",
]


def looks_like_meeting_minutes(text: str) -> bool:
    """Deteksi sederhana: apakah teks yang dikirim user mirip notulensi rapat."""
    lowered = text.lower()

    if any(kw in lowered for kw in _MEETING_KEYWORDS):
        return True

    # Kalau tidak ada kata kunci eksplisit, tebak dari kombinasi kata + panjang teks
    if "rapat" in lowered and ("peserta" in lowered or "agenda" in lowered or "dihadiri" in lowered):
        return len(text.strip()) > 200

    return False


# ================= DETEKSI PERMINTAAN EKSPOR (mis. "buatkan pdf nya") =================

_EXPORT_KEYWORDS = [
    "pdf", "word", "docx", "doc nya",
    "unduh", "download", "ekspor", "export",
    "buatkan file", "jadikan file", "kirim file", "kirimkan file",
    "jadi pdf", "jadi word", "bentuk pdf", "bentuk word",
]


def looks_like_export_request(text: str) -> bool:
    """Deteksi sederhana: apakah pesan user minta hasil (ringkasan/notulensi) yang
    SUDAH ADA sebelumnya dijadikan file PDF/Word (mis. "buatkan pdf nya",
    "jadi word aja", "unduh dalam bentuk pdf"). Dipakai bersama get_pending_export()
    supaya hanya berlaku kalau memang ada ringkasan yang sedang menunggu diekspor."""
    lowered = text.lower()
    return any(kw in lowered for kw in _EXPORT_KEYWORDS)


# ================= SIMPAN & AMBIL DOKUMEN YANG MENUNGGU DIEKSPOR =================

def save_pending_export(chat_id: int, data: dict, is_meeting: bool = True):
    """`data` adalah dict notulensi terstruktur (lihat summarize_meeting_minutes)."""
    _pending_exports[chat_id] = {
        "data": data,
        "is_meeting": is_meeting,
    }


def get_pending_export(chat_id: int) -> Optional[dict]:
    return _pending_exports.get(chat_id)


def clear_pending_export(chat_id: int):
    _pending_exports.pop(chat_id, None)


# ================= GENERATE DOCX DARI TEMPLATE BAKTI =================

def _clear_body_keep_sectpr(doc: DocxDocument):
    """
    Hapus semua isi body dari template TAPI pertahankan elemen <w:sectPr>
    (pengaturan halaman + referensi header/footer/letterhead), supaya
    logo & footer Bakti tetap muncul di dokumen baru.
    """
    body = doc.element.body
    for child in list(body):
        if child.tag.endswith("}sectPr"):
            continue
        body.remove(child)


def _set_run_style(run, bold=False, size=12, color: Optional[RGBColor] = None):
    run.font.name = FONT_NAME
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def _add_bottom_border(paragraph, color="2E4F8A", size=6):
    """Tambah garis bawah tipis pada paragraf lewat XML (pengganti manual dari style
    'Heading' bawaan Word, karena template custom sering tidak punya style tsb)."""
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def _add_section_heading(doc: DocxDocument, text: str):
    """Heading Romawi seperti 'I. INFORMASI RAPAT' dengan warna navy + garis bawah,
    meniru contoh. Dibuat manual (bukan doc.add_heading) supaya tidak bergantung pada
    style 'Heading 2' yang belum tentu ada di template custom."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    _set_run_style(run, bold=True, size=13, color=NAVY)
    _add_bottom_border(p)
    return p


def _add_paragraph_text(doc: DocxDocument, text: str, size=12, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    _set_run_style(run, size=size)
    return p


def _apply_hanging_indent(paragraph, indent_cm=0.63, hanging_cm=0.63, space_after=4):
    """Indent gantung manual, dipakai untuk meniru tampilan list bernomor/bullet
    tanpa bergantung pada style Word 'List Number'/'List Bullet' (template custom
    sering tidak punya style itu -> KeyError kalau dipaksa pakai style)."""
    pf = paragraph.paragraph_format
    pf.left_indent = Cm(indent_cm)
    pf.first_line_indent = Cm(-hanging_cm)
    pf.space_after = Pt(space_after)


def _add_numbered_list(doc: DocxDocument, items: list):
    for i, item in enumerate(items, start=1):
        p = doc.add_paragraph()
        _apply_hanging_indent(p)
        run = p.add_run(f"{i}.\t{item}")
        _set_run_style(run, size=12)


def _add_bullet_paragraph(container, text: str, size=12, is_first_paragraph=False):
    """Tambah 1 baris bullet manual ('•  teks') ke dalam doc atau ke dalam sel tabel."""
    p = container.paragraphs[0] if is_first_paragraph else container.add_paragraph()
    _apply_hanging_indent(p, indent_cm=0.5, hanging_cm=0.5, space_after=2)
    run = p.add_run(f"•\t{text}")
    _set_run_style(run, size=size)
    return p


def _fill_cell(cell, text: str, bold=False, size=12, color: Optional[RGBColor] = None,
               align_center=False, as_bullet_list: Optional[list] = None):
    """Isi 1 sel tabel. Kalau as_bullet_list diisi, tiap item jadi paragraf bullet terpisah."""
    cell.text = ""
    if as_bullet_list is not None and len(as_bullet_list) > 0:
        for i, item in enumerate(as_bullet_list):
            _add_bullet_paragraph(cell, item, size=size, is_first_paragraph=(i == 0))
        return
    p = cell.paragraphs[0]
    if align_center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    _set_run_style(run, bold=bold, size=size, color=color)


def _shade_cell(cell, hex_color: str):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(shd)


def _set_table_borders(table, size=4, color="7F7F7F"):
    """Gambar garis tabel (grid) langsung lewat XML, pengganti table.style='Table Grid'
    yang error kalau template custom tidak punya style tsb terdaftar."""
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    if tbl_pr is None:
        tbl_pr = OxmlElement("w:tblPr")
        tbl.insert(0, tbl_pr)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tbl_pr.append(borders)


def generate_docx(data: dict) -> Path:
    """
    Bangun file .docx mengikuti layout contoh:
      Judul "Notulensi Rapat" + garis dekoratif
      I. INFORMASI RAPAT      (Kegiatan / Tanggal / Lokasi / Penyusun Notulen)
      II. TUJUAN RAPAT        (paragraf)
      III. AGENDA RAPAT       (list bernomor)
      IV. HASIL PEMBAHASAN    (tabel TOPIK | HASIL PEMBAHASAN, header navy)
      V. TINDAK LANJUT        (list bernomor)
      Kalimat penutup

    `data` adalah dict seperti hasil summarize_meeting_minutes():
      {
        "kegiatan": str, "tanggal": str, "lokasi": str, "penyusun": str,
        "tujuan": str, "agenda": [str, ...],
        "hasil_pembahasan": [{"topik": str, "poin": [str, ...]}, ...],
        "tindak_lanjut": [str, ...],
      }
    """
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template tidak ditemukan di {TEMPLATE_PATH}")

    doc = DocxDocument(TEMPLATE_PATH)
    _clear_body_keep_sectpr(doc)

    kegiatan = data.get("kegiatan") or "Notulensi Rapat"
    tanggal = data.get("tanggal") or "[Isi Tanggal]"
    lokasi = data.get("lokasi") or "[Isi Lokasi]"
    penyusun = data.get("penyusun") or "[Isi Nama Penyusun]"
    tujuan = data.get("tujuan") or "-"
    agenda = data.get("agenda") or []
    hasil_pembahasan = data.get("hasil_pembahasan") or []
    tindak_lanjut = data.get("tindak_lanjut") or []

    # ===========================
    # JUDUL + GARIS DEKORATIF
    # ===========================
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_p.add_run("Notulensi Rapat")
    _set_run_style(run, bold=True, size=20)

    deco_p = doc.add_paragraph()
    deco_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    deco_run = deco_p.add_run("─────────  ❖  ─────────")
    _set_run_style(deco_run, size=11, color=NAVY)

    doc.add_paragraph()

    # ===========================
    # I. INFORMASI RAPAT
    # ===========================
    _add_section_heading(doc, "I. INFORMASI RAPAT")

    info_table = doc.add_table(rows=4, cols=3)
    info_table.alignment = WD_TABLE_ALIGNMENT.LEFT
    info_table.autofit = True

    rows_data = [
        ("Kegiatan", kegiatan),
        ("Tanggal", tanggal),
        ("Lokasi", lokasi),
        ("Penyusun Notulen", penyusun),
    ]
    for i, (label, value) in enumerate(rows_data):
        _fill_cell(info_table.cell(i, 0), label, bold=True)
        _fill_cell(info_table.cell(i, 1), ":")
        _fill_cell(info_table.cell(i, 2), value)

    doc.add_paragraph()

    # ===========================
    # II. TUJUAN RAPAT
    # ===========================
    _add_section_heading(doc, "II. TUJUAN RAPAT")
    _add_paragraph_text(doc, tujuan)
    doc.add_paragraph()

    # ===========================
    # III. AGENDA RAPAT
    # ===========================
    _add_section_heading(doc, "III. AGENDA RAPAT")
    if agenda:
        _add_numbered_list(doc, agenda)
    else:
        _add_paragraph_text(doc, "-")
    doc.add_paragraph()

    # ===========================
    # IV. HASIL PEMBAHASAN
    # ===========================
    _add_section_heading(doc, "IV. HASIL PEMBAHASAN")
    if hasil_pembahasan:
        hp_table = doc.add_table(rows=1, cols=2)
        _set_table_borders(hp_table)
        hp_table.alignment = WD_TABLE_ALIGNMENT.LEFT

        header_cells = hp_table.rows[0].cells
        _fill_cell(header_cells[0], "TOPIK", bold=True, color=RGBColor(255, 255, 255), align_center=True)
        _fill_cell(header_cells[1], "HASIL PEMBAHASAN", bold=True, color=RGBColor(255, 255, 255), align_center=True)
        for cell in header_cells:
            _shade_cell(cell, HEADER_FILL)

        for item in hasil_pembahasan:
            row_cells = hp_table.add_row().cells
            _fill_cell(row_cells[0], item.get("topik", "-"), bold=True)
            _fill_cell(row_cells[1], "", as_bullet_list=item.get("poin", []) or ["-"])
    else:
        _add_paragraph_text(doc, "-")
    doc.add_paragraph()

    # ===========================
    # V. TINDAK LANJUT
    # ===========================
    _add_section_heading(doc, "V. TINDAK LANJUT")
    if tindak_lanjut:
        _add_numbered_list(doc, tindak_lanjut)
    else:
        _add_paragraph_text(doc, "-")

    doc.add_paragraph()

    # ===========================
    # PENUTUP
    # ===========================
    _add_paragraph_text(
        doc,
        "Demikian notulensi rapat ini dibuat sebagai ringkasan jalannya rapat dan hasil "
        "pembahasan yang telah disepakati."
    )

    out_path = EXPORT_DIR / f"{uuid.uuid4().hex}.docx"
    doc.save(out_path)

    return out_path




def convert_docx_to_pdf(docx_path: Path) -> Path:
    """
    Konversi DOCX ke PDF menggunakan Microsoft Word (docx2pdf).
    """
    docx_path = Path(docx_path)
    pdf_path = EXPORT_DIR / f"{docx_path.stem}.pdf"

    convert(str(docx_path), str(pdf_path))

    if not pdf_path.exists():
        raise FileNotFoundError("Gagal membuat file PDF.")

    return pdf_path