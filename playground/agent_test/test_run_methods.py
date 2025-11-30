"""Test script demonstrating different ways to run an agent programmatically."""

import asyncio
from google.adk.agents.llm_agent import Agent

# Create an agent
agent = Agent(
    model='gemini-2.5-flash',
    name='test_agent',
    description='A helpful assistant for testing.',
    instruction='Answer questions briefly and accurately.',
)


def test_synchronous_run():
    """Test the synchronous run() method."""
    print('=== Testing synchronous run() ===')
    for event in agent.run('What is the capital of France?'):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f'[{event.author}]: {part.text}')
    print()


async def test_asynchronous_run():
    """Test the asynchronous run_async_simple() method."""
    print('=== Testing asynchronous run_async_simple() ===')
    async for event in agent.run_async_simple('What is 2 + 2?'):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f'[{event.author}]: {part.text}')
    print()


def test_multi_turn_conversation():
    """Test multi-turn conversation with the Runner."""
    print('=== Testing multi-turn conversation ===')
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(agent=agent, app_name='test_app')
    session_id = 'test_session'
    user_id = 'test_user'

    # Create session
    async def create_session():
        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id
        )
    asyncio.run(create_session())

    # First message
    print('User: My name is Alice')
    for event in runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=types.UserContent(parts=[types.Part(text='My name is Alice')])
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f'[{event.author}]: {part.text}')

    # Second message - should remember the name
    print('\nUser: What is my name?')
    for event in runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=types.UserContent(parts=[types.Part(text='What is my name?')])
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f'[{event.author}]: {part.text}')
    print()


if __name__ == '__main__':
    # Run tests
    test_synchronous_run()
    asyncio.run(test_asynchronous_run())
    test_multi_turn_conversation()

    print('=' * 60)
    print('All tests completed!')
    print()
    print('To run the agent in interactive CLI mode, use:')
    print('  python agent_test/agent.py')
    print()
    print('Or in your code:')
    print('  agent.run_cli()')
    print('=' * 60)
