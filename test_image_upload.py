import os
import base64
import logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Test Image Upload", 
              description="Simple API to test image upload functionality",
              version="1.0.0")

# Set up templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "app/templates"))

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/test-image")
async def test_image(
    image: UploadFile = File(...),
):
    try:
        logger.info(f"Received image: {image.filename}, content_type: {image.content_type}")
        
        # Read image data
        image_data = await image.read()
        image_size = len(image_data)
        
        # Get file extension
        _, ext = os.path.splitext(image.filename)
        ext = ext.lower()
        
        # Determine content type based on extension
        content_type = "application/octet-stream"
        if ext in ['.jpg', '.jpeg']:
            content_type = "image/jpeg"
        elif ext == '.png':
            content_type = "image/png"
        elif ext == '.gif':
            content_type = "image/gif"
        
        # Create a small preview (base64 encoded)
        preview = base64.b64encode(image_data[:1024]).decode('utf-8')
        
        return {
            "status": "success",
            "filename": image.filename,
            "size_bytes": image_size,
            "content_type": content_type,
            "detected_extension": ext,
            "preview_base64_truncated": preview[:100] + "..."
        }
    
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("test_image_upload:app", host="0.0.0.0", port=5000, reload=True)
