# 🧠 Intelligent Test Case Search Platform – Modular Edition  
### TestCases-RAG Version 2.0

---

## 🔍 Overview

This project is a **production-grade backend platform** for uploading, enriching, indexing, and semantically searching software test cases using:

✅ **FastAPI** – REST APIs  
✅ **MongoDB Atlas** – persistence & vector search  
✅ **SentenceTransformers (all-MiniLM-L6-v2)** – embeddings  
✅ **Google Gemini** – enrichment, query expansion, re-ranking  
✅ **JWT Authentication** – role-based access control  
✅ **Advanced ranking heuristics + A/B testing**  
✅ **Search caching**  
✅ **Audit logging + metrics**

This refactor modularizes the original single-file app into clean layers for easier debugging, scaling, and experimentation workflows.

---

## 📂 Project Structure

```

app/
├── main.py                # App startup + lifespan orchestration
│
├── core/                  # Global configuration & security
│   ├── config.py          # Env + constants
│   ├── logging.py         # Structured logging
│   ├── cache.py           # In-memory query caching
│   ├── security.py        # JWT + password hashing
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
│   ├── embeddings.py     # SentenceTransformer lifecycle + batching
│   ├── keywords.py       # Keyword extraction & fallback summaries
│   ├── enrichment.py     # Gemini test-case enrichment
│   ├── expansion.py      # Gemini query expansion
│   ├── rerank.py          # Gemini reranking
│   └── ranking.py         # Multi-signal scoring + A/B logic
│
├── routes/
│   ├── auth.py            # Login / Register APIs
│   ├── upload.py          # CSV/XLSX ingestion + enrichment + embeddings
│   ├── search.py          # Hybrid vector + heuristic ranking search
│   ├── update.py          # Test case updates + reprocessing
│   └── admin.py           # Admin maintenance + metrics APIs
│
└── middleware/            # Optional global middleware (future work)

```

---

## ⚙️ Setup & Installation

### ✅ 1. Python Version

```

Python 3.10+

````

---

### ✅ 2. Clone & Setup Virtual Environment

```bash
git clone <your-repository-url>
cd <your-repository>

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
````

---

### ✅ 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 📦 Required Packages

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

## 🔑 Environment Variables

Create a `.env` file in project root:

```
GOOGLE_API_KEY=your-google-api-key
MONGO_CONNECTION_STRING=your-mongodb-uri

JWT_SECRET_KEY=change-me-in-prod
```

---

## ✅ MongoDB Requirements

Create a **Vector Search Index** in MongoDB Atlas on the field:

```
main_vector
```

### Vector Index Configuration

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

### Index Name (must match exactly)

```
vector_index
```

---

## ▶️ Running the App

Start the server:

```bash
uvicorn app.main:app --reload
```

---

### API Base URL

```
http://localhost:8000
```

---

### Interactive API Docs

```
http://localhost:8000/docs
```

---

## 🔐 Authentication & User Roles

---

### 📝 Create Account

**POST** `/auth/register`

```json
{
  "username": "admin",
  "password": "test123",
  "role": "admin"
}
```

---

### 🔑 Login

**POST** `/auth/login`

Form-encoded request

Response:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

---

### 🔓 Use Token

Pass JWT in headers for protected routes:

```
Authorization: Bearer YOUR_TOKEN
```

---

### 👥 Role Permissions

| Role   | Allowed actions                              |
| ------ | -------------------------------------------- |
| viewer | Search only                                  |
| editor | Upload, update, delete individual test cases |
| admin  | Full control + delete-all + metrics          |

---

## 📤 Uploading Test Cases

---

### Endpoint

**POST** `/api/upload`
*AUTH REQUIRED: `editor` or `admin`*

---

### Accepted file formats

```
.csv
.xlsx
```

---

### Required Columns

```
Test Case ID
Feature
Test Case Description
Pre-requisites
Test Step
Expected Result
Step No.
```

---

### Optional Columns

```
Tags (comma-separated)
Priority
Platform
```

---

### File Processing Flow

1. Gemini enrichment → summary + keywords
2. Batch SentenceTransformer embeddings
3. Mean vector creation
4. MongoDB insert + vector indexing

---

---

## 🔍 Searching Test Cases

---

### Endpoint

**POST** `/api/search`

---

### Request Example

```json
{
  "query": "payment failure",
  "feature": "Checkout",
  "tags": ["Regression"],
  "priority": "High",
  "platform": "Mobile",
  "ranking_variant": "B"
}
```

---

### Search Pipeline

```
Input Query
    ↓
Embedding
    ↓
MongoDB $vectorSearch
    ↓
Local Signal Fusion Ranker
    ↓
(Gemini Re-Ranking – optional)
    ↓
Diversity Filtering
    ↓
Final TOP-K Results
```

---

## 📊 Scoring Signals

---

### Ranking A — "Baseline"

```
0.60 * Vector similarity
0.25 * Max cosine similarity
+ Token match boosts
```

---

### Ranking B — "Enhanced"

```
0.45 * Vector similarity
0.20 * Semantic similarity
0.12 * Keyword overlap
0.08 * Feature match
0.05 * Token density
0.05 * Popularity weighting
```

---

### Variant selection

```
"ranking_variant": "A" | "B"
```

---

---

## 🔄 Updating Records

---

### Endpoint

**PUT** `/api/update/{doc_id}`

---

### Partial Update Example

```json
{
  "feature": "Payments",
  "priority": "Critical",
  "tags": ["Smoke","API"]
}
```

---

### Automatic Triggers

* Gemini re-enrichment (if needed)
* Re-embedding vectors
* Vector recomputation

---

---

## 👮 Admin APIs

---

### Get all test cases

**GET** `/api/get-all`

---

### Delete all data (ADMIN ONLY)

**POST** `/api/delete-all?confirm=true`

---

### Delete single test case

**DELETE** `/api/testcase/{id}`

---

### Metrics

**GET** `/api/metrics`

---

#### Example Response

```json
{
  "queries_today": 281,
  "top_features": ["Login", "Checkout"]
}
```

---

---

## 🧾 Audit Logging

Every **search request** is logged into the **`api_audit_logs`** collection:

Captured fields:

* Timestamp
* Endpoint
* User
* Request payload
* Ranking variant
* Result count

---

### Why this matters

Audit analytics enables:

✅ Quality tracking
✅ Ranking variant experiments (A/B testing)
✅ Popular query discovery
✅ Continuous UX improvement

---

---

## 🧠 Development Workflow

---

### Ranking tuning

➡ Modify:

```python
app/services/ranking.py
```

---

### LLM strategies

➡ Iterate in:

```python
app/services/expansion.py
app/services/rerank.py
```

---

### Schema evolution

➡ Update DTOs in:

```python
app/models/schemas.py
```

---

### Routing only

➡ Routes go strictly in:

```
app/routes/
```

(No business logic inside routers.)

---

---

## ✅ Version

```
TestCases-RAG — Version 2.0
```

---

```

---

