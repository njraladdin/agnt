# Artifacts

Artifacts are a powerful feature in ADK that allow you to store and manage files (text, images, documents, etc.) associated with user sessions or users. They provide a way to persist data outside of conversation history, enabling efficient context management and data sharing.

## What Are Artifacts?

Artifacts are versioned files stored by the ADK framework that can be:

- **Session-scoped**: Available only within a specific conversation session
- **User-scoped**: Available across all sessions for a particular user
- **Versioned**: Each save creates a new version, allowing you to track changes over time
- **Metadata-enriched**: Can include custom metadata for additional context

Think of artifacts as a file storage system integrated into your agent, where files are automatically organized by app, user, and session.

## Why Use Artifacts?

### 1. **Context Window Management**

Large files (reports, documents, images) consume valuable LLM context space. By storing them as artifacts and loading them only when needed, you can:

- Keep conversation history lean
- Reduce token costs
- Maintain longer conversation histories
- Load data on-demand rather than keeping it in every turn

### 2. **Data Persistence**

Artifacts persist beyond individual messages:

- Save user uploads for later use
- Store generated reports or analysis results
- Share data across multiple conversation turns
- Maintain user-scoped data across sessions

### 3. **Efficient Data Handling**

- Version tracking for all changes
- Automatic organization by user and session
- Support for both text and binary data
- Custom metadata for searchability

## Storage Scopes

### Session-Scoped Artifacts

Default behavior. Artifacts are tied to a specific conversation session:

```python
# Saved to current session only
await tool_context.save_artifact('report.txt', types.Part.from_text('...'))
```

**Storage path**: `root/users/{user_id}/sessions/{session_id}/artifacts/{filename}/versions/{version}/`

### User-Scoped Artifacts

Available across all sessions for a user. Prefix the filename with `user:`:

```python
# Available across all sessions for this user
await tool_context.save_artifact('user:preferences.json', types.Part.from_text('...'))
```

**Storage path**: `root/users/{user_id}/artifacts/{filename}/versions/{version}/`

## Core API

### Saving Artifacts

Save artifacts from within tools using `ToolContext`:

```python
from google.adk.tools.tool_context import ToolContext
from google.genai import types

async def my_tool(tool_context: ToolContext, data: str):
    # Save text artifact
    artifact_part = types.Part.from_text(text=data)
    version = await tool_context.save_artifact(
        filename='output.txt',
        artifact=artifact_part,
        custom_metadata={'summary': 'Generated report', 'tags': ['important']}
    )
    return {'message': f'Saved as version {version}'}
```

**For binary data** (images, PDFs, etc.):

```python
# Save binary artifact
binary_data = b'...'  # Your binary data
artifact_part = types.Part(
    inline_data=types.Blob(
        mime_type='image/png',
        data=binary_data
    )
)
version = await tool_context.save_artifact('screenshot.png', artifact_part)
```

### Loading Artifacts

```python
# Load latest version
artifact = await tool_context.load_artifact('report.txt')

# Load specific version
artifact = await tool_context.load_artifact('report.txt', version=2)

# Load user-scoped artifact
artifact = await tool_context.load_artifact('user:preferences.json')
```

### Listing Artifacts

```python
# List all available artifacts (both session and user-scoped)
artifact_names = await tool_context.list_artifacts()
# Returns: ['report.txt', 'user:preferences.json', ...]
```

### Getting Artifact Metadata

```python
# Get version info with metadata
version_info = await tool_context.get_artifact_version('report.txt')
if version_info:
    print(f"Version: {version_info.version}")
    print(f"Created: {version_info.create_time}")
    print(f"Metadata: {version_info.custom_metadata}")
    print(f"URI: {version_info.canonical_uri}")
```

## Built-in Tools

### LoadArtifactsTool

ADK provides a built-in tool that allows the LLM to load artifacts on-demand:

```python
from google.adk import Agent
from google.adk.tools.load_artifacts_tool import load_artifacts_tool

agent = Agent(
    model='gemini-2.0-flash',
    name='my_agent',
    tools=[load_artifacts_tool],  # Add the built-in tool
)
```

**How it works:**

1. The tool automatically injects instructions about available artifacts into the LLM context
2. When the LLM needs artifact content, it calls `load_artifacts(artifact_names=['file.txt'])`
3. The tool temporarily injects the artifact content into the LLM request
4. The content is NOT saved to session history (context offloading)

### SaveFilesAsArtifactsPlugin

Automatically saves user-uploaded files as artifacts:

