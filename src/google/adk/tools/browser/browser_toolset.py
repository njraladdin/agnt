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

import asyncio
import logging
from typing import Dict
from typing import List
from typing import Optional

from typing_extensions import override

from ...agents.readonly_context import ReadonlyContext
from ..base_toolset import BaseToolset
from .base_browser import BaseBrowser
from .browser_tool import BrowserTool

logger = logging.getLogger('google_adk.' + __name__)


class BrowserToolset(BaseToolset):
  """Session-aware browser toolset for ADK agents.

  This toolset automatically manages browser instances based on context:
  - With session context (API): Creates unique browser per session
  - Without session context (CLI): Creates single shared browser

  This architecture ensures proper isolation for multi-user deployments
  while still working seamlessly for local development.

  Example (Recommended - Session-aware):
    ```python
    from google.adk.agents import Agent
    from google.adk.tools.browser import BrowserToolset
    from google.adk.tools.browser import (
        BrowserOptions,
        BrowserConfig
    )

    agent = Agent(
        model='gemini-2.5-flash',
        name='browser_agent',
        tools=[
            BrowserToolset(
                browser_options=BrowserOptions(
                    browser=BrowserConfig(
                        headless=True,
                        undetectable=True,
                    )
                )
            )
        ],
    )
    ```

  Example (Backward Compatible - Shared browser):
    ```python
    browser = SeleniumBaseBrowser(options=...)
    await browser.initialize()

    agent = Agent(
        tools=[BrowserToolset(browser=browser)]
    )
    ```

  Attributes:
    _shared_browser: Optional browser instance for backward compatibility.
    _browser_options: Configuration for creating browser instances.
    _session_browsers: Dictionary mapping session IDs to browser instances.
    _fallback_browser: Single browser instance for CLI use.
  """

  def __init__(
      self,
      browser: Optional[BaseBrowser] = None,
      *,
      browser_options: Optional['BrowserOptions'] = None,
      enable_network_capture: bool = True,
      auto_generate_page_map: bool = True,
      inject_page_map_in_prompt: bool = True,
      page_map_mode: str = 'lean',
      **kwargs,
  ):
    """Initialize BrowserToolset.

    Args:
      browser: Optional browser instance for backward compatibility or
        explicit control. If provided, this browser will be shared across
        all sessions (not recommended for multi-user deployments).
      browser_options: Configuration for creating browser instances. This is
        the recommended approach as it enables session-scoped browsers.
      enable_network_capture: Enable network request capture in page map.
      auto_generate_page_map: Auto-generate page map after browser actions.
      inject_page_map_in_prompt: Inject page map into system instructions.
      page_map_mode: 'lean' (default) or 'rich' format for page maps.
      **kwargs: Additional arguments to pass to BaseToolset.
    """
    super().__init__(**kwargs)
    self._shared_browser = browser
    self._browser_options = browser_options
    self._session_browsers: Dict[str, BaseBrowser] = {}
    self._fallback_browser: Optional[BaseBrowser] = None
    self._enable_network_capture = enable_network_capture
    self._auto_generate_page_map = auto_generate_page_map
    self._inject_page_map_in_prompt = inject_page_map_in_prompt
    self._page_map_mode = page_map_mode

  async def _get_session_browser(self, session_id: str) -> BaseBrowser:
    """Get or create browser for a specific session.

    Args:
      session_id: The session ID to get/create browser for.

    Returns:
      Browser instance for this session.

    Raises:
      ValueError: If no browser_options provided for session-scoped use.
    """
    if session_id not in self._session_browsers:
      if not self._browser_options:
        raise ValueError(
            'BrowserToolset requires browser_options to create '
            'session-scoped browsers. Please provide browser_options '
            'in the constructor.'
        )

      logger.info('Creating new browser instance for session: %s', session_id)
      from .seleniumbase_browser import SeleniumBaseBrowser

      browser = SeleniumBaseBrowser(options=self._browser_options)
      await browser.initialize()
      self._session_browsers[session_id] = browser
    else:
      logger.debug('Reusing existing browser for session: %s', session_id)

    return self._session_browsers[session_id]

  async def _get_fallback_browser(self) -> BaseBrowser:
    """Get or create fallback browser for CLI use.

    Returns:
      Fallback browser instance.

    Raises:
      ValueError: If no browser_options provided.
    """
    if not self._fallback_browser:
      if not self._browser_options:
        raise ValueError(
            'BrowserToolset requires browser_options to create browsers. '
            'Please provide either browser or browser_options in the '
            'constructor.'
        )

      logger.info('Creating fallback browser for CLI use')
      from .seleniumbase_browser import SeleniumBaseBrowser

      browser = SeleniumBaseBrowser(options=self._browser_options)
      await browser.initialize()
      self._fallback_browser = browser

    return self._fallback_browser

  def _create_tools(self, browser: BaseBrowser) -> List[BrowserTool]:
    """Create browser tools for the given browser instance.

    Args:
      browser: Browser instance to create tools for.

    Returns:
      List of BrowserTool instances.
    """
    tools = [
        BrowserTool(browser.navigate_to),
        BrowserTool(browser.click_element),
        BrowserTool(browser.type_text),
        BrowserTool(browser.press_keys),
        BrowserTool(browser.scroll_to_element),
        BrowserTool(browser.wait_for_element),
        BrowserTool(browser.check_element_exists),
        BrowserTool(browser.wait_for_element_to_change),
    ]

    # Note: generate_page_map is now an internal utility only,
    # automatically called after each browser action.
    # It is not exposed as a tool to the agent.

    return tools

  @override
  async def get_tools(
      self,
      readonly_context: Optional[ReadonlyContext] = None,
  ) -> List[BrowserTool]:
    """Get browser tools with appropriate browser instance.

    This method automatically determines which browser to use:
    - If session context exists: Use/create session-scoped browser
    - If shared browser provided: Use shared browser (backward compat)
    - Otherwise: Use/create fallback browser for CLI

    Args:
      readonly_context: Optional context containing session information.

    Returns:
      List of BrowserTool instances for agent use.
    """
    # Determine which browser to use based on context
    if readonly_context and readonly_context.session:
      # Session-scoped browser for API deployments
      browser = await self._get_session_browser(readonly_context.session.id)
    elif self._shared_browser:
      # Shared browser for backward compatibility
      browser = self._shared_browser
    else:
      # Fallback browser for CLI use
      browser = await self._get_fallback_browser()

    return self._create_tools(browser)

  @override
  async def process_llm_request(
      self, *, tool_context, llm_request
  ) -> None:
    """Generate page map and inject into system instructions before LLM request.

    This method automatically generates a fresh page map if a browser is open,
    then formats it into the system instructions. This ensures the agent always
    has the most up-to-date view of the page before making decisions.

    Args:
      tool_context: The context of the tool.
      llm_request: The outgoing LLM request.
    """
    if not self._inject_page_map_in_prompt:
      return

    # Get the appropriate browser for this session
    browser = None
    if tool_context.session:
      if tool_context.session.id in self._session_browsers:
        browser = self._session_browsers[tool_context.session.id]
      elif self._shared_browser:
        browser = self._shared_browser
      elif self._fallback_browser:
        browser = self._fallback_browser
    elif self._shared_browser:
      browser = self._shared_browser
    elif self._fallback_browser:
      browser = self._fallback_browser

    # No browser open, nothing to inject
    if not browser:
      return

    # Generate fresh page map if auto-generation is enabled
    if self._auto_generate_page_map:
      try:
        page_map_data = browser.generate_page_map(map_type=self._page_map_mode)
        url = browser.get_current_url()
        title = browser.get_page_title()
        logger.debug('Auto-generated page map before LLM request')
      except Exception as e:
        logger.warning(f'Failed to auto-generate page map: {e}')
        return
    else:
      # If auto-generation is disabled, try to use cached data
      page_map_data = tool_context.session.state.get('_browser_page_map')
      if not page_map_data:
        return
      url = tool_context.session.state.get('_browser_url')
      title = tool_context.session.state.get('_browser_title')

    # Unpack the tuple: (page_elements, interactive_string, content_string, api_string)
    page_elements, interactive_string, content_string, api_string = (
        page_map_data
    )

    # Format the page map for injection
    page_map_text = 'CURRENT PAGE CONTENT:\n'
    if page_elements and len(page_elements) > 0:
      page_map_text += f'Page title: "{title}"\n'
      page_map_text += f'URL: {url}\n\n'

      if interactive_string:
        page_map_text += 'INTERACTIVE ELEMENTS:\n'
        page_map_text += interactive_string + '\n\n'

      if content_string:
        page_map_text += 'CONTENT ELEMENTS:\n'
        page_map_text += content_string + '\n\n'

      if api_string:
        page_map_text += 'CAPTURED API REQUESTS:\n'
        page_map_text += api_string + '\n'
    else:
      page_map_text += 'No page content available yet.\n'

    # Inject into system instructions
    llm_request.append_instructions([page_map_text])

  async def close_session_browser(self, session_id: str) -> None:
    """Close browser for a specific session.

    This should be called when a session ends to properly cleanup browser
    resources. Typically called from the session deletion endpoint.

    Args:
      session_id: The session ID whose browser should be closed.
    """
    if session_id in self._session_browsers:
      logger.info('Closing browser for session: %s', session_id)
      browser = self._session_browsers.pop(session_id)
      try:
        await browser.close()
      except Exception as e:
        logger.warning(
            'Error closing browser for session %s: %s', session_id, e
        )

  @override
  async def close(self) -> None:
    """Close all browsers and cleanup resources.

    This method is called when the toolset is no longer needed,
    ensuring proper cleanup of all browser resources.
    """
    browsers_to_close = []

    # Collect all browsers to close
    if self._shared_browser:
      browsers_to_close.append(self._shared_browser)

    if self._fallback_browser:
      browsers_to_close.append(self._fallback_browser)

    browsers_to_close.extend(self._session_browsers.values())

    if browsers_to_close:
      logger.info('Closing %d browser instance(s)', len(browsers_to_close))

      # Close all browsers concurrently
      close_tasks = [browser.close() for browser in browsers_to_close]
      results = await asyncio.gather(*close_tasks, return_exceptions=True)

      # Log any errors
      for browser, result in zip(browsers_to_close, results):
        if isinstance(result, Exception):
          logger.warning('Error closing browser: %s', result)

    # Clear all references
    self._session_browsers.clear()
    self._fallback_browser = None

