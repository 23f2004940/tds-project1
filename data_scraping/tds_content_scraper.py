import requests
import re
import os
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Constants
BASE_ROUTE = "https://tds.s-anand.net/#/"
RAW_MD_BASE = "https://tds.s-anand.net/"
SIDEBAR_URL = "https://tds.s-anand.net/2025-01/_sidebar.md"

# Step 1: Download the sidebar
sidebar_md = requests.get(SIDEBAR_URL).text

# Step 2: Extract all .md file paths from the sidebar
md_links = re.findall(r'\(([^)]+\.md)\)', sidebar_md)

# Step 3: Convert to actual URLs
md_entries = []
for link in md_links:
    clean_path = link.replace("../", "")
    raw_md_url = urljoin(RAW_MD_BASE, clean_path)
    page_name = clean_path.replace(".md", "").replace("/", "_")
    md_entries.append((page_name, raw_md_url))

# Step 4: Download content and extract text + images
scraped_pages = []

for page_name, url in md_entries:
    try:
        res = requests.get(url)
        if res.status_code != 200:
            continue

        markdown = res.text

        # Extract images from markdown format ![alt](url)
        image_matches = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', markdown)
        images = [
            {"alt": alt.strip(), "url": urljoin(RAW_MD_BASE, src.strip())}
            for alt, src in image_matches
        ]

        # Convert to plain text using BeautifulSoup (optional fallback for .md syntax)
        text_content = BeautifulSoup(markdown, "html.parser").get_text()

        scraped_pages.append({
            "source": f"tds/{page_name}",
            "url": url,
            "content": text_content.strip(),
            "images": images
        })

    except Exception as e:
        print(f"Failed to fetch {url}: {e}")

# Step 5: Save output
with open("tds_content_with_images.json", "w", encoding="utf-8") as f:
    json.dump(scraped_pages, f, indent=2, ensure_ascii=False)

print(f"Scraped {len(scraped_pages)} pages with images")
