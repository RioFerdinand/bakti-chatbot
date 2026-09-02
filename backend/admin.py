"""
admin.py
Fungsi bantu untuk fitur admin: kelola dokumen knowledge base
(kategori "public" -> documents/public/, "non-public" -> documents/member/).
"""
import os
import shutil

from auth import get_user_by_id

BASE_DIR = os.path.dirname(__file__)
PUBLIC_DIR = os.path.join(BASE_DIR, "documents", "public")
MEMBER_DIR = os.path.join(BASE_DIR, "documents", "member")

os.makedirs(PUBLIC_DIR, exist_ok=True)
os.makedirs(MEMBER_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf"}  # ingest.py saat ini cuma baca PDF


def _category_to_dir(category: str) -> str:
    if category == "public":
        return PUBLIC_DIR
    elif category == "non-public":
        return MEMBER_DIR
    raise ValueError("Kategori harus 'public' atau 'non-public'")


class AdminPermissionError(Exception):
    """User yang bersangkutan bukan admin."""
    pass


def require_admin(user_id: int):
    """
    Pastikan user_id yang diklaim benar-benar admin (dicek ulang ke
    database, TIDAK percaya begitu saja klaim dari frontend). Raise
    AdminPermissionError kalau bukan admin.
    """
    user = get_user_by_id(user_id)
    if not user or user.get("role") != "admin":
        raise AdminPermissionError("Akses ditolak, akun ini bukan admin")
    return user


def list_documents():
    """Daftar semua dokumen di kedua kategori."""
    result = []
    for category, folder in (("public", PUBLIC_DIR), ("non-public", MEMBER_DIR)):
        for filename in sorted(os.listdir(folder)):
            if filename.startswith("."):
                continue
            path = os.path.join(folder, filename)
            if os.path.isfile(path):
                result.append({
                    "name": filename,
                    "category": category,
                    "size_kb": round(os.path.getsize(path) / 1024, 1),
                })
    return result


def save_document(file_bytes: bytes, filename: str, category: str) -> str:
    """Simpan file baru ke folder sesuai kategori. Return nama file final."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Tipe file {ext} belum didukung, sementara cuma PDF")

    folder = _category_to_dir(category)
    dest_path = os.path.join(folder, filename)

    # Kalau ada nama yang sama, tambahkan angka biar tidak menimpa file lama
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(dest_path):
        filename = f"{base} ({counter}){ext}"
        dest_path = os.path.join(folder, filename)
        counter += 1

    with open(dest_path, "wb") as f:
        f.write(file_bytes)

    return filename


def delete_document(filename: str, category: str):
    """Hapus file dari folder sesuai kategori."""
    folder = _category_to_dir(category)
    path = os.path.join(folder, filename)

    # Cegah path traversal (misal filename berisi ../../)
    if os.path.dirname(os.path.abspath(path)) != os.path.abspath(folder):
        raise ValueError("Nama file tidak valid")

    if not os.path.isfile(path):
        raise FileNotFoundError(f"File {filename} tidak ditemukan di kategori {category}")

    os.remove(path)
