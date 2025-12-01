# Playground Directory

Quick experiments and example agents for the ADK library.

## Directory Structure

```
playground/
├── browser_examples/       # Browser automation examples
│   └── browser_agent.py   # Interactive browser agent
│
├── api_server/            # FastAPI server examples
│   ├── api_server_example.py  # Browser agent API server
│   ├── test_api_client.py     # API client test script
│   └── README.md              # API server documentation
│
├── agent_test/            # Test agent for development
│
├── chrome-data/           # Browser data (gitignored)
├── downloaded_files/      # Downloaded files (gitignored)
├── screenshots/           # Browser screenshots (gitignored)
│
├── .env                   # Environment variables (gitignored)
├── .env.example           # Example environment variables
└── README.md              # This file
```

## Quick Start

### Browser Agent (CLI)

```bash
cd browser_examples
python browser_agent.py
```

Interactive browser automation agent with CLI interface.

### API Server

```bash
cd api_server
uvicorn api_server_example:app --reload
```

Then test with:

```bash
python test_api_client.py
```

See [api_server/README.md](api_server/README.md) for full documentation.

### Test Agent

```bash
cd agent_test
python agent.py
```

Simple test agent for development and experimentation.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:

- `GOOGLE_API_KEY` - Your Google AI API key (for Gemini models)

## Adding New Examples

When adding new examples:

1. **Browser-related**: Add to `browser_examples/`
2. **API/Server-related**: Add to `api_server/`
3. **General agents**: Add to root or create new category folder
4. **Include README**: Document how to run and what it demonstrates

## See Also

- [Running Agents Programmatically](../docs/running-agents-programmatically.md)
- [Browser Automation](../docs/browser-automation.md)
- [Deploying Agents](../docs/deploying-agents.md)
