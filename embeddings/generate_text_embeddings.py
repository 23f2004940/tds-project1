# File: data_scraping/generate_text_embeddings.py

import json
import os
import sys
from openai import OpenAI

if len(sys.argv) < 2:
    print("Usage: python generate_text_embeddings.py <input_json_path>")
    sys.exit(1)

input_path = sys.argv[1]
output_path = input_path.replace(".json", "_embedded.json")

# Load OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Load JSON content
with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Generating embeddings for {len(data)} entries in {input_path}")

# Generate embeddings (one at a time)
for i, item in enumerate(data):
    if "content" not in item or not item["content"].strip():
        print(f"kipping item {i} — no content")
        continue

    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=item["content"]
        )
        item["embedding"] = response.data[0].embedding
        if i % 10 == 0:
            print(f" Embedded {i + 1}/{len(data)}")
    except Exception as e:
        print(f"Error on item {i}: {e}")

# Save with embeddings
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Embeddings saved to {output_path}")
