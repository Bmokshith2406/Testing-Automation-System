# Python Method Extractor (AST-Only, Production-Grade)

A fast, deterministic, LLM-free Python method extraction service built using AST parsing.

Optimized for:
- Selenium automation scripts  
- Large enterprise Python codebases  
- Byte-perfect extraction (no code modification)  
- Static analysis and test-case workflows  
- High-volume API processing with MongoDB logging  

The system extracts top-level functions, class methods, and nested methods, injects constructor-initialized variables when needed, and returns a single-column CSV containing each method as a clean block.

---

# Features

### 1. AST-Based Extraction (No LLMs)
- Byte-perfect slicing from the original source  
- No decorators included  
- Preserves indentation, spacing, and code style  
- Supports async functions  
- Supports nested functions  

### 2. Class Variable Injection
Constructor-assigned attributes such as:

```python
self.driver = driver
self.wait = WebDriverWait(driver, 10)
````

are injected above a method only if that method references them.

### 3. Chunking System

Splits extraction output into safe chunks (20,000 characters by default), without ever splitting a method.

### 4. CSV Output

Produces a single-column CSV file with a header:

```
Raw Method
```

Each row contains one extracted method block.

### 5. REST API (FastAPI)

Endpoints:

```
GET  /health
POST /extract
```

### 6. MongoDB Logging

Stores:

* API logs
* Raw uploaded scripts

### 7. Production-Grade Architecture

Includes middleware, error handling, validation, structured logging, environment-based configuration, and Docker support.

---

# Architecture Overview

```
app/
│
├── core/
│   ├── config.py          # Settings loader
│   ├── logging.py         # Global logging config
│   └── utils.py           # Safe decoding, timing helpers
│
├── db/
│   └── mongo.py           # Async MongoDB client + storage functions
│
├── middleware/
│   └── audit.py           # API call logging middleware
│
├── models/
│   └── schemas.py         # Pydantic APILog and RawScript schemas
│
├── routes/
│   ├── extract.py         # Method extraction API
│   └── health.py          # Health check
│
├── services/
│   ├── scanner.py         # AST-based extractor
│   ├── chunker.py         # Chunk splitting system
│   ├── csv_writer.py      # CSV builder
│   └── validator.py       # Validation layer
│
└── main.py                # FastAPI app entry
```

---

# AST Extraction Rules

### Extracted

* Top-level functions
* Class methods (excluding `__init__`)
* Nested functions

### Ordering

Preserved exactly in source order.

### Byte-Perfect Guarantee

* Extraction begins exactly at the `def` or `async def` line
* No decorators included
* No modification or normalization of code

### Not Extracted

* Constructors (`__init__`)
* Decorators
* Comments above method definitions

---

# Injection Logic (Constructor to Methods)

If a class contains:

```python
def __init__(self):
    self.driver = driver
    self.url = "https://example.com"
```

and a method references:

```python
self.driver
self.url
```

The extracted block becomes:

```
self.driver = driver
self.url = "https://example.com"

def open(self):
    self.driver.get(self.url)
```

Rules:

* Only attributes assigned in `__init__` qualify
* Only injected if referenced inside the method
* Injection preserves original formatting

---

# Project File Structure

```
.
├── app/
│   ├── core/
│   ├── db/
│   ├── middleware/
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── main.py
├── requirements.txt
├── .env
└── README.md
```

---

# Installation

Clone the repository:

```bash
cd python-method-extractor
```

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Environment Variables (.env Example)

```
MONGO_URI=mongodb://localhost:27017
MONGO_DB=method_extractor
LOG_LEVEL=INFO
MAX_CHARS_PER_CHUNK=20000
VERSION=1.0.0
```

---

# Running the Application

Start FastAPI using Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open API docs:

```
http://localhost:8000/docs
```

---

# API Documentation

---

## GET /health

Returns service status.

Response:

```json
{
  "status": "ok"
}
```

---

## POST /extract

### Option 1: Upload a File

```
multipart/form-data
file: my_script.py
```

### Option 2: Paste Code

```
script="def f(): pass"
```

### Response

A CSV file download containing extracted method blocks.

---

# MongoDB Storage

### Raw Scripts Collection (`raw_scripts`)

```
{
  "filename": "login.py",
  "content": "...",
  "size": 3240,
  "timestamp": "2025-01-10T12:30:00Z"
}
```

### API Logs Collection (`api_logs`)

```
{
  "timestamp": "2025-01-10T12:30:01Z",
  "ip": "127.0.0.1",
  "user_agent": "...",
  "file_name": "login.py",
  "method_count": 12,
  "chunk_count": 1,
  "status": "success",
  "duration_ms": 15.2
}
```

---

# Logging

All logs follow the configured format:

```
2025-01-10 11:00:00 | INFO | method_extractor | Extracted 12 methods
```

---

# Validation Rules

Validation ensures:

* Code begins with `def` or `async def`
* No decorators included
* Methods are sorted by original line numbers
* Injected vars are plain strings

On failure, a `ValidationError` is raised internally.

---

# Docker Deployment

### Build image:

```bash
docker build -t method-extractor .
```

### Run container:

```bash
docker run -p 8000:8000 --env-file .env method-extractor
```

---

# Troubleshooting

### Method does not start with def

Decorators are present in source code. Decorators are intentionally excluded.

### No methods extracted

Possible reasons:

* Syntax errors in source
* All functions are inside **init**
* File encoding issues

### CSV issues in Excel

Excel may interpret rows as formulas.
The CSV writer safely escapes dangerous prefixes.

---

# FAQ

### Why AST instead of an LLM?

AST parsing is deterministic, reliable, reproducible, and safe for large automation codebases.

### Does it support async functions?

Yes.

### Does it modify code?

No. All extraction is byte-perfect.

### Does method order match the file?

Yes. Guaranteed.

---

