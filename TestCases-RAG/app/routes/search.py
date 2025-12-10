from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Body

from app.core.cache import cache_get, cache_set
from app.core.config import get_settings
from app.core.logging import logger
from app.core.analytics import log_api_call

from app.db.mongo import get_testcase_collection
from app.models.schemas import SearchResponse, SearchRequest, SearchResultItem

from app.services.embeddings import embed_text
from app.services.expansion import normalize_query, expand_query
from app.services.ranking import build_candidates, select_final_results

# FINAL LLM RERANKER
from app.services.finalRanking import final_llm_rerank

router = APIRouter()
settings = get_settings()


# -------------------------------------------------------------------
# SEARCH API
# -------------------------------------------------------------------

@router.post("/search", response_model=SearchResponse)
async def search_test_cases(payload: SearchRequest = Body(...)):

    col = get_testcase_collection()

    try:
        raw_query = (payload.query or "").strip()
    except Exception:
        raw_query = ""

    if not raw_query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    try:
        feature_filter = (payload.feature or "").strip() or None
    except Exception:
        feature_filter = None

    try:
        ranking_variant = (payload.ranking_variant or "A").upper()
    except Exception:
        ranking_variant = "A"

    cache_key = f"{raw_query}::feature={feature_filter}::rank={ranking_variant}"

    # ================================================================
    # CACHE HIT
    # ================================================================
    try:
        cached = cache_get(cache_key)
    except Exception:
        cached = None

    if cached:
        logger.info(f"Cache hit: '{raw_query}'")
        return SearchResponse(**{**cached, "from_cache": True})

    # ================================================================
    # STEP 1 — Normalize & expand
    # ================================================================
    try:
        normalized = normalize_query(raw_query)
    except Exception:
        normalized = raw_query

    try:
        expansions = (
            expand_query(normalized, n=settings.QUERY_EXPANSIONS)
            if settings.QUERY_EXPANSION_ENABLED
            else [normalized]
        )
    except Exception:
        expansions = [normalized]

    try:
        all_expansions = list(dict.fromkeys([normalized] + expansions))
    except Exception:
        all_expansions = [normalized]

    try:
        combined_query = " ".join(all_expansions)
    except Exception:
        combined_query = normalized

    logger.info(f"Normalized   : {normalized}")
    logger.info(f"Expansions   : {all_expansions}")
    logger.info(f"Combined vec : {combined_query}")

    # ================================================================
    # STEP 2 — Embed query
    # ================================================================
    try:
        query_vector = embed_text(combined_query)
    except Exception:
        logger.exception("Embedding failure")
        raise HTTPException(
            status_code=500,
            detail="Embedding computation failed",
        )

    # ================================================================
    # STEP 3 — Mongo vector search
    # ================================================================
    try:
        search_spec: Dict[str, Any] = {
            "index": settings.VECTOR_INDEX_NAME,
            "path": "main_vector",
            "queryVector": query_vector,
            "numCandidates": 150,
            "limit": settings.CANDIDATES_TO_RETRIEVE,
        }

        if feature_filter:
            search_spec["filter"] = {
                "Feature": {"$eq": feature_filter}
            }

        pipeline = [
            {"$vectorSearch": search_spec},
            {"$project": {
                "score": {"$meta": "vectorSearchScore"},
                "document": "$$ROOT",
            }},
        ]
    except Exception as err:
        logger.exception(f"Pipeline assembly failed: {err}")
        raise HTTPException(
            status_code=500,
            detail="Search pipeline failed",
        )

    try:
        search_results = await col.aggregate(
            pipeline
        ).to_list(length=settings.CANDIDATES_TO_RETRIEVE)

    except Exception:
        logger.exception("Mongo vector search failure")
        raise HTTPException(
            status_code=500,
            detail="Vector search failed",
        )

    # ================================================================
    # NO RESULTS
    # ================================================================
    if not search_results:

        empty = {
            "query": raw_query,
            "feature_filter": feature_filter,
            "results_count": 0,
            "results": [],
            "ranking_variant": ranking_variant,
        }

        try:
            cache_set(cache_key, empty)
        except Exception:
            pass

        return SearchResponse(**{
            **empty,
            "from_cache": False,
        })

    # ================================================================
    # STEP 4 — MULTI-SIM + INITIAL GEMINI RANKING
    # ================================================================
    try:
        candidates = build_candidates(
            raw_query=raw_query,
            all_expansions=all_expansions,
            query_vector=query_vector,
            search_results=search_results,
        )
    except Exception as err:
        logger.exception(f"Candidate build failed: {err}")
        raise HTTPException(
            status_code=500,
            detail="Scoring failed",
        )

    try:
        final_list = select_final_results(
            raw_query=raw_query,
            candidates=candidates,
            ranking_variant=ranking_variant,
            use_gemini_rerank=settings.GEMINI_RERANK_ENABLED,
            final_results=settings.FINAL_RESULTS,
        )
    except Exception as err:
        logger.exception(f"Final candidate selection failed: {err}")
        raise HTTPException(
            status_code=500,
            detail="Result ranking failed",
        )

    # ================================================================
    # STEP 5 — RESPONSE MAPPING
    # ================================================================
    response_items: List[SearchResultItem] = []

    try:
        total = max(len(final_list), 1)
    except Exception:
        total = 1

    for rank, c in enumerate(final_list or [], start=1):
        try:
            # local probability calc — WILL BE OVERWRITTEN by final LLM stage
            rank_weight = (total - rank + 1) / total
            norm_sim = float(c.get("local_score_norm", 0.0))

            score_pct = round(
                (0.6 * norm_sim + 0.4 * rank_weight) * 100,
                2,
            )

            payload_doc = c.get("payload", {}) or {}

            response_items.append(
                SearchResultItem(
                    id=str(payload_doc.get("_id") or payload_doc.get("id")),
                    probability=score_pct,   # provisional score
                    test_case_id=payload_doc.get("Test Case ID", "NA"),
                    feature=payload_doc.get("Feature", "N/A"),
                    description=payload_doc.get("Test Case Description", ""),
                    prerequisites=payload_doc.get("Pre-requisites", ""),
                    steps=payload_doc.get("Steps", ""),
                    summary=payload_doc.get("TestCaseSummary", ""),
                    keywords=payload_doc.get("TestCaseKeywords", []),
                    tags=payload_doc.get("Tags", []),
                    priority=payload_doc.get("Priority"),
                    platform=payload_doc.get("Platform"),
                )
            )
        except Exception:
            continue

    # ================================================================
    # STEP 5.5 — FINAL INTENT-ONLY LLM RERANK + REAL PROBABILITY
    # ================================================================
    try:
        response_items = await final_llm_rerank(
            query=raw_query,
            results=response_items
            # top_k auto-read from settings.TOP_K
        )
    except Exception:
        logger.exception("Final LLM ranking failed — keeping base ordering")

    # ================================================================
    # STEP 5.6 — FORCE FINAL ORDER BY PROBABILITY (DESC)
    # ================================================================
    try:
        response_items.sort(
            key=lambda x: (x.probability or 0),
            reverse=True
        )
    except Exception:
        pass

    # ================================================================
    # STEP 6 — CACHE + AUDIT
    # ================================================================
    result = {
        "query": raw_query,
        "feature_filter": feature_filter,
        "results_count": len(response_items),
        "results": response_items,
        "ranking_variant": ranking_variant,
    }

    try:
        cache_set(cache_key, result)
    except Exception:
        pass

    try:
        await log_api_call(
            endpoint="/api/search",
            method="POST",
            user=None,
            payload=payload.dict(),
            extra={
                "results_count": len(response_items),
                "ranking_variant": ranking_variant,
            },
        )
    except Exception:
        pass

    return SearchResponse(**{
        **result,
        "from_cache": False,
    })
