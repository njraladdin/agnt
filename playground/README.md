# Playground

This directory is for quick experiments, testing, and scratchwork while developing the agnt library.

## Purpose

- **Quick testing** - Try out new features without creating formal examples
- **Debugging** - Reproduce and fix issues
- **Experiments** - Test ideas before implementing them properly
- **Learning** - Explore the library's capabilities

## Important Notes

⚠️ **This directory is gitignored** - Files here won't be committed to the repository.

- Feel free to create any test scripts here
- Don't put important code here - it won't be saved to git
- For permanent examples, use the `examples/` directory (or `agent_test/`)
- For tests, use the `tests/` directory

## Setup

1. Copy `.env.example` to `.env` and add your API keys:
   ```bash
   cp .env.example .env
   ```

2. Create test scripts as needed:
   ```python
   # test_something.py
   from google.adk.agents.llm_agent import Agent

   agent = Agent(model='gemini-2.5-flash', name='test', ...)
   agent.run_cli()
   ```

3. Run them:
   ```bash
   python playground/test_something.py
   ```

## Common Use Cases

### Quick Agent Test
```python
from google.adk.agents.llm_agent import Agent

agent = Agent(
    model='gemini-2.5-flash',
    name='quick_test',
    instruction='You are helpful'
)

# Test in CLI
agent.run_cli()

# Or test programmatically
for event in agent.run('Hello!'):
    if event.content:
        print(event.content)
```

### Testing with Tools
```python
from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

agent = Agent(
    model='gemini-2.5-flash',
    name='math_agent',
    tools=[FunctionTool(add)]
)

agent.run_cli()
```

### Multi-Agent Testing
```python
specialist1 = Agent(name='specialist1', ...)
specialist2 = Agent(name='specialist2', ...)

coordinator = Agent(
    name='coordinator',
    sub_agents=[specialist1, specialist2]
)

coordinator.run_cli()
```

## Tips

- Use descriptive filenames: `test_memory.py`, `debug_tool_calling.py`, etc.
- Add comments to remember what you were testing
- Clean up old scripts occasionally
- If something works well, consider moving it to `examples/` or writing a test
