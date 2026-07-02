from models.user import get_connection


def save_dream(user_id: int, dream_text: str, interpretation: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO dreams (user_id, dream_text, interpretation) VALUES (?, ?, ?)",
        (user_id, dream_text, interpretation),
    )
    conn.commit()
    conn.close()


def get_dreams(user_id: int, limit: int = 20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM dreams WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return rows
