import time
import re
from typing import Tuple, List, Dict, Any

import google.generativeai as genai

from app.core.config import get_settings
from app.core.logging import logger
from app.services.keywords import extract_keywords, build_fallback_summary


settings = get_settings()


# -------------------------------------------------------
# Clean Gemini text output
# -------------------------------------------------------

def _parse_gemini_enrichment_text(text: str) -> Tuple[str, List[str]]:
    """
    Ground-truth parser for Gemini enrichment output.
    """

    summary = ""
    keywords: List[str] = []

    collecting_summary = False
    summary_lines: List[str] = []

    try:
        if not text or not isinstance(text, str):
            return "", []

        for line in text.splitlines():
            try:
                l = line.strip()
                lower = l.lower()

                if lower.startswith("summary:"):
                    collecting_summary = True
                    raw = l.split(":", 1)[1].strip()
                    if raw:
                        summary_lines.append(raw)
                    continue

                if lower.startswith("keywords:"):
                    collecting_summary = False
                    raw_kw = l.split(":", 1)[1]

                    try:
                        keywords = [
                            re.sub(r"^[\-\*\d\.\)\s]+", "", k.strip())
                            for k in raw_kw.split(",")
                            if len(k.strip()) >= 2
                        ]
                    except Exception:
                        keywords = []

                    continue

                if collecting_summary and l:
                    summary_lines.append(l)

            except Exception:
                continue

        # ---- Final summary cleanup

        try:
            if summary_lines:
                summary = " ".join(summary_lines)
                summary = " ".join(summary.split())[:900]
        except Exception:
            summary = ""

        try:
            if not summary:
                parts = [p.strip() for p in text.split("\n\n") if p.strip()]
                if parts:
                    summary = parts[0][:800]
        except Exception:
            pass

        # ---- Keyword fallback ONLY if Gemini fails

        try:
            if not keywords:
                keywords = extract_keywords(text, max_keywords=15)
        except Exception:
            keywords = []

        # ---- Clean keywords

        try:
            keywords = [
                k for k in keywords
                if not str(k).lower().startswith("keywords:")
            ]
        except Exception:
            pass

        try:
            keywords = list(dict.fromkeys(keywords))[:20]
        except Exception:
            keywords = keywords[:20]

        return summary.strip(), keywords

    except Exception:
        return "", []


# -------------------------------------------------------
# Gemini enrichment entrypoint — BASELINE-COMPATIBLE
# -------------------------------------------------------

def get_gemini_enrichment(
    test_case_description: str,
    feature: str,
    steps: str = "",
) -> Dict[str, Any]:

    try:
        description_text = (test_case_description or "").strip()
    except Exception:
        description_text = ""

    try:
        steps_text = (steps or "").strip()
    except Exception:
        steps_text = ""

    try:
        fallback_summary = build_fallback_summary(
            description_text,
            steps_text,
            max_sentences=2,
        )
    except Exception:
        fallback_summary = ""

    try:
        fallback_keywords = extract_keywords(
            (description_text + " " + steps_text + " " + fallback_summary).strip(),
            max_keywords=15,
        )
    except Exception:
        fallback_keywords = []


    # -------------------------------------------------------
    # Gemini disabled → pure fallback
    # -------------------------------------------------------

    try:
        if not settings.GOOGLE_API_KEY:
            return {
                "summary": fallback_summary,
                "keywords": fallback_keywords,
            }
    except Exception:
        return {
            "summary": fallback_summary,
            "keywords": fallback_keywords,
        }


    # -------------------------------------------------------
    # SIMPLE BASELINE PROMPT
    # -------------------------------------------------------

    try:
        prompt = settings.TestCase_Enrichment_Prompt.format(
            feature=feature,
            description_text=description_text,
            steps_text=steps_text
        )
    except Exception as err:
        logger.warning(f"Gemini enrichment prompt build failed: {err}")
        return {
            "summary": fallback_summary,
            "keywords": fallback_keywords,
        }


    # -------------------------------------------------------
    # Gemini execution with retries
    # -------------------------------------------------------

    try:
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
        except Exception as err:
            logger.warning(f"Gemini model initialization failed: {err}")
            return {
                "summary": fallback_summary,
                "keywords": fallback_keywords,
            }

        for attempt in range(max(1, settings.GEMINI_RETRIES)):
            try:
                response = model.generate_content(prompt)

                try:
                    text = (response.text or "").strip()
                except Exception:
                    text = ""

                summary, keywords = _parse_gemini_enrichment_text(text)

                if summary and len(summary) > 30 and len(keywords) >= 3:
                    try:
                        time.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)
                    except Exception:
                        pass

                    return {
                        "summary": summary,
                        "keywords": keywords,
                    }

            except Exception as e:
                logger.warning(
                    f"Gemini enrichment attempt {attempt+1} failed: {e}"
                )

                try:
                    time.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)
                except Exception:
                    pass


        # -------------------------------------------------------
        # Final attempt + fallback merge
        # -------------------------------------------------------

        try:
            response = model.generate_content(prompt)

            try:
                text = (response.text or "").strip()
            except Exception:
                text = ""

            summary, keywords = _parse_gemini_enrichment_text(text)

            if not summary:
                summary = fallback_summary

            if not keywords or len(keywords) < 3:
                try:
                    keywords = list(dict.fromkeys(
                        (keywords or []) + fallback_keywords
                    ))[:15]
                except Exception:
                    keywords = fallback_keywords[:15]

            try:
                time.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)
            except Exception:
                pass

            return {
                "summary": summary,
                "keywords": keywords,
            }

        except Exception:
            return {
                "summary": fallback_summary,
                "keywords": fallback_keywords,
            }

    except Exception as e:
        logger.error(
            f"Gemini enrichment fatal error: {e}",
            exc_info=True,
        )

        return {
            "summary": fallback_summary,
            "keywords": fallback_keywords,
        }
