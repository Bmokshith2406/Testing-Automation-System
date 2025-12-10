# Intelligent Playwright Python Methods Search Platform – Modular Edition

## Overview

This project is a production-grade backend platform for uploading, enriching, indexing, and semantically searching **Python Playwright automation methods** using:

- FastAPI for APIs  
- MongoDB Atlas for persistence and vector search  
- SentenceTransformers (`all-MiniLM-L6-v2`) for embeddings  
- Google Gemini for MADL enrichment, query expansion, and reranking  
- JWT authentication with role-based access  
- Advanced ranking heuristics with A/B experimentation  
- Search caching  
- Audit logging and metrics  

This refactor modularizes the original monolithic application into clean service layers for easier debugging, scaling, and experimentation.

---

## Project Structure

```

app/
├── main.py                # App startup and lifespan orchestration
│
├── core/                  # Global configuration and security
│   ├── config.py          # Environment config and constants
│   ├── logging.py         # Structured logging
│   ├── cache.py           # In-memory query caching
│   ├── security.py        # JWT and password hashing
│   └── analytics.py      # Audit logging
│
├── db/
│   └── mongo.py           # MongoDB connection + helpers
│
├── models/
│   ├── schemas.py         # Pydantic DTO schemas
│   └── users.py           # Mongo user CRUD helpers
│
├── services/
│   ├── embeddings.py     # SentenceTransformer lifecycle + vector utilities
│   ├── keywords.py       # Keyword extraction & fallback summaries
│   ├── expansion.py      # Gemini query normalization & expansion
│   ├── rerank.py         # Gemini reranking
│   ├── ranking.py        # Multi-signal candidate scoring + A/B logic
│   ├── method_madl.py    # Playwright method-to-MADL enrichment
│   ├── dedupe_summary.py # Gemini dedupe-summary generator
│   └── dedupe_verifier.py# Duplicate detection logic
│
├── routes/
│   ├── auth.py            # Login / Register APIs
│   ├── upload.py          # CSV/XLSX ingestion + MADL + embeddings
│   ├── search.py          # Hybrid vector + heuristic ranking APIs
│   ├── update.py          # Method updates + reprocessing
│   └── admin.py           # Admin maintenance + metrics APIs
│
└── middleware/            # Optional global middleware (future use)

````

---

## Setup & Installation

### 1. Python Version

Python 3.10+

---

### 2. Clone & Setup Virtual Environment

```bash
git clone <your-repository>
cd <your-repository>

python -m venv .venv
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate       # Windows
````

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Required Packages

Your `requirements.txt` should include:

```
fastapi
uvicorn
motor
pymongo
sentence-transformers
numpy
pandas
python-dotenv
python-jose
passlib[bcrypt]==1.7.4
bcrypt==3.2.2
openpyxl
google-generativeai
python-multipart
```

---

## Environment Variables

Create a `.env` file:

```
GOOGLE_API_KEY=your-google-api-key
MONGO_CONNECTION_STRING=your-mongodb-uri
JWT_SECRET_KEY=change-me-in-prod
```

---

## MongoDB Requirements

Create a **Vector Search Index** on the `main_vector` field:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "main_vector",
      "numDimensions": 384,
      "similarity": "cosine",
      "quantization": "none"
    }
  ]
}
```

Index name must be:

```
vector_index
```

---

## Running the App

Start the backend:

```bash
uvicorn app.main:app --reload
```

API Endpoint:

```
http://localhost:8000
```

Swagger Docs:

```
http://localhost:8000/docs
```

---

## Authentication & Roles

### Create Account

```
POST /auth/register
```

```json
{
  "username": "admin",
  "password": "test123",
  "role": "admin"
}
```

---

### Login

```
POST /auth/login
```

Returns JWT:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

---

### Use Token

Include in request headers:

```
Authorization: Bearer YOUR_TOKEN
```

---

### Role Permissions

| Role   | Allowed Actions                           |
| ------ | ----------------------------------------- |
| viewer | Search only                               |
| editor | Upload, update, delete individual methods |
| admin  | Full access, delete-all, metrics          |

---

## Uploading Playwright Python Methods

```
POST /api/upload
```

Authentication required: `editor` or `admin`

Accepted file formats:

* `.csv`
* `.xlsx`

Required column:

```
Raw Method
```

Each row must contain a valid **Python Playwright method** source block.

### Processing Flow

1. Duplicate detection via Gemini (summary + vector similarity)
2. MADL generation using Gemini
3. SentenceTransformer embedding
4. Multi-vector creation and indexing
5. MongoDB insertion

---

## Searching Methods

```
POST /api/search
```

```json
{
  "query": "click login button",
  "ranking_variant": "B"
}
```

---

## Search Pipeline

```
User Query
   ↓
Sentence Embedding
   ↓
MongoDB $vectorSearch
   ↓
Local multi-signal ranker
   ↓
(Gemini reranking optional)
   ↓
Final TOP-K results
```

---

## Ranking Signals

### Variant A – Baseline

```
0.60 * Vector similarity
0.25 * Semantic cosine similarity
+ Token match boosts
```

---

### Variant B – Enhanced

```
0.45 * Vector similarity
0.20 * Semantic similarity
0.12 * Keyword overlap
0.05 * Token density
0.05 * Popularity weighting
```

Set via:

```
"ranking_variant": "A" | "B"
```

---

## Updating Methods

```
PUT /api/update/{doc_id}
```

Partial MADL updates supported:

```json
{
  "summary": "New description of method",
  "keywords": ["click", "login", "wait"]
}
```

Automatically triggers:

* Vector regeneration
* MADL re-indexing
* Main-vector recomputation

---

## Admin APIs

### Fetch All Methods

```
GET /api/get-all-methods
```

---

### Delete All Methods

```
POST /api/delete-all?confirm=true
```

Admin only.

---

### Delete Single Method

```
DELETE /api/method/{id}
```

---

### Metrics

```
GET /api/metrics
```

Response:

```json
{
  "queries_today": 281,
  "top_methods": ["login_user()", "click_submit()"]
}
```

---

## Audit Logging

Every search request logs:

* Timestamp
* Endpoint
* User
* Request payload
* Ranking variant
* Result count

Stored in:

```
api_audit_logs
```

### Why Audit Logging Matters

* Query trend analysis
* Ranking quality evaluation
* Popular automation workflow discovery
* Search relevance tuning

---

## Development Workflow

### Ranking Logic

```
app/services/ranking.py
```

---

### LLM Strategies

```
app/services/expansion.py
app/services/rerank.py
```

---

### Schema & DTO Updates

```
app/models/schemas.py
```

---

### Route Wiring Only

```
app/routes/
```


