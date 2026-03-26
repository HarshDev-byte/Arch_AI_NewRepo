"""
agents/chat_agent.py — Design Chat Agent for ArchAI.

Interprets natural language design commands (e.g. "Make it more minimalist",
"Add a butterfly roof", "Larger windows facing south") and maps them to:
  1. Precise Design DNA field mutations
  2. A list of sub-agents to re-run (layout / compliance / sustainability)
  3. A one-sentence explanation for the chat UI

Design decisions
----------------
- Uses Claude claude-3-5-haiku-20241022 (fast, cheap) for command parsing — the
  payload is small and latency matters for chat UX.
- Falls back to Groq (Llama-3) when Anthropic key is absent to keep the
  feature working in dev environments.
- apply_dna_mutations preserves all existing fields and only overlays
  non-null mutations, so partial updates never lose data.
- The seed is re-derived from the mutated state + time so the 3D model
  generator will produce a differentiated output.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from config import settings

logger = logging.getLogger(__name__)


# ─── JSON schema handed to the LLM ───────────────────────────────────────────

_SCHEMA = """\
You MUST return ONLY a single, valid JSON object — no markdown, no explanation.

Schema:
{
  "intent": "modify_style | modify_form | modify_materials | modify_spaces | modify_sustainability | rerun_full",
  "dna_mutations": {
    "primary_style":                  "<style_name or null>",
    "secondary_style":                "<style_name or null>",
    "building_form":                  "<rectangular|L-shape|U-shape|courtyard|split-level or null>",
    "roof_form":                      "<flat_roof|butterfly|shed|gabled|curved|skillion or null>",
    "facade_material_palette":        "<material combo string or null>",
    "facade_pattern":                 "<pattern string or null>",
    "window_style":                   "<full_glass|punched|strip|corner or null>",
    "window_wall_ratio":              <0.2–0.8 or null>,
    "floor_height":                   <2.7–4.5 or null>,
    "has_courtyard":                  <true|false|null>,
    "double_height_spaces":           <true|false|null>,
    "rooftop_utility":                "<garden|solar|terrace|pool or null>",
    "natural_ventilation_strategy":   "<cross_ventilation|stack_effect|wind_catchers or null>",
    "shading_coefficient":            <0.1–0.9 or null>
  },
  "agents_to_rerun": ["layout", "compliance", "sustainability"],
  "explanation": "One sentence describing what was changed and why."
}

Valid style names: contemporary_minimalist, tropical_modern, indo_contemporary,
japanese_wabi_sabi, mediterranean_fusion, brutalist_modern, biophilic_organic,
deconstructivist, parametric_geometric, kerala_modern, rajasthani_fusion,
coastal_vernacular, industrial_loft, neoclassical_modern, scandinavian_minimal

Guidance:
- Set a field to null if it shouldn't change.
- agents_to_rerun should include "layout" when room arrangements change,
  "compliance" when FSI/setbacks/height could be affected,
  "sustainability" when solar, ventilation, or green features change.
- If the user wants a full redesign, set intent="rerun_full" and include all three agents.
"""

_SYSTEM = (
    "You are an expert architectural design assistant specialising in residential "
    "architecture in India. Interpret natural language design commands as precise "
    "Design DNA mutations. " + _SCHEMA
)


# ─── LLM client helpers ───────────────────────────────────────────────────────

async def _call_claude(system: str, user: str, api_key: str | None = None) -> str:
    from anthropic import AsyncAnthropic
    key = api_key or settings.anthropic_api_key
    client = AsyncAnthropic(api_key=key)
    response = await client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=700,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


async def _call_groq(system: str, user: str, api_key: str | None = None) -> str:
    """Groq / Llama-3 fallback for dev environments with no Anthropic key."""
    from groq import AsyncGroq
    key = api_key or settings.groq_api_key
    client = AsyncGroq(api_key=key)
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=700,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


async def _llm_call(system: str, user_prompt: str, user_id: str | None = None) -> str:
    """Resolve provider + key (per-user override possible) and call the LLM.

    Falls back to settings-based keys when no user assignment exists.
    """
    from services.key_manager import get_provider_and_key

    provider, key = await get_provider_and_key(user_id, "chat")
    provider = (provider or "").lower()
    if provider in ("anthropic", "claude"):
        try:
            return await _call_claude(system, user_prompt, api_key=key)
        except Exception as exc:
            logger.warning("Claude failed: %s — falling back to Groq", exc)
            # Fall through
    if provider == "groq":
        return await _call_groq(system, user_prompt, api_key=key)
    # Default fallback
    if settings.groq_api_key:
        return await _call_groq(system, user_prompt, api_key=settings.groq_api_key)
    if settings.anthropic_api_key:
        return await _call_claude(system, user_prompt, api_key=settings.anthropic_api_key)
    raise RuntimeError("No LLM API keys configured or available for this user/agent.")


# ─── Core chat functions ──────────────────────────────────────────────────────

async def interpret_design_command(
    user_message: str,
    current_dna: dict[str, Any],
    project_context: dict[str, Any],
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Parse a natural language design command into a structured mutation payload.

    Returns
    -------
    dict with keys: intent, dna_mutations, agents_to_rerun, explanation
    """
    context_str = (
        f"Current design snapshot:\n"
        f"  - Primary style    : {current_dna.get('primary_style')}\n"
        f"  - Secondary style  : {current_dna.get('secondary_style')}\n"
        f"  - Building form    : {current_dna.get('building_form')}\n"
        f"  - Roof form        : {current_dna.get('roof_form')}\n"
        f"  - Facade materials : {current_dna.get('facade_material_palette')}\n"
        f"  - Window ratio     : {current_dna.get('window_wall_ratio')}\n"
        f"  - Has courtyard    : {current_dna.get('has_courtyard')}\n"
        f"  - Rooftop utility  : {current_dna.get('rooftop_utility')}\n"
        f"  - Floors           : {project_context.get('floors')}\n"
        f"  - Plot area        : {project_context.get('plot_area_sqm')} sqm\n"
        f"  - Budget           : ₹{project_context.get('budget_inr', 0):,}\n"
    )
    user_prompt = f"{context_str}\nUser command: {user_message}"

    raw = await _llm_call(_SYSTEM, user_prompt, user_id=user_id)

    # Strip markdown code fences if the model accidentally adds them
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip("` \n")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Chat agent: invalid JSON from LLM: %s\nRaw: %s", exc, raw)
        # Return a safe default — no mutations, just the raw text as explanation
        parsed = {
            "intent": "modify_style",
            "dna_mutations": {},
            "agents_to_rerun": [],
            "explanation": raw[:200] if raw else "Could not parse design command.",
        }

    return parsed


async def apply_dna_mutations(
    current_dna: dict[str, Any],
    mutations: dict[str, Any],
) -> dict[str, Any]:
    """
    Overlay non-null mutations onto the current DNA dict.

    - Preserves all un-mutated fields.
    - Re-derives the seed so downstream generators produce a distinct output.
    """
    updated = dict(current_dna)
    dna_mutations: dict[str, Any] = mutations.get("dna_mutations") or {}

    applied: list[str] = []
    for key, value in dna_mutations.items():
        if value is not None:
            updated[key] = value
            applied.append(key)

    # Derive a new seed from the old seed + changed fields + time
    seed_source = f"{current_dna.get('seed', '')}_chat_{'_'.join(sorted(applied))}_{time.time_ns()}"
    updated["seed"] = hashlib.sha256(seed_source.encode()).hexdigest()

    logger.info("Design chat: applied %d mutations: %s", len(applied), applied)
    return updated
