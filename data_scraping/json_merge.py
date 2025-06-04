import json

with open("tds_discourse_posts.json") as f1, open("tds_content_with_images.json") as f2:
    discourse = json.load(f1)
    tds = json.load(f2)

combined_data = discourse + tds

with open("combined_content.json", "w", encoding="utf-8") as f:
    json.dump(combined_data, f, indent=2, ensure_ascii=False)
