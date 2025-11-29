# ADK Quick Reference Docs

Quick reference documentation for working with the Agent Development Kit.

## What We Added

These docs focus on what we worked on recently - running agents programmatically.

## Documents

### [Running Agents Programmatically](running-agents-programmatically.md)
The main feature we added - how to run agents directly from code.

**Key Points:**
- Three new methods: `run()`, `run_async_simple()`, `run_cli()`
- `run_cli()` for interactive chat (most common use case)
- No manual runner/session setup needed
- Auto-loads `.env` files

**Quick Example:**
```python
from google.adk.agents.llm_agent import Agent

agent = Agent(model='gemini-2.5-flash', name='my_agent',
              instruction='You are helpful')

agent.run_cli()  # Start interactive chat
```

### [Environment Loading](environment-loading.md)
How `.env` files are automatically loaded.

**Key Points:**
- Uses `sys.argv[0]` to find script location
- Searches upwards from script directory
- Matches `adk run` behavior
- Works from any directory

**Why This Matters:**
Running `python agent_test/agent.py` from project root now finds `agent_test/.env` automatically.

### [Agent Module](agent-module.md)
Structure of the agent module.

**Key Points:**
- `BaseAgent` - abstract base class
- `LlmAgent` - main implementation (aliased as `Agent`)
- Agent trees for multi-agent systems
- Lifecycle hooks (before/after callbacks)
- New programmatic methods added to `BaseAgent`

### [Runner Module](runner-module.md)
How the Runner system executes agents.

**Key Points:**
- `Runner` class orchestrates execution
- `InMemoryRunner` for testing
- Sessions track conversation state
- Services: session, artifact, memory, credential
- `run_async()` is the main production API

## How These Relate

```
User Code
    ↓
agent.run_cli()  ← New convenience method we added
    ↓
InMemoryRunner   ← Creates this internally
    ↓
runner.run_async()
    ↓
agent.run_async() ← BaseAgent method
    ↓
LlmAgent execution
    ↓
Events yielded back
```

## File Locations

```
src/google/adk/
├── agents/
│   ├── base_agent.py       ← Added run(), run_cli(), _load_dotenv()
│   ├── llm_agent.py        ← Main Agent class
│   └── invocation_context.py
├── runners.py              ← Runner class
├── sessions/
│   ├── session.py
│   └── in_memory_session_service.py
└── cli/
    ├── cli.py              ← Original adk run implementation
    └── utils/
        └── envs.py         ← Original env loading (we replicated this)
```

## Examples

All in `agent_test/`:
- `agent.py` - Simple interactive CLI
- `test_run_methods.py` - All three methods demonstrated
- `quick_test.py` - Minimal test

## For Next Session

When starting a new session, refer to:

1. **"What can agents do now?"** → [running-agents-programmatically.md](running-agents-programmatically.md)
2. **"How does .env loading work?"** → [environment-loading.md](environment-loading.md)
3. **"How do agents work?"** → [agent-module.md](agent-module.md)
4. **"How does execution work?"** → [runner-module.md](runner-module.md)

## What's Not Covered

These are minimal docs focusing on what we worked on. For full ADK features, see:
- Official ADK documentation
- Source code comments
- Example agents in the repo
