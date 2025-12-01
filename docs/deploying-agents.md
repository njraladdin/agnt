# Deploying Agents

This guide covers different deployment strategies for agents built with the ADK library, from local API servers to cloud-based production deployments.

## Overview

ADK agents can be deployed in several ways:

1. **Local API Server** - FastAPI server for development and testing
2. **Google Cloud Run** - Containerized deployment with auto-scaling
3. **Vertex AI Agent Engine** - Managed AI agent platform
4. **Custom Deployment** - Using the `Runner` class programmatically

## Deployment Option 1: Local API Server

The simplest way to make your agent accessible via API is to run the built-in FastAPI server.

### Quick Start

```bash
# Start API server for all agents in a directory
adk api_server path/to/agents_dir

# With custom port
adk api_server path/to/agents_dir --port 8080

# With CORS support for web clients
adk api_server path/to/agents_dir --allow_origins http://localhost:3000
```

### API Endpoints

The server exposes RESTful endpoints for agent interaction:

#### List Available Agents

```http
GET /list-apps
```

#### Session Management

```http
# Create a new session
POST /apps/{app_name}/users/{user_id}/sessions
{
  "session_id": "optional-custom-id",
  "state": {"key": "value"}
}

# Get session
GET /apps/{app_name}/users/{user_id}/sessions/{session_id}

# List sessions for a user
GET /apps/{app_name}/users/{user_id}/sessions

# Delete session
DELETE /apps/{app_name}/users/{user_id}/sessions/{session_id}
```

#### Run Agent

```http
POST /apps/{app_name}/run
{
  "user_id": "user123",
  "session_id": "session456",
  "new_message": {
    "parts": [{"text": "Hello, agent!"}]
  },
  "streaming": false
}
```

### Example: Python Client

```python
import requests

BASE_URL = "http://localhost:8000"
APP_NAME = "my_agent"
USER_ID = "user123"

# Create a session
response = requests.post(
    f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions"
)
session_id = response.json()["id"]

# Send a message to the agent
response = requests.post(
    f"{BASE_URL}/apps/{APP_NAME}/run",
    json={
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {
            "parts": [{"text": "What's the weather like?"}]
        },
        "streaming": False
    }
)

# Process events
for event in response.json():
    if event.get("content"):
        print(event["content"])
```

### Example: JavaScript/TypeScript Client

```typescript
const BASE_URL = "http://localhost:8000";
const APP_NAME = "my_agent";
const USER_ID = "user123";

// Create a session
const sessionResponse = await fetch(
  `${BASE_URL}/apps/${APP_NAME}/users/${USER_ID}/sessions`,
  { method: "POST" }
);
const { id: sessionId } = await sessionResponse.json();

// Send a message
const runResponse = await fetch(`${BASE_URL}/apps/${APP_NAME}/run`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    user_id: USER_ID,
    session_id: sessionId,
    new_message: {
      parts: [{ text: "What's the weather like?" }],
    },
    streaming: false,
  }),
});

const events = await runResponse.json();
events.forEach((event) => {
  if (event.content) {
    console.log(event.content);
  }
});
```

### Advanced Server Configuration

For production-like local deployments, you can customize the server:

```python
from google.adk.cli.adk_web_server import AdkWebServer
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.evaluation.eval_sets_manager import EvalSetsManager
from google.adk.evaluation.eval_set_results_manager import EvalSetResultsManager
from google.adk.cli.utils.agent_loader import AgentLoader
import uvicorn

# Initialize services
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()
artifact_service = InMemoryArtifactService()
credential_service = InMemoryCredentialService()
eval_sets_manager = EvalSetsManager(agents_dir="./agents")
eval_set_results_manager = EvalSetResultsManager(agents_dir="./agents")
agent_loader = AgentLoader(agents_dir="./agents")

# Create web server
web_server = AdkWebServer(
    agent_loader=agent_loader,
    session_service=session_service,
    memory_service=memory_service,
    artifact_service=artifact_service,
    credential_service=credential_service,
    eval_sets_manager=eval_sets_manager,
    eval_set_results_manager=eval_set_results_manager,
    agents_dir="./agents"
)

# Get FastAPI app
app = web_server.get_fast_api_app(
    allow_origins=["http://localhost:3000"],
    otel_to_cloud=False
)

# Run with uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Deployment Option 2: Google Cloud Run

Deploy your agent as a containerized service with automatic scaling.

### Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed and configured
- Docker installed (optional, Cloud Run can build from source)

### Deploy Command

```bash
# Basic deployment
adk deploy to-cloud-run \
  --agent-folder path/to/my_agent \
  --service-name my-agent-service \
  --project my-gcp-project \
  --region us-central1

