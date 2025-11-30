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

from __future__ import annotations

import abc
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import pydantic

from ...utils.feature_decorator import experimental


@experimental
class BrowserState(pydantic.BaseModel):
  """Represents the current state of the browser.

  Attributes:
    screenshot_path: Path to the screenshot file in PNG format.
    url: The current URL of the webpage being displayed.
    title: The current page title.
    page_map_data: Optional page element map data for context.
  """

  screenshot_path: Optional[str] = pydantic.Field(
      default=None, description="Path to screenshot in PNG format"
  )
  url: Optional[str] = pydantic.Field(
      default=None, description="Current webpage URL"
  )
  title: Optional[str] = pydantic.Field(
      default=None, description="Current page title"
  )
  page_map_data: Optional[Dict[str, Any]] = pydantic.Field(
      default=None, description="Page element map data"
  )


@experimental
class BaseBrowser(abc.ABC):
  """Abstract base class for browser implementations.

  This abstract base class defines the standard interface for controlling
  web browsers for AI agent automation.
  """

  @abc.abstractmethod
  async def initialize(self) -> None:
    """Initialize the browser.

    This method should be called before any other browser operations.
    It sets up the browser instance and prepares it for automation.
    """
    pass

  @abc.abstractmethod
  async def close(self) -> None:
    """Close the browser and cleanup resources.

    This method should be called when browser automation is complete.
    It ensures proper cleanup of browser processes and resources.
    """
    pass

  @abc.abstractmethod
  def navigate_to(self, url: str) -> bool:
    """Navigate to a URL.

    Args:
      url: The URL to navigate to.

    Returns:
      True if navigation was successful, False otherwise.
    """

  @abc.abstractmethod
  def click_element(self, selector: str) -> bool:
    """Click an element by CSS selector or XPath.

    The element is automatically scrolled into view before clicking.

    Args:
      selector: CSS selector or XPath to identify the element.

    Returns:
      True if click was successful, False otherwise.
    """

  @abc.abstractmethod
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

  @abc.abstractmethod
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

  @abc.abstractmethod
  def scroll_to_element(self, selector: str) -> bool:
    """Scroll to an element to bring it into view.

    Args:
      selector: CSS selector or XPath to identify the element.

    Returns:
      True if scroll was successful, False otherwise.
    """

  @abc.abstractmethod
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

  @abc.abstractmethod
  def get_current_state(self) -> BrowserState:
    """Get the current state of the browser.

    Returns:
      BrowserState object containing current URL, title, and screenshot path.
    """

  @abc.abstractmethod
  def get_current_url(self) -> Optional[str]:
    """Get the current URL.

    Returns:
      Current URL or None if browser not initialized.
    """

  @abc.abstractmethod
  def get_page_title(self) -> Optional[str]:
    """Get the current page title.

    Returns:
      Page title or None if browser not initialized.
    """
