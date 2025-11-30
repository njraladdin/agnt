# Memory System

Quick reference for the memory system in Google ADK.

## Overview

The memory system allows agents to store and retrieve information from past conversations. Memory is **session-based** - entire conversation sessions are ingested into memory and can be searched semantically.

## Key Files

- `src/google/adk/memory/base_memory_service.py` - Abstract interface
- `src/google/adk/memory/in_memory_memory_service.py` - Testing implementation
- `src/google/adk/memory/vertex_ai_memory_bank_service.py` - Production (Memory Bank)
- `src/google/adk/memory/vertex_ai_rag_memory_service.py` - Production (RAG)
- `src/google/adk/tools/load_memory_tool.py` - Manual memory loading
- `src/google/adk/tools/preload_memory_tool.py` - Automatic memory loading

## Core Concepts

### Memory Entry

```python
class MemoryEntry:
    content: types.Content          # The actual content
    custom_metadata: dict[str, Any] # Optional metadata
    id: Optional[str]               # Unique identifier
    author: Optional[str]           # Who created it (user/agent)
    timestamp: Optional[str]        # When it was created (ISO 8601)
```

### Base Memory Service

All memory services implement this interface:

```python
class BaseMemoryService(ABC):
    @abstractmethod
    async def add_session_to_memory(self, session: Session):
        """Adds a session to memory storage"""

    @abstractmethod
    async def search_memory(
        self, *, app_name: str, user_id: str, query: str
    ) -> SearchMemoryResponse:
        """Searches for relevant memories"""
```

## Memory Implementations

### 1. InMemoryMemoryService (Testing Only)

**Technology:** Simple keyword matching (no vector database)

**How it works:**

- Stores sessions in a dictionary in RAM
- Searches using word overlap (case-insensitive)
- Example: "What did I eat?" matches "I ate pizza" because "I" overlaps

**Characteristics:**

- ❌ No semantic understanding
- ❌ No persistence (lost on restart)
- ✅ Fast and simple for testing
- ✅ Thread-safe

**Usage:**

```python
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService

memory_service = InMemoryMemoryService()
```

### 2. VertexAiMemoryBankService (Production)

**Technology:** Google Vertex AI Memory Bank with vector embeddings

**How it works:**

- Sessions are sent to Vertex AI Memory Bank
- Google automatically generates embeddings (vectors)
- Semantic search finds relevant memories
- Returns extracted "facts" from conversations

**Characteristics:**

- ✅ Semantic search (understands meaning)
- ✅ Managed by Google (no manual setup)
- ✅ Persistent storage
- ✅ Returns ranked results

**Usage:**

```python
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService

memory_service = VertexAiMemoryBankService(
    project='my-project',
    location='us-central1',
    agent_engine_id='123456'
)
```

### 3. VertexAiRagMemoryService (Production)

**Technology:** Vertex AI RAG (Retrieval Augmented Generation) with vector database

**How it works:**

- Sessions saved as text files
- Uploaded to Vertex AI RAG Corpus
- RAG automatically chunks text and generates embeddings
- Vector similarity search retrieves relevant chunks

**Characteristics:**

- ✅ Full vector database (RAG corpus)
- ✅ Configurable similarity thresholds
- ✅ Returns full text chunks (not just facts)
- ✅ Persistent storage

**Usage:**

```python
from google.adk.memory.vertex_ai_rag_memory_service import VertexAiRagMemoryService

memory_service = VertexAiRagMemoryService(
    rag_corpus='projects/my-project/locations/us-central1/ragCorpora/123',
    similarity_top_k=5,
    vector_distance_threshold=0.5
)
```

## Memory Lookup Methods

| Implementation            | Search Method           | Vector DB           | Semantic | Use Case               |
| ------------------------- | ----------------------- | ------------------- | -------- | ---------------------- |
| InMemoryMemoryService     | Keyword matching        | ❌ No               | ❌ No    | Testing                |
| VertexAiMemoryBankService | Embeddings + similarity | ✅ Yes (managed)    | ✅ Yes   | Production (facts)     |
| VertexAiRagMemoryService  | RAG vector search       | ✅ Yes (RAG corpus) | ✅ Yes   | Production (full text) |

