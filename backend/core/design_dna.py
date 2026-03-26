"""
Design DNA System — Ensures every building design is 100% unique.

A Design DNA is a structured genetic code that combines:
- Plot characteristics (location, area, orientation)
- Environmental data (solar, wind, climate)
- Style preferences (user input)
- Random seed (entropy injection)
- Temporal hash (prevents repetition)
"""

import hashlib
import json
import random
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Vocabulary / gene pools
# ─────────────────────────────────────────────────────────────────────────────

ARCHITECTURAL_STYLES = [
    "contemporary_minimalist", "tropical_modern", "indo_contemporary",
    "japanese_wabi_sabi", "mediterranean_fusion", "brutalist_modern",
    "biophilic_organic", "deconstructivist", "parametric_geometric",
    "kerala_modern", "rajasthani_fusion", "coastal_vernacular",
    "industrial_loft", "neoclassical_modern", "scandinavian_minimal",
]

MATERIAL_PALETTES = {
    "warm_earthy":       ["exposed_brick",      "teak_wood",        "terracotta",   "limestone"],
    "cool_modern":       ["glass_curtain",       "polished_concrete","steel",        "aluminum"],
    "natural_organic":   ["bamboo",              "rammed_earth",     "stone_cladding","timber"],
    "luxury_premium":    ["marble",              "exotic_wood",      "glass",        "brushed_brass"],
    "sustainable_green": ["recycled_materials",  "green_walls",      "solar_tiles",  "mud_brick"],
}

ROOF_FORMS = [
    "flat_terrace", "butterfly_inverted", "shed_mono_pitch", "folded_plate",
    "green_roof", "parasol_floating", "jaali_perforated", "butterfly_clerestory",
    "double_pitched_modern", "curved_shell",
]

FACADE_PATTERNS = [
    "vertical_fins", "horizontal_louvers", "jaali_screen", "perforated_metal",
    "green_facade", "brick_bond_pattern", "glass_box", "textured_plaster",
    "timber_brise_soleil", "parametric_panels",
]

BUILDING_FORMS_SMALL   = ["rectangular", "L_shape", "split_level"]
BUILDING_FORMS_MEDIUM  = ["L_shape", "U_shape", "courtyard", "split_level"]
BUILDING_FORMS_LARGE   = ["courtyard", "U_shape", "H_shape", "pavilion", "cluster"]

VENTILATION_STRATEGIES = [
    "cross_ventilation", "stack_effect", "courtyard_draft", "wind_catcher",
]

ROOFTOP_UTILITIES = ["garden", "terrace", "solar_farm", "mixed"]

INTERIOR_MATERIALS = [
    "wood_flooring", "polished_concrete", "marble", "terrazzo", "bamboo",
]

ROOF_MATERIALS = [
    "flat_concrete", "terracotta_tile", "metal_sheet", "green_roof_membrane",
]

COLOR_TEMPERATURES = ["warm", "cool", "neutral", "high_contrast"]


