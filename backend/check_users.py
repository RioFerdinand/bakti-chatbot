import sqlite3

conn = sqlite3.connect('app.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, nama, email FROM users")
rows = cur.fetchall()

if not rows:
    print("Tabel users kosong. Kamu belum register akun, atau app.db yang dipakai server beda dengan yang ini.")
else:
    for r in rows:
        print(dict(r))

conn.close()