# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastapi",
#     "pydantic",
#     "openai",
#     "numpy",
#     "scikit-learn",
#     "tiktoken",
#     "uvicorn"
# ]
# ///

import os
import base64
import numpy as np
import tiktoken
from io import BytesIO
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from typing import Optional, List
from sklearn.metrics.pairwise import cosine_similarity
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path


# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Constants
EMBED_MODEL = "text-embedding-3-small"
COMPLETION_MODEL = "gpt-4o"

CAPTION_SYSTEM_PROMPT = (
    "You are an AI assistant helping a Retrieval-Augmented Generation (RAG) system answer questions in the "
    "Tools in Data Science course. The user may include an image along with their question to provide additional context. "
    "These images often contain screenshots of exam questions, assignment instructions, code outputs, browser windows, error messages, "
    "or forum replies.\n\n"
    "Your task is to generate a clear and concise caption that describes what the image shows, so that it can be used for semantic embedding "
    "and retrieval. Focus on visual elements like text, structure, diagrams, or questions visible in the image. "
    "Avoid speculation — just describe exactly what is visible. The caption will be combined with the student’s question to help an AI model understand and answer it accurately."
)

ANSWER_SYSTEM_PROMPT = (
    "You are a helpful virtual teaching assistant for the 'Tools for Data Science' course at IITM.\n\n"
    "**RULES:**\n"
    "1. If the user provides an image, it is the highest source of truth.\n"
    "2. If any context chunk is marked with [[[ PRIMARY CONTEXT DOCUMENT ]]], use it as the next most authoritative source.\n"
    "3. Quote numbers, scores, or phrases **exactly as written** in the context. Do not infer or rewrite them.\n"
    "4. Be concise: answer in 3–6 sentences in markdown format.\n"
    "5. Do NOT guess. If the context doesn't directly answer the question, say:\n"
    "   'The answer is not available in the provided course or forum content.'\n"
    "6. Always include source links:\n"
    "   - For course: use 'source_url'\n"
    "   - For Discourse forum: include both 'topic_url' and 'post_url'"
)

ENCODER = tiktoken.encoding_for_model(EMBED_MODEL)

CHUNKS_PATH = Path(__file__).parent.parent / "data" / "chunks.npz"
archive = np.load(CHUNKS_PATH, allow_pickle=True)
embeddings = archive["embeddings"]
metadata = [m for m in archive["metadata"].tolist() if m]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str
    image: Optional[str] = None

def caption_image(base64_str: str) -> str:
    data_uri = "data:image/png;base64," + base64_str
    response = client.chat.completions.create(
        model=COMPLETION_MODEL,
        messages=[
            {"role": "system", "content": CAPTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_uri}}
                ]
            }
        ],
        max_tokens=100
    )
    return response.choices[0].message.content.strip()

def embed_text(text: str) -> List[float]:
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return response.data[0].embedding

def retrieve_top_chunks(query_embedding: List[float], top_k: int = 5):
    sims = cosine_similarity([query_embedding], embeddings)[0]
    top_indices = sims.argsort()[::-1][:top_k]

    results = []
    seen_replies = set()

    primary_chunk = metadata[top_indices[0]]
    primary_replies = set(primary_chunk.get("replies", []))

    print(f"\n🔎 Top match post_id: {primary_chunk.get('post_id')} → replies: {primary_replies}")

    for idx in top_indices:
        base = metadata[idx]
        if not base:
            continue
        results.append({"text": base["text"], "is_primary": False, **base})

    for meta in metadata:
        if meta and meta.get("post_id") in primary_replies and meta.get("text"):
            if meta["post_id"] not in seen_replies:
                print(f"✅ Marking PRIMARY CONTEXT from reply post_id={meta['post_id']}")
                results.append({"text": meta["text"], "is_primary": True, **meta})
                seen_replies.add(meta["post_id"])

    return results

def truncate_context(chunks: List[dict], max_tokens: int = 4000):
    selected = []
    total = 0
    for chunk in chunks:
        tokens = len(ENCODER.encode(chunk["text"]))
        if total + tokens > max_tokens:
            break
        selected.append(chunk)
        total += tokens
    return selected

def extract_links(context_chunks: List[dict]):
    links = []
    seen = set()
    for chunk in context_chunks:
        if chunk["source"] == "course":
            url = chunk.get("source_url")
            if url and url not in seen:
                links.append({"url": url, "text": "Course content"})
                seen.add(url)
        elif chunk["source"] == "discourse":
            turl = chunk.get("topic_url")
            purl = chunk.get("post_url")
            if turl and turl not in seen:
                links.append({"url": turl, "text": "Discourse topic"})
                seen.add(turl)
            if purl and purl not in seen:
                links.append({"url": purl, "text": "Discourse post"})
                seen.add(purl)
    return links

@app.post("/api")
async def ask(request: QueryRequest):
    caption = caption_image(request.image) if request.image else ""
    full_query = f"{request.question.strip()} {caption}".strip()
    query_embedding = embed_text(full_query)
    top_chunks = retrieve_top_chunks(query_embedding)

    if not top_chunks:
        return {
            "answer": "The answer is not available in the provided course or forum content.",
            "links": []
        }

    top_chunks = truncate_context(top_chunks)

    # Log all context chunks sent to GPT (preview only)
    print("\n📦 Final context chunks sent to GPT (console preview only):")
    for i, c in enumerate(top_chunks):
        token_len = len(ENCODER.encode(c["text"]))
        label = "PRIMARY" if c.get("is_primary") else "OTHER"
        preview = c["text"][:500].replace("\n", " ")
        print(f"\n--- Chunk {i+1} [{label}] ({token_len} tokens) ---")
        print(preview)

    # Full context for GPT input
    context_text = "\n\n".join(
        [f"[[[ PRIMARY CONTEXT DOCUMENT ]]]\n{c['text']}" if c.get("is_primary") else c["text"] for c in top_chunks]
    )

    messages = [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        {"role": "user", "content": f"{context_text}\n\nQuestion: {request.question}\n\n{caption}"}
    ]

    response = client.chat.completions.create(
        model=COMPLETION_MODEL,
        messages=messages,
        max_tokens=500,
        temperature=0
    )
    answer = response.choices[0].message.content.strip()
    links = extract_links(top_chunks)

    return {
        "answer": answer,
        "links": links
    }