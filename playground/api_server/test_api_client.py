"""
Test client for the Browser Agent API

This script demonstrates how to interact with the API server.
Make sure the API server is running first: uvicorn api_server_example:app --reload
"""

import requests
import json


BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")


def test_chat(message: str, session_id=None):
    """Send a message to the agent."""
    print(f"Sending message: {message}")
    
    payload = {
        "message": message,
        "user_id": "test_user"
    }
    
    if session_id:
        payload["session_id"] = session_id
    
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Session ID: {data['session_id']}")
        print(f"Response: {data['response']}")
        print(f"Events: {data['events_count']}\n")
        return data['session_id']
    else:
        print(f"Error: {response.status_code}")
        print(f"Details: {response.text}\n")
        return None


def test_list_sessions(user_id="test_user"):
    """List all sessions for a user."""
    print(f"Listing sessions for user: {user_id}")
    response = requests.get(f"{BASE_URL}/sessions/{user_id}")
    
    if response.status_code == 200:
        sessions = response.json()
        print(f"Found {len(sessions)} session(s):")
        for session in sessions:
            print(f"  - {session['session_id']}: {session['message_count']} messages")
        print()
        return sessions
    else:
        print(f"Error: {response.status_code}\n")
        return []


def test_delete_session(user_id, session_id):
    """Delete a session."""
    print(f"Deleting session: {session_id}")
    response = requests.delete(f"{BASE_URL}/sessions/{user_id}/{session_id}")
    
    if response.status_code == 200:
        print(f"Session deleted successfully\n")
    else:
        print(f"Error: {response.status_code}\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Browser Agent API Client Test")
    print("=" * 60 + "\n")
    
    # Test 1: Health check
    test_health_check()
    
    # Test 2: Send first message (creates new session)
    print("Test 1: New conversation")
    print("-" * 60)
    session_id = test_chat("Navigate to example.com and tell me what you see")
    
    if not session_id:
        print("Failed to create session. Is the server running?")
        return
    
    # Test 3: Continue conversation in same session
    print("Test 2: Continue conversation")
    print("-" * 60)
    test_chat("What links are available on the page?", session_id=session_id)
    
    # Test 4: List sessions
    print("Test 3: List sessions")
    print("-" * 60)
    sessions = test_list_sessions("test_user")
    
    # Test 5: Delete session
    if sessions:
        print("Test 4: Delete session")
        print("-" * 60)
        test_delete_session("test_user", session_id)
        
        # Verify deletion
        print("Test 5: Verify deletion")
        print("-" * 60)
        test_list_sessions("test_user")
    
    print("=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
