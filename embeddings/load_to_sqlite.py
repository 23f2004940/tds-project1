import sqlite3
import sqlite_vec  # registers the VECTOR extension
import numpy as np
import json
import os
import sys

if len(sys.argv) < 2:
    print("Usage: python load_to_sqlite.py <input_embedded_json_path>")
    sys.exit(1)

INPUT_JSON = sys.argv[1]

# Store DB in same folder as script
script_dir = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(script_dir, "content.sqlite")

# Connect to SQLite
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

# Create vector-enabled table
cur.execute("""
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    source TEXT,
    url TEXT,
    content TEXT,
    embedding VECTOR
)
""")

# Load JSON content
with open(INPUT_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

# Insert rows
inserted = 0
for i, item in enumerate(data):
    if "embedding" not in item or not item["embedding"]:
        print(f"Skipping item {i} — missing embedding")
        continue

    try:
        cur.execute("INSERT INTO documents (source, url, content, embedding) VALUES (?, ?, ?, ?)", (
            item.get("source", "unknown"),
            item.get("url", ""),
            item.get("content", ""),
            np.array(item["embedding"], dtype="float32")
        ))
        inserted += 1
        if inserted % 50 == 0:
            print(f"Inserted {inserted} entries...")
    except Exception as e:
        print(f"Error on item {i}: {e}")

conn.commit()
print(f"Inserted {inserted} total records into {DB_FILE}")
