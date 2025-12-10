from typing import List, Dict, Any
import re

import google.generativeai as genai

from app.core.config import get_settings
from app.core.logging import logger
from app.services.gemini_semaphore import run_gemini_call

settings = get_settings()


# --------------------------------------------------------
# Line normalization
# --------------------------------------------------------
def safe_parse_lines(text: str) -> List[str]:
    """
    Extract meaningful non-empty lines only.
    Cleans numbering / bullets automatically.
    Robust against varied Gemini formatting.
    """

    lines: List[str] = []

    try:
        if not text or not isinstance(text, str):
            return lines

        for l in text.splitlines():
            try:
                l = l.strip()
            except Exception:
                continue

            if not l:
                continue

            # remove bullets / numbering
            try:
                l = re.sub(r"^[\-\*\d\.\)\s]+", "", l)
            except Exception:
                pass

            if l:
                lines.append(l)

    except Exception as err:
        logger.warning(f"safe_parse_lines failed: {err}")
        return []

    return lines


# --------------------------------------------------------
# GEMINI RERANK — STRING PROMPT VERSION (METHOD)
# --------------------------------------------------------
async def rerank_with_gemini(
    query: str,
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    # Fallback to local ranking if Gemini disabled
    try:
        if not settings.GEMINI_RERANK_ENABLED or not settings.GOOGLE_API_KEY:
            return candidates
    except Exception:
        return candidates

    try:
        if not candidates:
            return candidates
    except Exception:
        return candidates

    try:
        # ------------------------------------------------
        # Model initialization
        # ------------------------------------------------
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
        except Exception as err:
            logger.warning(f"Gemini model initialization failed: {err}")
            return candidates

        # ------------------------------------------------
        # Build prompt as ONE STRING (no prompt_lines)
        # ------------------------------------------------
        try:
            prompt = settings.Results_ReRanking_Prompt.format(
                query=query
            )
        except Exception as err:
            logger.warning(f"Prompt formatting failed: {err}")
            return candidates

        # ------------------------------------------------
        # Attach METHOD candidates to prompt
        # ------------------------------------------------
        for c in candidates:
            try:
                brief = (
                    c.get("summary")
                    or c.get("method_documentation", {}).get("summary", "")
                    or ""
                )

                brief = brief.strip().replace("\n", " ")[:220]

                prompt += (
                    f"{c['_id']} | Method: {c.get('method_name','N/A')} | "
                    f"Summary: {brief}\n"
                )
            except Exception as err:
                logger.warning(
                    f"Prompt composition failed for candidate {c.get('_id')}: {err}"
                )

        # ------------------------------------------------
        # Gemini call (ASYNC SAFE — FIXED)
        # ------------------------------------------------
        try:
            response = await run_gemini_call(
                lambda: model.generate_content(prompt)
            )
        except Exception as err:
            logger.warning(f"Gemini API call failed: {err}")
            return candidates

        try:
            text = (response.text or "").strip()
        except Exception as err:
            logger.warning(f"Gemini response parsing failed: {err}")
            return candidates

        # ------------------------------------------------
        # Output parsing
        # ------------------------------------------------
        lines = safe_parse_lines(text)

        ordered_ids: List[str] = []

        for l in lines:
            try:
                cid = l.split()[0].strip(".,-_ ")
                if cid:
                    ordered_ids.append(cid)
            except Exception:
                continue

        # ------------------------------------------------
        # Rebuild ranked results
        # ------------------------------------------------
        try:
            id_to_candidate = {
                str(c["_id"]): c
                for c in candidates
            }
        except Exception:
            id_to_candidate = {}

        ordered: List[Dict[str, Any]] = []
        seen_ids = set()

        for cid in ordered_ids:
            try:
                if cid in id_to_candidate and cid not in seen_ids:
                    ordered.append(id_to_candidate[cid])
                    seen_ids.add(cid)
            except Exception:
                continue

        # ------------------------------------------------
        # Append leftovers preserving stability
        # ------------------------------------------------
        for cand in candidates:
            try:
                if str(cand.get("_id")) not in seen_ids:
                    ordered.append(cand)
            except Exception:
                continue

        return ordered

    except Exception as e:
        logger.warning(f"Gemini rerank failed: {e}")
        return candidates
