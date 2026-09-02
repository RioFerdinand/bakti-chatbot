import bcrypt
from database import db_cursor


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_user(nama: str, email: str, password: str, role: str = "user"):
    password_hash = hash_password(password)
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO users (nama, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (nama, email, password_hash, role),
        )
        user_id = cur.lastrowid
    return {"id": user_id, "nama": nama, "email": email, "role": role}


def get_user_by_email(email: str):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return {"id": user["id"], "nama": user["nama"], "email": user["email"], "role": user["role"]}