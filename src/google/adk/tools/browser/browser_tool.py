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

import logging
from pathlib import Path
from typing import Any

from google.genai import types
from typing_extensions import override

from ..function_tool import FunctionTool
from ..tool_context import ToolContext
from .base_browser import BrowserState

logger = logging.getLogger('google_adk.' + __name__)

# Artifact name for browser screenshots (single artifact, versioned)
BROWSER_SCREENSHOT_ARTIFACT = 'browser_screenshot'


class BrowserTool(FunctionTool):
  """Tool wrapper for browser functions.

  This class extends FunctionTool to provide special handling for browser
  operations, including automatic screenshot saving as artifacts.

  Screenshots are saved as a single versioned artifact named 'browser_screenshot'.
  The frontend can watch `artifactDelta` in events to know when the screenshot
  has been updated and fetch it via the artifact API.
  """

  def __init__(
      self,
      func,
      *,
      save_screenshot_as_artifact: bool = True,
      **kwargs,
  ):
    """Initialize BrowserTool.

    Args:
      func: Browser method to wrap.
      save_screenshot_as_artifact: Whether to save screenshot as artifact.
      **kwargs: Additional arguments to pass to FunctionTool.
    """
    super().__init__(func, **kwargs)
    self._save_screenshot_as_artifact = save_screenshot_as_artifact

  @override
  async def run_async(
      self, *, args: dict[str, Any], tool_context: ToolContext
  ) -> Any:
    """Run browser function and format response.

    This method executes the browser function, saves any screenshot as an
    artifact, and formats the response for LLM consumption.

    Screenshots are saved as a single versioned artifact. The artifact_delta
    in the event will indicate when the screenshot has been updated, allowing
    frontends to fetch the latest version via the artifact API.

    Args:
      args: Arguments for the browser function.
      tool_context: Context for the tool execution.

    Returns:
      Formatted response with URL, title, and screenshot artifact info.
    """
    # Execute the browser function
    result = await super().run_async(args=args, tool_context=tool_context)

    # If result is BrowserState, format for LLM
    if isinstance(result, BrowserState):
      response = {
          'url': result.url,
          'title': result.title,
      }

      # Save screenshot as artifact if available
      if self._save_screenshot_as_artifact and result.screenshot_path:
        try:
          screenshot_path = Path(result.screenshot_path)
          if screenshot_path.exists():
            screenshot_data = screenshot_path.read_bytes()
            
            # Save as artifact - this automatically populates artifact_delta
            version = await tool_context.save_artifact(
                BROWSER_SCREENSHOT_ARTIFACT,
                types.Part(
                    inline_data=types.Blob(
                        mime_type='image/png',
                        data=screenshot_data,
                    )
                ),
            )
            
            # Include artifact reference in response (not the actual data)
            response['screenshot'] = {
                'artifact': BROWSER_SCREENSHOT_ARTIFACT,
                'version': version,
            }
            logger.debug(
                'Saved screenshot as artifact %s version %d',
                BROWSER_SCREENSHOT_ARTIFACT,
                version,
            )
        except Exception as e:
          logger.warning('Failed to save screenshot as artifact: %s', e)

      return response

    return result
