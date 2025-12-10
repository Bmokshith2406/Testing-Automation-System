```markdown
# Intelligent Script Methods Search Platform – Modular Edition

## Overview

This project is a production-grade backend platform for uploading, enriching, indexing, deduplicating, and semantically searching **Selenium JavaScript (WebDriverJS) automation methods** using:

- FastAPI for APIs  
- MongoDB Atlas for persistence & vector search  
- SentenceTransformers (`all-MiniLM-L6-v2`) for embeddings  
- Google Gemini for MADL generation, query normalization, expansion, deduplication, and reranking  
- JWT Authentication with role-based access control  
- Advanced ranking heuristics with A/B scoring variants  
- Search caching for performance  
- Audit logging + operational metrics  

The platform ingests raw **JavaScript Selenium automation methods**, converts them into rich **MADL metadata**, computes embeddings, stores them in MongoDB, and enables highly-relevant semantic search with optional LLM reranking.

This modular refactor replaces earlier monolithic logic with clean service layers for easier scaling, debugging, and experimentation.

---

## Project Structure

```

app/
├── main.py                # App startup + lifespan orchestration
│
├── core/                  # Global configuration & utilities
│   ├── config.py          # Env settings + constants + LLM prompts
│   ├── logging.py         # Structured logging
│   ├── cache.py           # In-memory search caching
│   ├── security.py        # JWT authentication + password hashing
│   └── analytics.py      # API audit logging
│
├── db/
│   └── mongo.py           # MongoDB connection management & helpers
│
├── models/
│   ├── schemas.py         # Pydantic request/response DTO schemas
│   └── users.py           # MongoDB user CRUD helpers
│
├── services/
│   ├── embeddings.py     # SentenceTransformer lifecycle + encoding
│   ├── keywords.py       # Keyword extraction + fallback summarization
│   ├── expansion.py      # Gemini query normalization + expansion
│   ├── finalRanking.py   # Gemini TOP-K reranking with confidence scores
│   ├── ranking.py        # Multi-signal scoring (A/B variants)
│   ├── rerank.py         # Gemini fast rerank helper
│   ├── method_madl.py    # RAW JS method → MADL conversion via Gemini
│   ├── dedupe_summary.py # 12-word dedupe summary generator (Gemini)
│   ├── dedupe_search_helper.py # Vector lookup for dedupe candidates
│   ├── dedupe_verifier.py # LLM duplicate verification
│   └── gemini_semaphore.py # Global Gemini concurrency control
│
├── routes/
│   ├── auth.py            # Login & registration APIs
│   ├── upload.py          # CSV / XLSX ingestion + MADL + embeddings
│   ├── search.py          # Vector + heuristic + Gemini rerank search
│   ├── update.py          # MADL updates + embedding rebuild
│   └── admin.py           # Admin methods + metrics APIs
│
└── middleware/            # Reserved for future global middleware

````

---

## ⚙️ Setup & Installation

### 1. Python Version
Python **3.10+**

---

### 2. Clone & Setup Virtual Environment

```bash
git clone <your-repository>
cd <your-repository>

python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
````

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### Required Packages

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

## MongoDB Setup (Vector Search)

Create a MongoDB Atlas **Vector Search Index** on the `main_vector` field:

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

**Index name (must match config):**

```
vector_index
```

---

## ▶Running the Application

Start the API server:

```bash
uvicorn app.main:app --reload
```

### API Base URL

```
http://localhost:8000
```

### Interactive Docs (Swagger)

```
http://localhost:8000/docs
```

---

## Authentication & User Roles

### Register

`POST /auth/register`

```json
{
  "username": "admin",
  "password": "test123",
  "role": "admin"
}
```

---

### Login

`POST /auth/login`
(Form-encoded)

Returns JWT token:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

---

### Use Token

Add to request headers:

```
Authorization: Bearer YOUR_TOKEN
```

---

### Role Permissions

| Role   | Permissions                                               |
| ------ | --------------------------------------------------------- |
| viewer | Search only                                               |
| editor | Upload methods, update methods, delete individual methods |
| admin  | Full access + delete-all + metrics                        |

---

## Uploading Selenium JavaScript Methods

`POST /api/upload-methods`

**Role:** `editor` or `admin`

### Supported file formats

* `.csv`
* `.xlsx`

### Required Column

```
Raw Method
```

This column must contain **raw Selenium JavaScript (WebDriverJS) function code**.

---

### Processing Pipeline

**Per method:**

1. Gemini generates a **12-word dedupe summary**
2. Vector search checks for duplicates
3. LLM duplicate verification
4. If unique → MADL metadata generation via Gemini
5. Keyword extraction
6. SentenceTransformer embeddings:

   * Summary embedding
   * Raw JS code embedding
   * Full MADL embedding
   * Main vector (`summary + raw method`)
7. MongoDB insert with vectors & metadata

---

## Searching Selenium Methods

`POST /api/search`

Example payload:

```json
{
  "query": "login using username and password",
  "ranking_variant": "B"
}
```

---

### Search Pipeline

```
User Query
   ↓
Gemini query normalization
   ↓
Optional Gemini query expansion
   ↓
SentenceTransformer embedding
   ↓
MongoDB $vectorSearch
   ↓
Local multi-signal scoring
   ↓
(Gemini optional rerank + confidence scoring)
   ↓
Final TOP-K method results
```

---

### Scoring Variants

#### Ranking A — Baseline

```
0.60 × Mongo vector similarity
0.25 × Semantic similarity
+ Token match boosts
```

#### Ranking B — Enhanced

```
0.45 × Mongo vector similarity
0.20 × Semantic similarity
0.12 × Keyword overlap
0.05 × Token density
0.05 × Popularity weighting
```

Select variant using:

```json
"ranking_variant": "A" | "B"
```

---

## Updating Existing Methods

`PUT /api/update/{doc_id}`

Allows partial updates to MADL fields:

```json
{
  "summary": "Updated summary",
  "intent": "Updated intent",
  "keywords": ["login", "auth", "selenium"]
}
```

### Automatic actions

* Rebuild embeddings if any MADL field changed
* Recalculate main vector
* Replace MongoDB document

---

## Admin APIs

### Get all methods

`GET /api/get-all-methods`

---

### Delete ALL methods

`POST /api/delete-all?confirm=true`

**Admin only**

---

### Delete single method

`DELETE /api/method/{id}`

---

### Metrics

`GET /api/metrics`

Returns:

```json
{
  "queries_today": 281,
  "top_methods": [
    "loginUser()",
    "submitCheckoutForm()",
    "searchProduct()"
  ]
}
```

---

## Audit Logging

Every search call records:

* Timestamp
* Endpoint
* User info
* Query payload
* Ranking variant
* Result count

Stored in MongoDB collection:

```
api_audit_logs
```

---

### Why this matters

Enables:

* Ranking quality monitoring
* LLM strategy experimentation feedback
* Popular automation workflow discovery
* Search UX improvement insights

---

## Development Workflow

Recommended iteration flow:

### Ranking experimentation

```
app/services/ranking.py
```

### LLM prompt tuning & re-ranking

```
app/services/expansion.py
app/services/rerank.py
app/services/finalRanking.py
```

### MADL schema & metadata changes

```
app/services/method_madl.py
app/models/schemas.py
```

### API routing only

```
app/routes/
```

---

