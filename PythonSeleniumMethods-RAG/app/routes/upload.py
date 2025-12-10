import io, json, uuid
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.core.security import require_role
from app.core.logging import logger
from app.db.mongo import get_methods_collection

from app.services.embeddings import embed_text
from app.services.method_madl import get_method_madl

from app.services.dedupe_summary import generate_method_dedupe_summary
from app.services.dedupe_search_helper import search_similar_methods
from app.services.dedupe_verifier import llm_verify_method_duplicate

router = APIRouter()


@router.post("/upload-methods")
async def upload_methods(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role("editor", "admin")),
):

    # --------------------------------------------------
    # FILE VALIDATION
    # --------------------------------------------------
    if not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(
            status_code=400,
            detail="Only CSV or XLSX allowed.",
        )

    try:
        data = await file.read()
        buffer = io.BytesIO(data)

        if file.filename.endswith(".csv"):
            df = pd.read_csv(buffer)
        else:
            df = pd.read_excel(buffer)

        df = df.astype(str).replace(["NaN", "nan", pd.NA], "")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if "Raw Method" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="File must contain 'Raw Method' column."
        )

    col = get_methods_collection()
    docs = []


    # ==================================================
    # PROCESS EACH RAW METHOD
    # ==================================================
    for _, row in df.iterrows():

        raw_method = str(row.get("Raw Method", "")).strip()

        if len(raw_method) < 10:
            continue


        # --------------------------------------------------
        # 1️⃣ DEDUPE SUMMARY
        # --------------------------------------------------
        try:
            dedupe_summary = await generate_method_dedupe_summary(raw_method)


            matches = await search_similar_methods(
                query=dedupe_summary,
                limit=3,
            )

            is_duplicate = await llm_verify_method_duplicate(
                candidate={
                    "method_name": "",
                    "raw_method_code": raw_method,
                },
                top_matches=matches
            )

            if is_duplicate:
                logger.info("Duplicate skipped")
                continue

        except Exception:
            logger.exception("Deduplication failed")
            continue


        # --------------------------------------------------
        # 2️⃣ MADL GENERATION
        # --------------------------------------------------
        try:
            madl = await get_method_madl(raw_method)
            summary = madl["method_documentation"]["summary"]

        except Exception:
            logger.exception("MADL generation failed")
            continue


        # --------------------------------------------------
        # 3️⃣ EMBEDDINGS
        # --------------------------------------------------
        try:
            summary_embedding = embed_text(summary)
            raw_method_embedding = embed_text(raw_method)
            madl_embedding = embed_text(json.dumps(madl))

            main_vector = embed_text(f"{summary} {raw_method}")

        except Exception:
            logger.exception("Embedding failure")
            continue


        # --------------------------------------------------
        # 4️⃣ INGEST TO DB
        # --------------------------------------------------
        doc = {
            "_id": str(uuid.uuid4()),

            "method_name": madl["method_name"],
            "raw_method_code": raw_method,
            "method_documentation": madl["method_documentation"],

            "summary_embedding": summary_embedding,
            "raw_method_embedding": raw_method_embedding,
            "madl_embedding": madl_embedding,
            "main_vector": main_vector,

            "CreatedAt": datetime.utcnow(),
            "Popularity": 0.0,
        }

        docs.append(doc)


    # ==================================================
    # INSERT RESULTS
    # ==================================================
    if not docs:
        return {
            "message": "No unique methods found (all duplicates skipped)."
        }

    await col.insert_many(docs)

    return {
        "message": f"Successfully ingested {len(docs)} unique Selenium methods."
    }
