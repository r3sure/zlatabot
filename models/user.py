import sqlite3
from datetime import date, datetime
from pathlib import Path

from config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


TAROT_DAILY_LIMIT = 2


def get_tarot_usage(user_id: int) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT tarot_date, tarot_count FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if not row or row["tarot_date"] is None:
        return 0
    today = date.today().isoformat()
    if row["tarot_date"] != today:
        return 0
    return row["tarot_count"] or 0


def increment_tarot_usage(user_id: int):
    today = date.today().isoformat()
    conn = get_connection()
    row = conn.execute(
        "SELECT tarot_date, tarot_count FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row and row["tarot_date"] == today:
        conn.execute(
            "UPDATE users SET tarot_count = tarot_count + 1 WHERE user_id = ?",
            (user_id,),
        )
    elif row:
        conn.execute(
            "UPDATE users SET tarot_date = ?, tarot_count = 1 WHERE user_id = ?",
            (today, user_id),
        )
    else:
        conn.execute(
            "INSERT INTO users (user_id, tarot_date, tarot_count) VALUES (?, ?, 1)",
            (user_id, today),
        )
    conn.commit()
    conn.close()


def is_premium(user_id: int) -> bool:
    """Full premium (paid). Trial users return False."""
    conn = get_connection()
    row = conn.execute(
        "SELECT subscription_status FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return False
    return row["subscription_status"] == "premium"


def is_trial(user_id: int) -> bool:
    """Active trial (7 days, not expired)."""
    from datetime import datetime
    conn = get_connection()
    row = conn.execute(
        "SELECT subscription_status, subscription_end FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row or row["subscription_status"] != "trial":
        return False
    if not row["subscription_end"]:
        return True
    try:
        end = datetime.fromisoformat(row["subscription_end"])
        return end > datetime.now()
    except Exception:
        return True


def has_premium_access(user_id: int) -> bool:
    """Trial OR full premium."""
    return is_premium(user_id) or is_trial(user_id)


def start_trial(user_id: int, days: int = 3):
    """Grant a trial subscription to a user."""
    from datetime import datetime, timedelta
    end = (datetime.now() + timedelta(days=days)).isoformat()
    conn = get_connection()
    conn.execute(
        "UPDATE users SET subscription_status = 'trial', subscription_end = ? WHERE user_id = ?",
        (end, user_id),
    )
    conn.commit()
    conn.close()
    return end


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            zodiac_sign TEXT,
            birth_date TEXT,
            birth_time TEXT,
            birth_city TEXT,
            lat REAL,
            lng REAL,
            tz_str TEXT,
            nation TEXT,
            subscription_status TEXT DEFAULT 'free',
            subscription_type TEXT,
            subscription_end TEXT,
            stars_balance INTEGER DEFAULT 0,
            last_active TEXT,
            streak INTEGER DEFAULT 0,
            questions_count INTEGER DEFAULT 0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER REFERENCES users(user_id),
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(user_id),
            type TEXT,
            cards TEXT,
            interpretation TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS dreams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(user_id),
            dream_text TEXT,
            interpretation TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    # migrate existing DB — add lat/lng/tz_str/nation/gender columns if missing
    for col in ("lat", "lng", "tz_str", "nation"):
        typ = "REAL" if col in ("lat", "lng") else "TEXT"
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
        except Exception:
            pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN gender TEXT")
    except Exception:
        pass
    for col in ("tarot_date", "tarot_count"):
        typ = "TEXT" if col == "tarot_date" else "INTEGER DEFAULT 0"
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
        except Exception:
            pass
    for col in ("jailbreak_date", "jailbreak_count"):
        typ = "TEXT" if col == "jailbreak_date" else "INTEGER DEFAULT 0"
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
        except Exception:
            pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_deleted INTEGER DEFAULT 0")
    except Exception:
        pass
    conn.commit()
    conn.close()


def mark_user_deleted(user_id: int):
    conn = get_connection()
    conn.execute(
        """UPDATE users SET
            is_deleted = 1,
            name = NULL, birth_date = NULL, birth_time = NULL,
            birth_city = NULL, lat = NULL, lng = NULL, tz_str = NULL,
            nation = NULL, gender = NULL, zodiac_sign = NULL,
            subscription_status = 'free', subscription_end = NULL,
            jailbreak_date = NULL, jailbreak_count = 0,
            tarot_date = NULL, tarot_count = 0
        WHERE user_id = ?""",
        (user_id,),
    )
    conn.commit()
    conn.close()


def was_deleted(user_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT is_deleted FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return bool(row and row["is_deleted"])


def grant_premium(user_id: int, months: int = 1) -> str:
    """Grant or extend full premium for N months."""
    from datetime import datetime, timedelta
    conn = get_connection()
    row = conn.execute(
        "SELECT subscription_end FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    now = datetime.now()
    if row and row["subscription_end"]:
        try:
            current_end = datetime.fromisoformat(row["subscription_end"])
            base = current_end if current_end > now else now
        except Exception:
            base = now
    else:
        base = now
    end = (base + timedelta(days=30 * months)).isoformat()
    if row:
        conn.execute(
            "UPDATE users SET subscription_status = 'premium', subscription_end = ? WHERE user_id = ?",
            (end, user_id),
        )
    else:
        conn.execute(
            "INSERT INTO users (user_id, name, subscription_status, subscription_end) VALUES (?, 'User', 'premium', ?)",
            (user_id, end),
        )
    conn.commit()
    conn.close()
    return end


def get_subscription_status(user_id: int) -> str | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT subscription_status FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row["subscription_status"] if row else None
