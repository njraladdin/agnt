# Plugins

Plugins provide a structured way to intercept and modify agent, tool, and LLM behaviors at critical execution points. They work as callbacks that hook into the agent lifecycle.

## What Are Plugins?

Plugins are Python classes that inherit from `BasePlugin` and override specific callback methods. They allow you to:

- **Log and monitor** agent execution (requests, responses, tool calls)
- **Modify behavior** before/after LLM calls, tool executions, or agent runs
- **Handle errors** with custom retry logic or recovery strategies
- **Inject instructions** globally across all agents
- **Process user input** before it reaches the agent
- **Save artifacts** automatically from user uploads

## How Plugins Work

The `PluginManager` orchestrates plugin execution at key lifecycle points:

1. **User Message** → `on_user_message_callback`
2. **Before Run** → `before_run_callback`
3. **Before Agent** → `before_agent_callback`
4. **Before Model** → `before_model_callback`
5. **After Model** → `after_model_callback`
6. **Before Tool** → `before_tool_callback`
7. **After Tool** → `after_tool_callback`
8. **On Event** → `on_event_callback`
9. **After Agent** → `after_agent_callback`
10. **After Run** → `after_run_callback`

Error callbacks: `on_model_error_callback`, `on_tool_error_callback`

## Basic Usage

```python
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.plugins import LoggingPlugin

# Create plugin instance
logging_plugin = LoggingPlugin()

# Add to runner
runner = Runner(
    agents=[my_agent],
    plugins=[logging_plugin]
)
```

## Built-in Plugins

### LoggingPlugin

Logs all critical events to the console for debugging.

```python
from google.adk.plugins import LoggingPlugin

plugin = LoggingPlugin(name="my_logger")
```

**What it logs:**

- User messages and invocation context
- Agent execution flow
- LLM requests/responses with token usage
- Tool calls with arguments and results
- Events and errors

### GlobalInstructionPlugin

Injects global instructions into all LLM requests.

```python
from google.adk.plugins.global_instruction_plugin import GlobalInstructionPlugin

# Static instruction
plugin = GlobalInstructionPlugin(
    global_instruction="You are a helpful assistant specialized in Python."
)

# Dynamic instruction (function)
def get_instruction(context):
    return f"Current user: {context.user_id}"

plugin = GlobalInstructionPlugin(global_instruction=get_instruction)
```

### ReflectAndRetryToolPlugin

Automatically retries failed tool calls with reflection guidance.

```python
from google.adk.plugins import ReflectAndRetryToolPlugin

# Basic usage - retry up to 3 times per invocation
plugin = ReflectAndRetryToolPlugin(max_retries=3)

# Track failures globally across all invocations
from google.adk.plugins.reflect_retry_tool_plugin import TrackingScope

plugin = ReflectAndRetryToolPlugin(
    max_retries=5,
    tracking_scope=TrackingScope.GLOBAL
)

# Don't throw exceptions, just provide guidance
plugin = ReflectAndRetryToolPlugin(
    max_retries=3,
    throw_exception_if_retry_exceeded=False
)
```

**Features:**

- Concurrency-safe with async locking
- Per-tool failure tracking
- Structured reflection guidance for the LLM
- Configurable scope (per-invocation or global)

### SaveFilesAsArtifactsPlugin

Saves files from user messages as artifacts.

```python
from google.adk.plugins.save_files_as_artifacts_plugin import SaveFilesAsArtifactsPlugin

plugin = SaveFilesAsArtifactsPlugin()
```

**What it does:**

- Extracts inline file data from user messages
- Saves them to the artifact service
- Replaces files with placeholders in the message
- Makes files accessible to tools via artifact service

## Creating Custom Plugins

### Simple Example

```python
from google.adk.plugins import BasePlugin
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext

class CountInvocationPlugin(BasePlugin):
    """Counts agent and LLM invocations."""

    def __init__(self):
        super().__init__(name="count_invocation")
        self.agent_count = 0
        self.llm_request_count = 0

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ):
        self.agent_count += 1
        print(f"Agent run count: {self.agent_count}")
        return None  # Don't modify behavior

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request
    ):
        self.llm_request_count += 1
        print(f"LLM request count: {self.llm_request_count}")
        return None
```

### Advanced Example - Modifying Requests

```python
from google.adk.plugins import BasePlugin
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from typing import Optional

class CustomInstructionPlugin(BasePlugin):
    """Adds custom instructions based on context."""

    def __init__(self):
        super().__init__(name="custom_instruction")

    async def before_model_callback(
        self, *, callback_context, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        # Modify the system instruction
        current = llm_request.config.system_instruction or ""
        llm_request.config.system_instruction = (
            f"IMPORTANT: Be concise.\n\n{current}"
        )

        # Return None to proceed with modified request
        # Return LlmResponse to skip the LLM call entirely
        return None
```

