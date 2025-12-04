"""Example demonstrating the DebugPlugin for inspecting LLM requests.

This example shows how to use the DebugPlugin to save full LLM requests
to debug files for inspection.
"""

import asyncio

from google.genai import types
from google.adk.agents.llm_agent import LlmAgent
from google.adk.plugins.debug_plugin import DebugPlugin
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService


async def main():
  """Run an example agent with debug plugin enabled."""

  # Create the debug plugin
  debug_plugin = DebugPlugin(
      debug_dir="./debug",
  )

  # Create a simple agent
  agent = LlmAgent(
      name="example_agent",
      instruction="You are a helpful assistant. Always be concise and clear.",
      model="gemini-2.0-flash-exp",
  )

  # Create session service and session
  session_service = InMemorySessionService()
  await session_service.create_session(
      app_name="example_app",
      user_id="user",
      session_id="session",
  )

  # Create runner with the debug plugin
  runner = Runner(
      app_name="example_app",
      agent=agent,
      plugins=[debug_plugin],
      session_service=session_service,
  )

  # Run the agent with a test message
  print("Running agent with debug plugin enabled...")
  print("Requests will be saved to: ./debug/")
  print()

  async for event in runner.run_async(
      user_id="user",
      session_id="session",
      new_message=types.Content(role="user", parts=[types.Part(text="What is the capital of France?")]),
  ):
    if event.content and event.content.parts:
      for part in event.content.parts:
        if part.text:
          print(f"{event.author}: {part.text}")

  print()
  print("=" * 80)
  print("Debug files have been saved!")
  print("Check the ./debug/ directory to see the full requests.")
  print("=" * 80)


if __name__ == "__main__":
  asyncio.run(main())
