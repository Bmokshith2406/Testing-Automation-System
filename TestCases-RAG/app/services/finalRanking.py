# app/services/finalRanking.py

from typing import List
import re
import google.generativeai as genai

from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import SearchResultItem

settings = get_settings()


# ----------------------------------------------------
# Utilities
# ----------------------------------------------------

def _safe_parse_lines(text: str) -> List[str]:
    """
    Extract meaningful non-empty lines from LLM output.
    Safely removes bullets / numbering WITHOUT destroying UUIDs.
    Includes high-defensive checks to prevent malformed processing.
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
# FINAL LLM INTENT RANKER + REAL PROBABILITY SCORING
# ----------------------------------------------------

async def final_llm_rerank(
    query: str,
    results: List[SearchResultItem],
    top_k: int | None = None,
) -> List[SearchResultItem]:
    """
    FINAL LLM STAGE:

    - Gemini sees full test cases.
    - LLM chooses TOP-K results by intent only.
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
            return results[:top_k]

        # ------------------------------------------------
        # Build prompt (not logged)
        # ------------------------------------------------
        try:
            prompt = settings.Final_Ranking_Prompt.format(
                query=query,
                top_k=top_k,
            )
        except Exception:
            return results[:top_k]

        for r in results:
            try:
                prompt += f"""
-------------------------------------------------
ID: {r.id}
Feature: {r.feature}
Description: {r.description}

Prerequisites:
{r.prerequisites}

Steps:
{r.steps}

Summary:
{r.summary}

Keywords:
{", ".join(r.keywords or [])}
-------------------------------------------------
"""
            except Exception:
                pass

        # ------------------------------------------------
        # Gemini call (response not logged)
        # ------------------------------------------------
        try:
            response = model.generate_content(prompt)
        except Exception:
            return results[:top_k]

        try:
            raw_output = (response.text or "").strip()
        except Exception:
            return results[:top_k]

        ranked_items = []

        # ------------------------------------------------
        # Parse LLM response
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
            # silently skip bad lines
                pass

        # ------------------------------------------------
        # Ranking sanity
        # ------------------------------------------------
        if not ranked_items:
            return results[:top_k]

        ranked_items = ranked_items[:top_k]

        try:
            id_map = {str(r.id): r for r in results}
        except Exception:
            return results[:top_k]

        final_results: List[SearchResultItem] = []

        for _id, score in ranked_items:
            try:
                if _id in id_map:
                    item = id_map[_id]
                    item.probability = round(score, 2)
                    final_results.append(item)
            except Exception:
                pass

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
                    pass

        # ------------------------------------------------
        # FINAL RESULT LOG (SAFE)
        # ------------------------------------------------
        try:
            logger.info(f"Gemini rerank completed with {len(final_results)} results.")
        except Exception:
            pass

        return final_results

    except Exception:
        return results[:top_k]
