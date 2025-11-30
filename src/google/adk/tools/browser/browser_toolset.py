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

"""Browser toolset for ADK agent integration."""

from __future__ import annotations

from typing import List
from typing import Optional

from typing_extensions import override

from ...agents.readonly_context import ReadonlyContext
from ..base_toolset import BaseToolset
from .base_browser import BaseBrowser
from .browser_tool import BrowserTool


class BrowserToolset(BaseToolset):
  """Toolset for browser automation using SeleniumBase.

  This toolset provides a collection of browser control tools for agents,
  including navigation, element interaction, and page analysis capabilities.
  """

  def __init__(
      self,
      browser: BaseBrowser,
      *,
      enable_page_map: bool = True,
      enable_network_capture: bool = True,
      **kwargs,
  ):
    """Initialize BrowserToolset.

    Args:
      browser: Browser implementation (e.g., SeleniumBaseBrowser).
      enable_page_map: Enable page element mapping tool.
      enable_network_capture: Enable network request capture in page map.
      **kwargs: Additional arguments to pass to BaseToolset.
    """
    super().__init__(**kwargs)
    self._browser = browser
    self._enable_page_map = enable_page_map
    self._enable_network_capture = enable_network_capture

  @override
  async def get_tools(
      self,
      readonly_context: Optional[ReadonlyContext] = None,
  ) -> List[BrowserTool]:
    """Get list of browser tools.

    Args:
      readonly_context: Context for filtering tools (not used currently).

    Returns:
      List of BrowserTool instances for agent use.
    """
    tools = [
        BrowserTool(self._browser.navigate_to),
        BrowserTool(self._browser.click_element),
        BrowserTool(self._browser.type_text),
        BrowserTool(self._browser.press_keys),
        BrowserTool(self._browser.scroll_to_element),
    ]

    if self._enable_page_map:
      # Page map tool doesn't need screenshot since it generates its own
      tools.append(
          BrowserTool(
              self._browser.generate_page_map, include_screenshot=False
          )
      )

    return tools

  @override
  async def close(self) -> None:
    """Close the browser and cleanup resources.

    This method is called when the toolset is no longer needed,
    ensuring proper cleanup of browser resources.
    """
    await self._browser.close()
