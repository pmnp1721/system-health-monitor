import requests
import json
from datetime import datetime
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "1234"
HEADERS = {"X-API-Key": API_KEY}

def print_response(description, response):
    """Format and print response data"""
    print("\n" + "="*50)
    print(f"{description}:")
    print(f"Status Code: {response.status_code}")
    try:
        print("Response:", json.dumps(response.json(), indent=2))
    except:
        print("Response:", response.text)
    print("="*50 + "\n")

def test_all_endpoints():
    """Test all API endpoints"""
    
    # 1. Test root endpoint (no auth required)
    print("\nTesting root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print_response("Root Endpoint", response)

    # 2. Test current metrics
    print("\nTesting current metrics...")
    response = requests.get(f"{BASE_URL}/api/metrics", headers=HEADERS)
    print_response("Current Metrics", response)

    # 3. Test historical metrics
    print("\nTesting historical metrics...")
    response = requests.get(
        f"{BASE_URL}/api/metrics/history",
        params={"minutes": 60},
        headers=HEADERS
    )
    print_response("Historical Metrics", response)

    # 4. Test metadata operations
    print("\nTesting metadata operations...")
    
    # Create metadata
    metadata = {
        "name": "test-server",
        "environment": "production",
        "location": "us-east"
    }
    response = requests.post(
        f"{BASE_URL}/api/metadata",
        headers=HEADERS,
        json=metadata
    )
    print_response("Create Metadata", response)

    # Get metadata
    response = requests.get(f"{BASE_URL}/api/metadata", headers=HEADERS)
    print_response("Get Metadata", response)

    # Update metadata
    updated_metadata = {
        "name": "test-server",
        "environment": "staging",
        "location": "us-west"
    }
    response = requests.post(
        f"{BASE_URL}/api/metadata",
        headers=HEADERS,
        json=updated_metadata
    )
    print_response("Update Metadata", response)

    # 5. Test alerts
    print("\nTesting alerts...")
    
    # Get all alerts
    response = requests.get(f"{BASE_URL}/api/alerts", headers=HEADERS)
    print_response("Get All Alerts", response)

    # Get active alerts
    response = requests.get(
        f"{BASE_URL}/api/alerts",
        params={"status": "active"},
        headers=HEADERS
    )
    print_response("Get Active Alerts", response)

    # If there are any alerts, try to resolve one
    alerts = response.json()
    if alerts and len(alerts) > 0:
        alert_id = alerts[0]['id']
        response = requests.put(
            f"{BASE_URL}/api/alerts/{alert_id}/resolve",
            headers=HEADERS
        )
        print_response(f"Resolve Alert {alert_id}", response)

    # 6. Test notification
    print("\nTesting notification...")
    response = requests.post(
        f"{BASE_URL}/api/test-notification",
        headers=HEADERS
    )
    print_response("Test Notification", response)

def test_error_cases():
    """Test error cases and invalid inputs"""
    
    print("\nTesting error cases...")

    # 1. Test without API key
    response = requests.get(f"{BASE_URL}/api/metrics")
    print_response("Request without API key", response)

    # 2. Test with invalid API key
    response = requests.get(
        f"{BASE_URL}/api/metrics",
        headers={"X-API-Key": "invalid-key"}
    )
    print_response("Request with invalid API key", response)

    # 3. Test invalid metadata
    invalid_metadata = {
        "name": "t" * 51,  # Too long
        "environment": "test",
        "location": "local"
    }
    response = requests.post(
        f"{BASE_URL}/api/metadata",
        headers=HEADERS,
        json=invalid_metadata
    )
    print_response("Invalid metadata", response)

    # 4. Test invalid alert ID
    response = requests.put(
        f"{BASE_URL}/api/alerts/99999/resolve",
        headers=HEADERS
    )
    print_response("Invalid alert ID", response)

def monitor_system_for_period(minutes=5):
    """Monitor system for a specified period to generate some data"""
    
    print(f"\nMonitoring system for {minutes} minutes to generate data...")
    end_time = time.time() + (minutes * 60)
    
    while time.time() < end_time:
        # Get current metrics
        response = requests.get(f"{BASE_URL}/api/metrics", headers=HEADERS)
        metrics = response.json()
        
        print(f"\nCurrent Metrics at {datetime.now()}:")
        print(f"CPU: {metrics['cpu']['percent']}%")
        print(f"Memory: {metrics['memory']['percent']}%")
        print(f"Disk: {metrics['disk']['percent']}%")
        
        # Wait for 60 seconds before next check
        remaining = end_time - time.time()
        if remaining > 0:
            time.sleep(min(60, remaining))

if __name__ == "__main__":
    try:
        # Test all main functionality
        test_all_endpoints()
        
        # Test error cases
        test_error_cases()
        
        # Optional: Monitor system for a period
        choice = input("\nWould you like to monitor the system for 5 minutes? (y/n): ")
        if choice.lower() == 'y':
            monitor_system_for_period(5)
            
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to the server. Make sure it's running on", BASE_URL)
    except Exception as e:
        print("\nAn error occurred:", str(e))