```python
from google.adk import Agent
from google.adk.plugins.save_files_as_artifacts_plugin import SaveFilesAsArtifactsPlugin

agent = Agent(
    model='gemini-2.0-flash',
    name='my_agent',
    plugins=[SaveFilesAsArtifactsPlugin()],
)
```

**How it works:**

1. User uploads a file through the web UI
2. Plugin intercepts the file in the user message
3. Saves it as an artifact using the file's `display_name`
4. Replaces the file in the message with a placeholder: `[Uploaded Artifact: "filename.pdf"]`
5. For model-accessible URIs (GCS, HTTPS), also adds a file reference

**User-scoped uploads**: Prefix the filename with `user:` when uploading to make it available across sessions.

## Common Patterns

### Pattern 1: Save and Immediate Load

Generate data, save as artifact, but immediately inject it into context for the current turn:

```python
from google.adk.tools.function_tool import FunctionTool
from google.adk.models.llm_request import LlmRequest

class GenerateReportTool(FunctionTool):
    async def process_llm_request(self, *, tool_context, llm_request: LlmRequest):
        await super().process_llm_request(tool_context=tool_context, llm_request=llm_request)

        # Check if our tool was just called
        if llm_request.contents and llm_request.contents[-1].parts:
            func_response = llm_request.contents[-1].parts[0].function_response
            if func_response and func_response.name == 'generate_report':
                artifact_name = func_response.response.get('artifact_name')
                if artifact_name:
                    # Load and inject the artifact content immediately
                    artifact = await tool_context.load_artifact(artifact_name)
                    if artifact:
                        llm_request.contents.append(
                            types.Content(
                                role='user',
                                parts=[
                                    types.Part.from_text(f'Report {artifact_name}:'),
                                    artifact,
                                ]
                            )
                        )
```

**Use case**: Large data generation where you want the LLM to process it immediately, but don't want it cluttering future turns.

### Pattern 2: Context Offloading with Metadata

Save large data with descriptive metadata, allowing the LLM to know what's available without loading full content:

```python
# Save with rich metadata
await tool_context.save_artifact(
    'sales_report_q3.txt',
    types.Part.from_text(large_report_content),
    custom_metadata={
        'summary': 'Sales report for Q3 2025 - APAC region',
        'region': 'APAC',
        'quarter': 'Q3',
        'year': 2025
    }
)

# Custom load tool that shows summaries
class CustomLoadArtifactsTool(LoadArtifactsTool):
    async def _append_artifacts_to_llm_request(self, *, tool_context, llm_request):
        artifact_names = await tool_context.list_artifacts()
        summaries = []

        for name in artifact_names:
            version_info = await tool_context.get_artifact_version(name)
            if version_info and version_info.custom_metadata:
                summary = version_info.custom_metadata.get('summary', name)
                summaries.append(f'{name}: {summary}')

        # Tell LLM what's available
        llm_request.append_instructions([
            f"Available artifacts: {summaries}. "
            "Call load_artifacts when you need the full content."
        ])

        # ... rest of loading logic
```

**Use case**: Large datasets where the LLM needs to know what's available but should only load specific items on demand.

### Pattern 3: User Preferences Storage

Store user preferences across sessions:

```python
async def save_preferences(tool_context: ToolContext, preferences: dict):
    """Save user preferences across all sessions."""
    prefs_json = json.dumps(preferences)
    await tool_context.save_artifact(
        'user:preferences.json',  # user: prefix for cross-session access
        types.Part.from_text(prefs_json),
        custom_metadata={'last_updated': datetime.now().isoformat()}
    )
    return {'status': 'Preferences saved'}

async def load_preferences(tool_context: ToolContext) -> dict:
    """Load user preferences."""
    artifact = await tool_context.load_artifact('user:preferences.json')
    if artifact and artifact.text:
        return json.loads(artifact.text)
    return {}
```

### Pattern 4: File Upload Handling

Combine the plugin with custom processing:

```python
from google.adk.plugins.save_files_as_artifacts_plugin import SaveFilesAsArtifactsPlugin

# Add plugin to save uploads
agent = Agent(
    model='gemini-2.0-flash',
    plugins=[SaveFilesAsArtifactsPlugin()],
    tools=[process_document, load_artifacts_tool]
)

# Tool to process uploaded documents
async def process_document(tool_context: ToolContext, filename: str):
    """Process an uploaded document."""
    # Load the artifact that was saved by the plugin
    artifact = await tool_context.load_artifact(filename)

    if artifact and artifact.text:
        # Process text document
        word_count = len(artifact.text.split())
        return {'word_count': word_count, 'filename': filename}
    elif artifact and artifact.inline_data:
        # Process binary document
        size_kb = len(artifact.inline_data.data) / 1024
        return {'size_kb': size_kb, 'filename': filename}

    return {'error': 'Document not found'}
```

