import requests
import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path

# --- Config ---
DISCOURSE_T_COOKIE = "fON49Nrql2TWv4w1gmltmJzvtq1vy9TQr4jdl8uPpIxjdjE6mwAHoBTiYALTcGkBwVS7Zz4RdDqvYAUyd9OoQWDWVgc9XnH9iIY3W9xPuh2259V7brByg8IFGXzJFRdPnIhU%2B4jvRdygA6m6Cbwk8%2BWnwEzHCTbKse559UtZ%2FT9qZN4j4pGnpvAT5jdYzv9NKzpS2kswM0gWBURxSSop1ptEa1AufKvn%2B1E%2BqrNUJFKaxDoAyZDVY1kX6nyyiHkKhdAFORMNUTBeYD9J%2BVkZMTn%2FZ280NCpcVGtJVKzlYQL2ERL%2BTyrXL5q%2BEzCmRafS--L9eeQ2uVgekO9chA--kvx9yARmN4oFKCTnp3%2BRpA%3D%3D"
BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
CATEGORY_SLUG = "courses/tds-kb"
CATEGORY_ID = 34
RAW_DATA_DIR = Path("data/raw/discourse_content/raw_jsons")
FAILED_LOG = Path("logs/failed_posts_download.txt")
ERROR_LOG = Path("logs/errors.log")

START_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)
END_DATE = datetime(2025, 4, 15, tzinfo=timezone.utc)
MAX_PAGES = 7
DELAY_SECONDS = 3
COOLDOWN_EVERY = 20
COOLDOWN_SECONDS = 10

# --- Setup ---
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
FAILED_LOG.parent.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.cookies.set("_t", DISCOURSE_T_COOKIE, domain="discourse.onlinedegree.iitm.ac.in")
session.headers.update({"User-Agent": "Mozilla/5.0"})

def log_error(msg):
    with open(ERROR_LOG, "a") as f:
        f.write(msg + "\n")

def log_failed(post_id):
    with open(FAILED_LOG, "a") as f:
        url = f"https://discourse.onlinedegree.iitm.ac.in/posts/{post_id}.json"
        f.write(url + "\n")

def fetch_topics():
    topics = []
    for page in range(1, MAX_PAGES + 1):
        url = f"{BASE_URL}/c/{CATEGORY_SLUG}/{CATEGORY_ID}.json?page={page}"
        print(f"🔍 Fetching category page {page}...")
        try:
            resp = session.get(url)
            if resp.status_code != 200:
                print(f"  ❌ Failed page {page}")
                break
            for topic in resp.json()["topic_list"]["topics"]:
                created_at = datetime.fromisoformat(topic["created_at"].replace("Z", "+00:00"))
                if START_DATE <= created_at <= END_DATE:
                    topics.append(topic)
        except Exception as e:
            log_error(f"Error loading page {page}: {e}")
            break
    return topics

def get_topic_json(slug, topic_id):
    try:
        url = f"{BASE_URL}/t/{slug}/{topic_id}.json"
        resp = session.get(url)
        if resp.status_code != 200:
            log_error(f"Failed to fetch topic JSON: {url}")
            return None
        return resp.json()
    except Exception as e:
        log_error(f"Exception fetching topic {topic_id}: {e}")
        return None

def get_post_json(post_id):
    try:
        url = f"{BASE_URL}/posts/{post_id}.json"
        resp = session.get(url)
        if resp.status_code != 200:
            log_failed(post_id)
            return None
        return resp.json()
    except Exception as e:
        log_error(f"Error fetching post {post_id}: {e}")
        return None

def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def process_topic(topic):
    topic_id = topic["id"]
    slug = topic["slug"]
    title = topic["title"]
    topic_url = f"{BASE_URL}/t/{slug}/{topic_id}"
    tags = topic.get("tags", [])

    folder = RAW_DATA_DIR / str(topic_id)
    posts_dir = folder / "posts"
    folder.mkdir(parents=True, exist_ok=True)
    posts_dir.mkdir(exist_ok=True)

    meta_path = folder / "topic_meta.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        stream = meta.get("stream", [])
    else:
        topic_data = get_topic_json(slug, topic_id)
        if not topic_data:
            return
        stream = topic_data.get("post_stream", {}).get("stream", [])
        meta = {
            "topic_id": topic_id,
            "title": title,
            "topic_url": topic_url,
            "tags": tags,
            "created_at": topic["created_at"],
            "total_posts": len(stream),
            "stream": stream
        }
        save_json(meta_path, meta)

    for i, post_id in enumerate(stream):
        post_path = posts_dir / f"{post_id}.json"
        if post_path.exists():
            print(f"✅ Already downloaded post {post_id}")
            continue

        if i > 0 and i % COOLDOWN_EVERY == 0:
            print(f"⏳ Cooldown for {COOLDOWN_SECONDS}s after {i} posts...")
            time.sleep(COOLDOWN_SECONDS)

        print(f"⬇️ Downloading post {post_id}...")
        post_data = get_post_json(post_id)
        if post_data:
            save_json(post_path, post_data)
        else:
            print(f"❌ Failed post {post_id}")
        time.sleep(DELAY_SECONDS)

def main():
    print("🚀 Starting raw post download...")
    topics = fetch_topics()
    print(f"✅ {len(topics)} topics found in date range.\n")
    for topic in topics:
        print(f"\n📘 Processing topic {topic['id']} - {topic['title']}")
        process_topic(topic)
    print("\n🏁 All done.")

if __name__ == "__main__":
    main()