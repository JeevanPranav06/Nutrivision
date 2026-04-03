from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from services.food_detector import detect_food
from services.nutrition_service import get_nutrition

router = APIRouter()


@router.post("/")
async def scan_food(file: UploadFile = File(...)):
    """
    End-to-end scan pipeline:
    1) Receive image
    2) Detect food name
    3) Fetch real nutrition
    4) Return combined response
    """
    try:
        # Validate content type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

        image_bytes = await file.read()

        if not image_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded.")

        # Step 1: Detect food
        detection = detect_food(image_bytes)
        food_name = detection.get("food_name")

        if not food_name:
            raise HTTPException(status_code=500, detail="Food detection failed.")

        # Step 2: Get nutrition (real dataset / API-backed)
        nutrition = get_nutrition(food_name)

        # Step 3: Build response