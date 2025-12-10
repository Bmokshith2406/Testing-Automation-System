import asyncio

import google.generativeai as genai

from app.core.config import get_settings
from app.core.logging import logger
from app.services.gemini_semaphore import run_gemini_call


settings = get_settings()

DUPLICATE_TOKEN = "DUPLICATE"


# -------------------------------------------------------
# Gemini: Method duplicate verifier
# -------------------------------------------------------

async def llm_verify_method_duplicate(
    candidate: dict,
    top_matches: list,
) -> bool:
    """
    LLM determines if incoming Selenium JavaScript method matches ANY candidate result
    in functional intent + operational workflow.

    Returns:
        True  -> DUPLICATE
        False -> UNIQUE
    """

    # -------------------------------------------------------
    # Safety short-circuit
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
    # BUILD PROMPT USING CORRECT CONFIG KEY
    # -------------------------------------------------------
    try:
        existing_blocks = ""

        for i, match in enumerate(top_matches[:3], start=1):
            doc = match.get("document", {}) or {}

            existing_blocks += f"""
                        METHOD {i}
                        Method Name: {doc.get('method_name', '')}
                        Raw Method:
                        {doc.get('raw_method_code', '')}
                        -----------
                        """

        prompt = settings.Dedupe_Verification_Prompt.format(
            new_method_name=candidate.get("method_name", ""),
            new_raw_method=candidate.get("raw_method_code", ""),
            existing_blocks=existing_blocks,
        )

    except Exception as err:
        logger.exception(f"Method dedupe prompt build failed: {err}")
        return False


    # -------------------------------------------------------
    # Gemini execution with retries
    # -------------------------------------------------------
    try:
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
        except Exception as err:
            logger.warning(f"Method dedupe verifier model init failed: {err}")
            return False

        for attempt in range(max(1, settings.GEMINI_RETRIES)):
            try:
                response = await run_gemini_call(lambda: model.generate_content(prompt))

                try:
                    text = (response.text or "").strip().upper()
                except Exception:
                    text = ""

                if DUPLICATE_TOKEN in text:
                    await asyncio.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)
                    return True

                if "UNIQUE" in text:
                    await asyncio.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)
                    return False

            except Exception as e:
                logger.warning(
                    f"Method dedupe verification attempt {attempt+1} failed: {e}"
                )

                try:
                    await asyncio.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)
                except Exception:
                    pass

    except Exception:
        logger.exception("Method dedupe verifier fatal error")

    return False
