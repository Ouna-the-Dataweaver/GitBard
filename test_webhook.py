import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

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
        "note": "/oc_test",
        "noteable_type": "MergeRequest",
        "noteable_iid": 42,
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


def post_gitlab_comment(project_id, mr_iid, comment_text, gitlab_token):
    """Post a comment to a GitLab merge request"""
    gitlab_url = os.environ.get(
        "GITLAB_URL", "https://nid-gitlab.ad.speechpro.com"
    ).rstrip("/")
    url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    headers = {"PRIVATE-TOKEN": gitlab_token}
    data = {"body": comment_text}

    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()


def test_gitlab_comment():
    """Test posting a comment to GitLab MR"""
    gitlab_token = os.environ.get("GITLAB_PAT", "")
    if not gitlab_token:
        print("GITLAB_PAT not set in environment")
        return False

    print("\n=== Testing GitLab Comment Post ===")
    try:
        project_id = sample_mr_payload["project"]["id"]
        mr_iid = sample_mr_payload["object_attributes"]["iid"]
        comment_text = "trigger OK"

        resp_json = post_gitlab_comment(project_id, mr_iid, comment_text, gitlab_token)
        print(f"Status: 201")
        print(f"Response: {json.dumps(resp_json, indent=2)}")
        print(f"Posted comment ID: {resp_json['id']}")
        return True
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
        "gitlab_comment": test_gitlab_comment(),
    }

    print("\n=== Test Results ===")
    for test, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test}: {status}")

    all_passed = all(results.values())
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
