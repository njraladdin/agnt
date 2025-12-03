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
      browser=None,
      auto_generate_page_map: bool = False,
      page_map_mode: str = 'lean',
      **kwargs,
  ):
    """Initialize BrowserTool.

    Args:
      func: Browser method to wrap.
      include_screenshot: Whether to include screenshot in response.
      browser: Browser instance for auto-generating page maps.
      auto_generate_page_map: Whether to auto-generate page map after execution.
      page_map_mode: 'lean' or 'rich' format for page maps.
      **kwargs: Additional arguments to pass to FunctionTool.
    """
    super().__init__(func, **kwargs)
    self._include_screenshot = include_screenshot
    self._browser = browser
    self._auto_generate_page_map = auto_generate_page_map
    self._page_map_mode = page_map_mode

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

    # Auto-generate page map if enabled and browser is available
    if self._auto_generate_page_map and self._browser:
      # Only generate for actions that change page state
      action_triggers_map = [
          'navigate_to',
          'click_element',
          'press_keys',
      ]
      if self.name in action_triggers_map:
        try:
          # Generate page map (returns tuple)
          page_map_data = self._browser.generate_page_map(
              map_type=self._page_map_mode
          )
          # Store in session state
          tool_context.session.state['_browser_page_map'] = page_map_data
          tool_context.session.state['_browser_url'] = (
              self._browser.get_current_url()
          )
          tool_context.session.state['_browser_title'] = (
              self._browser.get_page_title()
          )
          logger.debug(
              f'Auto-generated page map after {self.name} (mode: {self._page_map_mode})'
          )
        except Exception as e:
          logger.warning(f'Failed to auto-generate page map: {e}')

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
