import os
import re
import requests
from pathlib import Path
from io import BytesIO
import openai

# ========== CONFIGURATION ==========
INPUT_DIR = "data/raw/course_content"
MODEL = "gpt-4o"  # or "gpt-4-vision-preview"

SYSTEM_PROMPT = (
    "You are an AI assistant helping prepare educational content for a Retrieval-Augmented Generation (RAG) system "
    "used in the Tools in Data Science course. Each image is part of lecture notes, assignments, or examples. "
    "Generate a clear and informative caption that accurately describes the content of the image, "
    "so that it can be used for semantic search and retrieval. Your caption should help both students and AI systems "
    "understand what the image represents, whether it's code, graphs, dashboards, error messages, or tables."
)

# ========== OPENAI CLIENT ==========
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ========== FUNCTIONS ==========

def extract_images_to_caption(md_text):
    # Match: ![Image](URL) 
    pattern = r'!\[Image\]\((.*?)\) '
    return re.findall(pattern, md_text)

def replace_placeholder_with_caption(md_text, image_url, caption):
    # Escape URL for safe regex replacement
    escaped_url = re.escape(image_url)
    pattern = rf'!\[Image\]\({escaped_url}\) '
    replacement = f'![Image]({image_url}) <!-- Caption: "{caption}" -->'
    return re.sub(pattern, replacement, md_text, count=1)

def generate_caption(image_url):
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]}
            ],
            max_tokens=100
        )
        caption = response.choices[0].message.content.strip()
        return caption
    except Exception as e:
        print(f"Failed to caption {image_url}: {e}")
        return None

def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    image_urls = extract_images_to_caption(content)
    if not image_urls:
        return

    print(f"\nProcessing {filepath.name} - {len(image_urls)} image(s)")
    modified = False

    for image_url in image_urls:
        print(f"→ Captioning: {image_url}")
        caption = generate_caption(image_url)
        if caption:
            content = replace_placeholder_with_caption(content, image_url, caption)
            modified = True
            print(f"   ✔ Caption: {caption}")
        else:
            print(f"   ✖ Skipped due to error.")

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✔ Updated {filepath.name}")
    else:
        print(f"No changes made to {filepath.name}")

# ========== MAIN ==========

if __name__ == "__main__":
    files = list(Path(INPUT_DIR).glob("*.md"))
    for file_path in files:
        process_file(file_path)

    print("\n✅ All course content images processed.")