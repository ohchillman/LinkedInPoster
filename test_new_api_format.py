import requests
import json
import base64
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_new_api_format():
    """
    Test the new API format for LinkedIn posting
    """
    # API endpoint
    url = "http://localhost:5001/api/post"
    
    # Test data
    test_data = {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "access_token": "test_access_token",
        "text": "Test post using new API format",
        # Optional base64 image can be added here
        # "image": "base64_encoded_image_data",
        # Optional proxy settings
        # "proxy": {
        #     "http": "http://user:pass@host:port",
        #     "https": "https://user:pass@host:port"
        # },
        "user_id": "test_user_id"
    }
    
    # Add a test image if available
    test_image_path = Path("test_image.png")
    if test_image_path.exists():
        logger.info(f"Adding test image from {test_image_path}")
        with open(test_image_path, "rb") as img_file:
            img_data = img_file.read()
            base64_img = base64.b64encode(img_data).decode('utf-8')
            test_data["image"] = base64_img
    
    # Print the request data
    logger.info("Sending test request with data:")
    logger.info(json.dumps(test_data, indent=2))
    
    # Make the request
    try:
        response = requests.post(url, json=test_data)
        
        # Print the response
        logger.info(f"Response status code: {response.status_code}")
        if response.status_code == 200:
            logger.info("Response content:")
            logger.info(json.dumps(response.json(), indent=2))
            
            # Verify the response format
            response_data = response.json()
            assert "status" in response_data, "Response missing 'status' field"
            assert "post_url" in response_data, "Response missing 'post_url' field"
            assert "post_id" in response_data, "Response missing 'post_id' field"
            
            logger.info("Response format validation passed!")
        else:
            logger.error(f"Error response: {response.text}")
    
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"Test error: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting API format test")
    test_new_api_format()