## Artifact Services

ADK provides multiple artifact service implementations:

### FileArtifactService (Default)

Stores artifacts on the local filesystem:

```python
from google.adk.artifacts.file_artifact_service import FileArtifactService

artifact_service = FileArtifactService(root_dir='./artifacts')
```

**Storage structure:**

```
artifacts/
└── users/
    └── {user_id}/
        ├── sessions/
        │   └── {session_id}/
        │       └── artifacts/
        │           └── {filename}/
        │               └── versions/
        │                   └── {version}/
        │                       ├── {filename}
        │                       └── metadata.json
        └── artifacts/  # user-scoped
            └── {filename}/...
```

### InMemoryArtifactService

For testing or temporary storage:

```python
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService

artifact_service = InMemoryArtifactService()
```

### GcsArtifactService

For cloud storage (Google Cloud Storage):

```python
from google.adk.artifacts.gcs_artifact_service import GcsArtifactService

artifact_service = GcsArtifactService(bucket_name='my-artifacts-bucket')
```

## Advanced: Custom Artifact URIs

Artifacts have canonical URIs that follow this format:

**Session-scoped:**

```
artifact://apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts/{filename}/versions/{version}
```

**User-scoped:**

```
artifact://apps/{app_name}/users/{user_id}/artifacts/{filename}/versions/{version}
```

You can parse and construct these URIs using utility functions:

```python
from google.adk.artifacts.artifact_util import parse_artifact_uri, get_artifact_uri

# Parse URI
parsed = parse_artifact_uri('artifact://apps/myapp/users/user123/artifacts/file.txt/versions/0')
print(parsed.app_name, parsed.user_id, parsed.filename, parsed.version)

# Construct URI
uri = get_artifact_uri(
    app_name='myapp',
    user_id='user123',
    filename='file.txt',
    version=0,
    session_id='session456'  # Optional
)
```

## Best Practices

1. **Use descriptive filenames**: Make it easy to identify artifacts

   ```python
   # Good
   'sales_report_apac_q3_2025.txt'

   # Bad
   'report.txt'
   ```

2. **Add meaningful metadata**: Help the LLM understand what's stored

   ```python
   custom_metadata={
       'summary': 'Q3 sales data for APAC region',
       'type': 'report',
       'region': 'APAC',
       'quarter': 'Q3'
   }
   ```

3. **Choose the right scope**:

   - Session-scoped: Temporary data, conversation-specific files
   - User-scoped: Preferences, persistent user data, shared resources

4. **Use context offloading**: Don't load artifacts into every turn

   - Save large data as artifacts
   - Load only when the LLM explicitly needs it
   - Use metadata to provide summaries

5. **Version awareness**: Remember that each save creates a new version

   ```python
   # Load latest
   artifact = await tool_context.load_artifact('file.txt')

   # Load specific version if needed
   artifact = await tool_context.load_artifact('file.txt', version=2)
   ```

6. **Handle missing artifacts gracefully**:
   ```python
   artifact = await tool_context.load_artifact('file.txt')
   if artifact is None:
       return {'error': 'File not found'}
   ```

## Examples

See the following sample projects for complete examples:

- **[artifact_save_text](file:///c:/Users/Mega-PC/Desktop/projects/agnt/contributing/samples/artifact_save_text)**: Basic artifact saving from a tool
- **[context_offloading_with_artifact](file:///c:/Users/Mega-PC/Desktop/projects/agnt/contributing/samples/context_offloading_with_artifact)**: Advanced pattern with context offloading and custom metadata

## API Reference

### ToolContext Methods

```python
async def save_artifact(
    filename: str,
    artifact: types.Part,
    custom_metadata: Optional[dict[str, Any]] = None
) -> int
```

Saves an artifact and returns the version number.

```python
async def load_artifact(
    filename: str,
    version: Optional[int] = None
) -> Optional[types.Part]
```

Loads an artifact. Returns `None` if not found.

```python
async def list_artifacts() -> list[str]
```

Lists all artifact filenames available in the current session (includes both session and user-scoped).

```python
async def get_artifact_version(
    filename: str,
    version: Optional[int] = None
) -> Optional[ArtifactVersion]
```

Gets metadata for an artifact version.

### ArtifactVersion Model

```python
class ArtifactVersion:
    version: int                      # Version number
    canonical_uri: str                # Artifact URI
    custom_metadata: dict[str, Any]   # User-defined metadata
    create_time: float                # Unix timestamp
    mime_type: Optional[str]          # MIME type for binary data
```
