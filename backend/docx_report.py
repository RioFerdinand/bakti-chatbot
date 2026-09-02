"""
docx_report.py
Mengisi template Word resmi BAKTI (backend/templates/Template_DOCS_Bakti.docx)
dengan hasil ringkasan rapat, lalu mengonversinya jadi PDF.

Template punya:
- Kop/logo BAKTI + Komdigi di header (otomatis ikut di setiap halaman)
- 3 placeholder di body: "Judul", "BAB", "SUBBAB"

Strategi: cari paragraf yang teksnya persis "Judul"/"BAB"/"SUBBAB", ganti
isinya, lalu sisipkan paragraf/tabel baru tepat setelah masing-masing.
"""
import subprocess
import uuid
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE_DIR = Path(__file__).parent
TEMPLATE_PATH = BASE_DIR / "templates" / "Template_DOCS_Bakti.docx"
OUTPUT_DIR = BASE_DIR / "generated_reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _find_paragraph(doc: Document, exact_text: str):
    for p in doc.paragraphs:
        if p.text.strip() == exact_text:
            return p
    raise ValueError(f"Placeholder {exact_text!r} tidak ditemukan di template")


def _insert_paragraph_after(paragraph, text="", style=None):
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    from docx.text.paragraph import Paragraph
    new_paragraph = Paragraph(new_p, paragraph._parent)
    if text:
        new_paragraph.add_run(text)
    if style:
        try:
            new_paragraph.style = style
        except KeyError:
            pass
    return new_paragraph


def _set_table_borders(table):
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "999999")
        borders.append(el)
    tbl_pr.append(borders)


def _insert_table_after(paragraph, headers, rows):
    doc = paragraph.part.document
    table = doc.add_table(rows=1, cols=len(headers))
    _set_table_borders(table)

    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h

    for row_data in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row_data):
            cells[i].text = str(val)

    paragraph._p.addnext(table._tbl)
    return table


def generate_meeting_report_docx(summary: dict) -> Path:
    """Isi template docx dengan hasil ringkasan rapat. Return path file .docx."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template tidak ditemukan di {TEMPLATE_PATH}")

    doc = Document(str(TEMPLATE_PATH))

    judul_p = _find_paragraph(doc, "Judul")
    judul_p.text = ""
    judul_p.add_run(summary.get("judul", "Ringkasan Rapat"))

    bab_p = _find_paragraph(doc, "BAB")
    bab_p.text = ""
    bab_p.add_run("BAB I. RINGKASAN UMUM")

    anchor = _insert_paragraph_after(bab_p, summary.get("ringkasan", "-"))

    peserta = summary.get("peserta") or []
    if peserta:
        anchor = _insert_paragraph_after(anchor, "Peserta: " + ", ".join(peserta))

    subbab_p = _find_paragraph(doc, "SUBBAB")
    subbab_p.text = ""
    subbab_p.add_run("BAB II. POIN-POIN PENTING")
    try:
        subbab_p.style = doc.styles["Heading 1"]
    except KeyError:
        pass

    poin_penting = summary.get("poin_penting") or []
    anchor = subbab_p
    for poin in poin_penting:
        anchor = _insert_paragraph_after(anchor, poin, style="List Bullet")

    action_items = summary.get("action_items") or []
    if action_items:
        anchor = _insert_paragraph_after(anchor, "BAB III. ACTION ITEMS", style="Heading 1")
        rows = [
            (a.get("tugas", "-"), a.get("penanggung_jawab", "-"), a.get("tenggat", "-"))
            for a in action_items
        ]
        _insert_table_after(anchor, ["Tugas", "Penanggung Jawab", "Tenggat"], rows)

    filename = f"laporan-rapat-{uuid.uuid4().hex[:8]}.docx"
    filepath = OUTPUT_DIR / filename
    doc.save(str(filepath))
    return filepath


def convert_docx_to_pdf(docx_path: Path) -> Path:
    """
    Konversi .docx jadi .pdf. Coba docx2pdf (butuh Microsoft Word, Windows/Mac)
    dulu, fallback ke LibreOffice headless (soffice) kalau tidak tersedia.
    """
    pdf_path = docx_path.with_suffix(".pdf")
    docx2pdf_error = None

    try:
        from docx2pdf import convert as docx2pdf_convert
        docx2pdf_convert(str(docx_path), str(pdf_path))
        if pdf_path.exists():
            return pdf_path
    except Exception as e:
        docx2pdf_error = e  # simpan dulu, jangan ditelan diam-diam

    # Fallback: LibreOffice headless (perlu LibreOffice terinstal & ada di PATH)
    try:
        subprocess.run(
            [
                "soffice", "--headless", "--convert-to", "pdf",
                "--outdir", str(docx_path.parent), str(docx_path),
            ],
            check=True,
            timeout=120,
        )
    except FileNotFoundError:
        # soffice juga gak ada -> laporkan error docx2pdf yang asli, itu yang penting
        raise RuntimeError(
            f"Konversi lewat Microsoft Word (docx2pdf) gagal: {docx2pdf_error}. "
            "LibreOffice (soffice) juga tidak ditemukan sebagai fallback."
        )

    if not pdf_path.exists():
        raise RuntimeError(
            f"Gagal convert docx ke PDF. Error docx2pdf: {docx2pdf_error}"
        )
    return pdf_path
