
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

"""SeleniumBase browser implementation for ADK."""

from __future__ import annotations

import logging
import os
import platform
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from pydantic import BaseModel
from seleniumbase import Driver
from typing_extensions import override

from .base_browser import BaseBrowser
from .base_browser import BrowserState
from .page_parser import PageElement
from .page_parser import PageParser

# Configure logging
logger = logging.getLogger('google_adk.' + __name__)


class BrowserConfig(BaseModel):
    """Browser configuration options"""
    headless: bool = False
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    window_size: str = "1920,1080"
    timeout: int = 30
    undetectable: bool = True
    incognito: bool = True


class ProxyConfig(BaseModel):
    """Proxy configuration options"""
    enabled: bool = False
    host: Optional[str] = None
    port: int = 9008
    username: Optional[str] = None
    password: Optional[str] = None


class BrowserOptions(BaseModel):
    """Browser initialization options"""
    browser: Optional[BrowserConfig] = None
    proxy: Optional[ProxyConfig] = None
    output_dir: Optional[str] = None
    start_fresh: bool = False


class SeleniumBaseBrowser(BaseBrowser):
    """
    SeleniumBaseBrowser class - Handles browser operations using SeleniumBase Driver
    General-purpose browser management that can be used by various tools
    """
    
    def __init__(self, options: Optional[BrowserOptions] = None):
        """
        Initialize Browser instance
        
        Args:
            options: Browser configuration options
        """
        if options is None:
            options = BrowserOptions()
            
        self.driver: Optional[Driver] = None
        self.parser: Optional[PageParser] = None
        
        # Configuration
        self.browser_config = options.browser or BrowserConfig()
        self.proxy_config = options.proxy or ProxyConfig()
        
        # Set up user data directory for Chrome profile
        self.user_data_dir = os.path.join(os.getcwd(), 'chrome-data')
        logger.info(f"Chrome profile data will be saved to: {self.user_data_dir}")
        
        # Create Chrome profile directory if it doesn't exist
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir, exist_ok=True)
            logger.info(f"Created Chrome profile directory at: {self.user_data_dir}")
        else:
            logger.info(f"Using existing Chrome profile directory at: {self.user_data_dir}")
        
        # Set up screenshots directory
        self.screenshots_dir = os.path.join(os.getcwd(), 'screenshots')
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir, exist_ok=True)
            logger.info(f"Created screenshots directory at: {self.screenshots_dir}")
        
        # Track latest screenshot
        self.latest_screenshot_path: Optional[str] = None
        # Track last clicked selector to help focus for subsequent key presses
        self.last_clicked_selector: Optional[str] = None

        # Network request interception tracking
        self.network_interception_enabled: bool = False
        self._captured_requests: List[Dict[str, Any]] = []

    def generate_page_map(self, max_text_length: int = 500, map_type: str = "lean", include_api_data: bool = True) -> tuple[List[PageElement], str, str, str]:
        """
        Generate a map of all elements on the current page, including API requests

        Args:
            max_text_length: Maximum length for text content
            map_type: "rich" for full CSS selectors, "lean" for ref-based format
            include_api_data: Whether to capture and include network API requests

        Returns:
            Tuple containing:
            - List of PageElement objects representing page elements
            - Formatted string for interactive elements (for LLM)
            - Formatted string for content elements (for LLM)
            - Formatted string for API requests (for LLM)
        """
        if not self.driver:
            raise Exception("Browser not initialized")

        if not self.parser:
            self.parser = PageParser(self.driver)

        # Use the updated PageParser API that returns all data in one call
        interactive_elements, interactive_map_string, content_elements, content_map_string = self.parser.get_page_maps(map_type=map_type)

        # Combine and sort by index for backward compatibility
        all_elements = interactive_elements + content_elements
        all_elements.sort(key=lambda x: x.index)

        # Capture API requests if requested
        api_map_string = ""
        if include_api_data:
            # Enable network interception if not already enabled
            if not self.network_interception_enabled:
                self.enable_network_interception()

            # Get network requests (filtering for API-like endpoints)
            network_requests = self.get_network_requests(filter_pattern=r'api|graphql|json|data|query|fetch')

            # Format API requests for LLM
            api_map_string = self._format_api_requests_for_llm(network_requests)

        # Automatically take a screenshot after generating page map
        self.take_auto_screenshot()

        return all_elements, interactive_map_string, content_map_string, api_map_string

    @override
    async def initialize(self) -> None:
        """Initialize the browser.
        
        This method sets up the browser instance and prepares it for automation.
        It's an alias for start() to satisfy the BaseBrowser interface.
        """
        await self.start()

    @override
    async def close(self) -> None:
        """Close the browser and cleanup resources.
        
        This method ensures proper cleanup of browser processes and resources.
        It's an alias for stop() to satisfy the BaseBrowser interface.
        """
        await self.stop()

    @override
    def get_current_state(self) -> BrowserState:
        """Get the current state of the browser.
        
        Returns:
            BrowserState object containing current URL, title, and screenshot path.
        """
        return BrowserState(
            url=self.get_current_url() or '',
            title=self.get_page_title() or '',
            screenshot_path=self.latest_screenshot_path
        )

    async def start(self) -> bool:
        """
        Start the browser
        
        Returns:
            True if successful, False otherwise
        """
        if self.driver:
            logger.info('Browser already running')
            return True

        try:
            logger.info('Launching browser with SeleniumBase...')
            
            # Set up SeleniumBase Driver options
            driver_kwargs = {
                'browser': 'chrome',
                'headless': self.browser_config.headless,
                'uc': self.browser_config.undetectable,
                'incognito': self.browser_config.incognito,
                'page_load_strategy': 'normal'
            }
            
            # Add proxy if configured
            if self.proxy_config.enabled and self.proxy_config.host:
                proxy_url = f"{self.proxy_config.host}:{self.proxy_config.port}"
                if self.proxy_config.username and self.proxy_config.password:
                    proxy_url = f"{self.proxy_config.username}:{self.proxy_config.password}@{proxy_url}"
                driver_kwargs['proxy'] = proxy_url
            
            # Create SeleniumBase Driver instance
            self.driver = Driver(**driver_kwargs)
            
            # Initialize the page parser
            self.parser = PageParser(self.driver)
            
            # Set user agent if different from default
            if self.browser_config.user_agent:
                self.driver.execute_script(f"Object.defineProperty(navigator, 'userAgent', {{get: () => '{self.browser_config.user_agent}'}});")
            
            # Navigate to about:blank as starting page
            self.driver.get('about:blank')
            
            logger.info('Browser started successfully')
            return True
            
        except Exception as error:
            logger.error(f'Error starting browser: {error}')
            return False

    async def stop(self) -> bool:
        """
        Stop the browser
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.driver:
                logger.info('Closing browser...')
                
                # Close browser
                self.driver.quit()
                self.driver = None
                self.parser = None
                
                logger.info('Browser closed successfully.')
                return True
            else:
                logger.info('No browser instance to close.')
                return False
                
        except Exception as error:
            logger.error(f'Error stopping browser: {error}')
            return False

    async def restart(self) -> bool:
        """
        Restart the browser - stop and start again
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info('Restarting browser...')
            
            # If browser is running, stop it first
            if self.driver:
                await self.stop()
            
            # Start the browser again
            await self.start()
            
            logger.info('Browser restarted. Navigate to websites in the browser window.')
            return True
            
        except Exception as error:
            logger.error(f'Error restarting browser: {error}')
            return False

    def get_driver(self) -> Optional[Driver]:
        """
        Get the SeleniumBase Driver instance
        
        Returns:
            SeleniumBase Driver instance or None
        """
        return self.driver

    def get_current_url(self) -> Optional[str]:
        """
        Get the current URL
        
        Returns:
            Current URL or None if browser not initialized
        """
        if not self.driver:
            return None
        return self.driver.get_current_url()

    def get_page_title(self) -> Optional[str]:
        """
        Get the current page title
        
        Returns:
            Page title or None if browser not initialized
        """
        if not self.driver:
            return None
        return self.driver.get_title()

    def navigate_to(self, url: str) -> bool:
        """
        Navigate to a URL
        
        Args:
            url: URL to navigate to
            
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            logger.error("Browser not initialized")
            return False
        
        try:
            # Use SeleniumBase's uc_open_with_reconnect for better compatibility
            self.driver.uc_open_with_reconnect(url)
            
            # Wait for page to settle
            #time.sleep(2)
            
            return True
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return False

    def wait_for_element(self, selector: str, timeout: int = 10) -> Optional[Any]:
        """
        Wait for an element to be present and visible
        
        Args:
            selector: CSS selector or XPath
            timeout: Maximum time to wait in seconds
            
        Returns:
            WebElement if found, None otherwise
        """
        if not self.driver:
            return None
        
        try:
            # Use SeleniumBase's built-in wait methods
            if selector.startswith('/') or selector.startswith('('):
                # XPath
                self.driver.wait_for_element(selector, by="xpath", timeout=timeout)
                return self.driver.find_element("xpath", selector)
            else:
                # CSS selector
                self.driver.wait_for_element(selector, timeout=timeout)
                return self.driver.find_element("css selector", selector)
            
        except Exception as e:
            logger.warning(f"Element not found: {selector}, Error: {e}")
            return None

    def find_element(self, selector: str) -> Optional[Any]:
        """
        Find an element by CSS selector or XPath
        
        Args:
            selector: CSS selector or XPath
            
        Returns:
            WebElement if found, None otherwise
        """
        if not self.driver:
            return None
        
        try:
            # Determine if selector is XPath or CSS
            if selector.startswith('/') or selector.startswith('('):
                # XPath
                element = self.driver.find_element("xpath", selector)
            else:
                # CSS selector
                element = self.driver.find_element("css selector", selector)
            
            return element
            
        except Exception as e:
            logger.warning(f"Element not found: {selector}, Error: {e}")
            return None

    def find_elements(self, selector: str) -> List[Any]:
        """
        Find multiple elements by CSS selector or XPath
        
        Args:
            selector: CSS selector or XPath
            
        Returns:
            List of WebElements
        """
        if not self.driver:
            return []
        
        try:
            # Determine if selector is XPath or CSS
            if selector.startswith('/') or selector.startswith('('):
                # XPath
                elements = self.driver.find_elements("xpath", selector)
            else:
                # CSS selector
                elements = self.driver.find_elements("css selector", selector)
            
            return elements
            
        except Exception as e:
            logger.warning(f"Elements not found: {selector}, Error: {e}")
            return []

    def execute_script(self, script: str, *args) -> Any:
        """
        Execute JavaScript in the browser
        
        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to the script
            
        Returns:
            Result of script execution
        """
        if not self.driver:
            return None
        
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            logger.error(f"Error executing script: {e}")
            # Re-raise the exception so _cmd_execute_js_script can handle it properly
            raise e

    def take_screenshot(self, filename: Optional[str] = None) -> bool:
        """
        Take a screenshot of the current page
        
        Args:
            filename: Optional filename for the screenshot
            
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            return False
        
        try:
            if filename is None:
                filename = f"screenshot_{int(time.time())}.png"
            
            # Use full path if not already provided
            if not os.path.isabs(filename):
                filename = os.path.join(self.screenshots_dir, filename)
            
            self.driver.save_screenshot(filename)
            logger.info(f"Screenshot saved as: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return False

    def take_auto_screenshot(self, filename_prefix: str = "auto_screenshot") -> Optional[str]:
        """
        Automatically take a screenshot with timestamp and store the path
        
        Args:
            filename_prefix: Optional prefix for the screenshot filename
        
        Returns:
            Path to the screenshot file if successful, None otherwise
        """
        if not self.driver:
            return None
        
        try:
            timestamp = int(time.time() * 1000)  # Use milliseconds for uniqueness
            filename = f"{filename_prefix}_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            
            self.driver.save_screenshot(filepath)
            self.latest_screenshot_path = filepath
            logger.info(f"Auto screenshot saved: {filename}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error taking auto screenshot: {e}")
            return None

    def get_latest_screenshot_path(self) -> Optional[str]:
        """
        Get the path to the latest screenshot
        
        Returns:
            Path to the latest screenshot or None
        """
        return self.latest_screenshot_path
# In browser.py

    def click_element(
        self, selector: Optional[str] = None, *, ref: Optional[str] = None
    ) -> bool:
        """
        Click an element using SeleniumBase's native click methods.
        Automatically scrolls the element into view before clicking.

        Args:
            selector: CSS selector or XPath
            ref: Short reference from page map (data-agent-ref attribute)

        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            logger.error("Browser not initialized, cannot click element.")
            return False

        try:
            # Resolve selector from either selector or ref
            resolved_selector = self._resolve_selector(selector, ref)
            if ref:
                logger.info(f"Resolved ref '{ref}' to selector: {resolved_selector}")

            # First, scroll the element into view to prevent click interception
            scroll_success = self.scroll_to_element(selector=resolved_selector)
            if not scroll_success:
                logger.warning(f"Could not scroll to element '{resolved_selector}', attempting click anyway")

            # Add a small delay after scrolling to ensure the page has settled
            time.sleep(0.3)

            if resolved_selector.startswith('/') or resolved_selector.startswith('('):
                # XPath - use SeleniumBase's click method with xpath
                self.driver.click(resolved_selector, by="xpath")
                logger.info(f"Successfully clicked XPath element: {resolved_selector}")
                self.last_clicked_selector = resolved_selector
                return True
            else:
                # CSS selector - use SeleniumBase's click method
                self.driver.click(resolved_selector)
                logger.info(f"Successfully clicked CSS selector: {resolved_selector}")
                self.last_clicked_selector = resolved_selector
                return True

        except Exception as e:
            logger.error(f"Failed to click element '{resolved_selector}': {e}")
            return False

    def press_keys(
        self,
        keys: Union[str, List[str]],
        selector: Optional[str] = None,
        *,
        ref: Optional[str] = None,
    ) -> bool:
        """
        Send keyboard input to an element or the active element/body.

        Args:
            keys: A string or list of strings (e.g., "ArrowDown", "Enter").
            selector: CSS selector or XPath. If None, sends to active element/body.
            ref: Short reference from page map (data-agent-ref attribute).

        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            return False

        try:
            # Resolve selector from either selector or ref (if provided)
            resolved_selector = None
            if selector or ref:
                resolved_selector = self._resolve_selector(selector, ref)
                if ref:
                    logger.info(f"Resolved ref '{ref}' to selector: {resolved_selector}")

            # Normalize keys to a list
            key_list = keys if isinstance(keys, list) else [keys]

            # Map common names to Selenium Keys
            from selenium.webdriver.common.keys import Keys
            key_map = {
                "ArrowDown": Keys.ARROW_DOWN, "Down": Keys.ARROW_DOWN, "DOWN": Keys.ARROW_DOWN,
                "ArrowUp": Keys.ARROW_UP, "Up": Keys.ARROW_UP, "UP": Keys.ARROW_UP,
                "ArrowLeft": Keys.ARROW_LEFT, "Left": Keys.ARROW_LEFT, "LEFT": Keys.ARROW_LEFT,
                "ArrowRight": Keys.ARROW_RIGHT, "Right": Keys.ARROW_RIGHT, "RIGHT": Keys.ARROW_RIGHT,
                "Enter": Keys.ENTER, "Return": Keys.RETURN,
                "Escape": Keys.ESCAPE, "Esc": Keys.ESCAPE,
                "Tab": Keys.TAB, "Space": Keys.SPACE, "PageDown": Keys.PAGE_DOWN, "PageUp": Keys.PAGE_UP,
                "Home": Keys.HOME, "End": Keys.END,
            }

            seq = [key_map.get(k, k) for k in key_list]

            # Prefer SeleniumBase's press_keys if available
            try:
                if resolved_selector:
                    if resolved_selector.startswith('/') or resolved_selector.startswith('('):
                        # XPath fallback: find element and send keys
                        element = self.find_element(resolved_selector)
                        if element:
                            try:
                                try:
                                    self.scroll_to_element(selector=resolved_selector)
                                except Exception:
                                    pass
                                try:
                                    self.driver.execute_script("arguments[0].focus();", element)
                                except Exception:
                                    pass
                                element.send_keys(*seq)
                                return True
                            except Exception:
                                pass
                    else:
                        # CSS selector via SeleniumBase (ensure focus on closest focusable ancestor)
                        try:
                            el = self.find_element(resolved_selector)
                            if el:
                                try:
                                    focus_target = self.driver.execute_script(
                                        """
                                        var el = arguments[0];
                                        var target = el.closest('[role="combobox"], select, [tabindex]') || el;
                                        try { target.focus(); } catch(e) {}
                                        try { target.dispatchEvent(new Event('focus', { bubbles: true })); } catch(e) {}
                                        return target;
                                        """,
                                        el,
                                    )
                                except Exception:
                                    focus_target = None
                                # Prefer sending to active element after focus
                                try:
                                    active = self.driver.switch_to.active_element
                                    if hasattr(active, 'tag_name') and (active.tag_name or '').lower() != 'body':
                                        active.send_keys(*seq)
                                        return True
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        # Fallback: direct press_keys on provided selector
                        self.driver.press_keys(resolved_selector, *seq)
                        return True
                else:
                    # No selector: prefer last clicked selector if available; otherwise focus generic ARIA/native components
                    if self.last_clicked_selector:
                        try:
                            # Attempt to focus and send keys to the last clicked element or its focusable ancestor
                            last_sel = self.last_clicked_selector
                            el = self.find_element(last_sel)
                            if el:
                                try:
                                    self.driver.execute_script(
                                        """
                                        var el = arguments[0];
                                        var target = el.closest('[role="combobox"], select, [tabindex]') || el;
                                        try { target.scrollIntoView({behavior:'instant', block:'center'}); } catch(e) {}
                                        try { target.focus(); } catch(e) {}
                                        try { target.dispatchEvent(new Event('focus', { bubbles: true })); } catch(e) {}
                                        return true;
                                        """,
                                        el,
                                    )
                                except Exception:
                                    pass
                                try:
                                    active = self.driver.switch_to.active_element
                                    if hasattr(active, 'tag_name') and (active.tag_name or '').lower() != 'body':
                                        active.send_keys(*seq)
                                        return True
                                except Exception:
                                    pass
                        except Exception:
                            pass

                    # Fallback: focus a generic, open, keyboard-driven component (ARIA roles / native select)
                    focus_script = """
                    (function(){
                      function isVisible(el){
                        const s = window.getComputedStyle(el);
                        return s.display !== 'none' && s.visibility !== 'hidden' && (el.offsetWidth + el.offsetHeight) > 0;
                      }

                      // Priority 1: An open combobox
                      const openCombobox = document.querySelector('[role="combobox"][aria-expanded="true"]');
                      if (openCombobox && isVisible(openCombobox)) {
                        try { openCombobox.focus(); } catch(e) {}
                        try { openCombobox.dispatchEvent(new Event('focus', { bubbles: true })); } catch(e) {}
                        return true;
                      }

                      // Priority 2: A visible listbox
                      const listbox = document.querySelector('[role="listbox"]');
                      if (listbox && isVisible(listbox)) {
                        // Focus its controller if available
                        const controller = document.querySelector('[aria-controls="' + (listbox.id || '') + '"]');
                        if (controller && isVisible(controller)) {
                          try { controller.focus(); } catch(e) {}
                          try { controller.dispatchEvent(new Event('focus', { bubbles: true })); } catch(e) {}
                          return true;
                        }
                        try { listbox.focus(); } catch(e) {}
                        try { listbox.dispatchEvent(new Event('focus', { bubbles: true })); } catch(e) {}
                        return true;
                      }

                      // Priority 3: Has popup listbox and is expanded
                      const hasPopup = document.querySelector('[aria-haspopup="listbox"][aria-expanded="true"]');
                      if (hasPopup && isVisible(hasPopup)) {
                        try { hasPopup.focus(); } catch(e) {}
                        try { hasPopup.dispatchEvent(new Event('focus', { bubbles: true })); } catch(e) {}
                        return true;
                      }

                      // Priority 4: Native select element
                      const nativeSelect = document.querySelector('select');
                      if (nativeSelect && isVisible(nativeSelect)) {
                        try { nativeSelect.focus(); } catch(e) {}
                        try { nativeSelect.dispatchEvent(new Event('focus', { bubbles: true })); } catch(e) {}
                        return true;
                      }

                      // Priority 5: Any visible focusable with tabindex >= 0 that controls a listbox
                      const focusables = Array.from(document.querySelectorAll('[tabindex]')).filter(el => {
                        const t = parseInt(el.getAttribute('tabindex') || '0', 10);
                        return t >= 0 && isVisible(el);
                      });
                      for (const el of focusables) {
                        const controls = el.getAttribute('aria-controls');
                        if (controls) {
                          const target = document.getElementById(controls);
                          if (target && (target.getAttribute('role') === 'listbox' || target.tagName.toLowerCase() === 'ul')) {
                            try { el.focus(); } catch(e) {}
                            try { el.dispatchEvent(new Event('focus', { bubbles: true })); } catch(e) {}
                            return true;
                          }
                        }
                      }

                      // Fallback: use the current active element if it's not body
                      const ae = document.activeElement;
                      if (ae && ae !== document.body && isVisible(ae)) {
                        try { ae.focus(); } catch(e) {}
                        return true;
                      }

                      return false;
                    })();
                    """
                    try:
                        self.driver.execute_script(focus_script)
                    except Exception:
                        pass

                    try:
                        active = self.driver.switch_to.active_element
                        if hasattr(active, 'tag_name') and (active.tag_name or '').lower() != 'body':
                            active.send_keys(*seq)
                            return True
                    except Exception:
                        pass

                    # Try focusing a known multiselect container directly and send keys
                    try:
                        target = self.driver.find_element("css selector", ".multiselect[tabindex='0']")
                        if target:
                            try:
                                self.driver.execute_script("arguments[0].focus();", target)
                            except Exception:
                                pass
                            target.send_keys(*seq)
                            return True
                    except Exception:
                        pass

                    # Last resort: send to body
                    try:
                        self.driver.press_keys("body", *seq)
                        return True
                    except Exception:
                        pass
            except Exception as e:
                # Fallback using WebDriver send_keys
                element = None
                if selector:
                    element = self.find_element(selector)
                    if element:
                        try:
                            try:
                                self.scroll_to_element(selector)
                            except Exception:
                                pass
                            try:
                                self.driver.execute_script("arguments[0].focus();", element)
                            except Exception:
                                pass
                            element.send_keys(*seq)
                            return True
                        except Exception:
                            pass

                # Send to active element or body
                try:
                    active = self.driver.switch_to.active_element
                    active.send_keys(*seq)
                    return True
                except Exception:
                    pass
                try:
                    body = self.driver.find_element("css selector", "body")
                    body.send_keys(*seq)
                    return True
                except Exception:
                    pass
                logger.error(f"Failed to press keys {key_list} on selector {selector}: {e}")
                return False

        except Exception as e:
            logger.error(f"Error pressing keys {keys} on {selector}: {e}")
            return False
    def type_text(
        self,
        text: str,
        selector: Optional[str] = None,
        *,
        ref: Optional[str] = None,
        clear_first: bool = True,
    ) -> bool:
        """
        Type text into an element using JavaScript for direct control
        
        Args:
            text: Text to type
            selector: CSS selector or XPath
            ref: Short reference from page map (data-agent-ref attribute)
            clear_first: Whether to clear existing text first
            
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            return False
        
        try:
            # Resolve selector from either selector or ref
            resolved_selector = self._resolve_selector(selector, ref)
            if ref:
                logger.info(f"Resolved ref '{ref}' to selector: {resolved_selector}")

            element = self.find_element(resolved_selector)
            if not element:
                logger.error(f"Element not found for selector '{resolved_selector}'")
                return False
            
            # Use JavaScript to set the value directly
            escaped_text = text.replace("'", "\\'")
            if clear_first:
                script = f"arguments[0].value = '{escaped_text}'; arguments[0].dispatchEvent(new Event('input', {{bubbles: true}}));"
            else:
                script = f"arguments[0].value += '{escaped_text}'; arguments[0].dispatchEvent(new Event('input', {{bubbles: true}}));"
            
            self.driver.execute_script(script, element)
            return True
            
        except Exception as e:
            logger.error(f"Error typing text into element {resolved_selector}: {e}")
            return False
    def get_text(self, selector: str) -> Optional[str]:
        """
        Get text content from an element
        
        Args:
            selector: CSS selector or XPath
            
        Returns:
            Text content or None if element not found
        """
        if not self.driver:
            return None
        
        try:
            # Use SeleniumBase's get_text method
            if selector.startswith('/') or selector.startswith('('):
                # XPath
                return self.driver.get_text(selector, by="xpath")
            else:
                # CSS selector
                return self.driver.get_text(selector)
            
        except Exception as e:
            logger.warning(f"Error getting text from element {selector}: {e}")
            return None

    def is_element_visible(self, selector: str) -> bool:
        """
        Check if an element is visible
        
        Args:
            selector: CSS selector or XPath
            
        Returns:
            True if element is visible, False otherwise
        """
        if not self.driver:
            return False
        
        try:
            # Use SeleniumBase's is_element_visible method
            if selector.startswith('/') or selector.startswith('('):
                # XPath
                return self.driver.is_element_visible(selector, by="xpath")
            else:
                # CSS selector
                return self.driver.is_element_visible(selector)
            
        except Exception as e:
            logger.warning(f"Error checking visibility of element {selector}: {e}")
            return False

    def check_element_exists(self, selector: str) -> bool:
        """
        Check if an element exists on the page (regardless of visibility)
        
        Args:
            selector: CSS selector or XPath
            
        Returns:
            True if element exists, False otherwise
        """
        if not self.driver:
            return False
        
        try:
            # Use SeleniumBase's is_element_present method
            if selector.startswith('/') or selector.startswith('('):
                # XPath
                return self.driver.is_element_present(selector, by="xpath")
            else:
                # CSS selector
                return self.driver.is_element_present(selector)
            
        except Exception as e:
            logger.warning(f"Error checking existence of element {selector}: {e}")
            return False

    def scroll_to_element(
        self, selector: Optional[str] = None, *, ref: Optional[str] = None
    ) -> bool:
        """
        Scroll to an element using JavaScript scrollIntoView with instant behavior
        
        Args:
            selector: CSS selector or XPath
            ref: Short reference from page map (data-agent-ref attribute)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            return False
        
        try:
            # Resolve selector from either selector or ref
            resolved_selector = self._resolve_selector(selector, ref)
            if ref:
                logger.info(f"Resolved ref '{ref}' to selector: {resolved_selector}")

            # Use instant scrolling to ensure immediate completion
            if resolved_selector.startswith('/') or resolved_selector.startswith('('):
                # XPath - use JavaScript with document.evaluate, properly escape the selector
                escaped_selector = resolved_selector.replace("'", "\\'")
                script = f"""
                var element = document.evaluate('{escaped_selector}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (element) {{
                    element.scrollIntoView({{behavior: 'instant', block: 'center'}});
                    return true;
                }}
                return false;
                """
                result = self.driver.execute_script(script)
                return bool(result)
            else:
                # CSS selector - properly escape the selector to prevent JavaScript syntax errors
                escaped_selector = resolved_selector.replace("'", "\\'")
                script = f"""
                var element = document.querySelector('{escaped_selector}');
                if (element) {{
                    element.scrollIntoView({{behavior: 'instant', block: 'center'}});
                    return true;
                }}
                return false;
                """
                result = self.driver.execute_script(script)
                return bool(result)
            
        except Exception as e:
            logger.error(f"Error scrolling to element {resolved_selector}: {e}")
            return False

    def enable_network_interception(self) -> bool:
        """
        Enable network request/response interception using Performance API.
        This allows capturing XHR/Fetch calls made by the page.

        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            logger.error("Browser not initialized")
            return False

        try:
            # Clear any previous captured requests
            self._captured_requests.clear()
            self.network_interception_enabled = True
            logger.info("Network interception enabled")
            return True
        except Exception as e:
            logger.error(f"Failed to enable network interception: {e}")
            return False

    def get_network_requests(self, filter_pattern: Optional[str] = None, same_domain_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get captured network requests from the Performance API.
        Captures XHR and Fetch requests with their URLs, methods, and timing.

        Args:
            filter_pattern: Optional regex pattern to filter URLs (e.g., 'api|graphql')
            same_domain_only: If True, only include requests to the same domain as the current page (filters out third-party APIs)

        Returns:
            List of network request dictionaries with url, method, size, duration, etc.
        """
        if not self.driver:
            logger.error("Browser not initialized")
            return []

        try:
            import json
            import re
            from urllib.parse import urlparse

            # Get current page domain for filtering
            current_url = self.get_current_url()
            current_domain = None
            if current_url and same_domain_only:
                parsed = urlparse(current_url)
                # Extract the main domain (e.g., 'whitetailproperties.com' from 'www.whitetailproperties.com')
                domain_parts = parsed.netloc.split('.')
                if len(domain_parts) >= 2:
                    # Get the last two parts (domain.com)
                    current_domain = '.'.join(domain_parts[-2:])
                else:
                    current_domain = parsed.netloc

                logger.info(f"Filtering API requests to same domain: {current_domain}")

            # Use Performance API to get network resources
            script = """
            const resources = performance.getEntriesByType('resource');
            const networkData = [];

            // Filter for XHR and Fetch requests
            for (const resource of resources) {
                if (resource.initiatorType === 'xmlhttprequest' || resource.initiatorType === 'fetch') {
                    networkData.push({
                        url: resource.name,
                        initiatorType: resource.initiatorType,
                        duration: resource.duration,
                        size: resource.transferSize || 0,
                        startTime: resource.startTime,
                        responseEnd: resource.responseEnd,
                        // Try to extract method from timing (usually not available in Performance API)
                        method: 'GET'  // Default, will try to get actual method below
                    });
                }
            }

            return networkData;
            """

            network_requests = self.driver.execute_script(script)

            # Filter by same domain if requested
            if same_domain_only and current_domain:
                filtered_requests = []
                for req in network_requests:
                    # Parse the request URL to get its actual domain
                    req_parsed = urlparse(req['url'])
                    req_domain_parts = req_parsed.netloc.split('.')
                    if len(req_domain_parts) >= 2:
                        req_domain = '.'.join(req_domain_parts[-2:])
                    else:
                        req_domain = req_parsed.netloc

                    # Check if request domain matches current domain
                    if req_domain == current_domain:
                        filtered_requests.append(req)

                logger.info(f"Filtered from {len(network_requests)} to {len(filtered_requests)} requests (same domain only)")
                network_requests = filtered_requests

            # Filter by pattern if provided
            if filter_pattern:
                pattern = re.compile(filter_pattern, re.IGNORECASE)
                network_requests = [req for req in network_requests if pattern.search(req['url'])]

            # Try to fetch response bodies for JSON endpoints
            enhanced_requests = []
            for req in network_requests:
                # Attempt to detect if this is a JSON API call
                if any(keyword in req['url'].lower() for keyword in ['api', 'graphql', 'json', 'data', 'query']):
                    # Try to fetch the response body
                    response_data = self._try_fetch_response_body(req['url'])
                    if response_data:
                        req['response_body'] = response_data
                        req['response_type'] = 'json' if isinstance(response_data, (dict, list)) else 'text'

                enhanced_requests.append(req)

            logger.info(f"Captured {len(enhanced_requests)} network requests (after all filters)")
            return enhanced_requests

        except Exception as e:
            logger.error(f"Failed to get network requests: {e}")
            return []

    def _try_fetch_response_body(self, url: str, timeout: int = 5) -> Optional[Union[Dict, List, str]]:
        """
        Try to re-fetch a URL to get its response body.
        Used to capture API responses for analysis.

        Args:
            url: The URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON (dict/list) or raw text, or None if failed
        """
        try:
            import requests

            # Get cookies from browser session
            cookies = self.driver.get_cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}

            # Get current page URL for referer
            current_url = self.get_current_url()

            headers = {
                'User-Agent': self.browser_config.user_agent,
                'Referer': current_url or '',
            }

            # Make the request
            response = requests.get(url, cookies=cookie_dict, headers=headers, timeout=timeout)

            # Try to parse as JSON
            try:
                return response.json()
            except:
                # Return raw text if not JSON
                return response.text[:5000]  # Limit to 5000 chars

        except Exception as e:
            logger.debug(f"Could not fetch response body for {url}: {e}")
            return None

    def _condense_json_data(self, data: Any, max_items: int = 10, max_array_items: int = 5, depth: int = 0) -> Any:
        """
        Recursively condense JSON data showing structure and sample values.
        Similar to the condensation used in tools.py for function responses.

        Args:
            data: The JSON data to condense
            max_items: Maximum object keys to show (default: 10)
            max_array_items: Maximum array items to show (default: 5)
            depth: Current recursion depth

        Returns:
            Condensed version of the data
        """
        if depth > 6:  # Prevent deep nesting
            return "<max_depth_reached>"

        if isinstance(data, dict):
            if not data:
                return {}

            keys = list(data.keys())
            condensed = {}

            # Show first few keys with their condensed values
            for key in keys[:max_items]:
                condensed[key] = self._condense_json_data(data[key], max_items, max_array_items, depth + 1)

            # Add indicator for remaining keys - show ALL remaining key names (with safety limit)
            if len(keys) > max_items:
                remaining_keys = keys[max_items:]
                # Safety limit: if too many keys, truncate the list but show count
                max_keys_to_show = 50
                if len(remaining_keys) > max_keys_to_show:
                    key_list = ', '.join(remaining_keys[:max_keys_to_show]) + f'... and {len(remaining_keys) - max_keys_to_show} more'
                else:
                    key_list = ', '.join(remaining_keys)
                condensed[f"__{len(keys) - max_items}_more_keys__"] = f"<{key_list}>"

            return condensed

        elif isinstance(data, list):
            if not data:
                return []

            condensed = []

            # Show first few items
            for item in data[:max_array_items]:
                condensed.append(self._condense_json_data(item, max_items, max_array_items, depth + 1))

            # Add indicator for remaining items
            if len(data) > max_array_items:
                condensed.append(f"... and {len(data) - max_array_items} more items (total: {len(data)})")

            return condensed

        elif isinstance(data, str):
            # Truncate very long strings
            if len(data) > 200:
                return f"{data[:200]}... <truncated, total: {len(data)} chars>"
            return data

        else:
            # Numbers, booleans, null
            return data

    def _format_api_requests_for_llm(self, network_requests: List[Dict[str, Any]]) -> str:
        """
        Format captured network requests in a readable way for the LLM.

        Args:
            network_requests: List of network request dictionaries

        Returns:
            Formatted string describing the API calls
        """
        if not network_requests:
            return "No API requests captured."

        import json
        from urllib.parse import urlparse, parse_qs

        formatted_lines = []

        for i, req in enumerate(network_requests, 1):
            # Parse URL to extract components
            parsed_url = urlparse(req['url'])
            query_params = parse_qs(parsed_url.query)

            # Build formatted output
            section = f"API Request #{i}:\n"
            section += f"  URL: {req['url']}\n"
            section += f"  Method: {req.get('method', 'GET')}\n"
            section += f"  Type: {req.get('initiatorType', 'unknown')}\n"

            # Add query parameters if present
            if query_params:
                section += "  Query Parameters:\n"
                for key, values in query_params.items():
                    section += f"    - {key}: {', '.join(values)}\n"

            # Add response body if available (using smart condensation)
            if 'response_body' in req:
                response_body = req['response_body']

                # Use smart condensation to show structure and sample data
                if isinstance(response_body, (dict, list)):
                    condensed = self._condense_json_data(response_body)
                    condensed_json = json.dumps(condensed, indent=2)

                    # Add metadata about the response
                    if isinstance(response_body, list):
                        section += f"  Response (JSON Array with {len(response_body)} items):\n"
                    else:
                        section += f"  Response (JSON Object with {len(response_body)} keys):\n"

                    section += f"{condensed_json}\n"

                else:
                    # Plain text response
                    text_preview = str(response_body)[:500]
                    if len(str(response_body)) > 500:
                        text_preview += "... (truncated)"
                    section += f"  Response (Text):\n{text_preview}\n"

            formatted_lines.append(section)

        return "\n".join(formatted_lines)

    async def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a command on the browser

        Args:
            command: Dictionary containing action and payload

        Returns:
            Dictionary with success status and result
        """
        try:
            action = command.get("action")
            payload = command.get("payload", {})

            if not action:
                return {"success": False, "error": "Action is required"}

            # Handle execute_js_script command
            if action == "execute_js_script":
                return self._cmd_execute_js_script(payload)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {"success": False, "error": f"Command execution failed: {str(e)}"}

    def _cmd_execute_js_script(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute JavaScript on the current page."""
        script = payload.get("script")
        if not script:
            return {"success": False, "error": "Script is required"}
        
        try:
            result = self.execute_script(script)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": f"Script execution failed: {str(e)}"}