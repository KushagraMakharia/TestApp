import os
import sys
import urllib.error
import urllib.request


def trigger_endpoint(endpoint: str, base_url: str = "http://127.0.0.1:8080"):
    url = f"{base_url}{endpoint}"
    print(f"Triggering endpoint: {url}")
    try:
        with urllib.request.urlopen(url) as response:
            print(f"Response: {response.read().decode('utf-8')}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error (expected): {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Connection Error: {e}")


if __name__ == "__main__":
    base_url = os.environ.get("TARGET_APP_URL", "http://127.0.0.1:8080")
    if len(sys.argv) < 2:
        print("Usage: python trigger_error.py [calculate|users|items|all]")
        sys.exit(1)

    choice = sys.argv[1]
    if choice == "calculate" or choice == "all":
        trigger_endpoint("/calculate?a=10&b=0", base_url)
    if choice == "users" or choice == "all":
        trigger_endpoint("/users?id=999", base_url)
    if choice == "items" or choice == "all":
        trigger_endpoint("/items?index=999", base_url)
