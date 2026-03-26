"""
evolutionary.py — Evolutionary Algorithm for ArchAI Design Generation.

Process:
  1. Generate N initial DNA variants        (population)
  2. Score each variant for fitness
  3. Select top K survivors
  4. Mutate & crossover survivors           (new generation)
  5. Repeat for G generations
  6. Return top 5 diversity-filtered variants for user selection

Design decisions:
  - Async-first so progress callbacks can push WebSocket events
  - Diversity filter ensures all returned variants look meaningfully different
  - Crossover included alongside mutation (not in original spec but improves
    genetic diversity — falls back to pure mutation if pool too small)
  - Elitism: generation 0 survivors are always carried through unchanged
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional, TypedDict

from core.design_dna import (
    DesignDNA,
    crossover_dna,
    express_dna,
    generate_seed,
    mutate_dna,
    score_dna,
)
from core.memory_store import (
    get_preferred_styles,
    get_seen_hashes,
    record_generated_dna,
)


# ─────────────────────────────────────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────────────────────────────────────

class Individual(TypedDict):
    dna: DesignDNA
    score: float
    generation: int
    parent_id: Optional[str]


ProgressCallback = Callable[[dict[str, Any]], Any]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _send(callback: Optional[ProgressCallback], payload: dict[str, Any]) -> None:
    """Fire-and-forget progress callback — handles both sync and async callables."""
    if callback is None:
        return
    result = callback(payload)
    if asyncio.iscoroutine(result):
        await result


def _diversity_key(ind: Individual) -> str:
    """Stable key that identifies a design "look" — used for diversity filtering."""
    dna = ind["dna"]
    return f"{dna.primary_style}|{dna.building_form}|{dna.roof_form}"


# ─────────────────────────────────────────────────────────────────────────────
# Core evolution function
# ─────────────────────────────────────────────────────────────────────────────

async def evolve_designs(
    plot_area: float,
    floors: int,
    budget: int,
    style_prefs: list[str],
    geo_data: dict[str, Any],
    progress_callback: Optional[ProgressCallback] = None,
    population_size: int = 12,
    generations: int = 3,
    survivors_per_gen: int = 4,
    final_variants: int = 5,
    memory_store: list[str] | None = None,
    user_id: str | None = None,
) -> list[Individual]:
    """
    Run the evolutionary algorithm and return the top ``final_variants``
    design variants, sorted by fitness score (descending).

    Args:
        user_id: Optional user identifier — used to fetch Redis-persisted
                 style preferences and previously seen DNA hashes.
                 Falls back to project-scoped memory when omitted.
    """
    if memory_store is None:
        # Fetch from Redis when not passed directly
        memory_store = await get_seen_hashes(user_id) if user_id else []

    # ── Preference bias: inject top styles for experienced users ──────────────
    effective_style_prefs = list(style_prefs)
    if user_id:
        preferred = await get_preferred_styles(user_id, top_n=2)
        for p in preferred:
            if p and p not in effective_style_prefs:
                effective_style_prefs.append(p)
        if preferred:
            await _send(progress_callback, {
                "stage":   "evolution",
                "phase":   "profile",
                "message": f"Style profile loaded — boosting: {', '.join(preferred)}",
            })

    effective_style_prefs = effective_style_prefs  # already built above
    lat = float(geo_data.get("latitude",  0.0))
    lon = float(geo_data.get("longitude", 0.0))

    # ─── GENERATION 0: seed the initial population ────────────────────────────
    await _send(progress_callback, {
        "stage":   "evolution",
        "phase":   "init",
        "message": f"Seeding initial population of {population_size} designs…",
    })

    population: list[Individual] = []
    for i in range(population_size):
        seed = generate_seed(
            latitude=lat,
            longitude=lon,
            plot_area=plot_area,
            budget=budget,
            style_prefs=style_prefs,
            extra_entropy=f"individual_{i}",
        )
        dna = express_dna(
            seed=seed,
            plot_area=plot_area,
            floors=floors,
            budget=budget,
            style_prefs=effective_style_prefs,
            geo_data=geo_data,
            memory_store=memory_store,
        )
        fitness = score_dna(dna, geo_data, budget)
        population.append(Individual(dna=dna, score=fitness, generation=0, parent_id=None))

        await _send(progress_callback, {
            "stage":      "evolution",
            "generation": 0,
            "individual": i + 1,
            "total":      population_size,
            "message":    f"Generated variant {i + 1}/{population_size} — score {fitness:.1f}",
        })

    # ─── EVOLUTION LOOP ───────────────────────────────────────────────────────
    for gen in range(1, generations + 1):
        # Sort, keep best survivors (elitism)
        population.sort(key=lambda x: x["score"], reverse=True)
        survivors: list[Individual] = population[:survivors_per_gen]

        top_score = survivors[0]["score"]
        await _send(progress_callback, {
            "stage":      "evolution",
            "generation": gen,
            "phase":      "selection",
            "message":    f"Generation {gen}: top score = {top_score:.1f}, "
                          f"kept {len(survivors)} elites",
        })

        # Build offspring pool
        offspring: list[Individual] = []

        # How many children per survivor
        slots = population_size - survivors_per_gen
        mutations_per = max(1, slots // survivors_per_gen)
        crossover_per = max(0, (slots - mutations_per * survivors_per_gen))

        # Mutation offspring
        for parent_data in survivors:
            for _ in range(mutations_per):
                child_dna = mutate_dna(parent_data["dna"], mutation_rate=0.25)
                child_score = score_dna(child_dna, geo_data, budget)
                offspring.append(Individual(
                    dna=child_dna,
                    score=child_score,
                    generation=gen,
                    parent_id=parent_data["dna"].dna_id,
                ))

        # Crossover offspring (genetic recombination between top survivors)
        if len(survivors) >= 2:
            for c in range(crossover_per):
                pa = survivors[c % len(survivors)]
                pb = survivors[(c + 1) % len(survivors)]
                if pa["dna"].dna_id != pb["dna"].dna_id:
                    child_dna = crossover_dna(pa["dna"], pb["dna"])
                else:
                    child_dna = mutate_dna(pa["dna"], mutation_rate=0.3)
                child_score = score_dna(child_dna, geo_data, budget)
                offspring.append(Individual(
                    dna=child_dna,
                    score=child_score,
                    generation=gen,
                    parent_id=pa["dna"].dna_id,
                ))

        # New population: elites + offspring
        population = survivors + offspring

        await _send(progress_callback, {
            "stage":      "evolution",
            "generation": gen,
            "phase":      "reproduction",
            "offspring":  len(offspring),
            "message":    f"Generation {gen} complete — {len(population)} individuals",
        })

    # ─── FINAL SELECTION with diversity filter ────────────────────────────────
    population.sort(key=lambda x: x["score"], reverse=True)

    selected: list[Individual] = []
    seen_keys: set[str] = set()

    for candidate in population:
        key = _diversity_key(candidate)
        # Always include the top 2 regardless of diversity
        if key not in seen_keys or len(selected) < 2:
            selected.append(candidate)
            seen_keys.add(key)
        if len(selected) >= final_variants:
            break

    # Safety pad — fill remaining slots from the ranked list
    remaining = [c for c in population if c not in selected]
    while len(selected) < final_variants and remaining:
        selected.append(remaining.pop(0))

    await _send(progress_callback, {
        "stage":   "evolution",
        "phase":   "complete",
        "total":   len(selected),
        "scores":  [round(s["score"], 2) for s in selected],
        "message": f"Evolution complete — returning {len(selected)} diverse variants",
    })

    # ── Record all selected variants back to Redis ────────────────────────────
    if user_id:
        for ind in selected:
            await record_generated_dna(user_id, ind["dna"])

    return selected[:final_variants]


# ─────────────────────────────────────────────────────────────────────────────
# Serialisation helper
# ─────────────────────────────────────────────────────────────────────────────

def individual_to_dict(ind: Individual, rank: int) -> dict[str, Any]:
    """
    Convert an Individual to a JSON-serialisable dict suitable for
    the API response and database storage.
    """
    dna = ind["dna"]
    return {
        "variant_number":  rank,
        "dna":             dna.to_dict(),
        "score":           ind["score"],
        "generation":      ind["generation"],
        "parent_id":       ind["parent_id"],
        "description":     dna.description(),
        "fingerprint":     dna.fingerprint(),
        "is_selected":     rank == 1,
    }
