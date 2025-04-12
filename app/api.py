from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

api_router = APIRouter()

@api_router.get("/docs", response_class=JSONResponse)
async def api_docs():
    """
    Return API documentation
    """
    docs = {
        "name": "LinkedIn Poster API",
        "version": "1.0.0",
        "description": "API for posting content to LinkedIn with proxy support",
        "endpoints": [
            {
                "path": "/health",
                "method": "GET",
                "description": "Health check endpoint",
                "response": {"status": "ok"}
            },
            {
                "path": "/api/post",
                "method": "POST",
                "description": "Post to LinkedIn with optional image",
                "request_body": {
                    "client_id": "LinkedIn Client ID",
                    "client_secret": "LinkedIn Client Secret",
                    "access_token": "LinkedIn access token",
                    "text": "Post text content",
                    "image": "(Optional) Base64 encoded PNG image",
                    "proxy": "(Optional) Proxy configuration object with http/https keys"
                },
                "response": {
                    "status": "success",
                    "post_url": "URL to the posted LinkedIn update",
                    "post_id": "ID of the posted LinkedIn update"
                }
            },
            {
                "path": "/api/docs",
                "method": "GET",
                "description": "API documentation",
                "response": "This documentation"
            }
        ]
    }
    return docs
