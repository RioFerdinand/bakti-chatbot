import json

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ai import ask_question
import vision

from database import init_db
import auth
import chats
import admin as admin_module
import ingest
from ai import invalidate_cache as ai_invalidate_cache

from fastapi.responses import FileResponse
import document_export as docexp

import os
import reports

app = FastAPI(title="Bakti AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Buat tabel database kalau belum ada, setiap kali server start
init_db()


# ================= SCHEMAS =================

class ChatRequest(BaseModel):
    chat_id: int
    question: str
    # True kalau dipanggil ulang setelah edit pesan (pesan user sudah di-update
    # lewat endpoint PATCH /chats/{chat_id}/messages/{message_id}, jadi di sini
    # tidak perlu disimpan lagi sebagai pesan baru).
    skip_user_save: bool = False

class EditMessageRequest(BaseModel):
    text: str

class ExportRequest(BaseModel):
    format: str  # "word" atau "pdf"

class RegisterRequest(BaseModel):
    nama: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class NewChatRequest(BaseModel):
    user_id: int
    title: str


class UpdateChatTitleRequest(BaseModel):
    title: str


# ================= ROOT =================

@app.get("/")
def root():
    return {"status": "Bakti AI aktif"}


# ================= AUTH =================

@app.post("/register")
def register(req: RegisterRequest):
    if not req.nama.strip() or not req.email.strip() or not req.password.strip():
        raise HTTPException(status_code=400, detail="Semua field wajib diisi")

    existing = auth.get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    user = auth.create_user(req.nama, req.email, req.password)
    return user


@app.post("/login")
def login(req: LoginRequest):
    user = auth.authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Email atau password salah")
    return user


# ================= CHATS =================

@app.get("/chats/{user_id}")
def list_chats(user_id: int):
    return chats.get_chats_by_user(user_id)


@app.post("/chats")
def new_chat(req: NewChatRequest):
    return chats.create_chat(req.user_id, req.title)


@app.delete("/chats/{chat_id}")
def remove_chat(chat_id: int):
    chats.delete_chat(chat_id)
    return {"status": "deleted"}


@app.patch("/chats/{chat_id}")
def rename_chat(chat_id: int, req: UpdateChatTitleRequest):
    chat_row = chats.get_chat(chat_id)
    if not chat_row:
        raise HTTPException(status_code=404, detail="Chat tidak ditemukan")

    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Judul tidak boleh kosong")

    return chats.update_chat_title(chat_id, req.title.strip())


@app.get("/chats/{chat_id}/messages")
def list_messages(chat_id: int):
    return chats.get_messages_by_chat(chat_id)


@app.patch("/chats/{chat_id}/messages/{message_id}")
def edit_message(chat_id: int, message_id: int, req: EditMessageRequest):
    """Edit isi sebuah pesan (dipakai untuk fitur 'edit pesan' di chat).

    Semua pesan SETELAH pesan ini (termasuk balasan bot yang lama) ikut dihapus,
    karena percakapan lanjutan yang lama sudah tidak relevan lagi setelah pesan
    diedit -- frontend akan meminta jawaban baru lewat POST /chat.
    """
    message = chats.get_message(message_id)
    if not message or message["chat_id"] != chat_id:
        raise HTTPException(status_code=404, detail="Pesan tidak ditemukan")

    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Teks pesan tidak boleh kosong")

    updated = chats.update_message(message_id, req.text.strip())
    chats.delete_messages_after(chat_id, message_id)

    return updated


# ================= CHAT (tanya jawab AI) =================

@app.post("/chat")
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Pertanyaan tidak boleh kosong")

    chat_row = chats.get_chat(req.chat_id)
    if not chat_row:
        raise HTTPException(status_code=404, detail="Chat tidak ditemukan")

    # Simpan pesan user (dilewati kalau ini regenerasi jawaban setelah user
    # mengedit pesan lamanya -- pesan itu sudah di-update lewat endpoint edit).
    user_msg = None
    if not req.skip_user_save:
        user_msg = chats.add_message(req.chat_id, "user", req.question)

# Kalau teksnya mirip notulensi rapat, langsung balas ringkasannya di chat
    # (TIDAK menawarkan/membuat file Word/PDF -- itu sekarang cuma lewat menu
    # "Ringkasan Rapat -> PDF" di sidebar).
    if docexp.looks_like_meeting_minutes(req.question):
        answer = docexp.summarize_text(req.question)
        bot_msg = chats.add_message(req.chat_id, "bot", answer)
        return {
            "answer": answer,
            "sources": [],
            "user_message_id": user_msg["id"] if user_msg else None,
            "bot_message_id": bot_msg["id"],
        }

    try:
        answer, sources = ask_question(req.question, use_full=True)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Simpan jawaban bot
    bot_msg = chats.add_message(req.chat_id, "bot", answer)

    return {
        "answer": answer,
        "sources": sources,
        "user_message_id": user_msg["id"] if user_msg else None,
        "bot_message_id": bot_msg["id"],
    }


# ================= CHAT UMUM (tanpa login, knowledge base terbatas) =================

class GuestChatRequest(BaseModel):
    question: str


@app.post("/chat/guest")
def chat_guest(req: GuestChatRequest):
    """
    Versi chat untuk pengunjung yang BELUM login. Tidak disimpan ke database
    (stateless -- riwayatnya hilang kalau halaman di-refresh), dan hanya
    mengakses knowledge base publik (chroma_db_public), bukan yang lengkap.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Pertanyaan tidak boleh kosong")

    try:
        answer, sources = ask_question(req.question, use_full=False)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {"answer": answer, "sources": sources}


# ================= UPLOAD GAMBAR / FILE (kamera & lampiran) =================

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


@app.post("/chat/upload")
async def chat_upload(
    chat_id: int = Form(...),
    question: str = Form(""),
    file: UploadFile = File(...),
):
    """
    Terima gambar (dari kamera/galeri) atau file dokumen (PDF/DOCX) dari user,
    ekstrak teksnya (OCR untuk gambar, parsing untuk dokumen), lalu ringkas
    atau jawab pertanyaan terkait isinya lewat LLM.
    """
    chat_row = chats.get_chat(chat_id)
    if not chat_row:
        raise HTTPException(status_code=404, detail="Chat tidak ditemukan")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="File kosong")
    if len(file_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="Ukuran file maksimal 10MB")

    filename = file.filename or "upload"

    # Catat pesan user (menunjukkan lampiran + caption/pertanyaan kalau ada)
    user_note = f"📎 {filename}" + (f"\n{question.strip()}" if question.strip() else "")
    chats.add_message(chat_id, "user", user_note)

    try:
        extracted_text, file_type = vision.extract_text(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal membaca isi file: {e}"
        )

    try:
        answer = vision.analyze_content(question, extracted_text)
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Gagal menghubungi Ollama: {e}"
        )

    chats.add_message(chat_id, "bot", answer)

    return {
        "answer": answer,
        "file_type": file_type,
        "filename": filename,
        "extracted_preview": extracted_text[:500],
    }

# ================= UPLOAD FILE/FOTO UNTUK DIRINGKAS =================

@app.post("/chat/{chat_id}/upload-summarize")
async def upload_summarize(chat_id: int, file: UploadFile = File(...)):
    chat_row = chats.get_chat(chat_id)
    if not chat_row:
        raise HTTPException(status_code=404, detail="Chat tidak ditemukan")

    content = await file.read()
    try:
        text = docexp.extract_text_from_file(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not text.strip():
        raise HTTPException(status_code=400, detail="Tidak ada teks yang bisa dibaca dari file ini")

    chats.add_message(chat_id, "user", f"📎 Mengirim file: {file.filename}")

    # Kalau isi file ternyata notulensi rapat, langsung buat versi terstruktur
    # (lebih rapi kalau nanti diekspor jadi Word/PDF pakai template).
    if docexp.looks_like_meeting_minutes(text):
        data = docexp.summarize_meeting_minutes(text, kegiatan_title=file.filename)
        summary = data.get("tujuan", "")
        docexp.save_pending_export(chat_id, data, is_meeting=True)
    else:
        # Ringkasan bebas (dokumen umum, bukan notulensi rapat).
        summary = docexp.summarize_text(text)
        data = {
            "kegiatan": file.filename,
            "tanggal": "",
            "lokasi": "",
            "penyusun": "",
            "tujuan": summary,
            "agenda": [],
            "hasil_pembahasan": [],
            "tindak_lanjut": [],
        }
        docexp.save_pending_export(chat_id, data, is_meeting=False)

    bot_text = (
        f"Berikut ringkasan dari **{file.filename}**:\n\n{summary}\n\n"
        "Mau saya buatkan jadi file **Word** atau **PDF**?"
    )
    chats.add_message(chat_id, "bot", bot_text)

    return {"answer": bot_text, "summary": summary, "awaiting_export": True}


# ================= EXPORT KE WORD / PDF =================

@app.post("/chat/{chat_id}/export")
def export_document(chat_id: int, req: ExportRequest):
    pending = docexp.get_pending_export(chat_id)
    if not pending:
        raise HTTPException(status_code=400, detail="Tidak ada ringkasan/notulensi yang menunggu diekspor")

    docx_path = docexp.generate_docx(pending["data"])

    if req.format == "word":
        final_path, media_type, filename = docx_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "Dokumen_Bakti.docx"
    elif req.format == "pdf":
        final_path = docexp.convert_docx_to_pdf(docx_path)
        media_type, filename = "application/pdf", "Dokumen_Bakti.pdf"
    else:
        raise HTTPException(status_code=400, detail="Format harus 'word' atau 'pdf'")

    docexp.clear_pending_export(chat_id)

    # Simpan pesan bot dengan metadata file (nama file asli di disk) TERSEMPULAN
    # setelah karakter NUL "\x00" -- tidak ikut tampil di chat, tapi dipakai
    # frontend untuk membangun link "unduh lagi" (GET /files/{file_id}) yang
    # tetap berfungsi walau halaman di-refresh atau chat lama dibuka ulang.
    file_meta = json.dumps({"file_id": final_path.name, "display_name": filename})
    bot_text = f"✅ File {filename} sudah dibuat, silakan unduh."
    chats.add_message(chat_id, "bot", f"{bot_text}\x00{file_meta}")

    return FileResponse(
        path=final_path,
        media_type=media_type,
        filename=filename,
        headers={"X-File-Id": final_path.name},
    )


@app.get("/files/{file_id}")
def download_file(file_id: str):
    """Unduh ulang file (docx/pdf) yang pernah dibuat lewat /chat/{chat_id}/export.
    file_id adalah nama file asli di disk (mis. '2754600db9fe418b898a5929d2fffdbf.docx')."""
    if "/" in file_id or "\\" in file_id or ".." in file_id:
        raise HTTPException(status_code=400, detail="file_id tidak valid")

    file_path = docexp.EXPORT_DIR / file_id
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File tidak ditemukan (mungkin sudah dihapus)")

    ext = file_path.suffix.lower()
    if ext == ".pdf":
        media_type = "application/pdf"
    elif ext == ".docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        media_type = "application/octet-stream"

    return FileResponse(path=file_path, media_type=media_type, filename=f"Dokumen_Bakti{ext}")


# ================= RINGKASAN RAPAT -> PDF/WORD (fitur baru: modal sidebar) =================

@app.post("/reports/extract-file")
async def extract_file(file: UploadFile = File(...)):
    """Baca teks dari foto catatan ATAU PDF notulen yang diupload lewat modal."""
    content = await file.read()
    try:
        text = docexp.extract_text_from_file(file.filename, content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membaca file: {e}")
    return {"text": text}


@app.post("/reports/generate")
def generate_report(
    user_id: int = Form(...),
    title: str = Form(...),
    text: str = Form(...),
):
    """Rangkum jadi notulensi terstruktur, generate Word (template BAKTI), lalu convert ke PDF,
    dan simpan ke riwayat laporan (tabel reports) supaya bisa diunduh ulang kapan saja."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Teks transkrip tidak boleh kosong")

    try:
        data = docexp.summarize_meeting_minutes(text, kegiatan_title=title)
        docx_path = docexp.generate_docx(data)
        pdf_path = docexp.convert_docx_to_pdf(docx_path)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Gagal membuat notulensi: {e}")

    report = reports.create_report(user_id, title, text, json.dumps(data), str(pdf_path), str(docx_path))
    return report


