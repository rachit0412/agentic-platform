import sqlite3

conn = sqlite3.connect("/data/platform.db")
tables = [
    t[0]
    for t in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
]
print("Tables:", tables)
for t in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
    print(f"  {t}: {count} rows")
    if count > 0 and count < 20:
        cols = [d[0] for d in conn.execute(f"SELECT * FROM [{t}] LIMIT 1").description]
        for row in conn.execute(f"SELECT * FROM [{t}]").fetchall():
            print(f"    {dict(zip(cols, row))}")
conn.close()
