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

"""SeleniumBase browser implementation adapter."""

from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from typing_extensions import override

from ..base_browser import BaseBrowser
from ..base_browser import BrowserState
from .browser import Browser
from .browser import BrowserOptions


class SeleniumBaseBrowser(BaseBrowser):
  """SeleniumBase implementation adapter.

  This class wraps the existing Browser class to conform to the BaseBrowser
  interface, allowing it to be used with ADK's tool system.
  """

  def __init__(self, options: Optional[BrowserOptions] = None):
    """Initialize SeleniumBase browser adapter.

    Args:
      options: Browser configuration options.
    """
    self._browser = Browser(options)

  @override
  async def initialize(self) -> None:
    """Initialize the browser.

    This method starts the browser instance and prepares it for automation.
    """
    await self._browser.start()

  @override
  async def close(self) -> None:
    """Close the browser and cleanup resources.

    This method stops the browser instance and releases all resources.
    """
    await self._browser.stop()

  @override
  def navigate_to(self, url: str) -> bool:
    """Navigate to a URL.

    Args:
      url: The URL to navigate to.

    Returns:
      True if navigation was successful, False otherwise.
    """
    return self._browser.navigate_to(url)

  @override
  def click_element(self, selector: str) -> bool:
    """Click an element by CSS selector or XPath.

    The element is automatically scrolled into view before clicking.

    Args:
      selector: CSS selector or XPath to identify the element.

    Returns:
      True if click was successful, False otherwise.
    """
    return self._browser.click_element(selector)

  @override
  def type_text(
      self, selector: str, text: str, clear_first: bool = True
  ) -> bool:
    """Type text into an element.

    Args:
      selector: CSS selector or XPath to identify the element.
      text: The text to type.
      clear_first: Whether to clear existing text before typing.

    Returns:
      True if typing was successful, False otherwise.
    """
    return self._browser.type_text(selector, text, clear_first)

  @override
  def press_keys(
      self, selector: Optional[str], keys: Union[str, List[str]]
  ) -> bool:
    """Send keyboard input to an element or the active element.

    Args:
      selector: CSS selector or XPath. If None, sends to active element.
      keys: A string or list of strings (e.g., "ArrowDown", "Enter").

    Returns:
      True if key press was successful, False otherwise.
    """
    return self._browser.press_keys(selector, keys)

  @override
  def scroll_to_element(self, selector: str) -> bool:
    """Scroll to an element to bring it into view.

    Args:
      selector: CSS selector or XPath to identify the element.

    Returns:
      True if scroll was successful, False otherwise.
    """
    return self._browser.scroll_to_element(selector)

  @override
  def generate_page_map(
      self,
      max_text_length: int = 500,
      map_type: str = "lean",
      include_api_data: bool = True,
  ) -> Tuple[List[Any], str, str, str]:
    """Generate a map of all elements on the current page.

    This method analyzes the page structure and returns both interactive
    and content elements, along with formatted strings for LLM consumption.

    Args:
      max_text_length: Maximum length for text content in elements.
      map_type: "rich" for full CSS selectors, "lean" for ref-based format.
      include_api_data: Whether to capture and include network API requests.

    Returns:
      A tuple containing:
        - List of all PageElement objects (interactive + content)
        - Formatted string for interactive elements (for LLM)
        - Formatted string for content elements (for LLM)
        - Formatted string for API requests (for LLM)
    """
    return self._browser.generate_page_map(
        max_text_length=max_text_length,
        map_type=map_type,
        include_api_data=include_api_data,
    )

  @override
  def get_current_state(self) -> BrowserState:
    """Get the current state of the browser.

    Returns:
      BrowserState object containing current URL, title, and screenshot path.
    """
    return BrowserState(
        screenshot_path=self._browser.get_latest_screenshot_path(),
        url=self._browser.get_current_url(),
        title=self._browser.get_page_title(),
    )

  @override
  def get_current_url(self) -> Optional[str]:
    """Get the current URL.

    Returns:
      Current URL or None if browser not initialized.
    """
    return self._browser.get_current_url()

  @override
  def get_page_title(self) -> Optional[str]:
    """Get the current page title.

    Returns:
      Page title or None if browser not initialized.
    """
    return self._browser.get_page_title()

  def get_browser(self) -> Browser:
    """Get the underlying Browser instance.

    This allows access to advanced features not exposed in the base interface.

    Returns:
      The underlying Browser instance.
    """
    return self._browser
