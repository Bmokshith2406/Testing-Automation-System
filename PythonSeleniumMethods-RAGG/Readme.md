# Python Selenium Methods RAG – Modular Edition  
Version 1.0

---

## Overview

This project is a production-grade backend platform for ingesting, enriching, indexing, deduplicating, and semantically searching **raw Selenium Python test automation methods** using a Retrieval-Augmented Generation (RAG) architecture.

The system converts scattered Selenium utility scripts into a structured, searchable, reusable knowledge base with intelligent deduplication and ranking powered by Large Language Models and vector embeddings.

Core capabilities include:

- FastAPI REST APIs
- MongoDB Atlas persistence with vector search
- SentenceTransformers (`all-MiniLM-L6-v2`) for embeddings
- Google Gemini for:
  - MADL (Method Abstract Description Language) generation
  - Query normalization
  - Query expansion
  - Deduplication verification
  - LLM-based reranking
- Centralized Gemini concurrency control via semaphore
- JWT-based authentication with role management
- Signal-fusion ranking heuristics with A/B test variants
- Search result caching
- Request-level audit logging
- Metrics collection

All LLM prompts and runtime parameters are centralized in configuration for easy live experimentation without modifying Python services.

---

## System Architecture

### Ingestion Pipeline

```

Raw Selenium Method
↓
Gemini dedupe summary creation
↓
Vector similarity matching vs stored methods
↓
Gemini duplicate verification
↓
MADL documentation generation
↓
Multi-vector embedding creation
↓
MongoDB storage + indexing

```

---

### Search Pipeline

```

User Query
↓
Query normalization
↓
Query expansion
↓
Embedding generation
↓
MongoDB $vectorSearch
↓
Local heuristic ranking
↓
Optional Gemini reranking
↓
Final Top-K results

```

---

## Project Structure

```

app/
├── main.py                      # FastAPI initialization and lifecycle
│
├── core/                        # Global configuration and infrastructure logic
│   ├── config.py               # Environment config and LLM prompts
│   ├── logging.py              # Structured log formatting
│   ├── cache.py                # In-memory query caching
│   ├── security.py             # JWT auth and credential hashing
│   └── analytics.py            # Search audit + analytics logging
│
├── db/
│   └── mongo.py                # MongoDB connection and collection helpers
│
├── models/
│   ├── schemas.py              # Pydantic request/response DTOs
│   └── users.py                # MongoDB user access helpers
│
├── services/
│   ├── embeddings.py           # SentenceTransformer embedding pipeline
│   ├── keywords.py             # Keyword extraction helpers
│   ├── expansion.py            # Gemini query expansion
│   ├── ranking.py              # Heuristic signal fusion scoring
│   ├── rerank.py               # Gemini reranking engine
│   ├── finalRanking.py         # Final post-processing ranking layer
│
│   ├── method_madl.py          # MADL generation logic
│   ├── dedupe_summary.py       # Gemini dedupe summarization flows
│   ├── dedupe_search_helper.py# Similarity candidate filtering
│   ├── dedupe_verifier.py      # LLM duplicate verification
│   └── gemini_semaphore.py     # Global Gemini rate/concurrency throttle
│
├── routes/
│   ├── auth.py                 # Authentication endpoints
│   ├── upload.py               # Selenium method ingestion
│   ├── search.py               # Query endpoints
│   ├── update.py               # MADL updates and re-embedding
│   └── admin.py                # Maintenance and metrics endpoints

```

---

## Setup and Installation

### Python Version

```

Python 3.10+

````

---

### Environment Setup

```bash
git clone <your-repository-url>
cd <your-repository>

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
````

---

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Required Packages

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

## Environment Configuration

Create `.env` in project root:

```env
GOOGLE_API_KEY=your-gemini-api-key
MONGO_CONNECTION_STRING=your-mongodb-atlas-uri
JWT_SECRET_KEY=change-this-in-production

EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
VECTOR_INDEX_NAME=vector_index

GEMINI_RETRIES=3
GEMINI_RATE_LIMIT_SLEEP=2
QUERY_EXPANSIONS=6
```

---

## MongoDB Vector Search Setup

Create a **MongoDB Atlas Vector Search index** on the `main_vector` field.

### Index Name

```
vector_index
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

---

## Running the Application

```bash
uvicorn app.main:app --reload
```

---

### Local Endpoints

```
http://localhost:8000
http://localhost:8000/docs
```

---

## Authentication

All protected endpoints use JWT bearer authentication.

---

### Register User

**POST /auth/register**

```json
{
  "username": "admin",
  "password": "test123",
  "role": "admin"
}
```

---

### Login

**POST /auth/login**

Form Body:

```
username
password
```

Response:

```json
{
  "access_token": "TOKEN",
  "token_type": "bearer"
}
```

---

### Use Token

```
Authorization: Bearer TOKEN
```

---

## Role Permissions

| Role   | Permissions                                            |
| ------ | ------------------------------------------------------ |
| viewer | Search methods only                                    |
| editor | Upload methods, update MADL, delete single methods     |
| admin  | Full access including delete-all and metrics endpoints |

---

## Upload Selenium Methods

**POST /api/upload-methods**

### Required Role

```
editor or admin
```

### Supported Formats

* `.csv`
* `.xlsx`

### Required Column

```
Raw Method
```

### Ingestion Processing

For each Selenium method:

* Gemini dedupe summary generated

* Vector similarity candidate search executed

* Gemini LLM duplicate verification

* Structured MADL JSON created

* Four embeddings generated:

  * `summary_embedding`
  * `raw_method_embedding`
  * `madl_embedding`
  * `main_vector`

* Results stored in MongoDB

---

## Search API

**POST /api/search**

Sample request:

```json
{
  "query": "wait until element clickable",
  "ranking_variant": "B"
}
```

---

### Ranking Variants

#### Variant A (Baseline)

```
0.60 * Vector similarity
0.25 * Cosine similarity
Lexical token match boosts
```

---

#### Variant B (Enhanced)

```
0.45 * Vector similarity
0.20 * Cosine similarity
0.12 * Keyword overlap
0.05 * Token density
0.05 * Popularity weighting
```

---

## Updating Methods

**PUT /api/update/{method_id}**

Partial updates apply only to MADL fields.

Automatic processing:

* Gemini re-enrichment if required
* Embedding regeneration
* Main vector recomputation

---

## Administrative Endpoints

### Retrieve All Methods

```
GET /api/get-all-methods
```

---

### Delete All Methods

```
POST /api/delete-all?confirm=true
```

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

Response example:

```json
{
  "queries_today": 42,
  "top_methods": ["wait_for_clickable", "open_page", "send_keys_safe"]
}
```

---

## Audit Logging

All `/api/search` requests are recorded in the `api_audit_logs` collection.

Captured fields:

* Timestamp
* Endpoint
* Request payload
* Ranking variant
* Result count

Purpose:

* Track ranking quality
* Enable A/B experimentation feedback
* Identify popular searches
* Guide platform tuning

---

## Gemini Concurrency Safety

All Gemini calls flow through:

```
app/services/gemini_semaphore.py
```

Default throttle:

```python
GEMINI_MAX_CONCURRENCY = 2
```

This prevents quota exhaustion and stabilizes parallel ingestion and search activity.

---

## Development Workflow

### Change prompts or runtime tuning

```
app/core/config.py
```

---

### Modify ranking logic

```
app/services/ranking.py
```

---

### Update ingestion logic

```
app/routes/upload.py
```

---

### Adjust embedding behavior

```
app/services/embeddings.py
```

---

### Reranking logic

```
app/services/finalRanking.py
```

---

