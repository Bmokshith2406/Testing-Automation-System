import os
from functools import lru_cache
from dotenv import load_dotenv

# Safe dotenv loading
try:
    load_dotenv()
except Exception:
    # If dotenv cannot load, continue safely with environment variables
    pass


class Settings:
    APP_NAME: str = "Intelligent Test Case Search API (MongoDB Edition)"
    VERSION: str = "2.0.0"
    CREATED_BY: str = "MOKSHITH BALIDI"

    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    MONGO_CONNECTION_STRING: str = os.getenv("MONGO_CONNECTION_STRING", "")

    DB_NAME: str = "test_case_db"
    COLLECTION_TESTCASES: str = "multilevel_test_cases_mongo"
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
    # LLM Prompt Templates (SAFE — defer substitution)
    # ------------------------------------------------------------------

    TestCase_Enrichment_Prompt = """
                                Analyze the following software test case end to end completely and generate enriched metadata.

                                Feature: "{feature}"

                                Test Case Description: "{description_text}"

                                Steps: "{steps_text}"

                                Output format (exactly):
                                Summary: Exactly 30 words clearly explaining purpose and process of the test case.
                                Keywords: Exactly 20 key words & phrases together, they shall be comma-separated.
                                """

    Query_Normalization_Prompt = """
                                This is a query that I have received from a user for test case searching.

                                Most important:
                                - Do not lose user intent.
                                - Do not lose requested action.
                                - Fix only spelling or minor grammar errors.
                                - Preserve wording and meaning.
                                - Return ONLY a single corrected sentence.

                                Query: "{query}"
                                """

    Query_Expansion_Prompt = """
                            You are an assistant that expands short search queries into useful
                            paraphrases and synonyms for software test-case search.

                            Goal:
                            - Widen semantic scope while preserving intent.

                            Instructions:
                            - Return only a comma-separated single line of {n} short paraphrases or keywords.
                            - Do NOT use numbering or bullet points.

                            Query: "{normalized_query}"
                            """

    Results_ReRanking_Prompt = """
                            You are an expert relevance-ranking assistant.

                            Your task:
                            Re-rank the following test cases based on how well each one matches the given query.

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
                    Look at these software test cases and choose the {top_k} that best match what the user really wants to test.

                    Ignore any previous scores, rankings, or ordering. Judge only by how well each test case matches the user’s intent.

                    User Query:
                    "{query}"

                    Reply with EXACTLY {top_k} lines.
                    Format each line as:

                    <test_case_id> | <confidence_score>

                    Where:
                    - <confidence_score> is an integer between 0 and 100 showing how well the test matches the user’s intent.
                    - Put the best match first.
                    - Do not add any other text.

                    Test cases:
                    """
                    
    Dedupe_Summary_Prompt = """
                            Analyze the following end-to-end software test case.

                            Your task:
                            Generate EXACTLY a 12-word summary describing only the functional intent of the test case.

                            Rules:
                            - EXACTLY 12 words (no more, no less).
                            - Single sentence.
                            - No quotes, bullet points, or numbering.
                            - No punctuation at end.
                            - No explanations or extra words.

                            Feature:
                            "{feature}"

                            Description:
                            "{description_text}"

                            Steps:
                            "{steps_text}"

                            Return ONLY the 12-word summary.
                            """
    
    Dedupe_Verification_Prompt = """
                                You are an expert QA test-case duplication detector.

                                Compare the NEW TEST CASE with the EXISTING TEST CASES below.

                                Determine if ANY existing test case validates the SAME FUNCTIONAL INTENT
                                with SUBSTANTIALLY THE SAME WORKFLOW.

                                Reply with EXACTLY one word only:

                                DUPLICATE
                                or
                                UNIQUE

                                Do NOT explain.

                                NEW TEST CASE
                                Feature: "{new_feature}"
                                Description: "{new_description}"
                                Steps:
                                "{new_steps}"

                                EXISTING TEST CASES
                                -------------------
                                {existing_blocks}
                                """

     
    

@lru_cache
def get_settings() -> Settings:
    return Settings()
