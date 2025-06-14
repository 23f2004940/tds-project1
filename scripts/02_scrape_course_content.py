import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

REPO_RAW_URL = "https://raw.githubusercontent.com/sanand0/tools-in-data-science-public/main/"
GITHUB_API_URL = "https://api.github.com/repos/sanand0/tools-in-data-science-public/contents/"
OUTPUT_DIR = "data/raw/course_content"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_root_level_md_files():
    print("Fetching root-level files from GitHub repo...")
    resp = requests.get(GITHUB_API_URL)
    resp.raise_for_status()
    data = resp.json()
    md_files = [f for f in data if f["type"] == "file" and f["name"].endswith(".md")]
    print(f"{len(md_files)} Markdown files found.")
    return md_files

def extract_image_links(markdown):
    image_links = []

    # Markdown style ![alt](url)
    markdown_links = re.findall(r'!\[.*?\]\((.*?)\)', markdown)
    image_links.extend(markdown_links)

    # HTML-style <img src="...">
    soup = BeautifulSoup(markdown, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            image_links.append(src)

    return list(set(image_links))

def mark_image_placeholders(content):
    def replace_md(match):
        url = match.group(1)
        return f"![Image]({url}) "

    def replace_html(match):
        url = match.group(1)
        return f"![Image]({url}) "

    # Markdown-style
    content = re.sub(r'!\[.*?\]\((.*?)\)', replace_md, content)

    # HTML-style
    content = re.sub(r'<img[^>]*src=["\'](.*?)["\'][^>]*>', replace_html, content)

    return content

def slug_from_filename(filename):
    return filename.replace(".md", "")

def enrich_and_save_file(file_meta):
    filename = file_meta["name"]
    url = urljoin(REPO_RAW_URL, filename)
    print(f"Downloading {filename}...")

    resp = requests.get(url)
    resp.raise_for_status()
    content = resp.text

    images = extract_image_links(content)
    slug = slug_from_filename(filename)
    course_url = f"https://tds.s-anand.net/#/{slug}"

    content = mark_image_placeholders(content)

    output_path = os.path.join(OUTPUT_DIR, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# {slug.replace('-', ' ').title()}\n\n")
        f.write(f"**Source URL:** {course_url}\n")
        if images:
            f.write(f"**Images:**\n")
            for img in images:
                f.write(f"- {img}\n")
        else:
            f.write(f"**Images:** None\n")
        f.write("\n---\n\n")
        f.write(content)

    print(f"Saved: {output_path}")

if __name__ == "__main__":
    md_files = get_root_level_md_files()
    for file_meta in md_files:
        enrich_and_save_file(file_meta)

    print("All course content files processed.")
