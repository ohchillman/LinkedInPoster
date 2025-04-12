import json
import base64
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_example_json():
    """
    Create example JSON files for the new API format
    """
    # Example request
    request_example = {
        "client_id": "YOUR_LINKEDIN_CLIENT_ID",
        "client_secret": "YOUR_LINKEDIN_CLIENT_SECRET",
        "access_token": "YOUR_LINKEDIN_ACCESS_TOKEN",
        "text": "Your LinkedIn post text",
        "image": "BASE64_ENCODED_PNG_IMAGE",  # Optional
        "proxy": {  # Optional
            "http": "http://user:pass@host:port",
            "https": "https://user:pass@host:port"
        },
        "user_id": "optional-linkedin-user-id"
    }
    
    # Example response
    response_example = {
        "status": "success",
        "post_url": "https://www.linkedin.com/feed/update/urn:li:share:1234567890",
        "post_id": "urn:li:share:1234567890"
    }
    
    # Write examples to files
    with open("example_request.json", "w") as f:
        json.dump(request_example, f, indent=2)
        logger.info("Created example_request.json")
    
    with open("example_response.json", "w") as f:
        json.dump(response_example, f, indent=2)
        logger.info("Created example_response.json")

if __name__ == "__main__":
    logger.info("Creating example JSON files for API documentation")
    create_example_json()
