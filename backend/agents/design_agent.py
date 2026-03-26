"""
design_agent.py — Design generation agent.

Orchestrates the Design DNA + evolutionary algorithm to produce N ranked
design variants, records fingerprints in the anti-repetition memory store,
and returns a summary ready for the database and API.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from core.design_dna import generate_seed
from core.evolutionary import evolve_designs, individual_to_dict
from core.memory_store import get_store
from agents.base_agent import BaseAgent


class DesignAgent(BaseAgent):
    def __init__(self, db=None, user_id: str | None = None):
        super().__init__("design", user_id)

    async def run(self, project: dict) -> dict[str, Any]:
        seed = int(time.time() * 1000) % 99999
        return await self._call_llm_json(
            prompt=f"""
Generate a unique architectural design DNA for this building.
Seed: {seed}
Style: {project.get('style', 'modern')}
Plot area: {project.get('plot_area_sqm')} sqm
Floors: {project.get('floors', 2)}
Budget: ₹{project.get('budget_inr', 3000000)}

Return JSON describing a UNIQUE design.
""",
            system="You are a world-class architect. Every design must be completely unique."
        )


async def generate_design(
    project_id: str,
    context: dict[str, Any],
    progress_callback: Optional[Callable] = None,
) -> dict[str, Any]:
    """
    Design agent entry point.

    Expected context keys:
      - latitude, longitude
      - plot_area_sqm, budget_inr, floors
      - style_preferences (list[str])
      - geo_data (dict — output from geo_agent)
      - max_design_variants (int, default from settings)
      - evolution_generations (int, default from settings)

    Returns:
      - design_seed        (str)
      - variants           (list[dict] with dna + score + rank + description)
      - best_dna           (dict)
      - best_score         (float)
      - best_description   (str)
      - total_variants     (int)
    """
    from config import settings

    lat        = float(context.get("latitude",       20.0))
    lon        = float(context.get("longitude",      78.0))
    plot_area  = float(context.get("plot_area_sqm",  1000.0))
    budget     = int(  context.get("budget_inr",     5_000_000))
    floors     = int(  context.get("floors",         2))
    style_prefs    = list(context.get("style_preferences", []))
    geo_data       = dict(context.get("geo_data", {}))
    n_variants     = int(context.get("max_design_variants",  settings.max_design_variants))
    n_generations  = int(context.get("evolution_generations", settings.evolution_generations))

    # Inject lat/lon into geo_data so evolve_designs can read them
    geo_data.setdefault("latitude",  lat)
    geo_data.setdefault("longitude", lon)

    # ── Anti-repetition memory ────────────────────────────────────────────────
    memory = await get_store(project_id)
    prior_fingerprints = await memory.get_all()

    # ── Unique seed for this run ──────────────────────────────────────────────
    seed = generate_seed(
        latitude=lat,
        longitude=lon,
        plot_area=plot_area,
        budget=budget,
        style_prefs=style_prefs,
        extra_entropy=project_id,
    )

    # ── Evolutionary algorithm ────────────────────────────────────────────────
    ranked = await evolve_designs(
        plot_area=plot_area,
        floors=floors,
        budget=budget,
        style_prefs=style_prefs,
        geo_data=geo_data,
        progress_callback=progress_callback,
        population_size=max(n_variants * 3, 12),
        generations=n_generations,
        survivors_per_gen=max(2, n_variants - 1),
        final_variants=n_variants,
        memory_store=prior_fingerprints,
    )

    # ── Record new fingerprints ───────────────────────────────────────────────
    variants_out = []
    for rank, individual in enumerate(ranked, start=1):
        fp = individual["dna"].fingerprint()
        await memory.record(fp)
        variants_out.append(individual_to_dict(individual, rank))

    best = ranked[0]
    best_dna = best["dna"]

    return {
        "design_seed":       seed,
        "variants":          variants_out,
        "best_dna":          best_dna.to_dict(),
        "best_score":        best["score"],
        "best_description":  best_dna.description(),
        "total_variants":    len(variants_out),
    }
