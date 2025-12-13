# JavaScript Method Extractor

### AST-Based, Deterministic, Production-Ready Method Extraction

### Verified to Work on Python 3.11 (Recommended Version)

This project is a reliable and fully deterministic system that extracts JavaScript methods from any script using Tree-sitter, a real Abstract Syntax Tree (AST) parser.
It is built for situations where you need accurate method extraction without depending on formatting, indentation, or AI heuristics.

The system is especially designed for:

* Selenium/WebDriver JavaScript automation code
* Large and complex enterprise JavaScript repositories
* Test case analysis and metadata generation
* High-volume backend API workloads

The extractor reads your JavaScript like a compiler would, not like a simple text parser.

---

# What This System Does (In Simple Terms)

When you give this system a JavaScript file, it:

1. Understands the code structure exactly (using AST)
2. Finds all real functions/methods defined in the file
3. Extracts each method exactly as written (same spacing, comments, formatting)
4. Optionally adds useful related information above each method:

   * Global variables defined earlier in the file
   * Constructor assignments (such as `this.driver = driver`)
5. Places each method into a clean CSV file, one method per row
6. Splits very large outputs into safe chunks so no method gets cut

In short:
It isolates only the useful methods you care about and gives them to you cleanly.

---

# Why This System Exists

Automation scripts often contain:

* Helper functions
* Logging utilities
* Wait functions
* Formatters
* Multiple classes
* Nested functions

But what you typically need when reviewing or analyzing code are **only the meaningful, task-level methods** such as:

```
login()
search()
checkout()
addToCart()
```

This extractor removes everything unnecessary and keeps only the functions that matter.

It does not guess.
It does not modify code.
It does not depend on formatting.
It uses AST, which guarantees correctness.

---

# Important Note About Python Compatibility

This project **has been tested and verified to work on Python 3.11**.

Tree-sitter currently has known compatibility problems with:

* Python 3.12 and above
* Python 3.14 (your previous environment that failed)

Therefore:

**Python 3.11 is the recommended version and the only version guaranteed to work with this system.**

---

# Features

### 1. Accurate JavaScript Parsing Using Tree-sitter AST

Tree-sitter processes JavaScript at a structural level.
This means the extractor identifies:

* Function declarations
* Class methods
* Arrow functions
* Function expressions
* Nested functions

With completely accurate start and end positions.

### 2. Global Variable Injection

If a method comes after global declarations like:

```js
const BASE_URL = "https://example.com";
let TIMEOUT = 5000;
```

Those lines are inserted at the top of the extracted method so the method becomes self-contained.

### 3. Constructor Injection

If a class constructor has lines like:

```js
constructor() {
    this.driver = driver;
    this.url = "/login";
}
```

And a method inside the class uses `this.driver` or `this.url`,
those lines will be injected above the extracted method.

This makes each method independent and easier to analyze.

### 4. Clean CSV Output

Each method goes into one CSV row under a single column named:

```
Raw Method
```

This format is ideal for downloading, reviewing, storing, or feeding into LLM systems.

### 5. Chunking for Large Files

If your JavaScript file is extremely large, the system automatically splits the output into chunks of a controlled size (default: 20,000 characters).
It never splits a method across two chunks.

### 6. REST API (FastAPI)

Two endpoints:

```
GET /health      → Check if server is running
POST /extract    → Upload JS or paste raw code, receive CSV output
```

### 7. MongoDB Logging

The system stores:

* Uploaded scripts
* How many methods were extracted
* Processing time
* Errors
* API usage details

This is useful for audit, debugging, and analytics.

---

# Project Folder Structure

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
│   └── health.py
│
├── services/
│   ├── scanner.py       → The AST extractor
│   ├── chunker.py       → Handles chunk splitting
│   ├── csv_writer.py    → Builds final CSV
│   └── validator.py     → Ensures method validity
│
└── main.py              → Application startup
```

Everything is modular and production-ready.

---

# Installation Instructions (Simple Steps)

### 1. Clone the repository

```bash
git clone <repo_url>
cd SeleniumJavascriptMethodsExtractor
```

### 2. Create a Python 3.11 environment

```bash
py -3.11 -m venv .venv
```

### 3. Activate it

```bash
.venv\Scripts\activate
```

### 4. Install all dependencies

```bash
pip install -r requirements.txt
```

---

# Running the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open browser:

```
http://localhost:8000/docs
```

You can test the extractor directly from Swagger UI.

---

# API Usage

### POST /extract

You can send either:

1. A file:

   ```
   file: myscript.js
   ```

2. Raw JavaScript text:

   ```
   script="function login() { ... }"
   ```

Response:
A downloadable CSV containing all extracted methods.

---

# Troubleshooting (In Layman Terms)

### No methods are extracted

Your file may contain only helper functions or invalid JavaScript.

### Tree-sitter build errors

You are probably using Python 3.12+ or 3.14.
Switch to Python **3.11**.

### MongoDB errors

Start your database:

```bash
mongosh
```

### CSV shows strange characters in Excel

Some lines are automatically escaped to prevent Excel formula injection.
This is expected.

---

# Frequently Asked Questions

### Why not use regex?

JavaScript syntax is too complex for regex. Functions can be nested, formatted differently, or spread across lines.
AST parsing avoids all guesswork.

### Does this modify code?

No. It extracts methods exactly as written.

### Are nested functions extracted?

Yes.
They are included unless filtered.

### Can this handle very large files?

Yes. Chunking ensures no method is cut or corrupted.

---

# Summary

This system provides:

* Reliable and deterministic JavaScript method extraction
* Fully AST-based processing
* Support for Selenium-style modular functions
* Automatic global and constructor injections
* Clean CSV output
* Strong logging and audit trail
* A fast and robust API layer
* Guaranteed compatibility with Python 3.11

It is built for real production use cases and high-volume processing environments.
