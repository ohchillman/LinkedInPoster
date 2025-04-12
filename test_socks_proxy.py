import requests
import logging
from app.proxy_handler import ProxyHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_socks_proxy_handler():
    """
    Test the ProxyHandler class with SOCKS5 proxy format
    """
    # Test with SOCKS5 proxy format
    logger.info("Testing with SOCKS5 proxy format")
    
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
        proxies = proxy_handler.get_proxies()
        logger.info(f"Generated proxies dictionary: {proxies}")
        
        # This should raise an exception if the proxy doesn't work
        try:
            proxy_handler.check_proxy()
            logger.error("❌ Test failed: Non-working SOCKS5 proxy check should have raised ValueError")
        except ValueError as e:
            logger.info(f"✅ Test passed: Non-working SOCKS5 proxy correctly raised ValueError: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Test failed with unexpected error: {str(e)}")
    
    # Test with direct string format
    logger.info("\nTesting with direct string format")
    direct_proxy_string = "socks5://1111cpvbnd3wfl-corp.mobile-country-MD-state-618069-hold-session-session-67efeca1c7365:FxOQ5x8ym6c1GQfh@109.236.82.42:9999"
    
    # Parse the proxy string manually to test our parsing logic
    protocol = "socks5"
    proxy_url = direct_proxy_string.replace("socks5://", "")
    proxy_parts = proxy_url.split("@")
    
    if len(proxy_parts) > 1:
        auth, server = proxy_parts
        username, password = auth.split(":")
        host, port = server.split(":")
        
        proxy_settings = {
            "host": host,
            "port": int(port),
            "username": username,
            "password": password,
            "protocol": protocol
        }
    else:
        server = proxy_parts[0]
        host, port = server.split(":")
        
        proxy_settings = {
            "host": host,
            "port": int(port),
            "protocol": protocol
        }
    
    logger.info(f"Parsed proxy settings: {proxy_settings}")
    
    try:
        proxy_handler = ProxyHandler(proxy_settings)
        proxies = proxy_handler.get_proxies()
        logger.info(f"Generated proxies dictionary: {proxies}")
        
        # This should raise an exception if the proxy doesn't work
        try:
            proxy_handler.check_proxy()
            logger.error("❌ Test failed: Non-working SOCKS5 proxy check should have raised ValueError")
        except ValueError as e:
            logger.info(f"✅ Test passed: Non-working SOCKS5 proxy correctly raised ValueError: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Test failed with unexpected error: {str(e)}")

if __name__ == "__main__":
    test_socks_proxy_handler()
