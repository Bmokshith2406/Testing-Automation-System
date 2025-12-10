from fastapi import APIRouter, HTTPException, Body, Depends
from bson import ObjectId
import json

from app.core.logging import logger
from app.core.security import require_role

from app.db.mongo import get_methods_collection
from app.models.schemas import UpdateMethodRequest

from app.services.embeddings import embed_text
from app.services.method_madl import get_method_madl

router = APIRouter()


@router.put("/update/{doc_id}")
async def update_method(
    doc_id: str,
    update_data: UpdateMethodRequest = Body(...),
    current_user: dict = Depends(require_role("editor", "admin")),
):

    col = get_methods_collection()

    try:
        # ----------------------------------------------------------
        # Load existing METHOD document
        # ----------------------------------------------------------
        try:
            existing_doc = await col.find_one(
                {"_id": ObjectId(doc_id)}
            )
        except Exception as err:
            logger.exception(f"MongoDB find_one failed: {err}")
            raise HTTPException(
                status_code=500,
                detail="Failed fetching method from database.",
            )

        if existing_doc is None:
            raise HTTPException(
                status_code=404,
                detail="Method not found",
            )

        updated_doc = dict(existing_doc)

        doc_section = updated_doc.setdefault("method_documentation", {})

        should_reprocess = False

        # ----------------------------------------------------------
        # Apply updates ONLY to MADL docs
        # ----------------------------------------------------------
        try:
            for field in [
                "summary", "description", "intent",
                "applies", "returns",
                "owner", "example_usage", "reusable"
            ]:
                val = getattr(update_data, field, None)
                if val is not None:
                    doc_section[field] = val
                    should_reprocess = True

            if update_data.params is not None:
                doc_section["params"] = update_data.params
                should_reprocess = True

            if update_data.keywords is not None:
                doc_section["keywords"] = update_data.keywords
                should_reprocess = True

        except Exception as err:
            logger.exception(f"Error applying updates to method {doc_id}: {err}")
            raise HTTPException(
                status_code=500,
                detail="Failed to apply updates to method.",
            )

        # ----------------------------------------------------------
        # REBUILD EMBEDDINGS IF NEEDED
        # ----------------------------------------------------------
        try:
            if should_reprocess:

                raw_method = updated_doc.get("raw_method_code", "")

                summary = doc_section.get("summary", "")

                md_json = json.dumps(updated_doc["method_documentation"])

                updated_doc["summary_embedding"] = embed_text(summary)
                updated_doc["raw_method_embedding"] = embed_text(raw_method)
                updated_doc["madl_embedding"] = embed_text(md_json)
                updated_doc["main_vector"] = embed_text(
                    f"{summary} {raw_method}"
                )

        except Exception as err:
            logger.exception(f"Embedding rebuild failed for method {doc_id}: {err}")
            raise HTTPException(
                status_code=500,
                detail="Failed rebuilding embeddings for method.",
            )

        # ----------------------------------------------------------
        # SAVE
        # ----------------------------------------------------------
        try:
            await col.replace_one(
                {"_id": ObjectId(doc_id)},
                updated_doc,
            )
        except Exception as err:
            logger.exception(f"MongoDB replace_one failed: {err}")
            raise HTTPException(
                status_code=500,
                detail="Failed saving updated method.",
            )

        logger.info(f"Updated method {doc_id}")

        # ----------------------------------------------------------
        # RESPONSE (no vectors)
        # ----------------------------------------------------------
        response_doc = dict(updated_doc)
        response_doc["id"] = str(response_doc["_id"])

        # Drop vectors
        for k in [
            "summary_embedding",
            "raw_method_embedding",
            "madl_embedding",
            "main_vector",
        ]:
            response_doc.pop(k, None)

        return {
            "success": True,
            "message": f"Method {doc_id} updated successfully",
            "updated_method": response_doc,
        }

    except HTTPException:
        raise

    except Exception as err:
        logger.exception(
            f"Error updating method {doc_id}: {err}"
        )

        raise HTTPException(
            status_code=500,
            detail="An error occurred while updating the method.",
        )
