# Intelligent Test Case Search Platform – Modular Edition  
TestCases-RAG Version 2.0

---

## Overview

This project is a production-grade backend platform for uploading, enriching, indexing, and semantically searching software test cases using:

- FastAPI for APIs  
- MongoDB Atlas for persistence and vector search  
- SentenceTransformers (all-MiniLM-L6-v2) for embeddings  
- Google Gemini for enrichment, query expansion, and reranking  
- JWT authentication with role-based access  
- Advanced ranking heuristics with A/B testing  
- Search caching  
- Audit logging and metrics  

This refactor modularizes the original single-file application into clean layers for easier debugging, scaling, and experimentation workflows.

---

## Project Structure

```

app/
├── main.py                # App startup + lifespan orchestration
│
├── core/                  # Global configuration and security
│   ├── config.py          # Environment variables and constants
│   ├── logging.py         # Structured logging
│   ├── cache.py           # In-memory query caching
│   ├── security.py        # JWT and password hashing
│   └── analytics.py      # Audit logging
│
├── db/
│   └── mongo.py           # MongoDB connection and helpers
│
├── models/
│   ├── schemas.py         # Pydantic DTO schemas
│   └── users.py           # Mongo user CRUD helpers
│
├── services/
│   ├── embeddings.py     # SentenceTransformer lifecycle and batching
│   ├── keywords.py       # Keyword extraction and fallback summaries
│   ├── enrichment.py     # Gemini test-case enrichment
│   ├── expansion.py      # Gemini query expansion
│   ├── rerank.py         # Gemini reranking
│   └── ranking.py        # Multi-signal scoring and A/B testing logic
│
├── routes/
│   ├── auth.py            # Login and register APIs
│   ├── upload.py          # CSV/XLSX ingestion, enrichment, embeddings
│   ├── search.py          # Hybrid vector and heuristic ranking search
│   ├── update.py          # Test case updates and reprocessing
│   └── admin.py           # Admin maintenance and metrics APIs
│
└── middleware/            # Optional global middleware (future)

```

---

## Setup and Installation

### Python Version

```

Python 3.10 or later

````

---

### Clone and Setup Virtual Environment

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

### Install Dependencies

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

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your-google-api-key
MONGO_CONNECTION_STRING=your-mongodb-uri
JWT_SECRET_KEY=change-me-in-production
```

---

## MongoDB Configuration

You must create a Vector Search index in MongoDB Atlas on the field:

```
main_vector
```

### Vector Index Definition

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

### Index Name

```
vector_index
```

---

## Running the Application

Start the backend server:

```bash
uvicorn app.main:app --reload
```

---

### API URL

```
http://localhost:8000
```

---

### Interactive API Documentation

```
http://localhost:8000/docs
```

---

## Authentication and User Roles

---

### Register

**POST** `/auth/register`

```json
{
  "username": "admin",
  "password": "test123",
  "role": "admin"
}
```

---

### Login

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

### Authorization Header

Include JWT in protected requests:

```
Authorization: Bearer YOUR_TOKEN
```

---

### Role Permissions

| Role   | Permissions                                   |
| ------ | --------------------------------------------- |
| viewer | Search only                                   |
| editor | Upload, update, delete individual test cases  |
| admin  | Full control including delete-all and metrics |

---

## Uploading Test Cases

---

### Endpoint

**POST** `/api/upload`
Authorization required: `editor` or `admin`

---

### Supported Formats

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

### Processing Flow

1. Gemini summary and keyword enrichment
2. Batched SentenceTransformer embeddings generation
3. Mean vector creation for indexing
4. MongoDB insert and vector registration

---

## Searching Test Cases

---

### Endpoint

**POST** `/api/search`

---

### Example Request

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
Query Input
   ↓
Embedding Generation
   ↓
MongoDB Vector Search
   ↓
Local Signal Fusion Ranker
   ↓
Gemini Reranking (optional)
   ↓
Diversity Filtering
   ↓
Final Top-K Results
```

---

## Ranking Algorithms

---

### Variant A – Baseline

```
0.60 * Vector similarity
0.25 * Maximum cosine similarity
Token match boosts
```

---

### Variant B – Enhanced

```
0.45 * Vector similarity
0.20 * Semantic similarity
0.12 * Keyword overlap
0.08 * Feature match
0.05 * Token density
0.05 * Popularity weighting
```

---

### Usage

```
"ranking_variant": "A" | "B"
```

---

## Updating Records

---

### Endpoint

**PUT** `/api/update/{doc_id}`

---

### Example Request

```json
{
  "feature": "Payments",
  "priority": "Critical",
  "tags": ["Smoke", "API"]
}
```

---

### Automatic Updates

* Gemini re-enrichment when applicable
* Vector regeneration
* Reindexing

---

## Admin APIs

---

### Retrieve All Test Cases

**GET** `/api/get-all`

---

### Delete All Data (admin only)

**POST** `/api/delete-all?confirm=true`

---

### Delete Single Test Case

**DELETE** `/api/testcase/{id}`

---

### Metrics

**GET** `/api/metrics`

Response example:

```json
{
  "queries_today": 281,
  "top_features": ["Login", "Checkout"]
}
```

---

## Audit Logging

Every search request is logged in the `api_audit_logs` collection and captures:

* Timestamp
* Endpoint
* User
* Request payload
* Ranking variant
* Result count

This enables:

* Monitoring system quality
* A/B ranking experiments
* Discovery of popular search behavior
* Search UX optimization

---

## Development Workflow

---

### Ranking Changes

```
app/services/ranking.py
```

---

### LLM Experimentation

```
app/services/expansion.py
app/services/rerank.py
```

---

### Schema Updates

```
app/models/schemas.py
```

---

### Routing

All endpoint definitions belong strictly in:

```
app/routes/
```

Business logic should never reside in route handlers.

---

## Version

```
TestCases-RAG Version 2.0
```

---

```
```
