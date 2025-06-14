import os
import re
import shutil
import openai
from pathlib import Path
from tqdm import tqdm

# --- API Key ---
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- Paths ---
input_dir = Path("data/raw/discourse_content/converted_md")
output_dir = Path("data/processed/new_data")
output_dir.mkdir(parents=True, exist_ok=True)

log_path = Path("logs/failed_discourse_captions.txt")
log_path.parent.mkdir(parents=True, exist_ok=True)

# --- Regex pattern for markdown image ---
image_pattern = re.compile(r'!\[Image\]\((.*?)\)')

# --- System prompt ---
caption_prompt = (
    "You are an AI assistant helping prepare educational forum content for a Retrieval-Augmented Generation (RAG) system used in the Tools in Data Science course. "
    "Each image you see comes from a discussion between students and instructors. These images often include dashboards, code screenshots, browser errors, plots, schedules, or student queries. "
    "Generate a clear and detailed caption that accurately describes what the image shows, so that both students and AI systems can semantically understand and retrieve this content later. "
    "Focus on what is visible — such as interface elements, error messages, graphs, or page structure — and avoid speculation. Be concise and informative."
)

def generate_caption(image_url):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": caption_prompt},
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": image_url}}]}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Failed to caption {image_url}: {e}")
        with open(log_path, "a") as f:
            f.write(f"{image_url}  # {str(e)}\n")
        return None

def process_file(md_path):
    content = md_path.read_text(encoding="utf-8")
    matches = list(image_pattern.finditer(content))

    updated_content = content
    updated = False

    for match in matches:
        url = match.group(1)

        if url.lower().endswith(".svg"):
            print(f"⚠️ Skipping SVG: {url}")
            with open(log_path, "a") as f:
                f.write(f"{url}  # Skipped SVG\n")
            continue

        caption = generate_caption(url)
        if caption:
            original_line = match.group(0)
            replacement_line = f"[Image Caption: {caption}]"
            updated_content = updated_content.replace(original_line, replacement_line, 1)
            updated = True

    output_path = output_dir / md_path.name
    if updated:
        output_path.write_text(updated_content, encoding="utf-8")
        print(f"✅ Captioned: {md_path.name}")
    else:
        shutil.copy(md_path, output_path)
        print(f"📄 Copied (no image): {md_path.name}")

if __name__ == "__main__":
    print("🔍 Scanning Discourse markdown files for images to caption...")
    for md_file in tqdm(sorted(input_dir.glob("*.md"))):
        process_file(md_file)
    print("🎉 Captioning complete.")