# app/services/method_madl.py

from __future__ import annotations

import json
import asyncio
from datetime import datetime
from typing import Dict, Any

import google.generativeai as genai

from app.core.config import get_settings
from app.core.logging import logger
from app.services.keywords import extract_keywords
from app.services.gemini_semaphore import run_gemini_call

settings = get_settings()


# -------------------------------------------------------
# JAVASCRIPT FALLBACK HELPERS (REGEX BASED)
# -------------------------------------------------------

def _extract_signature(raw_code: str) -> str:
    """
    Extract full JavaScript function signature using regex.
    Supports:
      - function name(args)
      - async function name(args)
      - const name = (args) =>
      - const name = async (args) =>
    """
    try:
        import re

        patterns = [
            r"(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\)",
            r"(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>",
        ]

        for p in patterns:
            m = re.search(p, raw_code)
            if m:
                name = m.group(1)
                params = m.group(2).strip()
                return f"{name}({params})"

    except Exception:
        pass

    return "unknownMethod()"


def _extract_params(raw_code: str) -> Dict[str, str]:
    """
    Extract parameter map for JavaScript functions using regex.
    """
    params: Dict[str, str] = {}

    try:
        import re

        patterns = [
            r"(?:async\s+)?function\s+[A-Za-z0-9_$]+\s*\(([^)]*)\)",
            r"(?:const|let|var)\s+[A-Za-z0-9_$]+\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>",
        ]

        for p in patterns:
            m = re.search(p, raw_code)
            if m:
                raw_params = m.group(1)
                for p in [x.strip() for x in raw_params.split(",") if x.strip()]:
                    params[p] = f"Parameter `{p}` used by this method."
                break

    except Exception:
        pass

    return params


# -------------------------------------------------------
# JSON Parser
# -------------------------------------------------------

def _safe_json_parse(text: str) -> Dict[str, Any]:
    """
    Safely parse Gemini JSON output.
    """
    try:
        return json.loads(text)
    except Exception:
        pass

    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception:
        pass

    return {}


# -------------------------------------------------------
# CORE MADL GENERATION ENTRYPOINT
# -------------------------------------------------------

async def get_method_madl(raw_method: str) -> Dict[str, Any]:
    """
    Converts raw Playwright *JavaScript* method → MADL JSON.
    Prompt comes ONLY from config.
    """

    raw_method = (raw_method or "").strip()
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # -----------------------------
    # FALLBACK FROM REGEX
    # -----------------------------

    fallback_signature = _extract_signature(raw_method)
    fallback_params = _extract_params(raw_method)
    fallback_keywords = extract_keywords(raw_method, max_keywords=15)

    fallback_madl = {
        "method_name": fallback_signature,
        "raw_method_code": raw_method,
        "method_documentation": {
            "summary": "Playwright JavaScript utility automation method.",
            "description": "Generic helper function used in Playwright automation workflows.",
            "reusable": True,
            "intent": "Perform browser automation task.",
            "params": fallback_params,
            "applies": "Web elements and browser actions",
            "returns": "Promise<void>",
            "keywords": fallback_keywords,
            "owner": "QE-Core/Playwright JavaScript Automation",
            "example_usage": fallback_signature,
            "created": today,
            "last_updated": today,
        },
    }

    # -----------------------------
    # Gemini Disabled → Fallback
    # -----------------------------

    if not settings.GOOGLE_API_KEY:
        return fallback_madl

    # -----------------------------
    # Build Prompt from Config
    # -----------------------------

    try:
        prompt = settings.Method_MADL_Prompt.format(
            raw_method=raw_method
        )
    except Exception as err:
        logger.warning(f"MADL prompt build failed: {err}")
        return fallback_madl

    # -----------------------------
    # LLM Execution
    # -----------------------------

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        for attempt in range(max(1, settings.GEMINI_RETRIES)):
            try:
                response = await run_gemini_call(
                    lambda: model.generate_content(prompt)
                )

                text = (response.text or "").strip()
                madl = _safe_json_parse(text)

                if (
                    madl
                    and "method_name" in madl
                    and "method_documentation" in madl
                ):
                    madl["raw_method_code"] = raw_method

                    md = madl["method_documentation"]
                    md["created"] = md.get("created") or today
                    md["last_updated"] = today

                    await asyncio.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)

                    return madl

            except Exception as err:
                logger.warning(f"MADL Gemini attempt {attempt+1} failed: {err}")
                await asyncio.sleep(settings.GEMINI_RATE_LIMIT_SLEEP)

    except Exception:
        logger.error("MADL generation fatal error", exc_info=True)

    # -----------------------------
    # FINAL FALLBACK
    # -----------------------------

    return fallback_madl
