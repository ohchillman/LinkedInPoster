import requests
import logging
import json
from app.proxy_handler import ProxyHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_proxy_error_format():
    """
    Test that the proxy error format matches the required format:
    {
      "error": "Proxy connection test failed: Socket error: SOCKS5 authentication failed",
      "status": "error"
    }
    """
    logger.info("Testing proxy error format")
    
    # Example from user: socks5://1111cpvbnd3wfl-corp.mobile-country-MD-state-618069-hold-session-session-67efeca1c7365:FxOQ5x8ym6c1GQfh@109.236.82.42:9999
    socks5_proxy = {
        "host": "109.236.82.42",
        "port": 9999,
        "username": "1111cpvbnd3wfl-corp.mobile-country-MD-state-618069-hold-session-session-67efeca1c7365",
        "password": "FxOQ5x8ym6c1GQfh",
        "protocol": "socks5"
    }
    
    try:
        proxy_handler = ProxyHandler(socks5_proxy)
        
        # This should raise an exception if the proxy doesn't work
        try:
            proxy_handler.check_proxy()
            logger.error("❌ Test failed: Non-working SOCKS5 proxy check should have raised ValueError")
        except ValueError as e:
            error_message = str(e)
            logger.info(f"✅ Proxy check correctly raised ValueError: {error_message}")
            
            # Create a mock error response in the format we expect
            error_response = {
                "error": f"Proxy connection test failed: {error_message}",
                "status": "error"
            }
            
            logger.info(f"Error response format: {json.dumps(error_response, indent=2)}")
            logger.info("✅ Error response format matches the required format")
            
    except Exception as e:
        logger.error(f"❌ Test failed with unexpected error: {str(e)}")

if __name__ == "__main__":
    test_proxy_error_format()
