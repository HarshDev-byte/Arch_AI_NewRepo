"""
backend/agents/base_agent.py

BaseAgent provides LLM-calling helpers that automatically resolve the
per-user provider and decrypted API key via `services.key_vault`.

Agents can instantiate `BaseAgent(agent_name, user_id)` and call
`await _call_llm(prompt, system)` to get a string response.
"""
from __future__ import annotations

import json
from typing import Optional

import httpx

from services.gemini_client import call_gemini


class BaseAgent:
    def __init__(self, agent_name: str, user_id: str | None = None):
        self.agent_name = agent_name
        self.user_id = user_id

    async def _call_llm(self, prompt: str, system: str = "") -> str:
        """
        All agents call this. Gemini handles key rotation automatically.
        Falls back to local Ollama if all keys are busy.
        """
        return await call_gemini(prompt, system)

    async def _call_llm_json(self, prompt: str, system: str = "") -> dict:
        """
        Calls Gemini and parses JSON response.
        Adds JSON enforcement to the system prompt.
        """
        import re, json
        json_system = (system or "") + "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no explanation, no code blocks."
        raw = await call_gemini(prompt, json_system)
        raw = re.sub(r"```json|```", "", raw).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    return {"error": "Failed to parse JSON from response", "raw": raw}
            return {"error": "Failed to parse response", "raw": raw}
