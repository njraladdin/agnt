# Running Agents Programmatically

This directory demonstrates how to run agents directly from code without using CLI commands.

## Quick Start

### Interactive CLI Mode (Recommended)

Run the agent in an interactive chat interface:

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

**Usage:**
```bash
python agent_test/agent.py
```

Then type your messages and press Enter. Type `exit` to quit.

Example session:
```
Interactive CLI started. Type 'exit' to quit.
Session: default_session

[user]: What is the capital of France?
[my_agent]: The capital of France is Paris.
[user]: What is 2+2?
[my_agent]: 2+2 equals 4.
[user]: exit
```

## Other Ways to Run Agents

### 1. Synchronous (One-off queries)

For simple, single-turn interactions:

```python
for event in agent.run('What is 2+2?'):
    if event.content:
        print(event.content)
```

### 2. Asynchronous

For async/await patterns:

```python
import asyncio

async def main():
    async for event in agent.run_async_simple('What is 2+2?'):
        if event.content:
            print(event.content)

asyncio.run(main())
```

### 3. Multi-turn Conversations with Runner

For more control over sessions and state:

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

# Send messages
for event in runner.run(
    user_id='user1',
    session_id='session1',
    new_message=types.UserContent(parts=[types.Part(text='My name is Alice')])
):
    print(event.content)

# Agent will remember context from previous messages
for event in runner.run(
    user_id='user1',
    session_id='session1',
    new_message=types.UserContent(parts=[types.Part(text='What is my name?')])
):
    print(event.content)  # Will respond: "Your name is Alice"
```

## Methods Summary

| Method | Use Case | Maintains Context | Async |
|--------|----------|-------------------|-------|
| `run_cli()` | Interactive chat interface | ✅ Yes | No (handles internally) |
| `run()` | Simple one-off queries | ❌ No* | No |
| `run_async_simple()` | Simple async queries | ❌ No* | Yes |
| `InMemoryRunner.run()` | Full control, multi-turn | ✅ Yes | No |
| `InMemoryRunner.run_async()` | Full control, production | ✅ Yes | Yes |

*Context is not maintained across different `run()` calls because each creates a new runner instance. Use `run_cli()` or create a `Runner` manually for multi-turn conversations.

## Environment Setup

Make sure to create a `.env` file with your API credentials:

```
GOOGLE_GENAI_USE_VERTEXAI=0
GOOGLE_API_KEY=your_api_key_here
```

## Examples

See the following files:
- `agent.py` - Simple interactive CLI example
- `test_run_methods.py` - Demonstrates all run methods

## Production Use

For production applications, use the `Runner` class directly with proper:
- Session services (persistent storage)
- Artifact services
- Memory services
- Error handling
- Logging and monitoring

The convenience methods (`run()`, `run_cli()`, etc.) are designed for testing, debugging, and simple scripts.
