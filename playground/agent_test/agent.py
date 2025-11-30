from google.adk.agents.llm_agent import Agent

root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
)


# Example: Running the agent programmatically through code
if __name__ == '__main__':
    # Run the agent in interactive CLI mode
    # This will start an interactive session where you can chat with the agent
    # Type your messages and press Enter. Type 'exit' to quit.
    #
    # Note: The .env file will be automatically loaded from the current directory
    # or any parent directory, so your API keys will be available.
    root_agent.run_cli()
