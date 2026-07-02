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
