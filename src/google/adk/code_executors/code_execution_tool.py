# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A function tool that enables Python code execution with injected tools."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import logging
from typing import Any, Callable, Dict, Optional

from typing_extensions import override

from ..tools.base_toolset import BaseToolset
from ..tools.function_tool import FunctionTool
from ..tools.tool_context import ToolContext

logger = logging.getLogger('google_adk.' + __name__)


def execute_python_code(code: str) -> dict:
    """Execute Python code for multi-step workflows.
    
    PATTERN: Always define a function, log progress, then call it:
    
    ```python
    def scrape_all_pages():
        all_items = []
        
        for page_num in range(1, 6):
            print(f"[Page {page_num}] Extracting data...")
            
            data = execute_js_script(script="return ...")['result']
            all_items.extend(data)
            print(f"[Page {page_num}] Found {len(data)} items")
            
            if page_num < 5:
                print(f"[Page {page_num}] Clicking next...")
                click_element(selector='.next')
                wait_for_element_to_change(selector='.items')
        
        print(f"[Done] Total: {len(all_items)} items")
        return all_items
    
    result = scrape_all_pages()  # <-- Assign to result
    ```
    
    Guidelines:
    - Define a function for your logic
    - Use print() with [Step] prefixes for progress
    - Set `result = your_function()` at the end
    
    Returns:
        - 'success': bool - Execution succeeded
        - 'result': Any - The `result` variable (your function's return)
        - 'output': str - Print logs (truncated if large)
        - 'error': str|None - Error message if failed
    """
    # This is a placeholder - actual execution happens in run_async
    return {'success': False, 'result': None, 'output': '', 'error': 'Not implemented'}


# Tools to exclude from code execution (empty by default - all tools available)
DEFAULT_EXCLUDED_TOOLS = set()


class CodeExecutionTool(FunctionTool):
    """A tool that enables Python code execution with injected tools.
    
    This tool allows agents to execute Python code that has access to other
    tools. It's useful for complex workflows that require loops, conditionals,
    or multi-step operations - like paginated data extraction.
    
    The tool can be given:
    - A toolset: Tools are extracted from the toolset for the current session
    - Static tools: A dict of name -> callable
    - Both: Static tools are combined with toolset tools
    
    Example usage:
        ```python
        from google.adk.code_executors import CodeExecutionTool
        from google.adk.tools.browser import BrowserToolset
        
        browser_toolset = BrowserToolset(...)
        
        # Pass the toolset directly
        code_exec_tool = CodeExecutionTool(toolset=browser_toolset)
        
        agent = Agent(
            tools=[browser_toolset, code_exec_tool],
        )
        ```
    
    Note: By default, navigate_to is excluded from code execution to ensure
    the agent navigates first as a regular tool call and sees page context.
    """
    
    def __init__(
        self,
        *,
        toolset: Optional[BaseToolset] = None,
        tools: Optional[Dict[str, Callable]] = None,
        exclude_tools: Optional[set] = None,
    ):
        """Initialize CodeExecutionTool.
        
        Args:
            toolset: Optional toolset to extract tools from.
            tools: Optional static tools dict (name -> callable).
            exclude_tools: Tool names to exclude from code execution.
                Defaults to {'navigate_to'} to ensure navigation happens
                as regular tool calls with page context feedback.
        """
        # Initialize FunctionTool with the function (name is derived from func.__name__)
        super().__init__(execute_python_code)
        
        self._toolset = toolset
        self._static_tools = tools or {}
        self._exclude_tools = exclude_tools if exclude_tools is not None else DEFAULT_EXCLUDED_TOOLS
    
    async def _get_tools_from_toolset(
        self,
        tool_context: ToolContext
    ) -> Dict[str, Callable]:
        """Extract callable functions from the toolset."""
        if self._toolset is None:
            return {}
        
        tools_dict: Dict[str, Callable] = {}
        
        # Get readonly context from tool_context using its invocation_context
        readonly_context = None
        if hasattr(tool_context, '_invocation_context') and tool_context._invocation_context:
            from ..agents.readonly_context import ReadonlyContext
            readonly_context = ReadonlyContext(tool_context._invocation_context)
        
        # Get tools from the toolset
        try:
            toolset_tools = await self._toolset.get_tools(readonly_context)
            
            for tool in toolset_tools:
                # Skip excluded tools (e.g., navigate_to)
                if tool.name in self._exclude_tools:
                    continue
                # For FunctionTool-based tools, extract the underlying func
                if hasattr(tool, 'func'):
                    tools_dict[tool.name] = tool.func
        except Exception as e:
            logger.warning('Failed to get tools from toolset: %s', e)
        
        return tools_dict
    
    @override
    async def run_async(
        self, *, args: Dict[str, Any], tool_context: ToolContext
    ) -> Dict[str, Any]:
        """Execute the Python code with injected tools."""
        try:
            code = args.get('code', '')
            
            if not code:
                return {
                    'success': False,
                    'result': None,
                    'output': '',
                    'error': 'No code provided.',
                }
            
            # Combine static tools with toolset tools
            all_tools: Dict[str, Any] = dict(self._static_tools)
            
            # Get tools from toolset
            toolset_tools = await self._get_tools_from_toolset(tool_context)
            all_tools.update(toolset_tools)
            
            # Add common imports
            all_tools['json'] = json
            
            output = ''
            error = ''
            result = None
            
            try:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exec(code, all_tools, all_tools)
                output = stdout.getvalue()
                
                # Capture the result variable if set
                result = all_tools.get('result')
                
                # Truncate output if too large (keep first 2000 chars)
                if len(output) > 2000:
                    output = output[:2000] + f'\n... (truncated, {len(output)} total chars)'
                    
            except Exception as e:
                import traceback
                error = f'{e}\n{traceback.format_exc()}'
            
            # Build response
            response: Dict[str, Any] = {
                'success': not error,
                'result': result,
                'output': output,
                'error': error if error else None,
            }
            
            # Save code as artifact
            try:
                from google.genai import types
                code_artifact = types.Part.from_text(text=code)
                version = await tool_context.save_artifact(
                    filename='python_code',
                    artifact=code_artifact,
                )
                response['code_artifact'] = {'name': 'python_code', 'version': version}
            except Exception as e:
                logger.warning('Failed to save code artifact: %s', e)
            
            # Save result as artifact (if there's a result and no error)
            if result is not None and not error:
                try:
                    from google.genai import types
                    result_json = json.dumps(result, indent=2, default=str)
                    result_artifact = types.Part.from_text(text=result_json)
                    version = await tool_context.save_artifact(
                        filename='python_result',
                        artifact=result_artifact,
                    )
                    response['result_artifact'] = {'name': 'python_result', 'version': version}
                    
                    # Add summary for LLM (don't repeat huge data)
                    if isinstance(result, list) and len(result) > 3:
                        response['result_summary'] = {
                            'type': 'list',
                            'count': len(result),
                            'sample': result[:2],
                        }
                        # Don't include full result in response to save tokens
                        response['result'] = f'[{len(result)} items - see python_result artifact]'
                except Exception as e:
                    logger.warning('Failed to save result artifact: %s', e)
            
            return response
            
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'output': '',
                'error': f'Fatal error: {e}',
            }
