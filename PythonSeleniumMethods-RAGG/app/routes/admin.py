from datetime import datetime, timedelta
from bson import ObjectId

from fastapi import APIRouter, HTTPException, Depends, Query

from app.core.config import get_settings
from app.core.logging import logger
from app.core.security import require_role
from app.db.mongo import get_methods_collection, get_db

router = APIRouter()
settings = get_settings()


# -----------------------------------------------------
# GET ALL METHODS
# -----------------------------------------------------
@router.get("/get-all-methods")
async def get_all_methods(
    skip: int = 0,
    limit: int = 50,
    sort_by: str = "method_name",
    order: int = 1,
    current_user: dict = Depends(require_role("editor", "admin")),
):

    col = get_methods_collection()

    projection = {
        "summary_embedding": 0,
        "raw_method_embedding": 0,
        "madl_embedding": 0,
        "main_vector": 0,
    }

    sort_order = -1 if order < 0 else 1

    try:
        cursor = (
            col.find({}, projection)
            .sort(sort_by, sort_order)
            .skip(skip)
            .limit(limit)
        )
    except Exception as err:
        logger.exception(f"Mongo cursor build failed: {err}")
        raise HTTPException(
            status_code=500,
            detail="Failed to query database.",
        )

    methods = []

    async for doc in cursor:
        try:
            doc["id"] = str(doc["_id"])
            methods.append(doc)
        except Exception:
            continue

    return {
        "success": True,
        "count": len(methods),
        "skip": skip,
        "limit": limit,
        "methods": methods,
    }


# -----------------------------------------------------
# DELETE ALL METHODS
# -----------------------------------------------------
@router.post("/delete-all")
async def delete_all_data(
    confirm: bool = Query(False, description="Pass true to confirm deletion"),
    current_user: dict = Depends(require_role("admin")),
):

    col = get_methods_collection()

    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required. Pass ?confirm=true to delete all data.",
        )

    try:
        await col.drop()

        logger.warning(
            f"Dropped collection '{settings.COLLECTION_SCRIPT_METHODS}'"
        )

        return {
            "success": True,
            "collection": settings.COLLECTION_SCRIPT_METHODS,
            "message": f"All method data deleted.",
        }

    except Exception as e:
        logger.error("Delete failed", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while deleting data.",
        )


# -----------------------------------------------------
# DELETE METHOD BY ID
# -----------------------------------------------------
@router.delete("/method/{doc_id}")
async def delete_method(
    doc_id: str,
    current_user: dict = Depends(require_role("editor", "admin")),
):

    col = get_methods_collection()

    try:
        res = await col.delete_one(
            {"_id": ObjectId(doc_id)}
        )

        if res.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Method not found",
            )

        logger.info(f"Deleted method {doc_id}")

        return {
            "success": True,
            "message": f"Method {doc_id} deleted",
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"Error deleting method {doc_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to delete method",
        )


# -----------------------------------------------------
# METRICS
# -----------------------------------------------------
@router.get("/metrics")
async def get_metrics(
    current_user: dict = Depends(require_role("admin")),
):

    try:
        db = get_db()
        audit_col = db[settings.COLLECTION_AUDIT]
    except Exception as err:
        logger.exception(f"Failed resolving DB collections: {err}")
        raise HTTPException(
            status_code=500,
            detail="DB resolution failed.",
        )

    now = datetime.utcnow()
    since = now - timedelta(days=1)

    try:
        queries_today = await audit_col.count_documents(
            {
                "endpoint": "/api/search",
                "timestamp": {"$gte": since},
            }
        )
    except Exception as err:
        logger.exception(f"Mongo count_documents failed: {err}")
        raise HTTPException(
            status_code=500,
            detail="Failed retrieving metrics.",
        )

    try:
        pipeline = [
            {"$match": {"endpoint": "/api/search"}},
            {
                "$group": {
                    "_id": "$payload.method_name",
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": 5},
        ]

        top_methods = await audit_col.aggregate(
            pipeline
        ).to_list(length=5)

    except Exception as err:
        logger.exception(f"Mongo aggregate failed: {err}")
        raise HTTPException(
            status_code=500,
            detail="Failed computing metrics.",
        )

    return {
        "queries_today": queries_today,
        "top_methods": [
            f["_id"]
            for f in top_methods
            if f.get("_id")
        ],
    }
