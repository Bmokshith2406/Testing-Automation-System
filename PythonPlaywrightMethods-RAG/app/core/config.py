import os
from functools import lru_cache
from dotenv import load_dotenv

# Safe dotenv loading
try:
    load_dotenv()
except Exception:
    pass


class Settings:
    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    APP_NAME: str = "Intelligent Playwright Python Methods Search Platform"
    VERSION: str = "1.0.0"
    CREATED_BY: str = "MOKSHITH BALIDI"

    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    MONGO_CONNECTION_STRING: str = os.getenv("MONGO_CONNECTION_STRING", "")

    DB_NAME: str = "python_playwright_methods_db"
    COLLECTION_SCRIPT_METHODS: str = "playwright_python_methods"
    COLLECTION_USERS: str = "users"
    COLLECTION_AUDIT: str = "api_audit_logs"

    # ------------------------------------------------------------------
    # Embeddings / Vector Search
    # ------------------------------------------------------------------

    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    VECTOR_INDEX_NAME: str = "vector_index"

    CANDIDATES_TO_RETRIEVE: int = 15
    FINAL_RESULTS: int = 5
    TOP_K: int = 3

    # ------------------------------------------------------------------
    # Gemini Controls
    # ------------------------------------------------------------------

    GEMINI_RERANK_ENABLED: bool = True
    QUERY_EXPANSION_ENABLED: bool = True
    QUERY_EXPANSIONS: int = 6
    DIVERSITY_ENFORCE: bool = True
    DIVERSITY_PER_FEATURE: bool = True

    GEMINI_RATE_LIMIT_SLEEP: float = 0.5
    GEMINI_RETRIES: int = 2

    CACHE_TTL_SECONDS: int = 60 * 5

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-prod")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # ------------------------------------------------------------------
    # ------------------- LLM PROMPT TEMPLATES --------------------------
    # ------------------------------------------------------------------

    Method_MADL_Prompt = """
                Analyze this raw Playwright Python method and return STRICT JSON only with this schema:

                {{
                  "method_name": "",
                  "method_documentation": {{
                    "summary": "",
                "description": "",
                "reusable": true,
                "intent": "",
                "params": {{ "param": "description" }},
                "applies": "",
                "returns": "",
                "keywords": [],
                "owner": "QE-Core/Playwright Automation",
                "example_usage": "",
                "created": "",
                "last_updated": ""
              }}
            }}

            Rules:
            - Summary must contain 30–35 words maximum.
            - Total keywords must not exceed 10–15.
            - Never lose the core automation intent.
            - Response MUST be valid JSON only.
            - method_name must contain the complete function signature.
            - params must match Python method arguments.
            - returns must be "None" if nothing is returned.
            - keywords should be relevant to Playwright Python test automation and async browser interaction patterns.

            RAW METHOD:
            {raw_method}
            """


    Query_Normalization_Prompt = """
            This is a query that I received from a user for Playwright Python automation method searching.

            Rules:
            - Preserve user intent strictly.
            - Correct spelling and minor grammar only.
            - Do NOT paraphrase or expand meaning.
            - Keep wording nearly identical.
            - Return ONLY ONE corrected sentence.

            Query:
            "{query}"
            """


    Query_Expansion_Prompt = """
            You are an assistant that expands user search queries into useful paraphrases and synonyms for Playwright Python automation method search.

            Goal:
            - Increase semantic coverage without changing original intent.

            Instructions:
            - Return only ONE comma-separated single line of EXACTLY {n} short query variants.
            - No numbering.
            - No bullet points.

            Query:
            "{normalized_query}"
            """


    Results_ReRanking_Prompt = """
            You are an expert relevance-ranking assistant.

            Task:
            Re-rank the following Playwright Python automation methods based only on alignment with the user query.

            User Query:
            "{query}"

            Output rules:
            - Return ONLY a newline-separated list of candidate _id values.
            - Exactly one _id per line.
            - Order IDs from MOST relevant to LEAST relevant.
            - Do not add commentary or extra text.

            Candidates:
            """


    Final_Ranking_Prompt = """
            From these Playwright Python automation methods, select the TOP {top_k} that best match what the user wants to automate.

            Judge only on functional automation relevance.

            User Query:
            "{query}"

            STRICT output rules:
            - Provide EXACTLY {top_k} lines.
            - Each line format:

            <method_id> | <confidence_score>

            Where:
            - confidence_score is between 0 and 100.
            - Highest confidence first.
            - No extra commentary or formatting.

            Methods:
            """


    # ------------------------------------------------------------------
    # Deduplication Prompts
    # ------------------------------------------------------------------

    Dedupe_Summary_Prompt = """
            Analyze the following Playwright Python method.

            Produce EXACTLY a 12-word single sentence summary describing the automation intent only.

            Rules:
            - EXACTLY 12 words.
            - Single sentence.
            - No punctuation at end.
            - No quotes, bullet points, or numbering.
            - Absolutely no explanations.

            Raw Method:
            "{raw_method}"

            Return ONLY the 12-word summary.
            """


    Dedupe_Verification_Prompt = """
            You are a Playwright Python method duplication detection expert.

            Compare the NEW METHOD with the EXISTING METHODS below.

            Determine whether ANY existing method performs the SAME FUNCTIONAL AUTOMATION
            INTENT using a SUBSTANTIALLY IDENTICAL workflow.

            Reasoning rules:
            - Method names may differ.
            - If PARAMETERS differ → treat as UNIQUE.
            - If LOCATORS differ → treat as UNIQUE.
            - If ASYNC FLOW or WAIT STRATEGY differs → treat as UNIQUE.

            Reply with EXACTLY one word:

            DUPLICATE
            or
            UNIQUE

            No explanation allowed.

            NEW METHOD
            Method Name: "{new_method_name}"
            Raw Method:
            "{new_raw_method}"

            EXISTING METHODS
            -----------------
            {existing_blocks}
            """


# ----------------------------------------------------------------------
# Settings Loader
# ----------------------------------------------------------------------

@lru_cache
def get_settings() -> Settings:
    return Settings()
