# Browser Automation Tools

Guide for using browser automation capabilities with ADK agents.

## Overview

The browser module provides AI agents with web automation capabilities using SeleniumBase. Agents can navigate websites, interact with elements, and analyze page content intelligently.

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
import asyncio
from google.adk.agents.llm_agent import Agent
from google.adk.tools.browser import BrowserToolset, SeleniumBaseBrowser
from google.adk.tools.browser.implementations import BrowserOptions, BrowserConfig

async def main():
  # Initialize browser
  browser = SeleniumBaseBrowser(
      options=BrowserOptions(
          browser=BrowserConfig(
              headless=False,
              undetectable=True,
              incognito=True,
          )
      )
  )
  await browser.initialize()

  # Create agent
  agent = Agent(
      model='gemini-2.5-flash',
      name='browser_agent',
      instruction='You are a web automation assistant.',
      tools=[BrowserToolset(browser=browser)],
  )

  # Run
  agent.run_cli()

  # Cleanup
  await browser.close()

asyncio.run(main())
```

### 3. Run

```bash
python playground/browser_agent.py
```

## Available Tools

Agents get these browser tools automatically:

| Tool                                     | Description                                         |
| ---------------------------------------- | --------------------------------------------------- |
| `navigate_to(url)`                       | Navigate to a URL                                   |
| `generate_page_map()`                    | Analyze page structure and get interactive elements |
| `click_element(selector)`                | Click element by CSS selector or XPath              |
| `type_text(selector, text, clear_first)` | Type text into an element                           |
| `press_keys(selector, keys)`             | Send keyboard input (Arrow keys, Enter, etc.)       |
| `scroll_to_element(selector)`            | Scroll element into view                            |

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

## Page Map Feature

The `generate_page_map()` tool is the most powerful feature. It analyzes the page and returns:

1. **Interactive Elements** - Buttons, links, inputs with unique refs
2. **Content Elements** - Text, headings, paragraphs
3. **API Requests** - Network calls captured during page load

### Example Usage

```python
instruction = """
Best practices:
1. Always call generate_page_map() after navigating
2. Use element refs or CSS selectors from the page map
3. The page map separates interactive from content elements
4. Screenshots are automatically included in responses
"""
```

### Page Map Output

The agent receives formatted data like:

```
Interactive Elements:
[0] button "Submit" - #submit-btn
[1] input[type="text"] - #username
[2] a "Login" - .nav-login

Content Elements:
[10] h1 "Welcome"
[11] p "This is a paragraph..."
```

## Advanced Features

### Element Selection

Two ways to interact with elements:

1. **CSS Selectors**: `#id`, `.class`, `button[type="submit"]`
2. **XPath**: `//button[@id='submit']`, `//div[@class='container']//a`

### Keyboard Input

```python
# Send special keys
press_keys(selector, "Enter")
press_keys(selector, ["ArrowDown", "ArrowDown", "Enter"])

# Supported keys: ArrowUp, ArrowDown, ArrowLeft, ArrowRight,
# Enter, Escape, Tab, Space, PageDown, PageUp, Home, End
```

### Network Capture

The page map optionally captures API requests:

```python
BrowserToolset(
    browser=browser,
    enable_page_map=True,
    enable_network_capture=True,  # Capture XHR/Fetch requests
)
```

## Agent Instructions

### Recommended Instruction Template

```python
instruction = """You are a web automation assistant with browser capabilities.

Available tools:
- navigate_to(url): Navigate to a URL
- generate_page_map(): Analyze page and get interactive elements with refs
- click_element(selector): Click element by CSS selector or XPath
- type_text(selector, text, clear_first): Type into an element
- press_keys(selector, keys): Send keyboard input
- scroll_to_element(selector): Scroll to element

Best practices:
1. Always call generate_page_map() after navigating to understand the page
2. Use element refs or CSS selectors from the page map
3. The page map shows interactive elements separately from content
4. Screenshots are automatically included in your responses

Keep responses concise and focused on the task."""
```

## Example Tasks

### Navigate and Extract Information

```
User: "Go to example.com and tell me what links are available"
Agent:
1. Calls navigate_to("https://example.com")
2. Calls generate_page_map()
3. Analyzes interactive elements
4. Reports available links
```

### Form Filling

```
User: "Fill out the login form with username 'test' and password 'pass123'"
Agent:
1. Calls generate_page_map() to find form fields
2. Calls type_text("#username", "test")
3. Calls type_text("#password", "pass123")
4. Calls click_element("#submit-btn")
```

### Multi-Step Navigation

```
User: "Go to github.com, search for 'python', and click the first result"
Agent:
1. Calls navigate_to("https://github.com")
2. Calls generate_page_map()
3. Calls type_text(".search-input", "python")
4. Calls press_keys(".search-input", "Enter")
5. Waits for page load
6. Calls generate_page_map()
7. Calls click_element on first result
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

- Use `generate_page_map()` to verify element exists
- Try XPath if CSS selector doesn't work
- Check if element is in iframe (not currently supported)

## File Locations

```
src/google/adk/tools/browser/
├── __init__.py              # Main exports
├── base_browser.py          # Abstract interface
├── browser_tool.py          # Tool wrapper
├── browser_toolset.py       # Toolset
└── implementations/
    ├── browser.py           # SeleniumBase browser (1268 lines)
    ├── page_parser.py       # Page analysis (1798 lines)
    └── seleniumbase_browser.py  # Adapter

playground/
└── browser_agent.py         # Example agent

examples/
└── browser_simple_test.py   # Quick test script
```

## See Also

- [Running Agents Programmatically](running-agents-programmatically.md)
- [Agent Module](agent-module.md)
- [Memory System](memory-system.md)
