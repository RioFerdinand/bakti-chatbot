import sqlite3

conn = sqlite3.connect('app.db')
cur = conn.cursor()
cur.execute(
    "UPDATE users SET nama = ? WHERE email = ?",
    ("Farah Fadhilah", "EMAIL_ASLI_KAMU@contoh.com")
)
conn.commit()
print(f"Baris terupdate: {cur.rowcount}")
conn.close()