# With additional options
adk deploy to-cloud-run \
  --agent-folder path/to/my_agent \
  --service-name my-agent-service \
  --project my-gcp-project \
  --region us-central1 \
  --trace-to-cloud \
  --with-ui \
  --allow-origins https://myapp.com
```

### Deployment Options

| Option                   | Description                   | Default                |
| ------------------------ | ----------------------------- | ---------------------- |
| `--agent-folder`         | Path to agent directory       | Required               |
| `--service-name`         | Cloud Run service name        | Required               |
| `--project`              | GCP project ID                | Current gcloud project |
| `--region`               | GCP region                    | None (will prompt)     |
| `--port`                 | Container port                | 8080                   |
| `--trace-to-cloud`       | Enable Cloud Trace            | False                  |
| `--with-ui`              | Deploy with web UI            | False                  |
| `--allow-origins`        | CORS origins                  | None                   |
| `--session-service-uri`  | External session service URI  | None                   |
| `--artifact-service-uri` | External artifact service URI | None                   |
| `--memory-service-uri`   | External memory service URI   | None                   |

### What Gets Deployed

The deployment process:

1. Creates a Dockerfile with:

   - Python 3.11 base image
   - ADK library installation
   - Your agent code
   - Dependencies from `requirements.txt` (if present)

2. Builds and deploys to Cloud Run
3. Sets up environment variables:
   - `GOOGLE_GENAI_USE_VERTEXAI=1`
   - `GOOGLE_CLOUD_PROJECT`
   - `GOOGLE_CLOUD_LOCATION`

### Agent Folder Structure

Your agent folder should contain:

```
my_agent/
├── __init__.py           # Must import agent module
├── agent.py              # Must define root_agent or app
├── requirements.txt      # Optional: additional dependencies
└── ... (other files)
```

### Example: Accessing Deployed Agent

```python
import requests

# Your Cloud Run service URL
SERVICE_URL = "https://my-agent-service-abc123-uc.a.run.app"

# Create session
response = requests.post(
    f"{SERVICE_URL}/apps/my_agent/users/user1/sessions"
)
session_id = response.json()["id"]

# Run agent
response = requests.post(
    f"{SERVICE_URL}/apps/my_agent/run",
    json={
        "user_id": "user1",
        "session_id": session_id,
        "new_message": {"parts": [{"text": "Hello!"}]},
        "streaming": False
    }
)
```

### Using External Services

For production deployments, use managed services for persistence:

```bash
# Deploy with Cloud SQL for sessions
adk deploy to-cloud-run \
  --agent-folder path/to/my_agent \
  --service-name my-agent \
  --session-service-uri "postgresql://user:pass@/db?host=/cloudsql/project:region:instance"

# Deploy with Cloud Storage for artifacts
adk deploy to-cloud-run \
  --agent-folder path/to/my_agent \
  --service-name my-agent \
  --artifact-service-uri "gs://my-bucket/artifacts"
```

## Deployment Option 3: Vertex AI Agent Engine

Deploy to Google's managed AI agent platform for enterprise-grade hosting.

### Prerequisites

- Google Cloud account with Vertex AI API enabled
- `gcloud` CLI configured
- GCS bucket for staging

### Deploy Command

```bash
# Deploy new agent
adk deploy to-agent-engine \
  --agent-folder path/to/my_agent \
  --staging-bucket gs://my-staging-bucket \
  --project my-gcp-project \
  --region us-central1 \
  --display-name "My Agent"

# Update existing agent
adk deploy to-agent-engine \
  --agent-folder path/to/my_agent \
  --staging-bucket gs://my-staging-bucket \
  --agent-engine-id existing-agent-id
