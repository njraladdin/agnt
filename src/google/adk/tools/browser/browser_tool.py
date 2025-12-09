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
SCRIPT_ARTIFACT = 'js_script'


class BrowserTool(FunctionTool):
  """Tool wrapper for browser functions.

  This class extends FunctionTool to provide special handling for browser
  operations, including automatic artifact saving for screenshots and results.

  Artifacts are saved as single versioned items:
  - 'browser_screenshot': PNG screenshot after browser actions
  - 'tool_result': JSON result from tools with save_result_as_artifact=True
  - 'js_script': JavaScript code from tools with save_script_as_artifact=True

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
      save_script_as_artifact: bool = False,
      script_artifact_name: Optional[str] = None,
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
      save_script_as_artifact: Whether to save the 'script' argument as a
        text artifact. Useful for execute_js_script to enable rerunning.
      script_artifact_name: Custom name for the script artifact. If None,
        defaults to SCRIPT_ARTIFACT ('js_script').
      **kwargs: Additional arguments to pass to FunctionTool.
    """
    super().__init__(func, **kwargs)
    self._save_screenshot_as_artifact = save_screenshot_as_artifact
    self._save_result_as_artifact = save_result_as_artifact
    self._result_artifact_name = result_artifact_name or TOOL_RESULT_ARTIFACT
    self._save_script_as_artifact = save_script_as_artifact
    self._script_artifact_name = script_artifact_name or SCRIPT_ARTIFACT

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

    # Save script as artifact if configured (do this first, before result)
    if self._save_script_as_artifact and 'script' in args:
      result = await self._save_script_artifact(args['script'], result, tool_context)

    # Save result as JSON artifact if configured
    if self._save_result_as_artifact:
      result = await self._save_result_artifact(result, tool_context)

    # Save screenshot as artifact if configured
    if self._save_screenshot_as_artifact:
      result = await self._save_screenshot_artifact(result, browser, tool_context)

    return result

  # Configuration for result preview (to save LLM context tokens)
  _SAMPLE_ITEMS_COUNT = 5  # Number of sample items to show
  _MAX_RESULT_CHARS = 1000  # Max chars for non-array results

  def _create_result_preview(self, data: Any) -> Optional[dict[str, Any]]:
    """Create a structured preview of large results for LLM context efficiency.

    For large results, creates a preview that lets the LLM understand the
    data structure without consuming excessive context tokens.

    Args:
      data: The data to potentially create a preview for.

    Returns:
      A preview dict if data is large, or None if data is small enough
      to return as-is.
    """
    # Handle arrays with many items - show sample + metadata
    if isinstance(data, list) and len(data) > self._SAMPLE_ITEMS_COUNT:
      sample_items = data[:self._SAMPLE_ITEMS_COUNT]

      # Detect fields from sample items (for objects)
      detected_fields = set()
      for item in sample_items:
        if isinstance(item, dict):
          detected_fields.update(item.keys())

      return {
          'item_count': len(data),
          'sample': sample_items,
          'fields_in_sample': sorted(detected_fields) if detected_fields else None,
      }

    # Handle large non-array results - character preview
    json_str = json.dumps(data, indent=2, default=str)
    if len(json_str) > self._MAX_RESULT_CHARS:
      return {
          'preview': json_str[:self._MAX_RESULT_CHARS] + '...',
          'total_chars': len(json_str),
      }

    # Small result - no preview needed
    return None

  async def _save_result_artifact(
      self, result: Any, tool_context: ToolContext
  ) -> Any:
    """Save the result as a JSON artifact and return response for LLM.

    Full data is saved to the artifact. If the result is large, a structured
    preview is returned instead of the full data to save context tokens.

    Args:
      result: The result from the browser function.
      tool_context: Context for the tool execution.

    Returns:
      A dict with artifact info and either the full result (if small) or
      a structured preview (if large).
    """
    try:
      # Determine what to save - for dict results with 'result' key, save that
      if isinstance(result, dict) and 'result' in result:
        data_to_save = result['result']
        success = result.get('success', True)
      else:
        data_to_save = result
        success = True

      # Serialize to JSON (full data for artifact)
      json_bytes = json.dumps(data_to_save, indent=2, default=str).encode('utf-8')

      # Save full data as artifact
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

      # Check if we need a preview (for large results)
      preview = self._create_result_preview(data_to_save)
      if preview:
        return {
            'success': success,
            **preview,
        }

      # Small result - return as-is
      return result

    except Exception as e:
      logger.error('Failed to save result artifact: %s', e)

    return result

  async def _save_script_artifact(
      self, script: str, result: Any, tool_context: ToolContext
  ) -> Any:
    """Save the script code as a text artifact.

    Args:
      script: The JavaScript code to save.
      result: The result from the browser function.
      tool_context: Context for the tool execution.

    Returns:
      The result, potentially enhanced with script artifact info.
    """
    try:
      # Encode script as UTF-8 bytes
      script_bytes = script.encode('utf-8')

      # Save as artifact with text/javascript mime type
      version = await tool_context.save_artifact(
          self._script_artifact_name,
          types.Part(
              inline_data=types.Blob(
                  mime_type='text/javascript',
                  data=script_bytes,
              )
          ),
      )

      logger.info(
          'Saved script artifact "%s" v%d (%d bytes)',
          self._script_artifact_name,
          version,
          len(script_bytes),
      )

      # Artifact is tracked via artifact_delta, no need to include in LLM response

    except Exception as e:
      logger.error('Failed to save script artifact: %s', e)

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

