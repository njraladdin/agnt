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

import json
import logging
from typing import Any
from typing import Optional

from google.genai import types
from typing_extensions import override

from ..function_tool import FunctionTool
from ..tool_context import ToolContext

logger = logging.getLogger('google_adk.' + __name__)

# Artifact names (single artifacts, versioned)
BROWSER_SCREENSHOT_ARTIFACT = 'browser_screenshot'
TOOL_RESULT_ARTIFACT = 'tool_result'


class BrowserTool(FunctionTool):
  """Tool wrapper for browser functions.

  This class extends FunctionTool to provide special handling for browser
  operations, including automatic artifact saving for screenshots and results.

  Artifacts are saved as single versioned items:
  - 'browser_screenshot': PNG screenshot after browser actions
  - 'tool_result': JSON result from tools with save_result_as_artifact=True

  The frontend can watch `artifactDelta` in events to know when artifacts
  have been updated and fetch them via the artifact API.
  """

  def __init__(
      self,
      func,
      *,
      save_screenshot_as_artifact: bool = True,
      save_result_as_artifact: bool = False,
      result_artifact_name: Optional[str] = None,
      **kwargs,
  ):
    """Initialize BrowserTool.

    Args:
      func: Browser method to wrap.
      save_screenshot_as_artifact: Whether to save screenshot as artifact.
      save_result_as_artifact: Whether to save the result as a JSON artifact.
        Useful for tools that return structured data (e.g., execute_js_script).
      result_artifact_name: Custom name for the result artifact. If None,
        defaults to TOOL_RESULT_ARTIFACT ('tool_result').
      **kwargs: Additional arguments to pass to FunctionTool.
    """
    super().__init__(func, **kwargs)
    self._save_screenshot_as_artifact = save_screenshot_as_artifact
    self._save_result_as_artifact = save_result_as_artifact
    self._result_artifact_name = result_artifact_name or TOOL_RESULT_ARTIFACT

  @override
  async def run_async(
      self, *, args: dict[str, Any], tool_context: ToolContext
  ) -> Any:
    """Run browser function and save artifacts as configured.

    Args:
      args: Arguments for the browser function.
      tool_context: Context for the tool execution.

    Returns:
      Response dict with result and artifact info.
    """
    # Execute the browser function
    result = await super().run_async(args=args, tool_context=tool_context)

    # Get browser from the wrapped function's self reference
    browser = getattr(self.func, '__self__', None)
    if not browser:
      return result

    # Save result as JSON artifact if configured
    if self._save_result_as_artifact:
      result = await self._save_result_artifact(result, tool_context)

    # Save screenshot as artifact if configured
    if self._save_screenshot_as_artifact:
      result = await self._save_screenshot_artifact(result, browser, tool_context)

    return result

  async def _save_result_artifact(
      self, result: Any, tool_context: ToolContext
  ) -> Any:
    """Save the result as a JSON artifact.

    Args:
      result: The result from the browser function.
      tool_context: Context for the tool execution.

    Returns:
      The result, potentially enhanced with artifact info.
    """
    try:
      # Determine what to save - for dict results with 'result' key, save that
      if isinstance(result, dict) and 'result' in result:
        data_to_save = result['result']
      else:
        data_to_save = result

      # Serialize to JSON
      json_bytes = json.dumps(data_to_save, indent=2, default=str).encode('utf-8')

      # Save as artifact
      version = await tool_context.save_artifact(
          self._result_artifact_name,
          types.Part(
              inline_data=types.Blob(
                  mime_type='application/json',
                  data=json_bytes,
              )
          ),
      )

      logger.info(
          'Saved result artifact "%s" v%d (%d bytes)',
          self._result_artifact_name,
          version,
          len(json_bytes),
      )

      # Add artifact info to result
      if isinstance(result, dict):
        result['result_artifact'] = {
            'name': self._result_artifact_name,
            'version': version,
            'size_bytes': len(json_bytes),
        }
      else:
        result = {
            'result': result,
            'result_artifact': {
                'name': self._result_artifact_name,
                'version': version,
                'size_bytes': len(json_bytes),
            },
        }

    except Exception as e:
      logger.error('Failed to save result artifact: %s', e)

    return result

  async def _save_screenshot_artifact(
      self, result: Any, browser: Any, tool_context: ToolContext
  ) -> Any:
    """Save a screenshot as an artifact.

    Args:
      result: The current result from the browser function.
      browser: The browser instance.
      tool_context: Context for the tool execution.

    Returns:
      The result, enhanced with screenshot artifact info.
    """
    try:
      # Get screenshot bytes directly (no disk I/O)
      screenshot_bytes = browser.get_screenshot_bytes()
      if not screenshot_bytes:
        return result

      # Save as artifact
      version = await tool_context.save_artifact(
          BROWSER_SCREENSHOT_ARTIFACT,
          types.Part(
              inline_data=types.Blob(
                  mime_type='image/png',
                  data=screenshot_bytes,
              )
          ),
      )

      logger.info('Saved screenshot artifact v%d', version)

      # Get current state for URL/title
      state = browser.get_current_state()

      # Return enhanced response with artifact info
      if isinstance(result, bool):
        return {
            'result': result,
            'url': state.url,
            'title': state.title,
            'screenshot': {
                'artifact': BROWSER_SCREENSHOT_ARTIFACT,
                'version': version,
            },
        }
      elif isinstance(result, dict):
        result['screenshot'] = {
            'artifact': BROWSER_SCREENSHOT_ARTIFACT,
            'version': version,
        }
        return result

    except Exception as e:
      logger.error('Failed to save screenshot artifact: %s', e)

    return result

