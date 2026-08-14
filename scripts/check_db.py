import sqlite3
conn = sqlite3.connect("/data/platform.db")
print("Integrity:", conn.execute("PRAGMA integrity_check").fetchall())
print("Tables:", conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
for t in ["prompts", "agents", "skills", "conversations"]:
    try:
        c = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
        print(f"{t}: {c[0]} rows")
    except Exception as e:
        print(f"{t}: ERROR - {e}")
conn.close()
