from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/",
    summary="Health check for Playwright Python Method Extraction service",
)
async def health_check():
    """
    Simple health check endpoint.

    Used to verify that the Playwright Python Method
    Extraction API is running and responsive.
    """
    return {"status": "ok"}
