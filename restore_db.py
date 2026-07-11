import sqlite3

conn = sqlite3.connect("data/zlatabot.db")
with open("restore_users.sql") as f:
    conn.executescript(f.read())
conn.commit()
conn.close()
print("Users restored successfully")
