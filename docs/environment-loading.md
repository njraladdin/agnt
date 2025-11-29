# Environment Variable Loading

How `.env` files are loaded when running agents programmatically.

## Overview

The `_load_dotenv()` helper method automatically loads `.env` files when using convenience methods (`run()`, `run_async_simple()`, `run_cli()`).

**Location:** `src/google/adk/agents/base_agent.py:622-694`

## How It Works

### Search Order

1. **Script's directory** (using `sys.argv[0]`)
   - Finds the actual Python script being run
   - Searches from that directory upwards

2. **Current working directory**
   - Uses `dotenv.find_dotenv(usecwd=True)`
   - Searches upwards from where you ran the command

3. **Agent class location** (fallback)
   - Tries to find .env near the agent definition
   - Rarely used, mostly for edge cases

### Examples

All these scenarios work:

```bash
# From project root
cd /path/to/project
python agent_test/agent.py  # Finds agent_test/.env ✓

# From agent directory
cd agent_test
python agent.py  # Finds .env ✓

# With absolute path
python /full/path/to/agent_test/agent.py  # Finds .env ✓
```

## Implementation Details

```python
def _load_dotenv(self) -> None:
    """Loads .env file from the calling script's directory or current directory."""

    # 1. Try from script location (sys.argv[0])
    script_path = Path(sys.argv[0]).resolve()
    script_dir = script_path.parent
    # Walk up from script_dir looking for .env

    # 2. Try from current working directory
    dotenv_path = dotenv.find_dotenv(usecwd=True)

    # 3. Try from agent class module location
    module = inspect.getmodule(self.__class__)
    # Walk up from module location
```

## Comparison with CLI

This matches how `adk run` loads environment variables:

**CLI Approach** (`src/google/adk/cli/utils/envs.py`):
```python
def load_dotenv_for_agent(agent_name, agent_parent_folder):
    starting_folder = os.path.join(agent_parent_folder, agent_name)
    dotenv_file_path = _walk_to_root_until_found(starting_folder, '.env')
    load_dotenv(dotenv_file_path)
```

**Programmatic Approach** (what we added):
```python
def _load_dotenv(self):
    # Uses sys.argv[0] to find script location
    # Then walks up looking for .env
    # Same effect, different discovery method
```

Both use `python-dotenv` library under the hood.

## Disabling Auto-Load

Set `load_dotenv=False` when calling methods:

```python
agent.run_cli(load_dotenv=False)
agent.run('message', load_dotenv=False)
```

## Required Package

Uses `python-dotenv` library (already in dependencies):

```bash
pip install python-dotenv
```

If not installed, shows warning but doesn't crash.

## Troubleshooting

**Problem:** API key not found

**Solutions:**
1. Ensure `.env` file exists in agent directory
2. Check `.env` format:
   ```
   GOOGLE_GENAI_USE_VERTEXAI=0
   GOOGLE_API_KEY=your_key_here
   ```
3. Run from correct directory
4. Set environment variables manually: `export GOOGLE_API_KEY=...`
5. Pass `load_dotenv=False` and set env vars yourself

**Debug:**
```python
import os
print("API Key:", os.getenv('GOOGLE_API_KEY'))  # Check if loaded
```
