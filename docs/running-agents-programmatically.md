# Running Agents Programmatically

Quick reference for running agents directly from code without CLI commands.

## Overview

Added three convenience methods to `BaseAgent` class to run agents programmatically:
- `run()` - Synchronous, for simple scripts
- `run_async_simple()` - Asynchronous version
- `run_cli()` - Interactive CLI mode

**Location:** `src/google/adk/agents/base_agent.py` (lines 696-967)

## Methods

### `run_cli()` - Interactive Mode (Most Common)

Start an interactive chat session:

```python
from google.adk.agents.llm_agent import Agent

agent = Agent(
    model='gemini-2.5-flash',
    name='my_agent',
    instruction='You are a helpful assistant'
)

# Start interactive CLI
agent.run_cli()
```

**Features:**
- Interactive loop with prompt
- Maintains conversation context
- Type `exit` to quit
- Handles Ctrl+C gracefully
- Auto-loads .env files

**Parameters:**
- `user_id` (str): User identifier, default='default_user'
- `session_id` (str): Session identifier, default='default_session'
- `app_name` (str | None): Application name, defaults to agent name
- `run_config` (RunConfig | None): Optional run configuration
- `load_dotenv` (bool): Auto-load .env file, default=True

### `run()` - Synchronous

For simple one-off queries:

```python
for event in agent.run('What is 2+2?'):
    if event.content and event.content.parts:
        for part in event.content.parts:
            if part.text:
                print(part.text)
```

**Note:** Each call creates a new runner, so context is NOT preserved across calls.
Use `run_cli()` for multi-turn conversations.

### `run_async_simple()` - Asynchronous

Same as `run()` but async:

```python
import asyncio

async def main():
    async for event in agent.run_async_simple('Hello!'):
        if event.content:
            print(event.content)

asyncio.run(main())
```

## Multi-Turn Conversations with Context

For programmatic multi-turn conversations with full control:

```python
from google.adk.runners import InMemoryRunner
from google.genai import types

runner = InMemoryRunner(agent=agent, app_name='my_app')

# Create session
await runner.session_service.create_session(
    app_name='my_app',
    user_id='user1',
    session_id='session1'
)

# First message
for event in runner.run(
    user_id='user1',
    session_id='session1',
    new_message=types.UserContent(parts=[types.Part(text='My name is Alice')])
):
    print(event.content)

# Second message - context is preserved
for event in runner.run(
    user_id='user1',
    session_id='session1',
    new_message=types.UserContent(parts=[types.Part(text='What is my name?')])
):
    print(event.content)  # Will remember: "Alice"
```

## Environment Variables

All three methods automatically load `.env` files (via `_load_dotenv()` helper).

Set `load_dotenv=False` to disable:

```python
agent.run_cli(load_dotenv=False)
```

See [environment-loading.md](environment-loading.md) for details.

## Implementation Notes

- Methods create `InMemoryRunner` internally
- Session management is automatic
- For production: use `Runner` class directly with proper services
- Located in: `src/google/adk/agents/base_agent.py`

## Examples

See:
- `agent_test/agent.py` - Interactive CLI example
- `agent_test/test_run_methods.py` - All methods demonstrated
- `agent_test/quick_test.py` - Simple test
