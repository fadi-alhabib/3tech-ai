import os
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime
from typing import Optional
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Metalized Background Detector API",
    description="API for detecting metalized backgrounds in product images",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def detect_metalized_background(image_path: str) -> dict:
    """
    Detect if an image has a metalized background using the same logic as test_final.py
    Returns a dictionary with the result and confidence score.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {
                "is_metalized": False, 
                "confidence": 0.0, 
                "error": "Failed to read image"
            }

        # Convert to grayscale and enhance contrast
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        # Detect bright regions (barcode label)
        _, mask_white = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask_white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return {
                "is_metalized": False,
                "confidence": 0.0,
                "error": "No barcode region found"
            }

        # Find largest contour and get bounding box
        contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(contour)

        # Larger padding to capture background properly
        pad = int(1.0 * min(w, h))
        x0 = max(x - pad, 0)
        y0 = max(y - pad, 0)
        x1 = min(x + w + pad, img.shape[1])
        y1 = min(y + h + pad, img.shape[0])

        region = gray[y0:y1, x0:x1]

        # Mask barcode region to analyze surroundings
        mask = np.ones(region.shape, np.uint8) * 255
        bx0, by0 = x - x0, y - y0
        mask[by0:by0 + h, bx0:bx0 + w] = 0
        background = cv2.bitwise_and(region, region, mask=mask)

        # Feature 1: Detect reflections using adaptive threshold
        bright = cv2.adaptiveThreshold(background, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                     cv2.THRESH_BINARY, 21, -10)
        bright_ratio = np.sum(bright == 255) / bright.size

        # Feature 2: Measure contrast (edge intensity)
        laplacian = cv2.Laplacian(background, cv2.CV_64F)
        contrast_score = laplacian.var()
        
        # Feature 3: Standard deviation (variance in brightness)
        std_dev = np.std(background[background > 0])  # Exclude masked zeros
        
        # Feature 4: Mean brightness
        mean_brightness = np.mean(background[background > 0])
        
        # Feature 5: RGB channel correlation
        region_color = img[y0:y1, x0:x1]
        background_color = region_color.copy()
        background_color[mask == 0] = 0
        
        b, g, r = cv2.split(background_color)
        b_vals = b[mask > 0].flatten().astype(float)
        g_vals = g[mask > 0].flatten().astype(float)
        r_vals = r[mask > 0].flatten().astype(float)
        
        if len(b_vals) > 10:
            rg_corr = np.corrcoef(r_vals, g_vals)[0, 1]
            rb_corr = np.corrcoef(r_vals, b_vals)[0, 1]
            gb_corr = np.corrcoef(g_vals, b_vals)[0, 1]
            avg_channel_corr = (rg_corr + rb_corr + gb_corr) / 3
        else:
            avg_channel_corr = 1.0
        
        # Feature 6: Detect specular highlights (very bright spots)
        _, highlights = cv2.threshold(background, 200, 255, cv2.THRESH_BINARY)
        highlight_ratio = np.sum(highlights == 255) / highlights.size

        # Decision thresholds
        has_reflections = bright_ratio > 0.065
        has_highlights = highlight_ratio > 0.001
        reasonable_contrast = contrast_score < 1500
        has_texture = std_dev > 15
        not_too_bright = mean_brightness < 145
        good_variation = std_dev > 66
        is_metallic_tone = avg_channel_corr > 0.92
        
        # Combined decision
        is_metalized = (has_reflections and reasonable_contrast and 
                        (has_highlights or has_texture) and 
                        not_too_bright and good_variation and is_metallic_tone)
        
        # Calculate confidence score (0-100%)
        confidence = 0
        if is_metalized:
            # Higher confidence for metalized detections
            confidence = 70 + min(30, (bright_ratio * 100 + highlight_ratio * 1000) / 2)
        else:
            # Lower confidence for non-metalized detections
            confidence = min(100, 100 - (bright_ratio * 100))
        
        return {
            "is_metalized": bool(is_metalized),
            "confidence": min(100, max(0, confidence)),
            "metrics": {
                "bright_ratio": float(bright_ratio),
                "highlight_ratio": float(highlight_ratio),
                "contrast_score": float(contrast_score),
                "std_dev": float(std_dev),
                "mean_brightness": float(mean_brightness),
                "channel_correlation": float(avg_channel_corr)
            },
            "decision_factors": {
                "has_reflections": bool(has_reflections),
                "has_highlights": bool(has_highlights),
                "reasonable_contrast": bool(reasonable_contrast),
                "has_texture": bool(has_texture),
                "not_too_bright": bool(not_too_bright),
                "good_variation": bool(good_variation),
                "is_metallic_tone": bool(is_metallic_tone)
            }
        }
        
    except Exception as e:
        logger.error(f"Error in detection: {str(e)}")
        return {
            "is_metalized": False,
            "confidence": 0.0,
            "error": str(e)
        }

@app.post("/detect-metalized", response_model=dict)
async def detect_metalized(file: UploadFile = File(...)):
    """
    Detect if the uploaded image has a metalized background.
    
    - **file**: Image file to process (JPEG, PNG, etc.)
    """
    start_time = datetime.now()
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Create a temporary file
    temp_file = os.path.join(UPLOAD_DIR, f"temp_{int(datetime.now().timestamp())}_{file.filename}")
    
    try:
        # Save uploaded file
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the image
        result = detect_metalized_background(temp_file)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Log the request
        logger.info(
            f"Processed {file.filename} in {processing_time:.2f}s - "
            f"Result: {result.get('is_metalized')} (Confidence: {result.get('confidence', 0):.1f}%)"
        )
        
        # Prepare response
        response = {
            "filename": file.filename,
            "is_metalized": result["is_metalized"],
            "confidence": result.get("confidence", 0.0),
            "processing_time_seconds": processing_time,
            "details": {
                k: v for k, v in result.items() 
                if k not in ["is_metalized", "confidence"]
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}"
        )
        
    # finally:
        # Clean up temporary file
        # try:
        #     if os.path.exists(temp_file):
        #         os.remove(temp_file)
        # except Exception as e:
        #     logger.warning(f"Failed to delete temporary file {temp_file}: {str(e)}")

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Metalized Background Detector"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