@app.get("/reports/{user_id}")
def list_reports(user_id: int):
    """Ambil riwayat laporan ringkasan rapat milik user."""
    return reports.get_reports_by_user(user_id)


def _safe_download_name(title: str, ext: str) -> str:
    """Ubah judul laporan jadi nama file yang aman buat di-download, mis.
    'Rapat Mingguan Tim IT' -> 'Rapat_Mingguan_Tim_IT.pdf'."""
    keep = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in title)
    keep = keep.strip().replace(" ", "_") or "Laporan"
    return f"{keep}{ext}"


@app.get("/reports/download/{report_id}/{filetype}")
def download_report(report_id: int, filetype: str):
    """Download hasil ringkasan rapat dalam format pdf atau docx."""
    report = reports.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    if filetype == "pdf":
        path, media_type = report["pdf_path"], "application/pdf"
    elif filetype == "docx":
        path, media_type = report["docx_path"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=400, detail="filetype harus 'pdf' atau 'docx'")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File tidak ditemukan di server")

    download_name = _safe_download_name(report["title"], os.path.splitext(path)[1])
    return FileResponse(path, media_type=media_type, filename=download_name)

@app.delete("/reports/{report_id}")
def remove_report(report_id: int):
    """Hapus laporan dari riwayat + hapus file pdf/docx-nya dari server kalau ada."""
    report = reports.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")

    for path in (report["pdf_path"], report["docx_path"]):
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass  # file mungkin sedang dipakai/terkunci, biarkan saja

    reports.delete_report(report_id)
    return {"status": "deleted"}

