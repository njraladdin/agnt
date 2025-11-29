# Agent Module

Quick reference for the agent module structure.

## Key Files

### `src/google/adk/agents/base_agent.py`

Base class for all agents.

**Key Classes:**
- `BaseAgent` - Abstract base for all agent types
- `BaseAgentState` - Base for agent state classes

**Core Attributes:**
```python
class BaseAgent:
    name: str                    # Agent identifier (must be Python identifier)
    description: str             # Used for agent selection in multi-agent systems
    sub_agents: list[BaseAgent]  # Child agents (forms hierarchy)
    parent_agent: BaseAgent      # Parent reference (set automatically)
    before_agent_callback        # Pre-execution hook
    after_agent_callback         # Post-execution hook
```

**Core Methods:**
```python
# Execution
async def run_async(parent_context) -> AsyncGenerator[Event]  # Main entry point
async def run_live(parent_context) -> AsyncGenerator[Event]   # Audio/video mode

# Utilities
def clone(update=None) -> Agent              # Create modified copies
def find_agent(name) -> Optional[BaseAgent]  # Find by name in tree
property root_agent -> BaseAgent             # Get root of tree

# NEW: Programmatic execution (what we added)
def run(message, **kwargs) -> Generator[Event]          # Sync
async def run_async_simple(message, **kwargs)           # Async
def run_cli(**kwargs) -> None                           # Interactive CLI
def _load_dotenv() -> None                              # Helper for .env loading
```

### `src/google/adk/agents/llm_agent.py`

Primary agent implementation using LLMs.

**Key Class:**
```python
class LlmAgent(BaseAgent):
    model: Union[str, BaseLlm]                    # e.g., 'gemini-2.5-flash'
    instruction: Union[str, InstructionProvider]  # Dynamic instructions
    static_instruction: Optional[ContentUnion]    # Static system prompt
    tools: list[ToolUnion]                        # Available tools
    generate_content_config: Optional[...]        # Generation parameters
    disallow_transfer_to_parent: bool             # Control transfers
    disallow_transfer_to_peers: bool
    include_contents: Literal['default', 'none']  # Content inclusion
```

**Type Alias:**
```python
Agent = LlmAgent  # Convenience alias
```

## Agent Hierarchy

Agents can form trees for multi-agent systems:

```python
# Child agents
greeter = Agent(name="greeter", ...)
calculator = Agent(name="calculator", ...)

# Parent coordinates
coordinator = Agent(
    name="coordinator",
    sub_agents=[greeter, calculator]  # Hierarchy established
)

# Access
coordinator.sub_agents[0]      # greeter
greeter.parent_agent          # coordinator
coordinator.root_agent        # coordinator
greeter.root_agent           # coordinator
```

## Lifecycle Hooks

```python
def before_hook(callback_context):
    # Called before agent execution
    # Can return Content to skip agent execution
    return None  # or types.Content(...)

def after_hook(callback_context):
    # Called after agent execution
    # Can return Content to append to response
    return None  # or types.Content(...)

agent = Agent(
    name="my_agent",
    before_agent_callback=before_hook,
    after_agent_callback=after_hook
)
```

## Agent State

Agents can maintain state across invocations:

```python
from google.adk.agents.base_agent import BaseAgentState

class MyAgentState(BaseAgentState):
    counter: int = 0
    last_query: str = ""

# Access in agent
state = self._load_agent_state(ctx, MyAgentState)
```

## Loading Agents

### From Python Code

```python
from google.adk.agents.llm_agent import Agent

agent = Agent(
    model='gemini-2.5-flash',
    name='my_agent',
    instruction='You are helpful'
)
```

### From Config (YAML)

```yaml
# root_agent.yaml
name: my_agent
description: A helpful agent
model: gemini-2.5-flash
instruction: You are helpful
```

```python
agent = Agent.from_config(config, config_abs_path)
```

### Via CLI Loader

```python
from google.adk.cli.utils.agent_loader import AgentLoader

loader = AgentLoader(agents_dir='.')
agent = loader.load_agent('agent_folder_name')
```

## Agent Validation

Agent names must be valid Python identifiers:

```python
Agent(name="my_agent")    # ✓ Valid
Agent(name="my-agent")    # ✗ Invalid (has hyphen)
Agent(name="123agent")    # ✗ Invalid (starts with number)
Agent(name="user")        # ✗ Reserved name
```

## Key Concepts

- **Agent Tree**: Hierarchical structure with parent/child relationships
- **Agent Transfer**: Delegates control to other agents in tree
- **Tools**: Functions the agent can call
- **Instructions**: System prompts guiding behavior
- **Sessions**: Persistent conversation state
- **Events**: Output of agent execution (text, tool calls, transfers)

## Related Files

- `invocation_context.py` - Execution context
- `callback_context.py` - Context for hooks
- `run_config.py` - Runtime configuration
- `base_agent_config.py` - YAML config schema
