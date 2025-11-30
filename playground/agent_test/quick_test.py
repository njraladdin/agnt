"""Quick test to verify .env loading works."""
from google.adk.agents.llm_agent import Agent

agent = Agent(
    model='gemini-2.5-flash',
    name='test',
    instruction='Say hello'
)

# Run a single query
print("Testing from project root...")
for event in agent.run('Say hi'):
    if event.content and event.content.parts:
        for part in event.content.parts:
            if part.text:
                print(f'[{event.author}]: {part.text}')

print("\nSuccess! .env was loaded properly.")
