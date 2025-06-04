import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json

# Paste your _t cookie value here (from browser after login)
DISCOURSE_COOKIE = "macSNAGJqO0WM8BqHjSMKenN30gp1NSbwudPLZ7oNYVc0EnrAnN3MFMF6yVRKAFGbWzTLAJtaTqaThI4rRjKTMg2nvuOoDLp2cS%2B2tpzGb3PeI4XVNQuELBThYbe9RCxcClFUfX8oH7HTqFT4asqV1M%2F9MS90ONUE7Fvb3sJUsbdN6vlsDKglwwny0GEiuoPNaUXXemN7FnrftBY9dxH2V8TD%2F%2FyEFMICL%2FV4Ijd8lu2sjs7TLLoWXQ7oikvWLBGWzK9kENEXZbHZGn%2BnR1IM%2FJYWH1sTdlcc5m35BGneAPM7g0qhEnYf%2FMfTS6oPJhp--0c1UiUmdPlOTbo2U--LZQNIahnrxJfDtaEVUXulQ%3D%3D"

# Set up session with cookie
session = requests.Session()
session.cookies.set("_t", DISCOURSE_COOKIE, domain="discourse.onlinedegree.iitm.ac.in")

BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
CATEGORY_ID = 34
CATEGORY_SLUG = "courses/tds-kb"

all_posts = []

# Get topic list from category (20 pages max)
for page in range(20):
    url = f"{BASE_URL}/c/{CATEGORY_SLUG}/{CATEGORY_ID}.json?page={page}"
    res = session.get(url)
    if res.status_code != 200:
        break
    topics = res.json().get("topic_list", {}).get("topics", [])
    if not topics:
        break

    for topic in topics:
        # Skip if before 2025
        created = topic["created_at"].replace("Z", "+00:00")
        created_at = datetime.fromisoformat(created)
        if created_at < datetime(2025, 1, 1, tzinfo=timezone.utc):
            continue

        topic_id = topic["id"]
        post_url = f"{BASE_URL}/t/{topic_id}.json"
        r = session.get(post_url)
        if r.status_code != 200:
            continue

        for post in r.json()["post_stream"]["posts"]:
            text = BeautifulSoup(post["cooked"], "html.parser").get_text()
            all_posts.append({
                "username": post["username"],
                "created_at": post["created_at"],
                "content": text,
                "post_url": f"{BASE_URL}/t/{topic_id}/{post['post_number']}"
            })

# Save to JSON
with open("tds_discourse_posts.json", "w", encoding="utf-8") as f:
    json.dump(all_posts, f, indent=2, ensure_ascii=False)

print(f"Done! Scraped {len(all_posts)} posts.")
