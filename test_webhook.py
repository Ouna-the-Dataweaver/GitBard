import requests
import json

BASE_URL = "http://localhost:8585"

sample_mr_payload = {
    "object_kind": "merge_request",
    "event_type": "merge_request",
    "user": {
        "id": 1,
        "name": "Test User",
        "username": "testuser",
        "email": "test@example.com",
    },
    "project": {
        "id": 123,
        "name": "nidai",
        "description": "Test project",
        "web_url": "https://nid-gitlab.ad.speechpro.com/nid/nidai",
        "path_with_namespace": "nid/nidai",
    },
    "object_attributes": {
        "id": 456,
        "iid": 42,
        "action": "open",
        "title": "Add new feature",
        "description": "This MR adds a cool feature",
        "state": "opened",
    },
    "merge_request": {
        "id": 456,
        "iid": 42,
        "title": "Add new feature",
        "description": "This MR adds a cool feature",
        "source_branch": "feature-branch",
        "target_branch": "main",
        "state": "opened",
        "author_id": 1,
    },
}

sample_note_payload = {
    "object_kind": "note",
    "event_type": "note",
    "user": {
        "id": 1,
        "name": "Test User",
        "username": "testuser",
        "email": "test@example.com",
    },
    "project": {
        "id": 123,
        "name": "nidai",
        "web_url": "https://nid-gitlab.ad.speechpro.com/nid/nidai",
        "path_with_namespace": "nid/nidai",
    },
    "object_attributes": {
        "id": 789,
        "note": "/ai-review",
        "noteable_type": "MergeRequest",
    },
}


def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_mr_webhook():
    """Test merge request webhook"""
    print("\n=== Testing Merge Request Webhook ===")
    try:
        response = requests.post(f"{BASE_URL}/webhook", json=sample_mr_payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_note_webhook():
    """Test note (comment) webhook"""
    print("\n=== Testing Note Webhook ===")
    try:
        response = requests.post(f"{BASE_URL}/webhook", json=sample_note_payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    print("Testing GitLab AI Code Reviewer Webhook Service")
    print(f"Base URL: {BASE_URL}")

    results = {
        "health": test_health(),
        "mr_webhook": test_mr_webhook(),
        "note_webhook": test_note_webhook(),
    }

    print("\n=== Test Results ===")
    for test, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test}: {status}")

    all_passed = all(results.values())
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
