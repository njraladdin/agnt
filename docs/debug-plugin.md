# Debug Plugin

The `DebugPlugin` is a development tool for inspecting the exact requests sent to LLMs during agent execution.

## Problem It Solves

When developing agents, you often need to see:

- The **complete system instruction** sent to the LLM (including dynamically injected content from tools, memory, etc.)
- The full request contents and tool configurations

Terminal logging is often insufficient because:

- Logs are mixed together and hard to read
- System instructions are truncated (e.g., LoggingPlugin shows only 200 chars)
- You can't easily copy/paste or share the exact prompt for debugging

## Features

✅ **Saves full LLM requests** as JSON with all contents and tool configurations  
✅ **Organized by session** - each agent run gets its own directory  
✅ **Sequential numbering** - requests are numbered (001, 002, etc.) within each session  
✅ **Non-intrusive** - errors in the plugin won't break your agent

## Usage

### Basic Usage

```python
from google.adk.agents.llm_agent import LlmAgent
from google.adk.plugins.debug_plugin import DebugPlugin
from google.adk.runners.runner import Runner

# Create the debug plugin
debug_plugin = DebugPlugin(
    debug_dir="./debug",
)

# Create your agent
agent = LlmAgent(
    name="my_agent",
    instruction="You are a helpful assistant.",
    model="gemini-2.0-flash-exp",
)

# Add the plugin to the runner
runner = Runner(
    agents=[agent],
    plugins=[debug_plugin],
)

# Run your agent
async for event in runner.run_async("Hello!"):
    # ... handle events
    pass
```

## Output Structure

The plugin creates a directory structure like this:

```
debug/
├── session_abc123_my_agent/
│   ├── 001_request.json         # Full request details (JSON)
│   ├── 001_request.txt          # Human-readable request (Text)
│   ├── 002_request.json
│   ├── 002_request.txt
│   └── ...
└── session_xyz789_other_agent/
    └── ...
```

### Request JSON Format

The `*_request.json` files contain the full request details in structured JSON format, useful for programmatic analysis.

### Request Text Format

The `*_request.txt` files contain a human-readable version of the request, with properly formatted system instructions and content. This is best for reading the prompt.

```text
MODEL: gemini-2.0-flash-exp
================================================================================

SYSTEM INSTRUCTION:
--------------------
You are a helpful assistant...
[Full text with proper line breaks]

================================================================================

CONTENTS:
--------------------
[USER]
Hello!

[MODEL]
Hi there!

================================================================================
```

```json
{
  "model": "gemini-2.0-flash-exp",
  "system_instruction": "You are a helpful assistant...",
  "contents": [
    {
      "role": "user",
      "parts": [
        {
          "text": "Hello!"
        }
      ]
    }
  ],
  "tools": [
    {
      "name": "search",
      "description": "Search the web",
      "parameters": {}
    }
  ],
  "config": {
    "temperature": 0.7,
    "max_output_tokens": 1024
  }
}
```

## Configuration Options

| Parameter   | Type | Default          | Description                           |
| ----------- | ---- | ---------------- | ------------------------------------- |
| `name`      | str  | `"debug_plugin"` | Plugin instance name                  |
| `debug_dir` | str  | `"./debug"`      | Directory where debug files are saved |

## Use Cases

### 1. Debugging System Instructions

When tools or memory inject content into system instructions, you can see exactly what the LLM receives by inspecting the `system_instruction` field in the JSON file.

### 2. Analyzing Tool Configurations

See exactly how your tools are represented in the LLM request by checking the `tools` array in the JSON file.

### 3. Debugging Multi-Turn Conversations

Track how the conversation history is sent to the LLM across multiple turns. Each request will be numbered (001, 002, 003...) so you can see the progression.

### 4. Sharing Prompts for Review

When you need to share the exact prompt with a colleague or in a bug report:

1. Run your agent with the debug plugin
2. Find the relevant `*_request.json` file
3. Copy/paste or attach the file

## Best Practices

### Development vs. Production

**Only use this plugin in development!** It writes files to disk and can slow down your agent.

```python
import os

plugins = []
if os.getenv("DEBUG_MODE") == "true":
    plugins.append(DebugPlugin(debug_dir="./debug"))

runner = Runner(agents=[agent], plugins=plugins)
```

### Cleaning Up Debug Files

The plugin creates many files. Clean them up periodically:

```bash
# Remove all debug files older than 7 days
find ./debug -type f -mtime +7 -delete
```

Or add a cleanup script:

```python
import shutil
from pathlib import Path

def cleanup_debug_files(debug_dir="./debug", keep_latest=5):
    """Keep only the N most recent debug directories."""
    debug_path = Path(debug_dir)
    if not debug_path.exists():
        return

    # Get all subdirectories sorted by modification time
    dirs = sorted(debug_path.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)

    # Remove older directories
    for old_dir in dirs[keep_latest:]:
        if old_dir.is_dir():
            shutil.rmtree(old_dir)
```

### Combining with Other Plugins

The debug plugin works well with other plugins:

```python
from google.adk.plugins.logging_plugin import LoggingPlugin
from google.adk.plugins.debug_plugin import DebugPlugin

runner = Runner(
    agents=[agent],
    plugins=[
        LoggingPlugin(),      # Terminal output for quick feedback
        DebugPlugin(),        # Detailed files for deep inspection
    ],
)
```

## Troubleshooting

### Plugin Not Saving Files

1. Check that the debug directory is writable
2. Check for errors in the terminal (plugin errors are printed but don't break the agent)
3. Verify the plugin is added to the runner's `plugins` list

### Files Are Empty or Missing System Instructions

This happens when `llm_request.config.system_instruction` is `None`. This is normal for:

- Agents without instructions
- Some LLM providers that don't use system instructions

### Too Many Files

Use `save_system_instruction_only=True` to reduce file count, or implement the cleanup script above.

## Implementation Details

The plugin uses the `before_model_callback` hook from `BasePlugin`:

- **before_model_callback**: Captures the `LlmRequest` object right before it's sent to the LLM

This ensures you see the **exact** data sent, including all dynamic injections from tools, memory, global instructions, etc.

## Related

- [LoggingPlugin](../src/google/adk/plugins/logging_plugin.py) - Terminal-based logging
- [BasePlugin](../src/google/adk/plugins/base_plugin.py) - Plugin base class
- [Callbacks Documentation](https://google.github.io/adk-docs/callbacks/) - Agent callback system