### Advanced Example - Error Handling

```python
from google.adk.plugins import BasePlugin
from typing import Any, Optional

class CustomErrorHandlerPlugin(BasePlugin):
    """Custom error handling for specific tools."""

    def __init__(self):
        super().__init__(name="custom_error_handler")

    async def on_tool_error_callback(
        self, *, tool, tool_args: dict[str, Any], tool_context, error: Exception
    ) -> Optional[dict]:
        # Handle specific tool errors
        if tool.name == "database_query" and "connection" in str(error).lower():
            return {
                "error": "Database connection failed",
                "suggestion": "Please try again in a moment or use cached data."
            }

        # Return None to use default error handling
        return None
```

## Available Callbacks

All callbacks are async and return `Optional` values:

### Invocation Lifecycle

- `on_user_message_callback(invocation_context, user_message)` → `Optional[Content]`
- `before_run_callback(invocation_context)` → `Optional[Content]`
- `after_run_callback(invocation_context)` → `None`
- `on_event_callback(invocation_context, event)` → `Optional[Event]`

### Agent Lifecycle

- `before_agent_callback(agent, callback_context)` → `Optional[Content]`
- `after_agent_callback(agent, callback_context)` → `Optional[Content]`

### Model Lifecycle

- `before_model_callback(callback_context, llm_request)` → `Optional[LlmResponse]`
- `after_model_callback(callback_context, llm_response)` → `Optional[LlmResponse]`
- `on_model_error_callback(callback_context, llm_request, error)` → `Optional[LlmResponse]`

### Tool Lifecycle

- `before_tool_callback(tool, tool_args, tool_context)` → `Optional[dict]`
- `after_tool_callback(tool, tool_args, tool_context, result)` → `Optional[dict]`
- `on_tool_error_callback(tool, tool_args, tool_context, error)` → `Optional[dict]`

### Cleanup

- `close()` → Called when runner is closed

## Return Values

- **Return `None`**: Proceed normally with original data
- **Return a value**: Replace the original with your modified version
- **Raise exception**: Halt execution (in error callbacks)

## Best Practices

1. **Keep plugins focused** - One responsibility per plugin
2. **Handle errors gracefully** - Don't crash the agent
3. **Be async-aware** - Use `async`/`await` properly
4. **Avoid heavy computation** - Plugins run in the hot path
5. **Use meaningful names** - Makes debugging easier
6. **Return `None` when not modifying** - Don't copy data unnecessarily

## Common Use Cases

### Logging and Monitoring

Use `LoggingPlugin` or create custom loggers that send data to your monitoring system.

### Rate Limiting

Track requests in `before_model_callback` and delay or reject if limits exceeded.

### Caching

In `before_model_callback`, check cache and return cached `LlmResponse` to skip the API call.

### Content Filtering

Modify user messages in `on_user_message_callback` to filter sensitive content.

### Tool Retry Logic

Use `ReflectAndRetryToolPlugin` or build custom retry strategies in error callbacks.

### Metrics Collection

Track token usage, latency, and success rates across all callbacks.

### A/B Testing

Randomly modify instructions or model parameters to test different approaches.

## Plugin Registration

Plugins are registered with the `Runner`:

```python
from google.adk.runners import Runner

runner = Runner(
    agents=[agent],
    plugins=[
        LoggingPlugin(),
        GlobalInstructionPlugin("Be helpful"),
        ReflectAndRetryToolPlugin(max_retries=3),
        MyCustomPlugin()
    ]
)
```

Plugins execute in registration order. Order matters when plugins modify the same data.

## Accessing Plugin State

Retrieve registered plugins from the runner:

```python
# Get plugin by name
plugin = runner.plugin_manager.get_plugin("logging_plugin")

# Access plugin state
if isinstance(plugin, CountInvocationPlugin):
    print(f"Total calls: {plugin.agent_count}")
```

## Thread Safety

Plugins may be called concurrently for parallel tool executions. Use async locks if maintaining shared state:

```python
import asyncio

class StatefulPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="stateful")
        self._lock = asyncio.Lock()
        self.counter = 0

    async def before_tool_callback(self, **kwargs):
        async with self._lock:
            self.counter += 1
```

## Examples in the Repo

- **Basic**: `contributing/samples/plugin_basic/count_plugin.py`
- **Built-in**: `src/google/adk/plugins/`
- **Tests**: `tests/unittests/plugins/`
