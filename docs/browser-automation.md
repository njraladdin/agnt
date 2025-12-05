# Browser Automation Tools

Guide for using browser automation capabilities with ADK agents.

## Overview

The browser module provides AI agents with web automation capabilities using SeleniumBase. Agents can navigate websites, interact with elements, and analyze page content intelligently.

**Key Features**:

- **Session-aware by default** - Automatically creates isolated browser instances per session for multi-user API deployments
- **Automatic page maps** - Page structure is automatically analyzed and injected into agent's context
- **No manual page map calls needed** - Agent always has up-to-date view of the page

## Quick Start

### 1. Install Dependencies

```bash
pip install seleniumbase>=4.0.0
```

Or install all extensions:

```bash
pip install -e ".[extensions]"
```

### 2. Create a Browser Agent

```python
from google.adk.agents.llm_agent import Agent
from google.adk.tools.browser import BrowserToolset
from google.adk.tools.browser.implementations import BrowserOptions, BrowserConfig

# Create agent with BrowserToolset
agent = Agent(
    model='gemini-2.5-flash',
    name='browser_agent',
    instruction='You are a web automation assistant.',
    tools=[
        BrowserToolset(
            browser_options=BrowserOptions(
                browser=BrowserConfig(
                    headless=False,
                    undetectable=True,
                    incognito=True,
                )
            )
        )
    ],
)

# Run in interactive CLI mode
agent.run_cli()
```

### 3. Run

```bash
python playground/browser_agent.py
```

## How It Works

`BrowserToolset` automatically manages browsers based on context:

- **API Deployment** (with session context): Creates unique browser per session
- **CLI Development** (no session context): Creates single browser for your session
- **Backward Compatible**: Still accepts `browser` parameter for explicit control

This means you write your agent once, and it works correctly in both environments!

## Available Tools

Agents get these browser tools automatically:

| Tool                                         | Description                                   |
| -------------------------------------------- | --------------------------------------------- |
| `navigate_to(url)`                           | Navigate to a URL                             |
| `click_element(selector/ref)`                | Click element by CSS selector, XPath, or ref  |
| `type_text(text, selector/ref, clear_first)` | Type text into an element                     |
| `press_keys(keys, selector/ref)`             | Send keyboard input (Arrow keys, Enter, etc.) |
| `scroll_to_element(selector/ref)`            | Scroll element into view                      |

> [!TIP] > **Using Refs for Token Efficiency**
>
> All interaction tools accept either a `selector` (CSS/XPath) or `ref` (page map reference).
> When the page map shows `[ref=5]`, you can use `ref="5"` instead of the full CSS selector.
> This is preferred as it saves tokens and is more reliable.

> [!NOTE] > **Automatic Page Maps**
>
> Page maps are **automatically generated** after **every** browser tool call as an internal utility.
> The agent receives the page structure in its system instructions before each LLM request.
> This happens automatically without requiring any tool calls.

## Automatic Page Map Generation

The browser module automatically generates page maps before each LLM request if a browser is open, and injects them into the agent's system instructions.

### How It Works

1. **Browser Open**: Agent has an active browser session (from any previous browser tool call)
2. **Before LLM Request**: Page map is automatically generated from the current page state
3. **Inject**: Page map is added to system instructions before the LLM sees the request
4. **Agent Sees**: Current page structure with interactive elements and content

This approach is simpler and more efficient - the page map is always fresh and only generated when needed (right before the agent makes decisions).

### What the Agent Receives

After navigating, the agent automatically sees:

```
CURRENT PAGE CONTENT:
Page title: "Example Page"
URL: https://example.com

INTERACTIVE ELEMENTS:
[0] button "Submit" - #submit-btn
[1] input[type="text"] - #username
[2] a "Login" - .nav-login

CONTENT ELEMENTS:
[10] h1 "Welcome"
[11] p "This is a paragraph..."

CAPTURED API REQUESTS:
GET /api/data - 200 OK
```

### Configuration

```python
BrowserToolset(
    browser_options=BrowserOptions(...),
    auto_generate_page_map=True,  # Enable auto-generation (default)
    inject_page_map_in_prompt=True,  # Inject into system instructions (default)
    page_map_mode='lean',  # 'lean' (default) or 'rich'
)
```

**Options**:

- `auto_generate_page_map`: Enable/disable automatic generation (default: `True`)
- `inject_page_map_in_prompt`: Enable/disable injection into system instructions (default: `True`)
- `page_map_mode`:
  - `'lean'` (default): Compressed format with refs, minimal tokens
  - `'rich'`: Full CSS selectors, more verbose

### Disabling Auto-Generation

If you prefer manual control:

```python
BrowserToolset(
    browser_options=BrowserOptions(...),
    auto_generate_page_map=False,  # Disable
)
```

## Browser Configuration

### BrowserConfig Options

```python
BrowserConfig(
    headless=False,        # Run without visible browser window
    undetectable=True,     # Avoid bot detection
    incognito=True,        # Use incognito/private mode
    user_agent="...",      # Custom user agent
    window_size="1920,1080", # Browser window size
    timeout=30,            # Default timeout in seconds
)
```

### ProxyConfig (Optional)

```python
ProxyConfig(
    enabled=True,
    host="proxy.example.com",
    port=8080,
    username="user",
    password="pass",
)
```

## Session Management

### Automatic Session Cleanup

When deploying as an API, cleanup browsers when sessions end:

```python
from google.adk.tools.browser import BrowserToolset

@app.delete("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def delete_session(app_name: str, user_id: str, session_id: str):
    # Delete session
    await session_service.delete_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )

    # Cleanup browser for this session
    runner = await web_server.get_runner_async(app_name)
    for tool in runner._agent.tools:
        if isinstance(tool, BrowserToolset):
            await tool.close_session_browser(session_id)
```

## Screenshot Artifacts

Browser screenshots are automatically saved as **artifacts** after each browser action. This enables frontends to display a live view of what the browser is seeing.

### How It Works

1. **Browser takes screenshot** after each action (navigate, click, type, etc.)
2. **Screenshot saved as artifact** named `browser_screenshot` (single artifact, versioned)
3. **Event includes `artifactDelta`** so frontends know when the screenshot changed
4. **Frontend fetches artifact** via the artifact API to display

### Frontend Integration

Watch for artifact changes in events and fetch the updated screenshot:

```javascript
// Process events from agent
events.forEach((event) => {
  if (event.actions?.artifactDelta?.browser_screenshot) {
    const version = event.actions.artifactDelta.browser_screenshot;
    console.log(`Screenshot updated to version ${version}`);

    // Fetch and display the screenshot
    fetchAndDisplayScreenshot();
  }
});

async function fetchAndDisplayScreenshot() {
  const response = await fetch(
    `${BASE_URL}/apps/${appName}/users/${userId}/sessions/${sessionId}/artifacts/browser_screenshot`
  );
  const artifact = await response.json();

  // artifact.inlineData.data contains base64-encoded PNG
  if (artifact.inlineData) {
    const imgSrc = `data:${artifact.inlineData.mimeType};base64,${artifact.inlineData.data}`;
    document.getElementById("browser-preview").src = imgSrc;
  }
}
```

### React Example

```jsx
function BrowserPreview({ baseUrl, appName, userId, sessionId }) {
  const [screenshotSrc, setScreenshotSrc] = useState(null);
  const [version, setVersion] = useState(0);

  // Call this when processing events
  const onArtifactDelta = useCallback((artifactDelta) => {
    if (artifactDelta?.browser_screenshot) {
      setVersion(artifactDelta.browser_screenshot);
    }
  }, []);

  // Fetch screenshot when version changes
  useEffect(() => {
    if (version === 0) return;

    fetch(
      `${baseUrl}/apps/${appName}/users/${userId}/sessions/${sessionId}/artifacts/browser_screenshot`
    )
      .then((res) => res.json())
      .then((artifact) => {
        if (artifact.inlineData) {
          setScreenshotSrc(
            `data:${artifact.inlineData.mimeType};base64,${artifact.inlineData.data}`
          );
        }
      });
  }, [version, baseUrl, appName, userId, sessionId]);

  return (
    <div className="browser-preview">
      {screenshotSrc && <img src={screenshotSrc} alt="Browser view" />}
    </div>
  );
}
```

> [!TIP]
> The `browser_screenshot` artifact is a single versioned artifact. Each browser action creates a new version, but you don't need to track versions yourself—just fetch the latest when `artifactDelta` indicates a change.

## Advanced Features

### Element Selection

Three ways to interact with elements:

1. **Refs** (Recommended): `ref="5"` - Use the ref number from the page map
2. **CSS Selectors**: `#id`, `.class`, `button[type="submit"]`
3. **XPath**: `//button[@id='submit']`, `//div[@class='container']//a`

> [!TIP]
> Prefer using `ref` when available - it's more concise and saves tokens!

### Keyboard Input

```python
# Send special keys using ref
press_keys(keys="Enter", ref="5")
press_keys(keys=["ArrowDown", "ArrowDown", "Enter"], ref="5")

# Or using selector
press_keys(keys="Enter", selector="#my-input")

# Supported keys: ArrowUp, ArrowDown, ArrowLeft, ArrowRight,
# Enter, Escape, Tab, Space, PageDown, PageUp, Home, End
```

### Network Capture

The page map optionally captures API requests:

```python
BrowserToolset(
    browser_options=...,
    enable_network_capture=True,  # Capture XHR/Fetch requests
)
```

## Agent Instructions

### Recommended Instruction Template

```python
instruction = """You are a web automation assistant with browser capabilities.

Available tools (all accept either 'selector' CSS/XPath OR 'ref' from page map):
- navigate_to(url): Navigate to a URL
- click_element(selector/ref): Click element by CSS selector, XPath, or ref
- type_text(text, selector/ref, clear_first): Type into an element
- press_keys(keys, selector/ref): Send keyboard input
- scroll_to_element(selector/ref): Scroll to element

The page map is automatically provided in your system instructions after each action.
When you see [ref=5], you can use ref="5" instead of the full CSS selector.
Prefer using refs as they save tokens and are more reliable.

Keep responses concise and focused on the task."""
```

## Example Tasks

### Navigate and Extract Information

```
User: "Go to example.com and tell me what links are available"
Agent:
1. Calls navigate_to("https://example.com")
2. Page map automatically generated after navigation
3. Analyzes INTERACTIVE ELEMENTS section
4. Reports available links
```

### Form Filling

```
User: "Fill out the login form with username 'test' and password 'pass123'"
Agent:
1. Sees form fields in INTERACTIVE ELEMENTS from page map with refs like [ref=3], [ref=4]
2. Calls type_text("test", ref="3") → page map updated
3. Calls type_text("pass123", ref="4") → page map updated
4. Calls click_element(ref="5") → page map updated (for submit button)
```

### Multi-Step Navigation

```
User: "Go to github.com, search for 'python', and click the first result"
Agent:
1. Calls navigate_to("https://github.com") → page map generated
2. Calls type_text(".search-input", "python") → page map updated
3. Calls press_keys(".search-input", "Enter") → page map updated
4. Page changes, fresh page map automatically available
5. Calls click_element on first result → page map updated
```

## PageParser Intelligence

The browser module includes an advanced PageParser that:

- **Separates Interactive vs Content**: Distinguishes clickable elements from text
- **Pattern Compression**: Reduces repetitive elements (e.g., list items)
- **Hidden Element Detection**: Finds dropdown options, multiselect items
- **Table Support**: Special handling for table rows and cells
- **Network Awareness**: Captures API calls for context

This gives agents much better understanding than simple DOM scraping.

## Troubleshooting

### Import Error

If you see `ModuleNotFoundError: No module named 'google.adk.tools.browser'`:

```bash
# Re-run setup
python setup_dev.py
```

### Browser Not Starting

- Check if Chrome/Chromium is installed
- Try `headless=True` if display issues
- Check firewall/antivirus settings

### Element Not Found

- Check the INTERACTIVE ELEMENTS section in the auto-generated page map
- Try XPath if CSS selector doesn't work
- Check if element is in iframe (not currently supported)

## File Locations

```
src/google/adk/tools/browser/
├── __init__.py              # Main exports
├── base_browser.py          # Abstract interface
├── browser_tool.py          # Tool wrapper
├── browser_toolset.py       # Session-aware toolset
├── seleniumbase_browser.py  # SeleniumBase implementation
└── page_parser.py           # Page analysis

playground/
└── browser_agent.py         # Example agent

examples/
└── browser_simple_test.py   # Quick test script
```

## See Also

- [Running Agents Programmatically](running-agents-programmatically.md)
- [Agent Module](agent-module.md)
- [Memory System](memory-system.md)
- [Deploying Agents](deploying-agents.md)
