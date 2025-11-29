"""
Quick test example - demonstrates basic agent usage.

This file shows you how to quickly test agents in the playground.
Feel free to modify or delete this file.
"""

from google.adk.agents.llm_agent import Agent

# Create a simple agent
agent = Agent(
    model='gemini-2.5-flash',
    name='quick_test',
    description='A quick test agent',
    instruction='You are a helpful assistant. Keep responses brief and friendly.',
)

# Run in interactive CLI mode
# Type your messages and press Enter
# Type 'exit' to quit
if __name__ == '__main__':
    print("Starting quick test agent...")
    print("This is in the playground directory - feel free to experiment!\n")

    agent.run_cli()
