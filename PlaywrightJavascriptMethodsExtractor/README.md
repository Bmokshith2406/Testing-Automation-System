# Playwright JavaScript Method Extractor

### AST-Based, Deterministic, Production-Ready Method Extraction

### Verified to Work on Python 3.11 (Recommended Version)

This project is a reliable and fully deterministic system that extracts **Playwright JavaScript methods** from scripts and projects using **Tree-sitter**, a real Abstract Syntax Tree (AST) parser.

It is built for situations where you need **accurate, compiler-level method extraction** without relying on formatting, indentation, or AI/regex heuristics.

The extractor reads your JavaScript the way a compiler does, not like a text parser.

---

## What This System Is Designed For

This system is especially designed for:

- Playwright JavaScript automation code
- Playwright test suites and page object models
- Large and complex enterprise JavaScript / TypeScript repositories
- Test case analysis and metadata generation
- High-volume backend API workloads
- Downstream ML / embedding / search pipelines

---

## What This System Does (In Simple Terms)

When you give this system a **Playwright JavaScript file or project**, it:

1. Understands the code structure exactly using AST parsing
2. Finds all real functions and methods (not helpers or noise)
3. Extracts each method exactly as written  
   (same spacing, comments, formatting)
4. Optionally injects useful context above each method:
   - Global variables defined earlier
   - Constructor assignments (for Page Objects)
5. Outputs every method into a clean CSV file
6. Ensures large outputs are chunked safely without cutting methods

In short:  
It isolates **only the meaningful Playwright methods you care about** and gives them to you cleanly and reliably.

---

## Why This System Exists

Real Playwright repositories contain:

- Test specs
- Page objects
- Fixtures
- Utility helpers
- Hooks (`beforeEach`, `afterAll`, etc.)
- Logging and retry wrappers

But what you usually want to analyze or reuse are **task-level methods**, such as:

```

login()
searchProduct()
addToCart()
checkout()

````

This extractor:

- Removes framework noise
- Ignores Playwright DSL scaffolding
- Keeps only reusable, meaningful logic

It does not guess.  
It does not modify code.  
It does not depend on formatting.  
It uses AST parsing, which guarantees correctness.

---

## Important Note About Python Compatibility

This project has been **tested and verified to work on Python 3.11**.

Tree-sitter currently has known compatibility issues with:

- Python 3.12 and above
- Python 3.14

Therefore:

**Python 3.11 is the recommended and supported version for this system.**

---

## Features

### 1. Accurate JavaScript Parsing Using Tree-sitter AST

The extractor identifies, with full accuracy:

- Function declarations
- Class methods (Page Objects)
- Arrow functions
- Function expressions
- Nested functions

Each method is extracted using exact byte offsets from the source code.

---

### 2. Playwright-Aware Method Filtering

The extractor automatically ignores Playwright framework scaffolding such as:

- `test()`, `test.describe()`
- `beforeEach`, `afterAll`
- `expect()`
- Retry and delay helpers

This ensures only **real, reusable logic** is extracted.

---

### 3. Global Variable Injection

If a method depends on global variables defined earlier:

```js
const BASE_URL = "https://example.com";
let TIMEOUT = 5000;
````

Those lines are injected above the extracted method so it becomes self-contained.

---

### 4. Constructor Injection (Page Object Support)

For Playwright Page Objects:

```js
constructor(page) {
    this.page = page;
    this.url = "/login";
}
```

Any constructor assignments used by a method are injected above it.

This makes every extracted method **context-complete and independent**.

---

### 5. Clean CSV Output

All methods are exported into a CSV with a single column:

```
Raw Method
```

Each row contains one full method block.

This format is ideal for:

* Manual review
* Storage
* Embedding
* Search
* LLM pipelines

---

### 6. Chunking for Large Projects

For very large files or repositories:

* Output is automatically chunked (default: 20,000 characters)
* No method is ever split across chunks
* Chunk order is preserved

---

### 7. REST API (FastAPI)

The system exposes three main endpoints:

```
GET  /health
POST /extract
POST /extract-folder
```

#### `POST /extract`

* Upload a single JavaScript / TypeScript file
* Or paste raw Playwright code
* Returns a CSV of extracted methods

#### `POST /extract-folder`

* Upload a ZIP of a Playwright project
* Recursively scans subfolders
* Extracts methods from all `.js` and `.ts` files
* Ignores `node_modules`, build artifacts, and repo noise
* Returns a single combined CSV

---

### 8. ZIP Safety and Size Limits

The folder extraction endpoint enforces strict safety limits:

* Maximum ZIP size (compressed)
* Maximum total uncompressed size (zip-bomb protection)
* Maximum file count
* Maximum single file size

This makes the system safe for production use.

---

### 9. MongoDB Logging and Audit Trail

The system logs:

* Uploaded scripts / projects
* Number of extracted methods
* Chunk counts
* Processing time
* Errors and failures
* API usage metadata

This is useful for auditing, debugging, and analytics.

---

## Project Folder Structure

```
app/
│
├── core/
│   ├── config.py
│   ├── logging.py
│   └── utils.py
│
├── db/
│   └── mongo.py
│
├── middleware/
│   └── audit.py
│
├── models/
│   └── schemas.py
│
├── routes/
│   ├── extract.py
│   ├── extract_folder.py
│   └── health.py
│
├── services/
│   ├── scanner.py       → AST-based Playwright extractor
│   ├── chunker.py       → Chunk splitting logic
│   ├── csv_writer.py    → CSV output builder
│   └── validator.py    → Method validation
│
└── main.py              → Application startup
```

All components are modular, testable, and production-ready.

---

## Installation Instructions

### 1. Clone the repository

```bash
git clone <repo_url>
cd PlaywrightJavascriptMethodExtractor
```

### 2. Create a Python 3.11 virtual environment

```bash
py -3.11 -m venv .venv
```

### 3. Activate the environment

```bash
.venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open in browser:

```
http://localhost:8000/docs
```

Swagger UI allows you to test all endpoints directly.

---

## API Usage Examples

### Extract a Single File

```
POST /extract
```

* Upload `*.js` or `*.ts`
* Or paste raw Playwright code

Response:

* Downloadable CSV of extracted methods

---

### Extract a Full Playwright Project

```
POST /extract-folder
```

* Upload a ZIP of a Playwright project
* Methods from all eligible files are extracted
* One combined CSV is returned

---

## Troubleshooting

### No methods extracted

The project may only contain Playwright scaffolding or helper utilities.

### Tree-sitter errors

You are likely using Python 3.12+.
Switch to Python 3.11.

### MongoDB errors

Ensure MongoDB is running.

### Excel shows strange characters

Some lines are escaped to prevent Excel formula injection.
This is expected behavior.

---

## Frequently Asked Questions

### Why not use regex?

JavaScript syntax is too complex.
AST parsing avoids all ambiguity.

### Does this modify code?

No. Methods are extracted exactly as written.

### Are nested functions included?

Yes, unless filtered by framework rules.

### Can this handle large repositories?

Yes. Chunking and ZIP limits ensure safe processing.

---

## Summary

This system provides:

* Deterministic Playwright JavaScript method extraction
* Fully AST-based parsing
* Page Object and test logic support
* Global and constructor injection
* Single-file and full-project extraction
* ZIP safety protections
* Clean CSV output
* Strong logging and audit trail
* A production-grade FastAPI backend
* Guaranteed compatibility with Python 3.11

