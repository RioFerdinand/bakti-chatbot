from database import db_cursor


def create_chat(user_id: int, title: str):
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO chats (user_id, title) VALUES (?, ?)",
            (user_id, title),
        )
        chat_id = cur.lastrowid
        cur.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))
        row = cur.fetchone()
    return dict(row)


def get_chats_by_user(user_id: int):
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM chats WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_chat(chat_id: int):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def delete_chat(chat_id: int):
    with db_cursor() as cur:
        cur.execute("DELETE FROM chats WHERE id = ?", (chat_id,))


def add_message(chat_id: int, sender: str, text: str):
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO messages (chat_id, sender, text) VALUES (?, ?, ?)",
            (chat_id, sender, text),
        )
        msg_id = cur.lastrowid
        cur.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
        row = cur.fetchone()
    return dict(row)


def get_messages_by_chat(chat_id: int):
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC, id ASC",
            (chat_id,),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def update_chat_title(chat_id: int, title: str):
    with db_cursor() as cur:
        cur.execute(
            "UPDATE chats SET title = ? WHERE id = ?",
            (title, chat_id),
        )
        cur.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def get_message(message_id: int):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def update_message(message_id: int, text: str):
    """Ubah isi teks sebuah pesan (dipakai untuk fitur edit pesan user)."""
    with db_cursor() as cur:
        cur.execute(
            "UPDATE messages SET text = ? WHERE id = ?",
            (text, message_id),
        )
        cur.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def delete_messages_after(chat_id: int, message_id: int):
    """Hapus semua pesan dalam 1 chat yang dibuat SETELAH message_id tertentu.
    Dipakai saat user mengedit pesan lama: percakapan lanjutan yang lama (termasuk
    balasan bot) dianggap tidak berlaku lagi dan harus digenerate ulang."""
    with db_cursor() as cur:
        cur.execute(
            "DELETE FROM messages WHERE chat_id = ? AND id > ?",
            (chat_id, message_id),
        )