"""
Simple Browser Agent Test

Quick test script to verify browser integration works.
"""

import asyncio

from google.adk.agents import LlmAgent
from google.adk.tools.browser import BrowserToolset
from google.adk.tools.browser import SeleniumBaseBrowser
from google.adk.tools.browser.implementations import BrowserConfig
from google.adk.tools.browser.implementations import BrowserOptions


async def main():
  """Quick test of browser integration."""

  # Initialize browser
  browser = SeleniumBaseBrowser(
      options=BrowserOptions(
          browser=BrowserConfig(headless=True, undetectable=True)
      )
  )

  try:
    await browser.initialize()

    # Create simple agent
    agent = LlmAgent(
        name='test_agent',
        model='gemini-2.5-flash',
        instruction='You are a web automation assistant.',
        tools=[BrowserToolset(browser=browser)],
    )

    # Test navigation
    print('Testing browser integration...')
    async for event in agent.run_async_simple(
        'Navigate to example.com and tell me what you see'
    ):
      if event.content and event.content.parts:
        for part in event.content.parts:
          if part.text:
            print(part.text)

  finally:
    await browser.close()


if __name__ == '__main__':
  asyncio.run(main())
