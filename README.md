# TDS Virtual TA (Tools for Data Science - Jan/Sep 2025)

This is a Retrieval-Augmented Generation (RAG) based virtual assistant built for IITM’s **Tools for Data Science** course.

It allows students to ask questions — with or without images — and returns precise, source-grounded answers based on:
- 📘 Official course content (`tds.s-anand.net`)
- 💬 Discourse forum discussions (Jan 1 – Apr 15, 2025)

---

## 🔧 Features

- ✅ Supports image-based questions.
- ✅ Uses OpenAI GPT-4o for captioning and answering
- ✅ Retrieval powered by OpenAI `text-embedding-3-small` and cosine similarity
- ✅ FastAPI backend deployed on Render
- ✅ Responds with source links (Discourse post/topic or Course content)

---

## 📦 Folder Structure
.
├── main.py # FastAPI app with embedding + answer pipeline
├── chunks.npz # Precomputed embeddings of course+forum content
├── requirements.txt # Python dependencies
├── LICENSE # MIT License
└── README.md # This file

---

## 🧠 Query Pipeline

1. Accepts question (and optional image in base64)  
2. Captions image (if provided)  
3. Embeds question + caption → retrieves top chunks  
4. Fetches direct replies if discourse chunk  
5. Generates answer using GPT-4o with context  
6. Returns answer + list of source URLs  

---

## 🧪 API Usage

### Endpoint

POST /api


### Request

```json
{
  "question": "How is GA4 bonus calculated?",
  "image": null
}
```
### Response

```json
{
  "answer": "If a student scores 10/10 on GA4 and receives a bonus...",
  "links": [
    {
      "url": "https://discourse.onlinedegree.iitm.ac.in/t/...",
      "text": "Discourse post"
    }
  ]
}
```
## Deployment

Deployed to Render

uvicorn main:app --host 0.0.0.0 --port 8000

## Notes

- chunks.npz must be present alongside main.py

- Auto-replies to Discourse-linked posts are included

- Primary replies are tagged for better answer accuracy

- Uses tiktoken for chunk sizing and truncation