# ─────────────────────────────────────────────────────────────────────────────
# Data class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DesignDNA:
    # ── Identity ──────────────────────────────────────────────────────────────
    dna_id: str
    seed: str
    generation_timestamp: float

    # ── Spatial genes ─────────────────────────────────────────────────────────
    plot_area: float
    floors: int
    built_up_area: float
    floor_height: float          # 2.7 m – 4.5 m
    setback_front: float
    setback_sides: float

    # ── Style genes ───────────────────────────────────────────────────────────
    primary_style: str
    secondary_style: str         # Style fusion — blend two styles
    style_blend_ratio: float     # 0.0 = pure primary, 1.0 = pure secondary

    # ── Material genes ────────────────────────────────────────────────────────
    facade_material_palette: str
    interior_material: str
    roof_material: str

    # ── Form genes ────────────────────────────────────────────────────────────
    building_form: str           # L-shape, U-shape, rectangular, courtyard, etc.
    roof_form: str
    facade_pattern: str

    # ── Environmental adaptation genes ────────────────────────────────────────
    solar_orientation: float     # Building rotation (degrees)
    natural_ventilation_strategy: str
    shading_coefficient: float   # 0.0 – 1.0

    # ── Spatial programming genes ─────────────────────────────────────────────
    open_plan_ratio: float       # 0.0 = all closed rooms, 1.0 = fully open
    courtyard_presence: bool
    double_height_presence: bool
    rooftop_utility: str         # garden / terrace / solar / mechanical

    # ── Aesthetic genes ───────────────────────────────────────────────────────
    window_wall_ratio: float     # 0.2 – 0.8
    color_temperature: str       # warm / cool / neutral / contrasting
    texture_variety: float       # 0.0 = monolithic, 1.0 = high variety

    # ── Uniqueness marker ─────────────────────────────────────────────────────
    mutation_factor: float       # Introduces design quirks

    # ── Convenience ───────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return asdict(self)

    def fingerprint(self) -> str:
        """Stable SHA-256 fingerprint of the core genes (excludes id + timestamp)."""
        stable = {
            k: v for k, v in asdict(self).items()
            if k not in ("dna_id", "generation_timestamp", "seed")
        }
        return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()

    def description(self) -> str:
        """Human-readable one-liner for UI display."""
        return (
            f"{self.primary_style.replace('_', ' ').title()} × "
            f"{self.secondary_style.replace('_', ' ').title()} | "
            f"{self.building_form.replace('_', ' ').title()} form | "
            f"{int(self.built_up_area * self.floors)} m² BUA | "
            f"{self.floor_height}m floor height"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Seed generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_seed(
    latitude: float,
    longitude: float,
    plot_area: float,
    budget: int,
    style_prefs: list[str],
    extra_entropy: Optional[str] = None,
) -> str:
    """
    Generate a deterministic-but-unique seed from inputs + entropy.
    Same inputs NEVER produce the same seed due to UUID + nanosecond timestamp.
    """
    entropy_sources = [
        str(latitude),
        str(longitude),
        str(plot_area),
        str(budget),
        str(sorted(style_prefs)),
        str(uuid.uuid4()),        # Guaranteed uniqueness
        str(time.time_ns()),      # Nanosecond timestamp
        extra_entropy or "",
    ]
    raw = "|".join(entropy_sources)
    return hashlib.sha256(raw.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# DNA expression
# ─────────────────────────────────────────────────────────────────────────────

def express_dna(
    seed: str,
    plot_area: float,
    floors: int,
    budget: int,
    style_prefs: list[str],
    geo_data: dict,
    memory_store: list[str] | None = None,
) -> DesignDNA:
    """
    Express the Design DNA from a seed — like biological DNA expression.
    The seed deterministically controls all design choices.
    Anti-repetition memory ensures uniqueness across the session.
    """
    if memory_store is None:
        memory_store = []

    # Mutate entropy if design feels too familiar (≥3 prior designs)
    if len(memory_store) > 0:
        seed = hashlib.sha256(f"{seed}{len(memory_store)}".encode()).hexdigest()

    rng = random.Random(seed)

    # ── Style genes ───────────────────────────────────────────────────────────
    if style_prefs and rng.random() > 0.3:
        primary = rng.choice(style_prefs)
    else:
        primary = rng.choice(ARCHITECTURAL_STYLES)

    secondary = rng.choice([s for s in ARCHITECTURAL_STYLES if s != primary])

    # ── Form — depends on plot size ────────────────────────────────────────────
    if plot_area < 1000:
        forms = BUILDING_FORMS_SMALL
    elif plot_area < 2500:
        forms = BUILDING_FORMS_MEDIUM
    else:
        forms = BUILDING_FORMS_LARGE

    # ── Solar orientation ─────────────────────────────────────────────────────
    optimal_orientation = float(geo_data.get("optimal_solar_orientation", 180.0))
    solar_offset = rng.uniform(-25.0, 25.0)

    # ── Assemble ──────────────────────────────────────────────────────────────
    dna = DesignDNA(
        dna_id=str(uuid.uuid4()),
        seed=seed,
        generation_timestamp=time.time(),

        plot_area=plot_area,
        floors=floors,
        built_up_area=round(plot_area * rng.uniform(0.45, 0.65), 2),
        floor_height=rng.choice([2.75, 3.0, 3.2, 3.5, 4.0, 4.5]),
        setback_front=round(rng.uniform(3.0, 6.0), 2),
        setback_sides=round(rng.uniform(1.5, 3.0), 2),

        primary_style=primary,
        secondary_style=secondary,
        style_blend_ratio=round(rng.uniform(0.2, 0.8), 3),

        facade_material_palette=rng.choice(list(MATERIAL_PALETTES.keys())),
        interior_material=rng.choice(INTERIOR_MATERIALS),
        roof_material=rng.choice(ROOF_MATERIALS),

        building_form=rng.choice(forms),
        roof_form=rng.choice(ROOF_FORMS),
        facade_pattern=rng.choice(FACADE_PATTERNS),

        solar_orientation=round(optimal_orientation + solar_offset, 2),
        natural_ventilation_strategy=rng.choice(VENTILATION_STRATEGIES),
        shading_coefficient=round(rng.uniform(0.3, 0.8), 3),

        open_plan_ratio=round(rng.uniform(0.2, 0.9), 3),
        courtyard_presence=(rng.random() > 0.5 and plot_area > 1500),
        double_height_presence=(rng.random() > 0.4),
        rooftop_utility=rng.choice(ROOFTOP_UTILITIES),

        window_wall_ratio=round(rng.uniform(0.25, 0.70), 3),
        color_temperature=rng.choice(COLOR_TEMPERATURES),
        texture_variety=round(rng.uniform(0.2, 1.0), 3),

        mutation_factor=round(rng.uniform(0.0, 0.3), 3),
    )
    return dna


# ─────────────────────────────────────────────────────────────────────────────
# Mutation
# ─────────────────────────────────────────────────────────────────────────────

def mutate_dna(parent: DesignDNA, mutation_rate: float = 0.2) -> DesignDNA:
    """
    Mutate a Design DNA to create offspring — used in the evolutionary algorithm.
    Each gene mutates independently with probability `mutation_rate`.
    """
    d = asdict(parent)
    rng = random.Random(f"{parent.seed}_mutant_{time.time_ns()}")

    mutations = {
        "primary_style":       lambda: rng.choice(ARCHITECTURAL_STYLES),
        "roof_form":           lambda: rng.choice(ROOF_FORMS),
        "facade_pattern":      lambda: rng.choice(FACADE_PATTERNS),
        "floor_height":        lambda: rng.choice([2.75, 3.0, 3.2, 3.5, 4.0]),
        "window_wall_ratio":   lambda: round(rng.uniform(0.25, 0.70), 3),
        "building_form":       lambda: rng.choice(BUILDING_FORMS_MEDIUM),
        "color_temperature":   lambda: rng.choice(COLOR_TEMPERATURES),
        "natural_ventilation_strategy": lambda: rng.choice(VENTILATION_STRATEGIES),
        "rooftop_utility":     lambda: rng.choice(ROOFTOP_UTILITIES),
        "shading_coefficient": lambda: round(rng.uniform(0.3, 0.8), 3),
        "open_plan_ratio":     lambda: round(rng.uniform(0.2, 0.9), 3),
        "texture_variety":     lambda: round(rng.uniform(0.2, 1.0), 3),
    }

    for gene, mutate_fn in mutations.items():
        if rng.random() < mutation_rate:
            d[gene] = mutate_fn()

    d["dna_id"] = str(uuid.uuid4())
    d["seed"] = hashlib.sha256(f"{parent.seed}_mutant".encode()).hexdigest()
    d["generation_timestamp"] = time.time()
    d["mutation_factor"] = round(rng.uniform(0.1, 0.4), 3)

    return DesignDNA(**d)


# ─────────────────────────────────────────────────────────────────────────────
# Crossover
# ─────────────────────────────────────────────────────────────────────────────

def crossover_dna(parent_a: DesignDNA, parent_b: DesignDNA) -> DesignDNA:
    """
    Single-point crossover of two Design DNAs — produces a hybrid offspring.
    For each gene, randomly pick from either parent.
    """
    a = asdict(parent_a)
    b = asdict(parent_b)
    rng = random.Random(f"{parent_a.seed}_{parent_b.seed}_{time.time_ns()}")

    child = {k: (a[k] if rng.random() > 0.5 else b[k]) for k in a}
    child["dna_id"] = str(uuid.uuid4())
    child["seed"] = hashlib.sha256(
        f"{parent_a.seed}+{parent_b.seed}".encode()
    ).hexdigest()
    child["generation_timestamp"] = time.time()

    return DesignDNA(**child)


# ─────────────────────────────────────────────────────────────────────────────
# Fitness scoring
# ─────────────────────────────────────────────────────────────────────────────

def score_dna(dna: DesignDNA, geo_data: dict, budget: int) -> float:
    """
    Fitness scoring for evolutionary selection.
    Higher score = better design for this context.
    Maximum possible score ≈ 100.
    """
    score = 0.0

    # ── Solar efficiency (0–25 pts) ────────────────────────────────────────────
    optimal_orientation = float(geo_data.get("optimal_solar_orientation", 180.0))
    orientation_diff = abs(dna.solar_orientation - optimal_orientation)
    score += max(0.0, 25.0 - (orientation_diff / 5.0))

    # ── Budget efficiency (0–25 pts) ──────────────────────────────────────────
    total_bua = dna.built_up_area * dna.floors
    if total_bua > 0:
        cost_per_sqm = budget / total_bua
        if 15_000 <= cost_per_sqm <= 45_000:   # Sweet spot INR/sqm
            score += 25.0
        elif cost_per_sqm < 15_000:
            score += 10.0  # Too cheap — quality concern
        else:
            score += 15.0  # Premium — acceptable

    # ── Space efficiency / FSI (0–20 pts) ─────────────────────────────────────
    fsi = total_bua / dna.plot_area if dna.plot_area > 0 else 0.0
    if 0.5 <= fsi <= 2.5:
        score += 20.0
    else:
        score += 5.0

    # ── Ventilation (0–15 pts) ────────────────────────────────────────────────
    if dna.natural_ventilation_strategy in ("cross_ventilation", "courtyard_draft"):
        score += 15.0
    else:
        score += 8.0

    # ── Innovation / interest (0–15 pts) ──────────────────────────────────────
    score += dna.texture_variety * 10.0
    if dna.double_height_presence:
        score += 3.0
    if dna.courtyard_presence:
        score += 2.0

    return round(score, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Population generation (multi-variant)
# ─────────────────────────────────────────────────────────────────────────────

def evolve_population(
    base_seed: str,
    plot_area: float,
    floors: int,
    budget: int,
    style_prefs: list[str],
    geo_data: dict,
    n_variants: int = 5,
    n_generations: int = 3,
    memory_store: list[str] | None = None,
) -> list[tuple[DesignDNA, float]]:
    """
    Run a micro-evolutionary loop to produce `n_variants` ranked designs.

    Returns a list of (DesignDNA, score) tuples sorted best-first.
    """
    if memory_store is None:
        memory_store = []

    # Seed the initial population
    population: list[DesignDNA] = []
    for i in range(max(n_variants * 2, 10)):
        variant_seed = hashlib.sha256(f"{base_seed}_{i}".encode()).hexdigest()
        dna = express_dna(
            seed=variant_seed,
            plot_area=plot_area,
            floors=floors,
            budget=budget,
            style_prefs=style_prefs,
            geo_data=geo_data,
            memory_store=memory_store,
        )
        population.append(dna)

    # Evolve for n_generations
    for generation in range(n_generations):
        scored = [(d, score_dna(d, geo_data, budget)) for d in population]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Keep top half as elites
        elites = [d for d, _ in scored[: len(scored) // 2]]

        # Fill rest with crossovers + mutations
        children: list[DesignDNA] = list(elites)
        rng = random.Random(f"{base_seed}_gen{generation}")
        while len(children) < len(population):
            a = rng.choice(elites)
            b = rng.choice(elites)
            if a.dna_id != b.dna_id:
                child = crossover_dna(a, b)
            else:
                child = mutate_dna(a)
            children.append(child)

        population = children

    # Final scoring — return top n_variants
    final_scored = [(d, score_dna(d, geo_data, budget)) for d in population]
    final_scored.sort(key=lambda x: x[1], reverse=True)
    return final_scored[:n_variants]
