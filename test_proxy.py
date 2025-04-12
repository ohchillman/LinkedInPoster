import requests
import logging
from app.proxy_handler import ProxyHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_proxy_handler():
    """
    Test the ProxyHandler class with both working and non-working proxies
    """
    # Test with no proxy
    logger.info("Testing with no proxy")
    proxy_handler = ProxyHandler(None)
    assert proxy_handler.get_proxies() == {}
    assert proxy_handler.check_proxy() == True
    
    # Test with non-working proxy
    logger.info("Testing with non-working proxy")
    non_working_proxy = {
        "host": "non-existing-proxy.example.com",
        "port": 8080
    }
    proxy_handler = ProxyHandler(non_working_proxy)
    assert proxy_handler.check_proxy() == False
    # After check_proxy returns False, get_proxies should return empty dict
    assert proxy_handler.get_proxies() == {}
    
    # Test with potentially working proxy (will be skipped in automated tests)
    logger.info("You can manually test with a working proxy by uncommenting and modifying the code below")
    """
    working_proxy = {
        "host": "your-working-proxy.com",
        "port": 8080,
        "username": "user",
        "password": "pass"
    }
    proxy_handler = ProxyHandler(working_proxy)
    assert proxy_handler.check_proxy() == True
    assert proxy_handler.get_proxies() != {}
    """

if __name__ == "__main__":
    test_proxy_handler()
    logger.info("All proxy handler tests passed!")
