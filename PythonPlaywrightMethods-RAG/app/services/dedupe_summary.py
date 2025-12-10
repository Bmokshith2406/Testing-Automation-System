import google.generativeai as genai
import asyncio


from app.core.config import get_settings
from app.core.logging import logger
from app.services.gemini_semaphore import run_gemini_call


settings = get_settings()


# -------------------------------------------------------
# Gemini: 10–12-word dedupe summary generator (METHOD)
# -------------------------------------------------------

async def generate_method_dedupe_summary(
    raw_method: str,
) -> str:
    """
    Generates STRICT 10–12 word functional-purpose summary from raw Playwright Python
    method source code used only for semantic dedupe.
    """

    try:
        raw_method_text = (raw_method or "").strip()
    except Exception:
        raw_method_text = ""

    # -------------------------------------------------------
    # Hard fallback → simple truncation
    # -------------------------------------------------------
    fallback = " ".join(raw_method_text.split())[:80]


    # -------------------------------------------------------
    # Gemini disabled → fallback only
    # -------------------------------------------------------
    try:
        if not settings.GOOGLE_API_KEY:
            return fallback
    except Exception:
        return fallback


    # -------------------------------------------------------
    # USE CORRECT PROMPT FROM CONFIG
    # -------------------------------------------------------
    try:
        prompt = settings.Dedupe_Summary_Prompt.format(
            raw_method=raw_method_text,
        )
    except Exception as err:
        logger.warning(f"Method dedupe prompt build failed: {err}")
        return fallback


    # -------------------------------------------------------
    # Gemini execution with retries
    # -------------------------------------------------------
    try:
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
        except Exception as err:
            logger.warning(f"Method dedupe model init failed: {err}")
            return fallback

        for attempt in range(max(1, settings.GEMINI_RETRIES)):
            try:
                response = await run_gemini_call(lambda: model.generate_content(prompt))

                try:
                    text = (response.text or "").strip()
                except Exception:
                    text = ""

                words = text.split()

                # STRICT 10–12 word window
                if len(words) >= 10:
                    return " ".join(words[:12]).strip()

            except Exception as e:
                logger.warning(
                    f"Method dedupe summary attempt {attempt+1} failed: {e}"
                )
                try:
                    await asyncio.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)
                except Exception:
                    pass

    except Exception:
        logger.error("Method dedupe summary fatal error", exc_info=True)

    return fallback
