import requests
from app.proxy_handler import ProxyHandler
import sys

def test_proxy_requirement():
    print("Testing proxy requirement logic...")
    
    # Test 1: No proxy (should work)
    print("\nTest 1: No proxy")
    try:
        handler = ProxyHandler(None)
        result = handler.check_proxy()
        print(f"✅ Test passed: No proxy check returned {result}")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    # Test 2: Working proxy (should work)
    print("\nTest 2: Working proxy (using httpbin.org)")
    try:
        # Using a public test proxy service
        proxy_settings = {
            "host": "httpbin.org",
            "port": 80
        }
        handler = ProxyHandler(proxy_settings)
        # This will likely fail but we're testing the logic
        try:
            result = handler.check_proxy()
            print(f"✅ Test passed: Working proxy check returned {result}")
        except ValueError as e:
            print(f"ℹ️ Expected error with test proxy: {str(e)}")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    # Test 3: Non-working proxy (should fail with ValueError)
    print("\nTest 3: Non-working proxy")
    try:
        proxy_settings = {
            "host": "non-existent-proxy.example.com",
            "port": 8080
        }
        handler = ProxyHandler(proxy_settings)
        try:
            result = handler.check_proxy()
            print(f"❌ Test failed: Non-working proxy check returned {result} but should have raised ValueError")
        except ValueError as e:
            print(f"✅ Test passed: Non-working proxy correctly raised ValueError: {str(e)}")
    except Exception as e:
        if isinstance(e, ValueError):
            print(f"✅ Test passed: Non-working proxy correctly raised ValueError: {str(e)}")
        else:
            print(f"❌ Test failed: {str(e)}")
    
    # Test 4: Session with non-working proxy
    print("\nTest 4: Session with non-working proxy")
    try:
        proxy_settings = {
            "host": "non-existent-proxy.example.com",
            "port": 8080
        }
        handler = ProxyHandler(proxy_settings)
        session = requests.Session()
        try:
            handler.apply_to_session(session)
            print(f"❌ Test failed: apply_to_session with non-working proxy should have raised ValueError")
        except ValueError as e:
            print(f"✅ Test passed: apply_to_session correctly raised ValueError: {str(e)}")
    except Exception as e:
        if isinstance(e, ValueError):
            print(f"✅ Test passed: apply_to_session correctly raised ValueError: {str(e)}")
        else:
            print(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    test_proxy_requirement()
