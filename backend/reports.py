from database import db_cursor


def create_report(user_id: int, title: str, source_text: str, summary_text: str, pdf_path: str, docx_path: str):
    with db_cursor() as cur:
        cur.execute(
            """INSERT INTO reports (user_id, title, source_text, summary_text, pdf_path, docx_path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, title, source_text, summary_text, pdf_path, docx_path),
        )
        report_id = cur.lastrowid
        cur.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        row = cur.fetchone()
    return dict(row)


def get_reports_by_user(user_id: int):
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM reports WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_report(report_id: int):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        row = cur.fetchone()
    return dict(row) if row else None

def delete_report(report_id: int):
    with db_cursor() as cur:
        cur.execute("DELETE FROM reports WHERE id = ?", (report_id,))