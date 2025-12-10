import time

import google.generativeai as genai

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


# -------------------------------------------------------
# Gemini: 12-word dedupe summary generator
# -------------------------------------------------------

async def generate_dedupe_summary(
    feature: str,
    description: str,
    steps: str,
) -> str:
    """
    Generates STRICT 12-word functional-purpose summary used only
    for semantic search dedupe.
    """

    try:
        feature_text = (feature or "").strip()
        description_text = (description or "").strip()
        steps_text = (steps or "").strip()
    except Exception:
        feature_text = ""
        description_text = ""
        steps_text = ""


    # -------------------------------------------------------
    # Hard fallback → pure truncation-based text
    # -------------------------------------------------------
    fallback = " ".join(
        (description_text + " " + steps_text).split()
    )[:80]


    # -------------------------------------------------------
    # Gemini disabled → fallback only
    # -------------------------------------------------------
    try:
        if not settings.GOOGLE_API_KEY:
            return fallback
    except Exception:
        return fallback


    # -------------------------------------------------------
    # ✅ CENTRALIZED PROMPT TEMPLATE
    # -------------------------------------------------------
    try:
        prompt = settings.Dedupe_Summary_Prompt.format(
            feature=feature_text,
            description_text=description_text,
            steps_text=steps_text,
        )
    except Exception as err:
        logger.warning(f"Dedupe prompt build failed: {err}")
        return fallback


    # -------------------------------------------------------
    # Gemini execution with retries
    # -------------------------------------------------------

    try:
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
        except Exception as err:
            logger.warning(f"Dedupe model init failed: {err}")
            return fallback


        for attempt in range(max(1, settings.GEMINI_RETRIES)):
            try:

                response = model.generate_content(prompt)

                try:
                    text = (response.text or "").strip()
                except Exception:
                    text = ""

                words = text.split()

                if len(words) >= 8:
                    # Force exact 12-word output regardless of LLM variation
                    final = " ".join(words[:12])
                    return final.strip()

            except Exception as e:
                logger.warning(
                    f"Dedupe summary attempt {attempt+1} failed: {e}"
                )

                try:
                    time.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)
                except Exception:
                    pass


    except Exception:
        logger.error("Dedupe summary fatal error", exc_info=True)


    return fallback
