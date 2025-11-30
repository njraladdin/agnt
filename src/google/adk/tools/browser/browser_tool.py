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

"""Browser tool wrapper for ADK integration."""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from typing_extensions import override

from ..function_tool import FunctionTool
from ..tool_context import ToolContext
from .base_browser import BrowserState

logger = logging.getLogger('google_adk.' + __name__)


class BrowserTool(FunctionTool):
  """Tool wrapper for browser functions.

  This class extends FunctionTool to provide special handling for browser
  operations, including automatic screenshot inclusion in responses.
  """

  def __init__(
      self,
      func,
      *,
      include_screenshot: bool = True,
      **kwargs,
  ):
    """Initialize BrowserTool.

    Args:
      func: Browser method to wrap.
      include_screenshot: Whether to include screenshot in response.
      **kwargs: Additional arguments to pass to FunctionTool.
    """
    super().__init__(func, **kwargs)
    self._include_screenshot = include_screenshot

  @override
  async def run_async(
      self, *, args: dict[str, Any], tool_context: ToolContext
  ) -> Any:
    """Run browser function and format response.

    This method executes the browser function and formats the response
    for LLM consumption, including screenshots when available.

    Args:
      args: Arguments for the browser function.
      tool_context: Context for the tool execution.

    Returns:
      Formatted response, potentially including screenshot data.
    """
    # Execute the browser function
    result = await super().run_async(args=args, tool_context=tool_context)

    # If result is BrowserState, format for LLM
    if isinstance(result, BrowserState):
      response = {
          'url': result.url,
          'title': result.title,
      }

      # Include screenshot if requested and available
      if self._include_screenshot and result.screenshot_path:
        try:
          screenshot_path = Path(result.screenshot_path)
          if screenshot_path.exists():
            with open(screenshot_path, 'rb') as f:
              screenshot_data = f.read()
            response['image'] = {
                'mimetype': 'image/png',
                'data': base64.b64encode(screenshot_data).decode('utf-8'),
            }
        except Exception as e:
          logger.warning(f'Failed to include screenshot: {e}')

      return response

    return result