```

### Deployment Options

| Option              | Description                         |
| ------------------- | ----------------------------------- |
| `--agent-folder`    | Path to agent directory             |
| `--staging-bucket`  | GCS bucket for deployment artifacts |
| `--project`         | GCP project ID                      |
| `--region`          | GCP region                          |
| `--display-name`    | Human-readable agent name           |
| `--description`     | Agent description                   |
| `--agent-engine-id` | Update existing agent (optional)    |
| `--trace-to-cloud`  | Enable Cloud Trace                  |
| `--api-key`         | API key for Express Mode            |

### Agent Folder Structure

```
my_agent/
├── __init__.py
├── agent.py              # Define root_agent or app
├── requirements.txt      # Optional
├── .env                  # Optional: environment variables
└── .agent_engine_config.json  # Optional: agent engine config
```

### Custom App Configuration

Create a custom `adk_app.py` for advanced configuration:

```python
import os
import vertexai
from vertexai.agent_engines import AdkApp
from .agent import root_agent

vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION"),
)

adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
)
```

## Deployment Option 4: Custom Programmatic Deployment

Use the `Runner` class directly for custom deployment scenarios.

### Basic Custom Server

```python
from fastapi import FastAPI
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

app = FastAPI()

# Create agent
agent = Agent(
    model='gemini-2.5-flash',
    name='my_agent',
    instruction='You are a helpful assistant'
)

# Create runner
runner = InMemoryRunner(agent=agent, app_name='my_app')

@app.post("/chat")
async def chat(user_id: str, message: str):
    # Create or get session
    session = await runner.session_service.create_session(
        app_name='my_app',
        user_id=user_id
    )

    # Run agent
    events = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.UserContent(parts=[types.Part(text=message)])
    ):
        events.append(event)

    return {"events": events}
```

### With Persistent Services

```python
from google.adk.runners import Runner
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.adk.memory.vertex_ai_memory_service import VertexAiMemoryService
from google.adk.artifacts.gcs_artifact_service import GcsArtifactService

# Initialize services
session_service = VertexAiSessionService(
    project_id="my-project",
    location="us-central1"
)

memory_service = VertexAiMemoryService(
    project_id="my-project",
    location="us-central1"
)

artifact_service = GcsArtifactService(
    bucket_name="my-artifacts-bucket"
)

# Create runner with persistent services
runner = Runner(
    agent=agent,
    app_name='my_app',
    session_service=session_service,
    memory_service=memory_service,
    artifact_service=artifact_service
)
```

### Streaming Responses

```python
from fastapi.responses import StreamingResponse
import json

@app.post("/chat/stream")
async def chat_stream(user_id: str, message: str):
    session = await runner.session_service.create_session(
        app_name='my_app',
        user_id=user_id
    )

    async def event_generator():
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=types.UserContent(parts=[types.Part(text=message)])
        ):
            # Send event as JSON line
            yield json.dumps(event.model_dump()) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson"
    )
```

## Best Practices

### Security

1. **Authentication**: Implement authentication before exposing agents publicly
2. **API Keys**: Use environment variables for API keys, never hardcode
3. **CORS**: Configure `--allow-origins` appropriately for web clients
4. **Rate Limiting**: Implement rate limiting for production deployments

### Scalability

1. **Session Management**: Use Vertex AI or Cloud SQL for session persistence
2. **Artifact Storage**: Use GCS for artifact storage in production
3. **Memory Service**: Use Vertex AI Memory Service for long-term memory
4. **Horizontal Scaling**: Cloud Run auto-scales based on traffic

### Monitoring

1. **Cloud Trace**: Enable with `--trace-to-cloud` for distributed tracing
2. **Logging**: Use structured logging for better observability
3. **Metrics**: Monitor response times, error rates, and token usage

### Cost Optimization

1. **Session Cleanup**: Implement session expiration policies
2. **Event Compaction**: Use event compaction to reduce storage costs
3. **Model Selection**: Choose appropriate model sizes for your use case
4. **Caching**: Implement caching for frequently requested data

## Troubleshooting

### Common Issues

**Issue**: Agent not found

```
Solution: Ensure agent folder has __init__.py and agent.py with root_agent defined
```

**Issue**: Dependencies not installed

```
Solution: Add dependencies to requirements.txt in agent folder
```

**Issue**: Authentication errors

```
Solution: Set GOOGLE_APPLICATION_CREDENTIALS or use gcloud auth application-default login
```

**Issue**: CORS errors in browser

```
Solution: Add --allow-origins with your frontend URL
```

## Next Steps

- See [running-agents-programmatically.md](running-agents-programmatically.md) for local development
- See [agent-module.md](agent-module.md) for agent structure details
- See [memory-system.md](memory-system.md) for memory configuration
- See [browser-automation.md](browser-automation.md) for browser-based agents
