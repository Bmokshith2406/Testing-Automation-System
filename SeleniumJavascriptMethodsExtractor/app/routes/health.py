from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Health Check for JavaScript Selenium Extractor")
async def health_check():
    return {"status": "ok"}
