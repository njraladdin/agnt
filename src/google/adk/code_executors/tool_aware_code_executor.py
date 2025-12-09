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

"""A code executor that can inject callable tools into the execution context."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import logging
from typing import Any, Callable, Dict, Optional

from pydantic import Field
from typing_extensions import override

from ..agents.invocation_context import InvocationContext
from .base_code_executor import BaseCodeExecutor
from .code_execution_utils import CodeExecutionInput, CodeExecutionResult

logger = logging.getLogger('google_adk.' + __name__)

# Type for tool provider: takes invocation context, returns dict of tools
ToolProvider = Callable[[Optional[InvocationContext]], Dict[str, Callable]]


class ToolAwareCodeExecutor(BaseCodeExecutor):
    """A code executor that injects callable tools into the execution context.

    This executor allows code to call agent tools (like browser methods,
    search functions, etc.) directly from within executed code blocks.
    This enables complex workflows like loops, conditionals, and multi-step
    operations that combine tool calls with Python logic.

    Example with static tools:
        ```python
        from google.adk.code_executors import ToolAwareCodeExecutor

        # Create executor with injected browser tools
        executor = ToolAwareCodeExecutor(
            injected_tools={
                'navigate_to': browser.navigate_to,
                'click_element': browser.click_element,
                'execute_js_script': browser.execute_js_script,
            }
        )
        ```

    Example with dynamic tool provider (for session-scoped tools):
        ```python
        def get_browser_tools(invocation_context):
            # Get session-specific browser
            session_id = invocation_context.session.id
            browser = browser_toolset.get_session_browser(session_id)
            if browser:
                return {
                    'navigate_to': browser.navigate_to,
                    'click_element': browser.click_element,
                    'execute_js_script': browser.execute_js_script,
                }
            return {}

        executor = ToolAwareCodeExecutor(tool_provider=get_browser_tools)
        ```

    The injected tools define the boundary of what code can do. Unlike
    UnsafeLocalCodeExecutor which has full local access, this executor
    only allows calling the explicitly injected functions.

    Note:
        This executor runs code in the current Python process. Ensure
        injected tools are safe for the agent to call.
    """

    injected_tools: Dict[str, Callable] = Field(default_factory=dict)
    """Static tools to inject into the execution context.
    
    These tools are always available. Use this for tools that don't
    depend on session context.
    """

    # Note: tool_provider is stored as a private attribute since Pydantic
    # doesn't handle arbitrary callables well as fields.
    _tool_provider: Optional[ToolProvider] = None
    """Dynamic tool provider function.
    
    If set, this function is called at execution time with the invocation
    context to get additional tools. Useful for session-scoped tools.
    """

    # Overrides the BaseCodeExecutor attribute: this executor cannot be stateful.
    stateful: bool = Field(default=False, frozen=True, exclude=True)

    # Overrides the BaseCodeExecutor attribute: this executor cannot
    # optimize_data_file.
    optimize_data_file: bool = Field(default=False, frozen=True, exclude=True)

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True

    def __init__(
        self,
        *,
        injected_tools: Optional[Dict[str, Callable]] = None,
        tool_provider: Optional[ToolProvider] = None,
        **data
    ):
        """Initialize the ToolAwareCodeExecutor.

        Args:
            injected_tools: Static dictionary mapping function names to callables.
            tool_provider: Optional function that returns tools dynamically based
                on invocation context. Signature: (InvocationContext) -> Dict[str, Callable]
            **data: Additional arguments passed to BaseCodeExecutor.

        Raises:
            ValueError: If stateful or optimize_data_file is set to True.
        """
        if 'stateful' in data and data['stateful']:
            raise ValueError(
                'Cannot set `stateful=True` in ToolAwareCodeExecutor.'
            )
        if 'optimize_data_file' in data and data['optimize_data_file']:
            raise ValueError(
                'Cannot set `optimize_data_file=True` in ToolAwareCodeExecutor.'
            )
        
        # Handle injected_tools
        if injected_tools is not None:
            data['injected_tools'] = injected_tools
        
        super().__init__(**data)
        
        # Store tool_provider as private attribute
        object.__setattr__(self, '_tool_provider', tool_provider)

    def _get_tools(self, invocation_context: Optional[InvocationContext]) -> Dict[str, Callable]:
        """Get all available tools for execution.
        
        Combines static injected_tools with dynamic tools from tool_provider.
        
        Args:
            invocation_context: The current invocation context.
            
        Returns:
            Dictionary of all available tools.
        """
        tools: Dict[str, Callable] = dict(self.injected_tools)
        
        # Add dynamic tools from provider if available
        if self._tool_provider is not None:
            try:
                dynamic_tools = self._tool_provider(invocation_context)
                if dynamic_tools:
                    tools.update(dynamic_tools)
                    logger.debug('Tool provider added %d tools', len(dynamic_tools))
            except Exception as e:
                logger.warning('Error getting tools from provider: %s', e)
        
        return tools

    @override
    def execute_code(
        self,
        invocation_context: InvocationContext,
        code_execution_input: CodeExecutionInput,
    ) -> CodeExecutionResult:
        """Execute code with injected tools available.

        Args:
            invocation_context: The invocation context of the code execution.
            code_execution_input: The code execution input containing the code.

        Returns:
            CodeExecutionResult with stdout, stderr, and any output files.
        """
        # Get all tools (static + dynamic)
        tools = self._get_tools(invocation_context)
        
        logger.debug(
            'Executing code with %d tools:\n```\n%s\n```',
            len(tools),
            code_execution_input.code
        )

        output = ''
        error = ''

        try:
            # Build globals with tools
            globals_: Dict[str, Any] = dict(tools)

            # Add common imports for convenience
            globals_['json'] = json

            # Capture stdout
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exec(code_execution_input.code, globals_, globals_)
            output = stdout.getvalue()

        except Exception as e:
            error = str(e)
            logger.error('Code execution error: %s', error)

        return CodeExecutionResult(
            stdout=output,
            stderr=error,
            output_files=[],
        )

