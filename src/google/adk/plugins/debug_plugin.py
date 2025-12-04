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

"""Debug plugin for saving LLM requests to files."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from google.genai import types

from ..agents.callback_context import CallbackContext
from ..models.llm_request import LlmRequest
from ..models.llm_response import LlmResponse
from .base_plugin import BasePlugin


class DebugPlugin(BasePlugin):
  """A plugin that saves the full LLM request to debug files.

  This plugin is designed to help developers inspect the exact request
  sent to the LLM, including system instructions, contents, and tool
  configurations. Each LLM request is saved as a JSON file in a debug
  directory.

  Features:
    - Saves the complete LLM request as JSON
    - Each request gets a unique numbered file
    - Organized by session ID and agent name
    - Non-intrusive - errors won't break your agent

  Example:
      >>> debug_plugin = DebugPlugin(debug_dir="./debug")
      >>> runner = Runner(
      ...     agents=[my_agent],
      ...     plugins=[debug_plugin],
      ... )

  The debug directory structure will be:
      debug/
        └── session_abc123_agent_name/
            ├── 001_request.json
            ├── 002_request.json
            └── ...
  """

  def __init__(
      self,
      name: str = "debug_plugin",
      debug_dir: str = "./debug",
  ):
    """Initialize the debug plugin.

    Args:
      name: The name of the plugin instance.
      debug_dir: Directory where debug files will be saved.
    """
    super().__init__(name)
    self.debug_dir = Path(debug_dir)

    # Counter for requests within each session
    self._request_counters: dict[str, int] = {}
    
    # Cache for session directories
    self._session_dirs: dict[str, Path] = {}

    # Create debug directory if it doesn't exist
    self.debug_dir.mkdir(parents=True, exist_ok=True)

  async def before_model_callback(
      self, *, callback_context: CallbackContext, llm_request: LlmRequest
  ) -> Optional[LlmResponse]:
    """Save LLM request before sending to model.

    Args:
      callback_context: The context for the current agent call.
      llm_request: The prepared request object to be sent to the model.

    Returns:
      None (allows the request to proceed normally).
    """
    try:
      # Use session_id as the key for grouping requests
      session_id = callback_context._invocation_context.session.id
      agent_name = callback_context.agent_name

      # Get or initialize request counter for this session
      if session_id not in self._request_counters:
        self._request_counters[session_id] = 0
      self._request_counters[session_id] += 1
      request_num = self._request_counters[session_id]

      # Get or create session directory
      if session_id not in self._session_dirs:
        session_dir = (
            self.debug_dir
            / f"session_{session_id}_{agent_name}"
        )
        session_dir.mkdir(parents=True, exist_ok=True)
        self._session_dirs[session_id] = session_dir
      else:
        session_dir = self._session_dirs[session_id]

      # Save full request as JSON
      request_file = session_dir / f"{request_num:03d}_request.json"
      request_data = self._serialize_llm_request(llm_request)
      with open(request_file, "w", encoding="utf-8") as f:
        json.dump(request_data, f, indent=2, ensure_ascii=False)

      # Save human-readable text version
      text_file = session_dir / f"{request_num:03d}_request.txt"
      self._save_readable_request(text_file, llm_request, request_data)

    except Exception as e:
      # Don't let debug plugin errors break the agent
      print(f"[{self.name}] Error saving debug files: {e}")

    return None

  def _save_readable_request(
      self, file_path: Path, llm_request: LlmRequest, request_data: dict
  ):
    """Save a human-readable text version of the request."""
    with open(file_path, "w", encoding="utf-8") as f:
      f.write(f"MODEL: {llm_request.model}\n")
      f.write("=" * 80 + "\n\n")

      # System Instruction
      if request_data.get("system_instruction"):
        f.write("SYSTEM INSTRUCTION:\n")
        f.write("-" * 20 + "\n")
        f.write(request_data["system_instruction"])
        f.write("\n\n" + "=" * 80 + "\n\n")

      # Contents
      f.write("CONTENTS:\n")
      f.write("-" * 20 + "\n")
      for content in request_data.get("contents", []):
        role = content.get("role", "unknown")
        f.write(f"[{role.upper()}]\n")
        for part in content.get("parts", []):
          if "text" in part:
            f.write(part["text"] + "\n")
          elif "function_call" in part:
            fc = part["function_call"]
            f.write(f"FUNCTION CALL: {fc['name']}({json.dumps(fc['args'])})\n")
          elif "function_response" in part:
            fr = part["function_response"]
            f.write(f"FUNCTION RESPONSE: {fr['name']} -> {json.dumps(fr['response'])}\n")
          else:
            f.write(f"{part}\n")
        f.write("\n")
      
      f.write("=" * 80 + "\n\n")

      # Tools
      if request_data.get("tools"):
        f.write("TOOLS:\n")
        f.write("-" * 20 + "\n")
        for tool in request_data["tools"]:
          f.write(f"- {tool['name']}: {tool.get('description', '').strip()}\n")


  def _serialize_llm_request(self, llm_request: LlmRequest) -> dict:
    """Serialize LlmRequest to a JSON-compatible dictionary.

    Args:
      llm_request: The LLM request to serialize.

    Returns:
      A dictionary representation of the request.
    """
    request_data = {
        "model": llm_request.model,
        "system_instruction": (
            str(llm_request.config.system_instruction)
            if llm_request.config and llm_request.config.system_instruction
            else None
        ),
        "contents": [],
        "tools": [],
        "config": {},
    }

    # Serialize contents
    if llm_request.contents:
      for content in llm_request.contents:
        content_dict = {
            "role": content.role,
            "parts": [],
        }
        for part in content.parts:
          part_dict = {}
          if part.text:
            part_dict["text"] = part.text
          elif part.function_call:
            part_dict["function_call"] = {
                "name": part.function_call.name,
                "args": part.function_call.args,
            }
          elif part.function_response:
            part_dict["function_response"] = {
                "name": part.function_response.name,
                "response": part.function_response.response,
            }
          elif part.inline_data:
            part_dict["inline_data"] = {
                "mime_type": part.inline_data.mime_type,
                "data": "<binary data>",
            }
          else:
            part_dict["other"] = str(part)
          content_dict["parts"].append(part_dict)
        request_data["contents"].append(content_dict)

    # Serialize tools
    if llm_request.config and llm_request.config.tools:
      for tool in llm_request.config.tools:
        if tool.function_declarations:
          for func_decl in tool.function_declarations:
            request_data["tools"].append({
                "name": func_decl.name,
                "description": func_decl.description,
                "parameters": (
                    func_decl.parameters.model_dump(exclude_none=True)
                    if func_decl.parameters
                    else None
                ),
            })

    # Serialize config
    if llm_request.config:
      config_dict = llm_request.config.model_dump(exclude_none=True)
      # Remove tools and system_instruction as they're already captured
      config_dict.pop("tools", None)
      config_dict.pop("system_instruction", None)
      config_dict.pop("response_schema", None)  # Can be complex
      request_data["config"] = config_dict


    return request_data
