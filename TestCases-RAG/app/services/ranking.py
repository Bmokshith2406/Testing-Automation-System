import re
from typing import List, Dict, Any

import numpy as np

from app.core.config import get_settings
from app.core.logging import logger
from app.services.rerank import rerank_with_gemini


settings = get_settings()


# -----------------------------------------------------
# TRUE Cosine similarity
# -----------------------------------------------------
def _cosine_sim(a, b) -> float:
    try:
        a_arr = np.asarray(a, dtype=np.float32)
        b_arr = np.asarray(b, dtype=np.float32)

        if a_arr.size == 0 or b_arr.size == 0:
            return 0.0

        try:
            denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        except Exception:
            return 0.0

        if denom == 0:
            return 0.0

        try:
            return float(np.dot(a_arr, b_arr) / denom)
        except Exception:
            return 0.0

    except Exception:
        return 0.0


# -----------------------------------------------------
# Tokenizer — lexical intent booster
# -----------------------------------------------------
def _tokenize(text: str):
    try:
        if not text or not isinstance(text, str):
            return set()

        try:
            return set(re.findall(r"\b[\w\-']+\b", text.lower()))
        except Exception:
            return set()

    except Exception:
        return set()


# -----------------------------------------------------
# Candidate generation & scoring
# -----------------------------------------------------
def build_candidates(
    raw_query: str,
    all_expansions: List[str],
    query_vector: List[float],
    search_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    try:
        expansion_tokens = set()
        for ex in all_expansions or []:
            try:
                expansion_tokens.update(_tokenize(ex))
            except Exception:
                continue
    except Exception:
        expansion_tokens = set()

    candidates: List[Dict[str, Any]] = []

    for res in search_results or []:
        try:
            payload = res.get("document", {}) or {}
        except Exception:
            payload = {}

        try:
            base_score = float(res.get("score", 0.0) or 0.0)
        except Exception:
            base_score = 0.0

        # -------------------------------------------------
        # Semantic similarity — EXACT BASELINE LOGIC
        # -------------------------------------------------
        try:
            desc_emb = payload.get("desc_embedding", [])
            steps_emb = payload.get("steps_embedding", [])
            summary_emb = payload.get("summary_embedding", [])
        except Exception:
            desc_emb, steps_emb, summary_emb = [], [], []

        sim_desc = _cosine_sim(query_vector, desc_emb)
        sim_steps = _cosine_sim(query_vector, steps_emb)
        sim_summary = _cosine_sim(query_vector, summary_emb)

        try:
            semantic_max = max(sim_desc, sim_steps, sim_summary)
        except Exception:
            semantic_max = 0.0


        # -------------------------------------------------
        # Lexical boosts — BASELINE SOURCE FIELDS
        # -------------------------------------------------
        try:
            keywords = [
                str(k).lower()
                for k in payload.get("TestCaseKeywords", []) or []
            ]
        except Exception:
            keywords = []

        try:
            text_fields = (
                f'{payload.get("Feature","")} '
                f'{payload.get("Test Case Description","")} '
                f'{payload.get("Steps","")}'
            ).lower()
        except Exception:
            text_fields = ""

        text_tokens = _tokenize(text_fields)

        token_boost = 0.0

        for tok in expansion_tokens:
            try:
                if tok in text_tokens:
                    token_boost += 0.10
                if tok in keywords:
                    token_boost += 0.15
            except Exception:
                continue

        # Clamp boost so token spam cannot dominate ranking
        try:
            max_possible_boost = max(len(expansion_tokens), 1)
            token_boost = min(token_boost, max_possible_boost * 0.15)
        except Exception:
            pass


        # -------------------------------------------------
        # PRIMARY SCORE FORMULA (Variant A) — BASELINE
        # -------------------------------------------------
        try:
            score_v1 = (
                0.60 * base_score +
                0.25 * semantic_max +
                token_boost
            )
        except Exception:
            score_v1 = 0.0


        # -------------------------------------------------
        # OPTIONAL: Variant B (kept for experimentation)
        # -------------------------------------------------
        try:
            popularity = float(payload.get("Popularity", 0.0) or 0.0)
        except Exception:
            popularity = 0.0

        try:
            popularity_boost = min(popularity / 100.0, 0.10)
        except Exception:
            popularity_boost = 0.0

        feature_match = 0.0
        try:
            if payload.get("Feature") and any(
                tok in payload.get("Feature", "").lower()
                for tok in expansion_tokens
            ):
                feature_match = 1.0
        except Exception:
            feature_match = 0.0

        try:
            keyword_overlap = len([k for k in keywords if k in expansion_tokens])
        except Exception:
            keyword_overlap = 0

        try:
            score_v2 = (
                0.45 * base_score
                + 0.20 * semantic_max
                + 0.12 * min(keyword_overlap, 5) / 5.0
                + 0.08 * feature_match
                + 0.05 * token_boost
                + 0.05 * popularity_boost
            )
        except Exception:
            score_v2 = 0.0


        try:
            candidates.append(
                {
                    "_id": payload.get("_id") or payload.get("id"),
                    "raw_score": base_score,
                    "local_score_v1": float(score_v1),
                    "local_score_v2": float(score_v2),

                    "feature": payload.get("Feature", "N/A"),
                    "test_case_id": payload.get("Test Case ID", "NA"),

                    "description": payload.get(
                        "Test Case Description",
                        payload.get("description", ""),
                    ),

                    "summary": payload.get(
                        "TestCaseSummary",
                        payload.get("summary", ""),
                    ),

                    "keywords": payload.get(
                        "TestCaseKeywords",
                        payload.get("keywords", []),
                    ),

                    "payload": payload,
                }
            )
        except Exception as err:
            logger.warning(f"Failed building candidate record: {err}")

    return candidates


# -----------------------------------------------------
# Score normalization
# -----------------------------------------------------
def _normalize_scores(
    candidates: List[Dict[str, Any]],
    key: str,
):

    try:
        if not candidates:
            return

        try:
            scores = np.array(
                [c[key] for c in candidates],
                dtype=np.float32,
            )
        except Exception:
            return

        try:
            min_s = float(scores.min())
            max_s = float(scores.max())
        except Exception:
            return

        if max_s - min_s > 1e-12:
            for c in candidates:
                try:
                    c["local_score_norm"] = (
                        (c[key] - min_s) / (max_s - min_s)
                    )
                except Exception:
                    c["local_score_norm"] = 0.0
        else:
            for c in candidates:
                try:
                    c["local_score_norm"] = 1.0
                except Exception:
                    c["local_score_norm"] = 1.0

    except Exception:
        return


# -----------------------------------------------------
# Final Selection — GEMINI AUTHORITY PRESERVED
# -----------------------------------------------------
def select_final_results(
    raw_query: str,
    candidates: List[Dict[str, Any]],
    ranking_variant: str = "A",
    use_gemini_rerank: bool = True,
    final_results: int = 3,
    **_,
) -> List[Dict[str, Any]]:

    try:
        if not candidates:
            return []

        try:
            score_key = (
                "local_score_v1"
                if ranking_variant.upper() == "A"
                else "local_score_v2"
            )
        except Exception:
            score_key = "local_score_v1"

        _normalize_scores(candidates, score_key)

        # Rough ordering before Gemini
        try:
            candidates.sort(
                key=lambda x: x[score_key],
                reverse=True,
            )
        except Exception:
            pass

        try:
            top_candidates = candidates[
                : settings.CANDIDATES_TO_RETRIEVE
            ]
        except Exception:
            top_candidates = candidates

        # AUTHORITATIVE LLM RERANK
        if use_gemini_rerank:
            try:
                reranked = rerank_with_gemini(
                    raw_query,
                    top_candidates,
                )
                return reranked[:final_results]

            except Exception as e:
                logger.warning(f"Gemini rerank failed: {e}")

        # Fallback heuristic order
        return top_candidates[:final_results]

    except Exception:
        return []
