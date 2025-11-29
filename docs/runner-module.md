# Runner Module

Quick reference for the Runner system that executes agents.

## Key File

**Location:** `src/google/adk/runners.py`

## Runner Class

Execution engine that manages agent execution within sessions.

### Initialization

```python
from google.adk.runners import Runner, InMemoryRunner
from google.adk.apps.app import App

# Option 1: With App (recommended)
app = App(name='my_app', root_agent=my_agent, plugins=[...])
runner = Runner(
    app=app,
    session_service=session_service,
    artifact_service=artifact_service,
    credential_service=credential_service,
)

# Option 2: Without App
runner = Runner(
    app_name='my_app',
    agent=my_agent,
    session_service=session_service,
    artifact_service=artifact_service,
)

# Option 3: In-Memory (for testing)
runner = InMemoryRunner(agent=my_agent, app_name='my_app')
```

### Key Attributes

```python
class Runner:
    app_name: str                                  # Application identifier
    agent: BaseAgent                               # Root agent to execute
    session_service: BaseSessionService            # Manages sessions
    artifact_service: Optional[BaseArtifactService]  # Artifact storage
    memory_service: Optional[BaseMemoryService]    # Conversation memory
    credential_service: Optional[BaseCredentialService]  # Auth
    plugin_manager: PluginManager                  # Plugins
    context_cache_config: Optional[...]            # Caching config
    resumability_config: Optional[...]             # Resume config
```

## Execution Methods

### `run()` - Synchronous

For testing/convenience:

```python
for event in runner.run(
    user_id='user1',
    session_id='session1',
    new_message=types.Content(...)
):
    print(event.content)
```

**Note:** Runs async code in background thread. Use `run_async()` for production.

### `run_async()` - Asynchronous (Production)

Main production interface:

```python
async for event in runner.run_async(
    user_id='user1',
    session_id='session1',
    new_message=types.Content(...),
    run_config=RunConfig(...),
):
    # Process events
    if event.content:
        print(event.content)
```

**Parameters:**
- `user_id` (str): User identifier
- `session_id` (str): Session identifier
- `invocation_id` (str | None): For resuming interrupted invocations
- `new_message` (Content | None): Message to process
- `state_delta` (dict | None): State changes to apply
- `run_config` (RunConfig | None): Runtime configuration

### `run_debug()` - Debug Helper

Quick testing without manual session management:

```python
events = await runner.run_debug(
    "What is 2+2?",
    user_id='test_user',
    session_id='test_session'
)

# Multiple messages
events = await runner.run_debug([
    "Hello!",
    "What is my name?"
], session_id='test_session')
```

### `run_live()` - Audio/Video Mode

For real-time audio/video conversations:

```python
from google.adk.agents.live_request_queue import LiveRequestQueue

queue = LiveRequestQueue()

async for event in runner.run_live(
    user_id='user1',
    session_id='session1',
    live_request_queue=queue,
):
    # Handle audio events
    pass
```

## Execution Flow

```
runner.run_async()
    ↓
1. Load/create Session from session_service
2. Create InvocationContext
3. Run plugin.before_run_callback()
4. Execute agent.run_async(context)
5. For each event:
   - Append to session.events
   - Run plugin.on_event_callback()
   - Yield to caller
6. Run plugin.after_run_callback()
7. Run event compaction (if enabled)
```

## Sessions

Sessions track conversations and state:

```python
from google.adk.sessions.session import Session

class Session:
    id: str                     # Unique identifier
    app_name: str              # Associated app
    user_id: str               # User identifier
    state: dict[str, Any]      # Conversation state
    events: list[Event]        # All conversation events
    last_update_time: float    # Timestamp
```

### Session Management

```python
# Create
session = await session_service.create_session(
    app_name='my_app',
    user_id='user1',
    session_id='session1'
)

# Get
session = await session_service.get_session(
    app_name='my_app',
    user_id='user1',
    session_id='session1'
)

# Append event
await session_service.append_event(session, event)
```

## InMemoryRunner

Convenience class for testing:

```python
class InMemoryRunner(Runner):
    """Uses in-memory implementations for all services."""

    def __init__(
        self,
        agent: Optional[BaseAgent] = None,
        app_name: Optional[str] = None,
        plugins: Optional[list[BasePlugin]] = None,
        app: Optional[App] = None,
    ):
        # Automatically creates:
        # - InMemorySessionService
        # - InMemoryArtifactService
        # - InMemoryMemoryService
```

**Use for:**
- Quick testing
- Development
- Demos
- Simple scripts

**Don't use for:**
- Production (sessions lost on restart)
- Persistent conversations
- Multi-user systems

## Services

### Session Service

Manages conversation sessions:

```python
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.database_session_service import DatabaseSessionService

# In-memory (testing)
session_service = InMemorySessionService()

# Database (production)
session_service = DatabaseSessionService(
    connection_string='postgresql://...'
)
```

### Artifact Service

Manages files generated during conversations:

```python
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService

artifact_service = InMemoryArtifactService()

# Save
await artifact_service.save_artifact(
    app_name='my_app',
    user_id='user1',
    session_id='session1',
    filename='output.txt',
    artifact=types.Part(...)
)

# Get
artifact = await artifact_service.get_artifact(
    app_name='my_app',
    user_id='user1',
    session_id='session1',
    filename='output.txt'
)
```

### Credential Service

Manages authentication tokens:

```python
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService

credential_service = InMemoryCredentialService()
```

## Run Config

Control agent behavior at runtime:

```python
from google.adk.agents.run_config import RunConfig

run_config = RunConfig(
    support_cfc=True,                    # Code execution
    response_modalities=['TEXT'],        # Output format
    save_input_blobs_as_artifacts=False, # File handling
    # ... more options
)

await runner.run_async(..., run_config=run_config)
```

## Context Management

```python
# Async context manager
async with runner:
    # Run agents
    async for event in runner.run_async(...):
        pass
# Automatically calls runner.close()
```

## Related Files

- `sessions/` - Session management
- `artifacts/` - Artifact storage
- `plugins/` - Plugin system
- `apps/app.py` - App container
- `agents/invocation_context.py` - Execution context
