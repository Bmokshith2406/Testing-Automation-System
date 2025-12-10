import time

import google.generativeai as genai

from app.core.config import get_settings
from app.core.logging import logger


settings = get_settings()

DUPLICATE_TOKEN = "DUPLICATE"


# -------------------------------------------------------
# Gemini: Test case duplicate verifier
# -------------------------------------------------------

async def llm_verify_duplicate(
    candidate: dict,
    top_matches: list,
) -> bool:
    """
    LLM determines if incoming test case matches ANY candidate result
    in functional intent + workflow steps.

    Returns:
        True  -> DUPLICATE
        False -> UNIQUE
    """

    # -------------------------------------------------------
    # Basic short-circuit
    # -------------------------------------------------------
    try:
        if not candidate or not top_matches:
            return False
    except Exception:
        return False

    try:
        if not settings.GOOGLE_API_KEY:
            return False
    except Exception:
        return False


    # -------------------------------------------------------
    # ✅ CENTRALIZED PROMPT TEMPLATE
    # -------------------------------------------------------
    try:
        existing_blocks = ""

        for i, match in enumerate(top_matches[:3], start=1):
            doc = match.get("document", {})

            existing_blocks += f"""
                            CASE {i}
                            Feature: {doc.get('Feature', '')}
                            Description: {doc.get('Test Case Description', '')}
                            Steps:
                            {doc.get('Steps', '')}
                            -----------
                            """

        prompt = settings.Dedupe_Verification_Prompt.format(
            new_feature=candidate.get("Feature", ""),
            new_description=candidate.get("Description", ""),
            new_steps=candidate.get("Steps", ""),
            existing_blocks=existing_blocks,
        )

    except Exception as err:
        logger.exception(f"Dedupe prompt build failed: {err}")
        return False


    # -------------------------------------------------------
    # Gemini execution with retries
    # -------------------------------------------------------

    try:

        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
        except Exception as err:
            logger.warning(f"Dedupe verifier model init failed: {err}")
            return False


        for attempt in range(max(1, settings.GEMINI_RETRIES)):

            try:
                response = model.generate_content(prompt)

                try:
                    text = (response.text or "").strip().upper()
                except Exception:
                    text = ""

                if DUPLICATE_TOKEN in text:
                    time.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)
                    return True

                if "UNIQUE" in text:
                    time.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)
                    return False

            except Exception as e:
                logger.warning(
                    f"Dedupe verification attempt {attempt+1} failed: {e}"
                )

                try:
                    time.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)
                except Exception:
                    pass


    except Exception:
        logger.exception("Dedupe verifier fatal error")


    return False
