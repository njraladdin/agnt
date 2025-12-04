"""
Simple FastAPI Server Example for Browser Agent

This example shows how to expose a browser agent via a REST API.
It demonstrates session management and agent execution in an API context.

Run with: uvicorn api_server_example:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import uuid
import os
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()  # Load from current directory
# Also try parent directory (playground folder)
load_dotenv(Path(__file__).parent.parent / '.env')

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.apps import App
from google.adk.tools.browser import BrowserToolset
from google.adk.tools.browser import BrowserOptions, BrowserConfig
from google.genai import types


# Create browser agent
browser_agent = Agent(
    model='gemini-2.5-flash',
    name='browser_agent',
    description='Web automation agent with browser control',
    instruction="""You are a web automation assistant with browser capabilities.

Available tools:
- navigate_to(url): Navigate to a URL
- generate_page_map(): Analyze page and get interactive elements
- click_element(selector): Click element by CSS selector or XPath
- type_text(selector, text, clear_first): Type into an element
- press_keys(selector, keys): Send keyboard input
- scroll_to_element(selector): Scroll to element

Best practices:
1. Always call generate_page_map() after navigating
2. Use element refs or CSS selectors from the page map
3. Keep responses concise and focused

Be helpful and efficient.""",
    tools=[
        BrowserToolset(
            browser_options=BrowserOptions(
                browser=BrowserConfig(
                    headless=True,  # Headless for server
                    undetectable=True,
                    incognito=True,
                )
            )
        )
    ],
)

# Create app and runner
adk_app = App(name='browser_app', root_agent=browser_agent)
runner = InMemoryRunner(app=adk_app)


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Browser Agent API starting up...")
    yield
    # Shutdown
    print("Browser Agent API shutting down...")
    await runner.close()


# Create FastAPI app with lifespan
app = FastAPI(
    title="Browser Agent API",
    description="API for interacting with a browser automation agent",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    events_count: int


class SessionInfo(BaseModel):
    session_id: str
    user_id: str
    message_count: int


# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "agent": "browser_agent",
        "message": "Browser Agent API is running. Use POST /chat to interact."
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the browser agent.
    
    The agent will process the message and return a response.
    Session is automatically managed - provide session_id to continue a conversation.
    """
    try:
        # Generate session_id if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Ensure session exists - create if it doesn't
        # This follows the ADK pattern from adk_web_server.py
        session = await runner.session_service.get_session(
            app_name='browser_app',
            user_id=request.user_id,
            session_id=session_id
        )
        
        if not session:
            # Session doesn't exist, create it using the proper method
            session = await runner.session_service.create_session(
                app_name='browser_app',
                user_id=request.user_id,
                session_id=session_id
            )
        
        # Run agent
        events = []
        response_text = ""
        
        async for event in runner.run_async(
            user_id=request.user_id,
            session_id=session_id,
            new_message=types.UserContent(
                parts=[types.Part(text=request.message)]
            )
        ):
            events.append(event)
            
            # Extract text from agent response
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
        
        return ChatResponse(
            session_id=session_id,
            response=response_text or "Agent completed the task.",
            events_count=len(events)
        )
        
    except Exception as e:
        import traceback
        print(f"Error in chat endpoint: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{user_id}", response_model=List[SessionInfo])
async def list_sessions(user_id: str):
    """List all sessions for a user."""
    try:
        response = await runner.session_service.list_sessions(
            app_name='browser_app',
            user_id=user_id
        )
        
        # Handle both response object and direct list
        sessions = response.sessions if hasattr(response, 'sessions') else response
        
        return [
            SessionInfo(
                session_id=session.id,
                user_id=session.user_id,
                message_count=len(session.events)  # Changed from turns to events
            )
            for session in sessions
        ]
    except Exception as e:
        import traceback
        print(f"Error in list_sessions: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sessions/{user_id}/{session_id}")
async def delete_session(user_id: str, session_id: str):
    """Delete a specific session and cleanup its browser."""
    try:
        # Delete session
        await runner.session_service.delete_session(
            app_name='browser_app',
            user_id=user_id,
            session_id=session_id
        )
        
        # Cleanup browser for this session
        for tool in browser_agent.tools:
            if isinstance(tool, BrowserToolset):
                await tool.close_session_browser(session_id)
        
        return {"status": "deleted", "session_id": session_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("Starting Browser Agent API server...")
    print("API docs available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
