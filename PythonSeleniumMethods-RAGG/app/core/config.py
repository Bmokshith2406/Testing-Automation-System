import os
from functools import lru_cache
from dotenv import load_dotenv

# Safe dotenv loading
try:
    load_dotenv()
except Exception:
    pass


class Settings:
    APP_NAME: str = "Intelligent Script Methods (MongoDB Edition for Selenium Python Only)"
    VERSION: str = "1.0.0"
    CREATED_BY: str = "MOKSHITH BALIDI"

    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    MONGO_CONNECTION_STRING: str = os.getenv("MONGO_CONNECTION_STRING", "")

    DB_NAME: str = "selenium_script_methods_db"
    COLLECTION_SCRIPT_METHODS: str = "multilevel_script_methods_mongo"
    COLLECTION_USERS: str = "users"
    COLLECTION_AUDIT: str = "api_audit_logs"

    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    VECTOR_INDEX_NAME: str = "vector_index"

    CANDIDATES_TO_RETRIEVE: int = 15
    FINAL_RESULTS: int = 5
    TOP_K: int = 3

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
    # LLM Prompt Templates
    # ------------------------------------------------------------------

    Method_MADL_Prompt = """
    Analyze this raw Selenium Python method and return STRICT JSON only with this schema:

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
        "owner": "QE-Core/Python Automation",
        "example_usage": "",
        "created": "",
        "last_updated": ""
      }}
    }}

    Rules:
    - The summary shall be of 30-35 words maximum.
    - Total keywords shall not exceed 10-15.
    - Never lose the intent of the method.
    - Response MUST be valid JSON only.
    - method_name must contain full function signature.
    - params must match Python arguments.
    - returns must be "None" if nothing is returned.
    - keywords should be Selenium + Python test automation terms.

    RAW METHOD:
    {raw_method}
    """


    Query_Normalization_Prompt = """
    This is a query that I have received from a user for Selenium automation method searching.

    Most important:
    - Do not lose user intent.
    - Do not lose requested action.
    - Fix only spelling or minor grammar errors.
    - Preserve wording and meaning.
    - Return ONLY a single corrected sentence.

    Query:
    "{query}"
    """


    Query_Expansion_Prompt = """
    You are an assistant that expands short search queries into useful
    paraphrases and synonyms for Selenium automation method search.

    Goal:
    - Widen semantic scope while preserving intent.

    Instructions:
    - Return only a comma-separated single line of {n} short paraphrases or keywords.
    - Do NOT use numbering or bullet points.

    Query:
    "{normalized_query}"
    """


    Results_ReRanking_Prompt = """
    You are an expert relevance-ranking assistant.

    Your task:
    Re-rank the following Selenium automation methods based on how well each one matches the given query.

    Query:
    "{query}"

    Instructions:
    - Return ONLY a newline-separated list of candidate IDs.
    - Each line must contain exactly one candidate _id.
    - Order the IDs from MOST relevant to LEAST relevant.
    - Do NOT include any explanations, commentary, formatting, or extra text.

    Candidates:
    """


    Final_Ranking_Prompt = """
    Look at these Selenium automation methods and choose the {top_k} that best match what the user really wants to automate.

    Ignore any previous scores, rankings, or ordering. Judge only by how well each method matches the user’s intent.

    User Query:
    "{query}"

    Reply with EXACTLY {top_k} lines.
    Format each line as:

    <method_id> | <confidence_score>

    Where:
    - <confidence_score> is an integer between 0 and 100 showing how well the method matches the user’s intent.
    - Put the best match first.
    - Do not add any other text.

    Methods:
    """


    Dedupe_Summary_Prompt = """
    Analyze the following Selenium Python method.

    Your task:
    Generate EXACTLY a 12-word summary describing only the functional intent of the method.

    Rules:
    - EXACTLY 12 words (no more, no less).
    - Single sentence.
    - No quotes, bullet points, or numbering.
    - No punctuation at end.
    - No explanations or extra words.

    Raw Method:
    "{raw_method}"

    Return ONLY the 12-word summary.
    """


    Dedupe_Verification_Prompt = """
    You are an expert Selenium automation method duplication detector.

    Compare the NEW METHOD with the EXISTING METHODS below.

    Determine if ANY existing method performs the SAME FUNCTIONAL INTENT
    with SUBSTANTIALLY THE SAME AUTOMATION WORKFLOW.

    It is fine if two different methods have different names – they may still
    be considered the same. However:

    - If their PARAMETERS differ, treat them as UNIQUE.
    - If their LOCATORS differ, treat them as UNIQUE, as locators play a vital
      role during execution.

    Reply with EXACTLY one word only:

    DUPLICATE
    or
    UNIQUE

    Do NOT explain.

    NEW METHOD
    Method Name: "{new_method_name}"
    Raw Method:
    "{new_raw_method}"

    EXISTING METHODS
    -----------------
    {existing_blocks}
    """



@lru_cache
def get_settings() -> Settings:
    return Settings()