# ================= ADMIN: KELOLA DOKUMEN KNOWLEDGE BASE =================

@app.get("/admin/documents")
def admin_list_documents(user_id: int):
    """Daftar semua dokumen (public + non-public). Hanya admin."""
    try:
        admin_module.require_admin(user_id)
    except admin_module.AdminPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return admin_module.list_documents()


@app.post("/admin/documents")
async def admin_upload_document(
    user_id: int = Form(...),
    category: str = Form(...),  # "public" atau "non-public"
    file: UploadFile = File(...),
):
    """Upload dokumen baru ke kategori tertentu. Hanya admin."""
    try:
        admin_module.require_admin(user_id)
    except admin_module.AdminPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    file_bytes = await file.read()

    try:
        saved_name = admin_module.save_document(file_bytes, file.filename, category)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"name": saved_name, "category": category}


@app.delete("/admin/documents/{filename}")
def admin_delete_document(filename: str, user_id: int, category: str):
    """Hapus dokumen dari kategori tertentu. Hanya admin."""
    try:
        admin_module.require_admin(user_id)
    except admin_module.AdminPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    try:
        admin_module.delete_document(filename, category)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "deleted"}


@app.post("/admin/reingest")
def admin_reingest(user_id: int):
    """
    Bangun ulang knowledge base (PUBLIC & FULL) dari isi folder documents/
    saat ini. Dipanggil admin setelah upload/hapus dokumen. Ini proses yang
    agak berat (perlu re-embed semua dokumen), jadi sengaja tidak otomatis
    jalan tiap kali upload -- admin klik tombol "Re-index" secara manual
    setelah selesai atur dokumennya.
    """
    try:
        admin_module.require_admin(user_id)
    except admin_module.AdminPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    try:
        stats = ingest.build_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal re-index: {e}")

    # Penting: kosongkan cache chain/retriever di memori supaya server
    # langsung pakai vector store yang baru saja dibangun ulang.
    ai_invalidate_cache()

    return {"status": "ok", **stats}
