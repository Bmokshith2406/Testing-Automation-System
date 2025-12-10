# app/services/method_madl.py

from __future__ import annotations

import ast
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
# AST Fallback Helpers
# -------------------------------------------------------

def _extract_signature(raw_code: str) -> str:
    """
    Extract full method signature using AST.
    """
    try:
        tree = ast.parse(raw_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                params = [a.arg for a in node.args.args]
                return f"{node.name}({', '.join(params)})"
    except Exception:
        pass

    return "unknown_method()"


def _extract_params(raw_code: str) -> Dict[str, str]:
    """
    Extract parameter map using AST.
    """
    params = {}

    try:
        tree = ast.parse(raw_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for p in node.args.args:
                    params[p.arg] = f"Parameter `{p.arg}` used by this method."
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
    Converts raw Selenium Python method → MADL JSON.
    Prompt comes ONLY from config.
    """

    raw_method = (raw_method or "").strip()
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # -----------------------------
    # FALLBACK FROM AST
    # -----------------------------

    fallback_signature = _extract_signature(raw_method)
    fallback_params = _extract_params(raw_method)
    fallback_keywords = extract_keywords(raw_method, max_keywords=15)

    fallback_madl = {
        "method_name": fallback_signature,
        "raw_method_code": raw_method,
        "method_documentation": {
            "summary": "Selenium utility automation method.",
            "description": "Generic helper function used in Selenium-based workflows.",
            "reusable": True,
            "intent": "Perform browser automation task.",
            "params": fallback_params,
            "applies": "Web elements and browser actions",
            "returns": "None",
            "keywords": fallback_keywords,
            "owner": "QE-Core/Python Automation",
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
                # ✅ FIXED: Use SYNC Gemini call inside semaphore
                response = await run_gemini_call(
                    lambda: model.generate_content(prompt)
                )

                text = (response.text or "").strip()
                madl = _safe_json_parse(text)

                # Minimal validity check
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
