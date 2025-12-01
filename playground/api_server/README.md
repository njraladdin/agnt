# Browser Agent API Server Example

This example demonstrates how to expose a browser agent via a REST API using FastAPI.

## Files

- `api_server_example.py` - FastAPI server that exposes the browser agent
- `test_api_client.py` - Test client to interact with the API

## Quick Start

### 1. Install Dependencies

```bash
pip install fastapi uvicorn
```

### 2. Start the API Server

```bash
# From the playground directory
uvicorn api_server_example:app --reload

# Or run directly
python api_server_example.py
```

The server will start at `http://localhost:8000`

### 3. View API Documentation

Open your browser to:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 4. Test the API

In a new terminal:

```bash
python test_api_client.py
```

## API Endpoints

### Health Check

```http
GET /
```

Returns server status.

### Chat with Agent

```http
POST /chat
Content-Type: application/json

{
  "message": "Navigate to example.com",
  "user_id": "user123",
  "session_id": "optional-session-id"
}
```

**Response:**

```json
{
  "session_id": "abc-123",
  "response": "I've navigated to example.com...",
  "events_count": 5
}
```

### List Sessions

```http
GET /sessions/{user_id}
```

Returns all sessions for a user.

### Delete Session

```http
DELETE /sessions/{user_id}/{session_id}
```

Deletes a session and cleans up its browser.

## Example Usage

### Python

```python
import requests

# Send a message
response = requests.post("http://localhost:8000/chat", json={
    "message": "Go to github.com and search for 'python'",
    "user_id": "user123"
})

data = response.json()
print(f"Agent: {data['response']}")
print(f"Session ID: {data['session_id']}")

# Continue conversation
response = requests.post("http://localhost:8000/chat", json={
    "message": "Click the first result",
    "user_id": "user123",
    "session_id": data['session_id']  # Same session
})
```

### JavaScript/TypeScript

```javascript
// Send a message
const response = await fetch("http://localhost:8000/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    message: "Navigate to example.com",
    user_id: "user123",
  }),
});

const data = await response.json();
console.log("Agent:", data.response);
console.log("Session ID:", data.session_id);
```

### cURL

```bash
# Send a message
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Navigate to example.com",
    "user_id": "user123"
  }'

# List sessions
curl "http://localhost:8000/sessions/user123"

# Delete session
curl -X DELETE "http://localhost:8000/sessions/user123/abc-123"
```

## How It Works

1. **Session Management**: Each user can have multiple sessions. Sessions are automatically created if not provided.

2. **Browser Isolation**: The `BrowserToolset` automatically creates a unique browser instance per session, ensuring proper isolation.

3. **Cleanup**: When a session is deleted, the associated browser is also cleaned up.

4. **Stateless API**: The API server is stateless - all state is managed by the `InMemoryRunner` and session service.

## Production Considerations

### Security

- Add authentication (e.g., API keys, OAuth)
- Validate and sanitize user inputs
- Set proper CORS origins (not `*`)
- Implement rate limiting

### Scalability

- Use persistent session storage (e.g., Redis, PostgreSQL)
- Deploy with multiple workers: `uvicorn api_server_example:app --workers 4`
- Use a reverse proxy (nginx, Caddy)
- Consider Cloud Run or Kubernetes for auto-scaling

### Monitoring

- Add logging for all requests
- Track response times and error rates
- Monitor browser resource usage
- Set up alerts for failures

## Example Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY api_server_example.py .

CMD ["uvicorn", "api_server_example:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Cloud Run

```bash
gcloud run deploy browser-agent-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## See Also

- [deploying-agents.md](../docs/deploying-agents.md) - Full deployment guide
- [browser-automation.md](../docs/browser-automation.md) - Browser agent documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
