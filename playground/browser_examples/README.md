# Browser Examples

Browser automation examples using the ADK browser toolset.

## Examples

### browser_agent.py

Interactive browser automation agent with CLI interface.

**Features**:

- Navigate websites
- Analyze page structure with `generate_page_map()`
- Click elements, fill forms, send keyboard input
- Screenshots automatically included in responses

**Run**:

```bash
python browser_agent.py
```

**Example commands**:

- "Go to example.com"
- "Navigate to github.com and generate a page map"
- "Search for 'python' and click the first result"

## Configuration

The browser agent uses `BrowserToolset` with session-aware architecture:

- Automatically creates browser instances as needed
- Proper cleanup on exit
- Works for both CLI and API deployments

To run headless (no visible browser):

```python
BrowserToolset(
    browser_options=BrowserOptions(
        browser=BrowserConfig(
            headless=True,  # Change to True
            undetectable=True,
            incognito=True,
        )
    )
)
```

## See Also

- [Browser Automation Documentation](../../docs/browser-automation.md)
- [API Server Example](../api_server/) - Browser agent as REST API
