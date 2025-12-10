Intelligent Test Case Search Platform – Modular Edition
🔍 Overview

This project is a production-grade backend platform for uploading, enriching, indexing, and semantically searching software test cases using:

✅ FastAPI for APIs

✅ MongoDB Atlas for persistence & vector search

✅ SentenceTransformers (all-MiniLM-L6-v2) for embeddings

✅ Google Gemini for enrichment, query expansion, and reranking

✅ JWT Authentication with role-based access

✅ Advanced ranking heuristics + A/B testing

✅ Search caching

✅ Audit logging + metrics

This refactor modularizes the original single-file app into clean layers for easier debugging, scaling, and experiment workflows.

📂 Project Structure
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

⚙️ Setup & Installation
✅ 1. Python version
Python 3.10+

✅ 2. Clone & setup virtual environment
git clone <your-repository>
cd <your-repository>

python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows

✅ 3. Install dependencies
pip install -r requirements.txt

📦 Required Packages

Your requirements.txt should include:

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

🔑 Environment Variables

Create a .env file:

GOOGLE_API_KEY=your-google-api-key
MONGO_CONNECTION_STRING=your-mongodb-uri

JWT_SECRET_KEY=change-me-in-prod

✅ MongoDB Requirements

You must create a Vector Search Index in MongoDB Atlas on the main_vector field:

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




Name the index exactly:

vector_index

▶️ Running the App

Start the backend:

uvicorn app.main:app --reload


API available at:

http://localhost:8000


Interactive docs:

http://localhost:8000/docs

🔐 Authentication & User Roles
Create Account
POST /auth/register

{
  "username": "admin",
  "password": "test123",
  "role": "admin"
}

Login
POST /auth/login


(form-encoded)

Returns JWT:

{
  "access_token": "...",
  "token_type": "bearer"
}

Use Token

Add to headers:

Authorization: Bearer YOUR_TOKEN

Role Permissions
Role	Allowed actions
viewer	Search only
editor	Upload, update, delete individual test cases
admin	Full control + delete-all + metrics
📤 Uploading Test Cases
POST /api/upload


Auth required: editor or admin

Accepts:

.csv

.xlsx

Required columns

Test Case ID

Feature

Test Case Description

Pre-requisites

Test Step

Expected Result

Step No.

Optional columns:

Tags – comma-separated

Priority

Platform

Processing Flow

File ingestion

Gemini summary + keyword generation

Batched SentenceTransformer embedding

Mean vector creation for indexing

Mongo insert

🔍 Searching Test Cases
POST /api/search

{
  "query": "payment failure",
  "feature": "Checkout",
  "tags": ["Regression"],
  "priority": "High",
  "platform": "Mobile",
  "ranking_variant": "B"
}

Search Pipeline
Input Query
   ↓
Embedding
   ↓
MongoDB $vectorSearch
   ↓
Local signal fusion ranker
   ↓
(Gemini re-ranking optional)
   ↓
Diversity filtering
   ↓
Final TOP-K results

Scoring Signals

Ranking A ("Baseline")

0.60 * Vector similarity
0.25 * Max cosine similarity
+ Token match boosts


Ranking B ("Enhanced")

0.45 * Vector similarity
0.20 * Semantic similarity
0.12 * Keyword overlap
0.08 * Feature name match
0.05 * Token density
0.05 * Popularity weighting


Use:

"ranking_variant": "A" | "B"

🔄 Updating Records
PUT /api/update/{doc_id}


Partial updates supported:

{
  "feature": "Payments",
  "priority": "Critical",
  "tags": ["Smoke","API"]
}

Triggers automatic:

Gemini re-enrichment if needed

Re-embedding

Main vector recalculation

👮 Admin APIs
Get all test cases
GET /api/get-all

Delete all data
POST /api/delete-all?confirm=true


(admin only)

Delete single case
DELETE /api/testcase/{id}

Metrics
GET /api/metrics


Returns:

{
  "queries_today": 281,
  "top_features": ["Login","Checkout"]
}

🧾 Audit Logging

Every search call records:

Timestamp

Endpoint

User

Request payload

Ranking variant

Result count

Mongo collection:

api_audit_logs

Why this matters

This enables:

✅ Quality monitoring
✅ Ranking experimentation feedback
✅ Popular query discovery
✅ Search UX improvements

🧠 Development Workflow
Recommended flow

Implement ranking changes in:

app/services/ranking.py


Experiment with LLM strategies in:

app/services/expansion.py
app/services/rerank.py


Update schema logic in:

app/models/schemas.py


Route wiring only in:

app/routes/
"# TestCases-RAG-Version-2.0" 
