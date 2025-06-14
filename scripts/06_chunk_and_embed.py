import os
import re
import json
import tiktoken
import openai
import numpy as np
from pathlib import Path
from tqdm import tqdm

openai.api_key = os.getenv("OPENAI_API_KEY")
ENCODER = tiktoken.encoding_for_model("text-embedding-3-small")

MAX_TOKENS = 300
OVERLAP = 75
DATA_DIR = Path("data/processed")
OUTPUT_FILE = Path("chunks.npz")

def num_tokens(text):
    return len(ENCODER.encode(text))

def sliding_window_chunks(text, max_tokens, overlap):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks, current, tokens = [], [], 0

    for sent in sentences:
        sent_tokens = num_tokens(sent)
        if sent_tokens > max_tokens:
            continue

        if tokens + sent_tokens > max_tokens:
            chunk_text = " ".join(current)
            if chunk_text:
                chunks.append(chunk_text)
            current = []
            tokens = 0
            if overlap:
                for back in reversed(sentences[:sentences.index(sent)]):
                    current.insert(0, back)
                    tokens = num_tokens(" ".join(current))
                    if tokens >= overlap:
                        break
        current.append(sent)
        tokens += sent_tokens

    if current:
        chunks.append(" ".join(current))
    return chunks

def extract_source_url(md_text):
    match = re.search(r"\*\*Source URL:\*\*\s*(\S+)", md_text)
    return match.group(1).strip() if match else None

def extract_topic_url(md_text):
    match = re.search(r"\*\*Topic URL:\*\*\s*(\S+)", md_text)
    return match.group(1).strip() if match else None

def extract_post_body(post_md: str):
    lines = post_md.strip().splitlines()
    content_lines = []
    in_body = False

    for line in lines:
        if line.startswith("### Post #"):
            in_body = True
            continue
        if line.startswith("**Post ID:**") or line.startswith("**Post URL:**") or line.startswith("**Replies:**"):
            continue
        if line.strip() == "---":
            continue
        if in_body:
            content_lines.append(line)

    return "\n".join(content_lines).strip()

def process_course_file(filepath):
    content = Path(filepath).read_text()
    source_url = extract_source_url(content)
    body = content.split("---", 1)[-1].strip()
    sections = re.split(r'(?=^#{2,}\s)', body, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if not section:
            continue
        for chunk in sliding_window_chunks(section, MAX_TOKENS, OVERLAP):
            yield {
                "text": chunk,
                "source": "course",
                "source_url": source_url
            }

def process_discourse_file(filepath):
    content = Path(filepath).read_text()
    topic_url = extract_topic_url(content)
    posts = re.split(r'(?=^### Post #)', content, flags=re.MULTILINE)

    for post in posts:
        match_post_id = re.search(r"\*\*Post ID:\*\*\s*(\d+)", post)
        match_url = re.search(r"\*\*Post URL:\*\*\s*(\S+)", post)
        match_replies = re.search(r"\*\*Replies:\*\*\s*\[([0-9,\s]*)\]", post)

        post_id = int(match_post_id.group(1)) if match_post_id else None
        post_url = match_url.group(1).strip() if match_url else None
        replies = [int(i.strip()) for i in match_replies.group(1).split(",") if i.strip()] if match_replies else []

        post_body = extract_post_body(post)
        if not post_body:
            continue

        for chunk in sliding_window_chunks(post_body, MAX_TOKENS, OVERLAP):
            yield {
                "text": chunk,
                "source": "discourse",
                "topic_url": topic_url,
                "post_url": post_url,
                "post_id": post_id,           # ✅ added post_id
                "replies": replies or []
            }

def main():
    all_chunks = []

    for file in sorted((DATA_DIR / "course_content").glob("*.md")):
        all_chunks.extend(process_course_file(file))

    for file in sorted((DATA_DIR / "discourse_content").glob("*.md")):
        all_chunks.extend(process_discourse_file(file))

    embeddings = []
    metadata = []

    for chunk in tqdm(all_chunks, desc="Embedding chunks"):
        try:
            response = openai.embeddings.create(
                model="text-embedding-3-small",
                input=chunk["text"]
            )
            embeddings.append(response.data[0].embedding)

            metadata.append({
                "text": chunk["text"],
                "source": chunk["source"],
                "source_url": chunk.get("source_url"),
                "topic_url": chunk.get("topic_url"),
                "post_url": chunk.get("post_url"),
                "post_id": chunk.get("post_id"),      # ✅ persist post_id
                "replies": chunk.get("replies", [])
            })

        except Exception as e:
            print(f"❌ Failed to embed chunk: {e}")
            print(f"→ Skipped text: {chunk['text'][:100]}...")

    np.savez_compressed(OUTPUT_FILE, embeddings=np.array(embeddings), metadata=np.array(metadata, dtype=object))
    print(f"\n✅ Saved {len(embeddings)} embeddings to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()