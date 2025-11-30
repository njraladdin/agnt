"""
Browser Agent - Web automation with AI

This agent demonstrates browser automation capabilities using the ADK browser toolset.
It can navigate websites, interact with elements, and analyze page content.
"""

import asyncio

from google.adk.agents.llm_agent import Agent
from google.adk.tools.browser import BrowserToolset
from google.adk.tools.browser import SeleniumBaseBrowser
from google.adk.tools.browser.implementations import BrowserConfig
from google.adk.tools.browser.implementations import BrowserOptions


# Initialize browser globally
browser = SeleniumBaseBrowser(
    options=BrowserOptions(
        browser=BrowserConfig(
            headless=False,  # Set to True for headless mode
            undetectable=True,
            incognito=True,
        )
    )
)


def main():
  """Run the browser agent."""
  print('Initializing browser...')
  # Initialize browser synchronously
  asyncio.run(browser.initialize())

  print('Creating browser agent...')
  # Create agent
  agent = Agent(
      model='gemini-2.5-flash',
      name='browser_agent',
      description='Web automation agent with browser control',
      instruction="""You are a web automation assistant with browser capabilities.

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

Keep responses concise and focused on the task.""",
      tools=[BrowserToolset(browser=browser)],
  )

  print('\nBrowser agent ready!')
  print('Example commands:')
  print('  - "Go to example.com"')
  print('  - "Navigate to github.com and generate a page map"')
  print('  - "Click the login button"')
  print('\nType "exit" to quit\n')

  try:
    # Run in interactive CLI mode (this handles its own event loop)
    agent.run_cli()
  finally:
    print('\nClosing browser...')
    asyncio.run(browser.close())


if __name__ == '__main__':
  main()
