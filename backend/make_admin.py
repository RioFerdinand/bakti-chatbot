"""
make_admin.py
Script CLI untuk menjadikan sebuah akun sebagai admin.

SENGAJA dibuat sebagai script terpisah (bukan endpoint API) sebagai best
practice keamanan: proses "menaikkan seseorang jadi admin" tidak boleh bisa
dipicu dari luar (misal lewat request HTTP), karena kalau itu jadi endpoint
publik, siapapun berpotensi mengeksploitasinya untuk mengangkat diri sendiri
jadi admin. Jadi ini HARUS dijalankan manual oleh developer/pemilik server.

Cara pakai:
    python make_admin.py email@user.com
"""
import sys

from database import init_db, db_cursor


def make_admin(email: str):
    with db_cursor() as cur:
        cur.execute("SELECT id, nama, role FROM users WHERE email = ?", (email,))
        row = cur.fetchone()

        if not row:
            print(f"Tidak ditemukan user dengan email: {email}")
            print("Pastikan akun ini sudah register dulu lewat halaman Register biasa.")
            return

        if row["role"] == "admin":
            print(f"{row['nama']} ({email}) sudah jadi admin sebelumnya.")
            return

        cur.execute("UPDATE users SET role = 'admin' WHERE email = ?", (email,))
        print(f"Berhasil! {row['nama']} ({email}) sekarang jadi admin.")


if __name__ == "__main__":
    init_db()

    if len(sys.argv) != 2:
        print("Cara pakai: python make_admin.py email@user.com")
        sys.exit(1)

    make_admin(sys.argv[1])
