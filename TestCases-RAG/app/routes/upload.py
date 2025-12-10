import io
import uuid
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.core.logging import logger
from app.core.security import require_role
from app.db.mongo import get_testcase_collection

# CORRECT EMBEDDING API
from app.services.embeddings import embed_multivector

# GEMINI ENRICHMENT
from app.services.enrichment import get_gemini_enrichment

# AI DEDUPE PIPELINE
from app.services.dedupe_summary import generate_dedupe_summary
from app.services.dedupe_search_helper import search_similar_testcases
from app.services.dedupe_verifier import llm_verify_duplicate


router = APIRouter()


@router.post("/upload")
async def upload_and_process_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role("editor", "admin")),
):

    # ==========================================================
    # VALIDATE FILE TYPE
    # ==========================================================
    try:
        if not file.filename.endswith((".csv", ".xlsx")):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload a CSV or XLSX file."
            )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid file upload request."
        )


    col = get_testcase_collection()

    # ==========================================================
    # READ FILE → DATAFRAME
    # ==========================================================
    try:
        contents = await file.read()
        buffer = io.BytesIO(contents)

        try:
            if file.filename.endswith(".csv"):
                df = pd.read_csv(buffer, encoding="utf-8")
            else:
                df = pd.read_excel(buffer)
        except Exception as err:
            logger.error(f"File parse failed: {err}", exc_info=True)
            raise HTTPException(
                status_code=400,
                detail="Parsing failed. Please check the file format."
            )

        # clean df
        try:
            df = df.astype(str).replace(["nan", "NaN", pd.NA], "")
        except Exception:
            pass

        # check TC ID column
        try:
            if "Test Case ID" not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail="CSV/XLSX must contain 'Test Case ID' column."
                )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Missing 'Test Case ID' column."
            )

        # forward fill TC IDs
        try:
            df["Test Case ID"] = (
                df["Test Case ID"].replace("", pd.NA).ffill()
            )
        except Exception:
            pass

        # remove empty IDs
        try:
            df.dropna(subset=["Test Case ID"], inplace=True)
            df = df[
                df["Test Case ID"].str.strip().str.upper().ne("NA") &
                df["Test Case ID"].str.strip().ne("")
            ]
        except Exception:
            pass

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error reading file: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {e}",
        )


    # ==========================================================
    # GROUP BY TEST CASE ID
    # ==========================================================
    try:
        grouped = df.groupby("Test Case ID")
    except Exception as e:
        logger.error(f"Failed to group DataFrame: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed grouping input file data."
        )

    logger.info(f"Processing {len(grouped)} unique test cases...")

    documents_to_insert = []


    # ==========================================================
    # PROCESS EACH TEST CASE
    # ==========================================================
    for test_case_id, group in grouped:

        # -------------------------------
        # METADATA FIELDS
        # -------------------------------
        try:
            feature = str(group.get("Feature", "").iloc[0]) if "Feature" in group else ""
            description = str(group.get("Test Case Description", "").iloc[0]) if "Test Case Description" in group else ""
            prerequisites = str(group.get("Pre-requisites", "").iloc[0]) if "Pre-requisites" in group else ""
        except Exception:
            feature = ""
            description = ""
            prerequisites = ""

        # tags
        tags = []
        if "Tags" in group:
            try:
                raw_tags = str(group.get("Tags", "").iloc[0])
                tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
            except Exception:
                tags = []

        try:
            priority = str(group.get("Priority", "").iloc[0]) if "Priority" in group else None
        except Exception:
            priority = None

        try:
            platform = str(group.get("Platform", "").iloc[0]) if "Platform" in group else None
        except Exception:
            platform = None

        # -------------------------------
        # BUILD STEPS
        # -------------------------------
        steps_list = []

        for _, row in group.iterrows():
            try:
                step_no = str(row.get("Step No.", "")).strip()
                test_step = str(row.get("Test Step", "")).strip()
                expected = str(row.get("Expected Result", "")).strip()

                if not test_step:
                    continue

                formatted = f"Step {step_no}: {test_step}" if step_no else test_step

                if expected:
                    formatted += f" → Expected: {expected}"

                steps_list.append(formatted)

            except Exception:
                continue

        steps_combined = "\n\n".join(steps_list) if steps_list else ""


        # ==========================================================
        # 🔥 AI DEDUPE PIPELINE
        # ==========================================================
        try:
            # ---- 1. LLM 12-word summary
            dedupe_query = await generate_dedupe_summary(
                feature,
                description,
                steps_combined,
            )

            # ---- 2. Vector search (top 3 similar cases)
            top_hits = await search_similar_testcases(
                query=dedupe_query,
                limit=3
            )

            # ---- 3. LLM verify duplicate
            is_duplicate = await llm_verify_duplicate(
                candidate={
                    "Feature": feature,
                    "Description": description,
                    "Steps": steps_combined,
                },
                top_matches=top_hits
            )

            if is_duplicate:
                logger.info(
                    f"DEDUPE SKIP — Test Case '{test_case_id}' "
                    f"matched existing case."
                )
                continue  # SKIP INSERTION

        except Exception:
            logger.exception("Dedupe pipeline error — continuing ingestion")

        # ==========================================================
        # GEMINI ENRICHMENT
        # ==========================================================
        try:
            enrichment = get_gemini_enrichment(
                description,
                feature,
                steps_combined,
            )

            summary = enrichment.get("summary", "")
            keywords = enrichment.get("keywords", []) or []

        except Exception:
            summary = ""
            keywords = []

        # ==========================================================
        # EMBEDDINGS
        # ==========================================================
        try:
            desc_emb, steps_emb, summary_emb, main_vector = embed_multivector(
                description=description,
                steps=steps_combined,
                summary=summary,
            )
        except Exception:
            desc_emb, steps_emb, summary_emb, main_vector = [], [], [], []


        # ==========================================================
        # DOCUMENT ASSEMBLY
        # ==========================================================
        try:
            doc = {
                "_id": str(uuid.uuid4()),

                "Test Case ID": test_case_id,
                "Feature": feature,
                "Test Case Description": description,
                "Pre-requisites": prerequisites,
                "Steps": steps_combined,

                "TestCaseSummary": summary,
                "TestCaseKeywords": keywords,

                # VECTORS
                "desc_embedding": desc_emb,
                "steps_embedding": steps_emb,
                "summary_embedding": summary_emb,
                "main_vector": main_vector,

                # metadata
                "Tags": tags,
                "Priority": priority,
                "Platform": platform,

                "CreatedAt": datetime.utcnow(),
                "Popularity": 0.0,
            }

            documents_to_insert.append(doc)

        except Exception:
            continue


    # ==========================================================
    # INSERT INTO MONGO
    # ==========================================================
    if not documents_to_insert:
        return {"message": "No valid test cases found (all duplicates skipped)."}

    try:
        result = await col.insert_many(documents_to_insert)

        logger.info(f"Inserted {len(result.inserted_ids)} test cases.")

        return {
            "message": (
                f"Successfully processed and stored "
                f"{len(result.inserted_ids)} unique test cases."
            )
        }

    except Exception as e:
        logger.error(f"Error inserting MongoDB: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error storing data: {e}",
        )