## Memory Tools

### 1. preload_memory_tool (Automatic)

**Purpose:** Automatically inject relevant memories into every LLM request

**How it works:**

1. Runs before each LLM request
2. Uses user's message as search query
3. Searches memory for relevant past conversations
4. Injects results into system instructions

**Usage:**

```python
from google.adk.tools.preload_memory_tool import preload_memory_tool

agent = Agent(
    name='my_agent',
    tools=[preload_memory_tool]
)
```

**What the agent sees:**

```
[Automatically injected into system instructions]
The following content is from your previous conversations with the user.
They may be useful for answering the user's current query.
<PAST_CONVERSATIONS>
Time: 2025-11-29T12:00:00
user: I ate pizza yesterday
</PAST_CONVERSATIONS>
```

**Characteristics:**

- ✅ Fully automatic
- ✅ No agent action required
- ✅ Provides passive context
- ❌ Agent can't control the query
- ❌ Always uses user's message as query

### 2. load_memory_tool (Manual)

**Purpose:** Let agents explicitly search memory with custom queries

**How it works:**

1. Agent decides when to search memory
2. Agent specifies the search query
3. Tool returns matching memories
4. Agent uses results to answer user

**Usage:**

```python
from google.adk.tools.load_memory_tool import load_memory_tool

agent = Agent(
    name='my_agent',
    tools=[load_memory_tool],
    instruction="""
You have memory. If questions need you to look up memory,
call load_memory function with a query.
"""
)
```

**Example conversation:**

```
User: "What's my favorite food?"
Agent: [calls load_memory(query="favorite food")]
Tool: [returns MemoryEntry(text="I love pizza")]
Agent: "Your favorite food is pizza!"
```

**Characteristics:**

- ✅ Agent-controlled
- ✅ Custom search queries
- ✅ Explicit memory retrieval
- ❌ Requires agent to decide when to use it
- ❌ Uses a tool call (costs tokens)

### Comparison

| Feature        | preload_memory_tool       | load_memory_tool       |
| -------------- | ------------------------- | ---------------------- |
| **Trigger**    | Automatic (every request) | Manual (agent decides) |
| **Control**    | System-controlled         | Agent-controlled       |
| **Query**      | User's message            | Agent specifies        |
| **Visibility** | System instructions       | Tool result            |
| **Best For**   | Passive context           | Active retrieval       |

**Recommendation:** Use both together! `preload_memory_tool` provides context, `load_memory_tool` lets agents dig deeper.

## Memory Workflow

### Adding Memory

```python
# 1. User has conversation
session = await session_service.create_session(
    app_name='my_app',
    user_id='user1'
)

# 2. Conversation happens
async for event in runner.run_async(
    user_id='user1',
    session_id=session.id,
    new_message=types.Content(...)
):
    # Events are added to session
    pass

# 3. External code saves session to memory
await memory_service.add_session_to_memory(session)
```

### Retrieving Memory

```python
# Automatic (with preload_memory_tool)
# - Happens automatically before each LLM request
# - Uses user's message as query
# - Injects into system instructions

# Manual (with load_memory_tool)
# - Agent calls: load_memory(query="...")
# - Returns: LoadMemoryResponse(memories=[...])
# - Agent uses results in response
```

## Important Limitations

### ❌ Agents Cannot Write to Memory Directly

There is **no tool** for agents to create memory entries. Agents can only:

- ✅ READ memory (via `load_memory_tool` or `preload_memory_tool`)
- ❌ WRITE memory (no such tool exists)

Memory is only created by:

```python
# External code (not agent)
await memory_service.add_session_to_memory(session)
```

### ❌ Memory is Session-Level, Not Note-Level

You cannot create individual notes like:

- "User's name is Jack"
- "User prefers dark mode"
- "User's birthday is Jan 1"

Instead, entire sessions are ingested:

