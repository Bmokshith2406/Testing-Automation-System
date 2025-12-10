from fastapi import APIRouter, HTTPException, Body, Depends

from app.core.logging import logger
from app.core.security import require_role
from app.db.mongo import get_testcase_collection
from app.models.schemas import UpdateTestCaseRequest

# CORRECT EMBEDDING FUNCTIONS
from app.services.embeddings import embed_multivector

from app.services.enrichment import get_gemini_enrichment


router = APIRouter()


@router.put("/update/{doc_id}")
async def update_test_case(
    doc_id: str,
    update_data: UpdateTestCaseRequest = Body(...),
    current_user: dict = Depends(require_role("editor", "admin")),
):
    col = get_testcase_collection()

    try:
        # ----------------------------------------------------------
        # Load existing document
        # ----------------------------------------------------------
        try:
            existing_doc = await col.find_one({"_id": doc_id})
        except Exception as err:
            logger.exception(f"MongoDB find_one failed: {err}")
            raise HTTPException(
                status_code=500,
                detail="Failed fetching test case from database.",
            )

        if existing_doc is None:
            raise HTTPException(
                status_code=404,
                detail="Test case not found",
            )

        try:
            updated_doc = existing_doc.copy()
        except Exception:
            updated_doc = dict(existing_doc)


        # ==========================================================
        # FLAG: REPROCESS WHEN SEARCH TEXT CHANGES
        # ==========================================================
        should_reprocess = False


        # --------------------
        # Apply field updates
        # --------------------
        try:
            if update_data.feature is not None:
                updated_doc["Feature"] = update_data.feature
                should_reprocess = True

            if update_data.description is not None:
                updated_doc["Test Case Description"] = update_data.description
                should_reprocess = True

            if update_data.prerequisites is not None:
                updated_doc["Pre-requisites"] = update_data.prerequisites

            if update_data.steps is not None:
                updated_doc["Steps"] = update_data.steps
                should_reprocess = True

            if update_data.summary is not None:
                updated_doc["TestCaseSummary"] = update_data.summary
                should_reprocess = True

            if update_data.keywords is not None:
                updated_doc["TestCaseKeywords"] = update_data.keywords
                should_reprocess = True

            if update_data.tags is not None:
                updated_doc["Tags"] = update_data.tags

            if update_data.priority is not None:
                updated_doc["Priority"] = update_data.priority

            if update_data.platform is not None:
                updated_doc["Platform"] = update_data.platform

            if update_data.popularity is not None:
                updated_doc["Popularity"] = float(update_data.popularity)

        except Exception as err:
            logger.exception(f"Error applying updates to test case {doc_id}: {err}")
            raise HTTPException(
                status_code=500,
                detail="Failed to apply updates to test case.",
            )


        # ==========================================================
        # GEMINI ENRICHMENT (Only if needed)
        # ==========================================================
        try:
            if (
                should_reprocess
                or not updated_doc.get("TestCaseSummary")
                or not updated_doc.get("TestCaseKeywords")
            ):
                enrichment = get_gemini_enrichment(
                    updated_doc.get("Test Case Description", ""),
                    updated_doc.get("Feature", ""),
                    updated_doc.get("Steps", ""),
                )

                if update_data.summary is None:
                    updated_doc["TestCaseSummary"] = enrichment.get(
                        "summary",
                        updated_doc.get("TestCaseSummary", ""),
                    )

                if update_data.keywords is None:
                    updated_doc["TestCaseKeywords"] = enrichment.get(
                        "keywords",
                        updated_doc.get("TestCaseKeywords", []),
                    )
        except Exception as err:
            logger.warning(
                f"Gemini enrichment failed for test case {doc_id}: {err}"
            )
            # Preserves baseline behavior — enrichment failure does NOT block update


        # ==========================================================
        # CORRECT EMBEDDING REBUILD (BASELINE PARITY)
        # ==========================================================
        try:
            desc_emb, steps_emb, summary_emb, main_vector = embed_multivector(
                description=updated_doc.get("Test Case Description", ""),
                steps=updated_doc.get("Steps", ""),
                summary=updated_doc.get("TestCaseSummary", ""),
            )
        except Exception as err:
            logger.exception(f"Embedding rebuild failed for test case {doc_id}: {err}")
            raise HTTPException(
                status_code=500,
                detail="Failed rebuilding embeddings for test case.",
            )

        updated_doc["desc_embedding"] = desc_emb
        updated_doc["steps_embedding"] = steps_emb
        updated_doc["summary_embedding"] = summary_emb
        updated_doc["main_vector"] = main_vector


        # ==========================================================
        # SAVE
        # ==========================================================
        try:
            await col.replace_one(
                {"_id": doc_id},
                updated_doc,
            )
        except Exception as err:
            logger.exception(f"MongoDB replace_one failed: {err}")
            raise HTTPException(
                status_code=500,
                detail="Failed saving updated test case.",
            )

        logger.info(f"Updated test case {doc_id}")


        # ==========================================================
        # RESPONSE
        # ==========================================================
        try:
            response_doc = updated_doc.copy()
        except Exception:
            response_doc = dict(updated_doc)

        # Never leak vectors in API responses
        for k in [
            "desc_embedding",
            "steps_embedding",
            "summary_embedding",
            "main_vector",
        ]:
            try:
                response_doc.pop(k, None)
            except Exception:
                pass

        response_doc["id"] = str(response_doc.get("_id"))

        return {
            "success": True,
            "message": f"Test case {doc_id} updated successfully",
            "updated_test_case": response_doc,
        }

    except HTTPException:
        raise

    except Exception as err:
        logger.exception(
            f"Error updating test case {doc_id}: {err}"
        )

        raise HTTPException(
            status_code=500,
            detail="An error occurred while updating the test case.",
        )
