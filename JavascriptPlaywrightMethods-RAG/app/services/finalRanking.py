# app/services/finalRanking.py

from typing import List
import re
import google.generativeai as genai

from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import SearchResultItem
from app.services.gemini_semaphore import run_gemini_call

settings = get_settings()


# ----------------------------------------------------
# Utilities
# ----------------------------------------------------

def _safe_parse_lines(text: str) -> List[str]:
    """
    Extract meaningful non-empty lines from LLM output.
    Safely removes bullets / numbering WITHOUT destroying UUIDs.
    """
    lines: List[str] = []

    try:
        if not isinstance(text, str):
            return lines

        for l in text.splitlines():
            try:
                l = l.strip()
            except Exception:
                continue

            if not l:
                continue

            # Remove numbering bullets like "1. ", "2) "
            try:
                l = re.sub(r"^(\d+[\.\)]\s*)", "", l)
            except Exception:
                pass

            # Remove dash / star bullets like "- ", "* "
            try:
                l = re.sub(r"^[\*\-]\s*", "", l)
            except Exception:
                pass

            if l:
                lines.append(l)

    except Exception:
        return []

    return lines


# ----------------------------------------------------
# FINAL LLM METHOD RERANKER + REAL PROBABILITY SCORING
# ----------------------------------------------------

async def final_llm_rerank(
    query: str,
    results: List[SearchResultItem],
    top_k: int | None = None,
) -> List[SearchResultItem]:
    """
    FINAL LLM STAGE – METHOD SEARCH:

    - Gemini sees MADL metadata for each method.
    - LLM chooses TOP-K methods by intent relevance only.
    - LLM assigns REAL confidence scores (0–100).
    - Probabilities are injected into result objects.
    """

    try:
        top_k = top_k or settings.TOP_K
    except Exception:
        top_k = settings.TOP_K

    # ------------------------------------------------
    # Early exit safety gate
    # ------------------------------------------------
    try:
        if (
            not settings.GEMINI_RERANK_ENABLED
            or not settings.GOOGLE_API_KEY
            or not results
            or len(results) <= 1
        ):
            return results[:top_k]
    except Exception:
        return results[:top_k]

    try:
        # ------------------------------------------------
        # Model initialization
        # ------------------------------------------------
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
        except Exception:
            logger.exception("Failed to initialize Gemini model")
            return results[:top_k]

        # ------------------------------------------------
        # Build base prompt
        # ------------------------------------------------
        try:
            prompt = settings.Final_Ranking_Prompt.format(
                query=query,
                top_k=top_k,
            )
        except Exception:
            logger.exception("Failed to build reranking prompt")
            return results[:top_k]

        # ------------------------------------------------
        # Attach MADL data to prompt
        # ------------------------------------------------
        for r in results:
            try:
                prompt += f"""
-------------------------------------------------
ID: {r.id}
Method Name: {r.method_name}

Summary:
{r.summary}

Description:
{r.description}

Intent:
{r.intent}

Parameters:
{", ".join([f"{k}: {v}" for k, v in (r.params or {}).items()])}

Keywords:
{", ".join(r.keywords or [])}
-------------------------------------------------
"""
            except Exception:
                continue

        # ------------------------------------------------
        # Gemini call (ASYNC SAFE — FIXED)
        # ------------------------------------------------
        try:
            response = await run_gemini_call(
                lambda: model.generate_content(prompt)
            )
        except Exception:
            logger.exception("Gemini rerank call failed")
            return results[:top_k]

        try:
            raw_output = (response.text or "").strip()
        except Exception:
            logger.exception("Failed reading Gemini response")
            return results[:top_k]

        ranked_items = []

        # ------------------------------------------------
        # Parse Gemini output
        # ------------------------------------------------
        for line in _safe_parse_lines(raw_output):
            try:
                parts = [p.strip() for p in line.split("|")]

                if len(parts) != 2:
                    continue

                _id, score_text = parts

                try:
                    score = float(score_text)
                except Exception:
                    continue

                score = max(0.0, min(100.0, score))
                ranked_items.append((_id, score))

            except Exception:
                continue

        # ------------------------------------------------
        # Ranking sanity
        # ------------------------------------------------
        if not ranked_items:
            return results[:top_k]

        ranked_items = ranked_items[:top_k]

        try:
            id_map = {str(r.id): r for r in results}
        except Exception:
            logger.exception("Failed building ID map")
            return results[:top_k]

        final_results: List[SearchResultItem] = []

        for _id, score in ranked_items:
            try:
                if _id in id_map:
                    item = id_map[_id]
                    item.probability = round(score, 2)
                    final_results.append(item)
            except Exception:
                continue

        # ------------------------------------------------
        # Fallback fill
        # ------------------------------------------------
        if len(final_results) < top_k:
            for r in results:
                try:
                    if r not in final_results:
                        r.probability = round(r.probability or 50.0, 2)
                        final_results.append(r)

                    if len(final_results) == top_k:
                        break
                except Exception:
                    continue

        # ------------------------------------------------
        # Final log
        # ------------------------------------------------
        try:
            logger.info(
                f"Gemini method rerank completed with {len(final_results)} results."
            )
        except Exception:
            pass

        return final_results

    except Exception:
        logger.exception("Uncaught reranking failure")
        return results[:top_k]