- Session 1: [user: "My name is Jack", agent: "Nice to meet you"]
- Session 2: [user: "I prefer dark mode", agent: "Noted"]

### ❌ No Structured Memory

Memory is unstructured conversation history, not:

- Key-value pairs
- Categorized facts
- Structured databases

## Creating Custom Memory Services

You can use **any vector database** (Qdrant, Pinecone, Weaviate, ChromaDB, etc.)

### Example: Qdrant Memory Service

```python
from qdrant_client import QdrantClient
from google.adk.memory.base_memory_service import BaseMemoryService, SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from google.genai import types

class QdrantMemoryService(BaseMemoryService):
    def __init__(self, qdrant_url: str, collection_name: str, embedding_model):
        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name
        self.embedding_model = embedding_model

    async def add_session_to_memory(self, session: Session):
        for event in session.events:
            if event.content and event.content.parts:
                text = ' '.join([p.text for p in event.content.parts if p.text])

                # Generate embedding
                embedding = self.embedding_model.encode(text)

                # Store in Qdrant
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[{
                        "id": event.id,
                        "vector": embedding,
                        "payload": {
                            "text": text,
                            "author": event.author,
                            "timestamp": event.timestamp,
                            "app_name": session.app_name,
                            "user_id": session.user_id
                        }
                    }]
                )

    async def search_memory(
        self, *, app_name: str, user_id: str, query: str
    ) -> SearchMemoryResponse:
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query)

        # Search Qdrant
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter={
                "must": [
                    {"key": "app_name", "match": {"value": app_name}},
                    {"key": "user_id", "match": {"value": user_id}}
                ]
            },
            limit=10
        )

        # Convert to MemoryEntry objects
        memories = [
            MemoryEntry(
                content=types.Content(parts=[types.Part(text=hit.payload["text"])]),
                author=hit.payload["author"],
                timestamp=hit.payload["timestamp"]
            )
            for hit in results
        ]

        return SearchMemoryResponse(memories=memories)
```

### Using Custom Memory Service

```python
from google.adk.runners import Runner

memory_service = QdrantMemoryService(
    qdrant_url="http://localhost:6333",
    collection_name="agent_memories",
    embedding_model=your_embedding_model
)

runner = Runner(
    agent=my_agent,
    app_name='my_app',
    session_service=session_service,
    memory_service=memory_service  # Your custom service!
)
```

## Complete Example

```python
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools.load_memory_tool import load_memory_tool
from google.adk.tools.preload_memory_tool import preload_memory_tool
from google.genai import types

# Create agent with memory tools
agent = Agent(
    name='memory_agent',
    model='gemini-2.0-flash-001',
    tools=[
        preload_memory_tool,  # Automatic context
        load_memory_tool,     # Manual search
    ],
    instruction="""
You are a helpful assistant with memory.
Past conversations are automatically provided in your context.
You can also call load_memory to search for specific information.
"""
)

# Create runner (uses InMemoryMemoryService by default)
runner = InMemoryRunner(agent=agent, app_name='my_app')

# Session 1: Create some memories
session_1 = await runner.session_service.create_session(
    app_name='my_app',
    user_id='user1'
)

async for event in runner.run_async(
    user_id='user1',
    session_id=session_1.id,
    new_message=types.Content(
        role='user',
        parts=[types.Part.from_text("My name is Jack and I love pizza")]
    )
):
    print(event.content)

# Save to memory
await runner.memory_service.add_session_to_memory(session_1)

# Session 2: Use memory
session_2 = await runner.session_service.create_session(
    app_name='my_app',
    user_id='user1'
)

async for event in runner.run_async(
    user_id='user1',
    session_id=session_2.id,
    new_message=types.Content(
        role='user',
        parts=[types.Part.from_text("What's my name and favorite food?")]
    )
):
    # Agent will use preloaded memory to answer
    # Or call load_memory if needed
    print(event.content)
```

## Related Files

- `sessions/` - Session management
- `runners.py` - Runner initialization
- `tools/` - Tool implementations
