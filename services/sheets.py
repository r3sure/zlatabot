import logging
import os
from pathlib import Path

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import BASE_DIR
from models.user import get_connection

# Bypass proxy for Google APIs (httplib2/requests picks up system proxy otherwise)
os.environ.setdefault("no_proxy", "googleapis.com,google.com,gstatic.com,googleusercontent.com")

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
_KEY_PATH = BASE_DIR / "zlata-500812-e45df0572f61.json"

_SHEET: gspread.Spreadsheet | None = None


def _get_sheet() -> gspread.Spreadsheet:
    global _SHEET
    if _SHEET:
        return _SHEET
    if not _KEY_PATH.exists():
        raise FileNotFoundError(f"Google key not found: {_KEY_PATH}")
    creds = ServiceAccountCredentials.from_json_keyfile_name(str(_KEY_PATH), SCOPE)
    client = gspread.authorize(creds)
    _SHEET = client.open("Zlata Users")
    return _SHEET


def _ensure_worksheet(spreadsheet: gspread.Spreadsheet, title: str, headers: list[str]):
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
        ws.append_row(headers)
    return ws


def sync_users():
    """Sync users table to Google Sheets."""
    try:
        sheet = _get_sheet()
    except Exception as e:
        logging.error(f"Sheets sync failed (users): {e}")
        return

    conn = get_connection()
    rows = conn.execute(
        "SELECT user_id, name, zodiac_sign, birth_date, birth_city, "
        "subscription_status, subscription_end, created_at, is_deleted "
        "FROM users ORDER BY user_id"
    ).fetchall()
    conn.close()

    ws = _ensure_worksheet(sheet, "users", [
        "user_id", "name", "zodiac_sign", "birth_date", "birth_city",
        "subscription", "subscription_end", "created_at", "is_deleted",
    ])
    ws.batch_clear(["A2:I2000"])
    data = [[
        r["user_id"], r["name"] or "", r["zodiac_sign"] or "", r["birth_date"] or "", r["birth_city"] or "",
        r["subscription_status"] or "free", r["subscription_end"] or "", r["created_at"] or "", r["is_deleted"] or 0,
    ] for r in rows]
    if data:
        ws.update(f"A2:I{len(data)+1}", data)
    logging.info(f"Sheets: synced {len(data)} users")


def sync_readings():
    """Sync readings table to Google Sheets."""
    try:
        sheet = _get_sheet()
    except Exception as e:
        logging.error(f"Sheets sync failed (readings): {e}")
        return

    conn = get_connection()
    rows = conn.execute(
        "SELECT id, user_id, type, cards, created_at "
        "FROM readings ORDER BY id DESC LIMIT 500"
    ).fetchall()
    conn.close()

    ws = _ensure_worksheet(sheet, "readings", [
        "id", "user_id", "type", "cards", "created_at",
    ])
    ws.batch_clear(["A2:E2000"])
    data = [[
        r["id"], r["user_id"], r["type"] or "", r["cards"] or "", r["created_at"] or "",
    ] for r in rows]
    if data:
        ws.update(f"A2:E{len(data)+1}", data)
    logging.info(f"Sheets: synced {len(data)} readings")


def sync_all():
    sync_users()
    sync_readings()
