from models.user import get_connection


def save_reading(user_id: int, reading_type: str, cards: list, interpretation: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO readings (user_id, type, cards, interpretation) VALUES (?, ?, ?, ?)",
        (user_id, reading_type, str(cards), interpretation),
    )
    conn.commit()
    conn.close()


def get_readings(user_id: int, limit: int = 10):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM readings WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return rows
