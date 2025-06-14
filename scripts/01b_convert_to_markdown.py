import json
from pathlib import Path
from bs4 import BeautifulSoup
import traceback

# --- Paths ---
RAW_BASE = Path("data/raw/new_data")
CONVERTED_DIR = RAW_BASE / "converted"
LOG_FILE = Path("logs/markdown_errors.log")

CONVERTED_DIR.mkdir(parents=True, exist_ok=True)

def log_error(message):
    with open(LOG_FILE, "a") as f:
        f.write(message + "\n")

def extract_text_with_images(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)

    valid_imgs = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "/user_avatar/" in src or "emoji.discourse-cdn.com" in src:
            continue
        valid_imgs.append(f"![Image]({src})")

    if valid_imgs:
        text += "\n" + "\n".join(valid_imgs)

    return text

def convert_topic(topic_dir: Path):
    try:
        topic_meta_path = topic_dir / "topic_meta.json"
        posts_dir = topic_dir / "posts"
        output_md = CONVERTED_DIR / f"{topic_dir.name}.md"

        if output_md.exists():
            print(f"⏭️ Already exists: {output_md.name}")
            return

        with open(topic_meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # Build post_number → post_id and reverse
        post_number_to_id = {}
        reply_graph = {}

        all_posts = {}
        for post_id in meta["stream"]:
            post_path = posts_dir / f"{post_id}.json"
            if not post_path.exists():
                log_error(f"Missing post JSON: {post_path}")
                continue
            with open(post_path, "r", encoding="utf-8") as f:
                post = json.load(f)
            all_posts[post_id] = post
            post_number_to_id[post["post_number"]] = post_id

        # Build reply graph
        for post_id, post in all_posts.items():
            reply_to = post.get("reply_to_post_number")
            if reply_to is not None:
                parent_id = post_number_to_id.get(reply_to)
                if parent_id:
                    reply_graph.setdefault(parent_id, []).append(post_id)

        # Start writing markdown
        lines = [
            f"# {meta['title']}",
            f"**Topic ID:** {meta['topic_id']}",
            f"**Created At:** {meta['created_at']}",
            f"**Topic URL:** {meta['topic_url']}",
            f"**Tags:** {', '.join(meta['tags']) if meta['tags'] else 'None'}",
            f"**Total Posts:** {meta['total_posts']}",
            ""
        ]

        for post_id in meta["stream"]:
            post = all_posts.get(post_id)
            if not post:
                continue

            post_url = post.get("post_url", "")
            post_number = post["post_number"]
            username = post["username"]
            created = post["created_at"]
            text = extract_text_with_images(post["cooked"])
            full_url = f"https://discourse.onlinedegree.iitm.ac.in{post_url}"
            replies = reply_graph.get(post_id, [])

            lines.extend([
                f"### Post #{post_number} by {username} on {created}",
                f"**Post ID:** {post_id}",
                f"**Post URL:** {full_url}",
                f"**Replies:** {replies}",
                "",
                text,
                "\n---\n"
            ])

        with open(output_md, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"✅ Wrote: {output_md.name}")

    except Exception as e:
        log_error(f"[{topic_dir.name}] {e}")
        log_error(traceback.format_exc())

def main():
    print("🛠️ Converting topics to markdown...")
    for topic_dir in RAW_BASE.iterdir():
        if topic_dir.is_dir() and (topic_dir / "topic_meta.json").exists():
            convert_topic(topic_dir)

    print("\n🏁 Markdown generation complete.")

if __name__ == "__main__":
    main()