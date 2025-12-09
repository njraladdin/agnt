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

"""Standard result type for ADK tools.

This module provides a consistent return structure for all tools in the ADK
library, making it easier for LLMs to work with tool outputs.
"""

from typing import Any, Optional
from typing import TypedDict


class ToolResult(TypedDict, total=False):
  """Standard return type for ADK tool methods.
  
  This provides a consistent interface for LLMs to work with tools.
  All tool action methods should return this structure.
  
  Attributes:
    success: Whether the operation completed successfully.
    result: The result value (type depends on the specific tool).
    error: Error message if success is False, None otherwise.
  
  Example usage:
    ```python
    def my_tool_function(arg: str) -> ToolResult:
        try:
            result = do_something(arg)
            return success(result)
        except Exception as e:
            return error(str(e))
    ```
  """
  success: bool
  result: Any
  error: Optional[str]


def success(result: Any = True) -> ToolResult:
  """Create a successful ToolResult.
  
  Args:
    result: The result value to include. Defaults to True for boolean operations.
    
  Returns:
    A ToolResult dict with success=True.
  """
  return {'success': True, 'result': result, 'error': None}


def error(message: str) -> ToolResult:
  """Create a failed ToolResult.
  
  Args:
    message: Error message describing what went wrong.
    
  Returns:
    A ToolResult dict with success=False.
  """
  return {'success': False, 'result': None, 'error': message}
