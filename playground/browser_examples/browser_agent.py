"""
Browser Agent - Web automation with AI

This agent demonstrates browser automation capabilities using the ADK browser toolset.
It can navigate websites, interact with elements, and analyze page content.

DEBUG MODE:
- System instructions (including auto-generated page maps) are saved to ./debug/browser/
- Each LLM request gets a numbered file showing the complete prompt sent to the model
- This helps you see exactly what page information the agent receives
"""

import asyncio
import logging

from google.adk.agents.llm_agent import Agent
from google.adk.plugins import DebugPlugin
from google.adk.runners import InMemoryRunner
from google.adk.tools.browser import BrowserToolset
from google.adk.tools.browser import BrowserConfig
from google.adk.tools.browser import BrowserOptions
from google.adk.utils.context_utils import Aclosing
from google.genai import types

#load env
from dotenv import load_dotenv
load_dotenv()

# Configure logging to show INFO level for google_adk
logging.basicConfig(
    level=logging.INFO,  # Set root logger to WARNING
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Enable INFO level specifically for google_adk
logging.getLogger('google_adk').setLevel(logging.INFO)


async def main_async():
  """Run the browser agent with debug plugin."""
  print('Creating browser agent...')

  # Create debug plugin to save system instructions
  # This is especially useful for browser agents to see the auto-generated page maps
  debug_plugin = DebugPlugin(
      name='browser_debug',
      debug_dir='./debug/browser'
  )

  # Create agent with BrowserToolset
  # BrowserToolset is session-aware and will automatically manage browsers
  agent = Agent(
      model='gemini-2.5-flash',
      name='browser_agent',
      description='Web automation agent with browser control',
      instruction="""You are a web automation assistant with browser capabilities.



""",
      tools=[
          BrowserToolset(
              browser_options=BrowserOptions(
                  browser=BrowserConfig(
                      headless=False,  # Set to True for headless mode
                      undetectable=True,
                      incognito=True,
                  ),
                  page_map_mode='rich'
              )
          )
      ],
  )

  # Create InMemoryRunner with plugins
  # We can't use agent.run_cli() because it doesn't support plugins
  runner = InMemoryRunner(
      agent=agent,
      app_name='browser_agent',
      plugins=[debug_plugin],
  )

  print('\nBrowser agent ready!')
  print('🔍 DEBUG MODE: System instructions will be saved to ./debug/browser/')
  print('   Check these files to see the auto-generated page maps!\n')
  print('Example commands:')
  print('  - "Go to example.com and tell me what you see"')
  print('  - "Navigate to github.com and search for python"')
  print('  - "Click the login button"')
  print('\nType "exit" to quit\n')

  # Create session
  user_id = 'default_user'
  session_id = 'default_session'
  
  session = await runner.session_service.get_session(
      app_name=runner.app_name,
      user_id=user_id,
      session_id=session_id,
  )
  if not session:
    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

  print(f"Interactive CLI started. Type 'exit' to quit.")
  print(f"Session: {session_id}\n")

  # Interactive loop
  while True:
    try:
      query = input('[user]: ')
    except (EOFError, KeyboardInterrupt):
      print('\nExiting...')
      break

    if not query or not query.strip():
      continue

    if query.strip().lower() == 'exit':
      break

    # Convert to Content
    content = types.UserContent(parts=[types.Part(text=query)])

    # Run the agent
    async with Aclosing(
        runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        )
    ) as agen:
      async for event in agen:
        if event.content and event.content.parts:
          text = ''.join(part.text or '' for part in event.content.parts)
          if text:
            print(f'[{event.author}]: {text}')

  # Close the runner
  await runner.close()


def main():
  """Entry point for the browser agent."""
  asyncio.run(main_async())


if __name__ == '__main__':
  main()


