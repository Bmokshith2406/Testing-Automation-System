from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query

from app.core.config import get_settings
from app.core.logging import logger
from app.core.security import require_role
from app.db.mongo import get_testcase_collection, get_db

router = APIRouter()
settings = get_settings()


@router.get("/get-all")
async def get_all_test_cases(
    skip: int = 0,
    limit: int = 50,
    sort_by: str = "Test Case ID",
    order: int = 1,
    current_user: dict = Depends(require_role("editor", "admin")),
):
    col = get_testcase_collection()

    try:
        # -------------------------------------------------
        # Mongo projection & cursor construction
        # -------------------------------------------------
        projection = {
            "desc_embedding": 0,
            "steps_embedding": 0,
            "summary_embedding": 0,
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

        test_cases = []

        async for doc in cursor:
            try:
                doc["id"] = str(doc["_id"])
                test_cases.append(doc)
            except Exception:
                continue

        return {
            "success": True,
            "count": len(test_cases),
            "skip": skip,
            "limit": limit,
            "test_cases": test_cases,
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"Error retrieving test cases from MongoDB: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving data.",
        )


@router.post("/delete-all")
async def delete_all_data(
    confirm: bool = Query(False, description="Pass true to confirm deletion"),
    current_user: dict = Depends(require_role("admin")),
):

    col = get_testcase_collection()

    try:
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Confirmation required. Pass ?confirm=true to delete all data.",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid confirmation flag.",
        )

    try:
        await col.drop()

        logger.warning(
            f"Dropped collection '{settings.COLLECTION_TESTCASES}'; all data cleared."
        )

        return {
            "success": True,
            "collection": settings.COLLECTION_TESTCASES,
            "message": f"All test case data in '{settings.COLLECTION_TESTCASES}' has been successfully deleted.",
        }

    except Exception as e:
        logger.error(
            f"Failed to delete all data from '{settings.COLLECTION_TESTCASES}': {e}",
            exc_info=True,
        )

        raise HTTPException(
            status_code=500,
            detail="An error occurred while deleting data.",
        )


@router.delete("/testcase/{doc_id}")
async def delete_test_case(
    doc_id: str,
    current_user: dict = Depends(require_role("editor", "admin")),
):

    col = get_testcase_collection()

    try:
        try:
            res = await col.delete_one({"_id": doc_id})
        except Exception as err:
            logger.exception(f"Mongo delete_one failed: {err}")
            raise HTTPException(
                status_code=500,
                detail="Database delete failed.",
            )

        if res.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Test case not found",
            )

        logger.info(f"Deleted test case {doc_id}")

        return {
            "success": True,
            "message": f"Test case {doc_id} deleted",
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"Error deleting test case {doc_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to delete test case",
        )


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
            detail="Failed to connect to audit database.",
        )

    try:
        now = datetime.utcnow()
        since = now - timedelta(days=1)
    except Exception:
        since = None

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
                    "_id": "$payload.feature",
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": 5},
        ]

        top_features = await audit_col.aggregate(
            pipeline
        ).to_list(length=5)

    except Exception as err:
        logger.exception(f"Mongo aggregate failed: {err}")
        raise HTTPException(
            status_code=500,
            detail="Failed computing feature metrics.",
        )

    return {
        "queries_today": queries_today,
        "top_features": [
            f["_id"]
            for f in top_features
            if f.get("_id")
        ],
    }
