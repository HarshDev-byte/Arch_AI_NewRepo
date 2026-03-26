"""
agents/image_agent.py — AI Architectural Image Generation for ArchAI.

Generates photorealistic exterior and interior renders from Design DNA using
the Hugging Face Inference API (free tier).

Models (tried in order)
-----------------------
1. stabilityai/stable-diffusion-xl-base-1.0   (best quality, slower)
2. runwayml/stable-diffusion-v1-5             (faster, always warm)
3. stabilityai/stable-diffusion-2-1           (fallback)

Free tier limits:  ~1000 GPU seconds / month; rate-limited to ~10 req/min.
Model cold-start:  503 → wait 20 s → retry up to 3×.

Environment variable: HF_API_KEY  (get at huggingface.co/settings/tokens)
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

logger = logging.getLogger(__name__)

HF_API_BASE = "https://api-inference.huggingface.co/models"

# ─── Style-to-prompt mapping ──────────────────────────────────────────────────

STYLE_PROMPTS: dict[str, str] = {
    "contemporary_minimalist": "clean lines, minimalist architecture, white concrete, floor-to-ceiling glass, flat roof, modernist house",
    "tropical_modern":         "tropical modernism, deep overhanging eaves, natural wood, lush landscaping, open plan living",
    "japanese_wabi_sabi":      "japanese architecture, wabi-sabi aesthetic, cedar wood, shoji screens, zen rock garden, natural materials",
    "biophilic_organic":       "biophilic design, living green walls, organic curved forms, abundant natural light, indoor plants, nature-integrated",
    "indo_contemporary":       "contemporary Indian architecture, parametric jaali screens, terracotta brick, courtyard house, modern vernacular",
    "mediterranean_fusion":    "mediterranean villa, arched openings, terracotta roof tiles, white lime-washed walls, bougainvillea",
    "brutalist_modern":        "exposed raw concrete, brutalist architecture, bold geometric volume, textured board-formed concrete, dramatic shadows",
    "deconstructivist":        "deconstructivist architecture, tilted planes, fractured geometry, angular volumes, statement facade",
    "parametric_geometric":    "parametric architecture, algorithmic facade pattern, complex geometry, futuristic residential, digital fabrication",
    "kerala_modern":           "Kerala traditional modern house, sloped nalukettu roof, teak wood, inner courtyard, monsoon-adapted architecture",
    "rajasthani_fusion":       "Rajasthani contemporary house, jharokha screens, pink sandstone, haveli-inspired, desert courtyard",
    "coastal_vernacular":      "coastal architecture, elevated on stilts, slatted timber screens, sea breeze orientation, tropical vernacular",
    "industrial_loft":         "industrial loft house, exposed steel, polished concrete, factory windows, mezzanine, raw materials",
    "neoclassical_modern":     "neoclassical modern house, symmetrical facade, columns, mouldings, contemporary interpretation",
    "scandinavian_minimal":    "Scandinavian architecture, light Nordic birch wood, minimalist form, large triple-pane windows, pitched roof",
}

_QUALITY = (
    ", architectural photography by Hufton+Crow, professional render, "
    "8k ultra-detailed, photorealistic, award-winning residential architecture, "
    "golden hour lighting, blue sky, sharp focus, DSLR"
)

_NEG_EXTERIOR = (
    "ugly, blurry, low quality, cartoon, sketch, painting, drawing, "
    "people blocking view, cars parked in front, unrealistic proportions, "
    "deformed, overexposed, watermark, text"
)

_NEG_INTERIOR = (
    "ugly, blurry, low quality, cartoon, people, unrealistic scale, "
    "overexposed, dark, cluttered, messy, watermark, text"
)

# ─── Prompt builders ──────────────────────────────────────────────────────────

def build_exterior_prompt(dna: dict[str, Any], geo_data: dict[str, Any]) -> tuple[str, str]:
    style1 = dna.get("primary_style",   "contemporary_minimalist")
    style2 = dna.get("secondary_style", "")
    form   = (dna.get("building_form",  "rectangular") or "rectangular").replace("_", " ")
    floors = dna.get("floors", 2)
    palette= (dna.get("facade_material_palette", "concrete and glass") or "concrete and glass").replace("_", " ")
    roof   = (dna.get("roof_form",      "flat roof") or "flat roof").replace("_", " ")

    # Try to get city name from geo data (nested under plot_data or location_context)
    loc    = geo_data.get("plot_data", {}) or {}
    city   = (
        loc.get("location_context", {}).get("address", {}).get("city")
        or geo_data.get("city")
        or "India"
    )

    style_desc  = STYLE_PROMPTS.get(style1, "modern architecture")
    style_desc2 = STYLE_PROMPTS.get(style2, "") if style2 else ""

    prompt = (
        f"Exterior photograph of a {floors}-storey {form} residential house in {city}, "
        f"{style_desc}"
        + (f", with {style_desc2}" if style_desc2 else "")
        + f", {palette} materials, {roof}{_QUALITY}"
    )
    return prompt, _NEG_EXTERIOR


def build_interior_prompt(dna: dict[str, Any]) -> tuple[str, str]:
    style       = dna.get("primary_style", "contemporary_minimalist")
    style_desc  = STYLE_PROMPTS.get(style, "modern interior design")
    int_mat     = (dna.get("interior_material", "light oak") or "light oak").replace("_", " ")
    wwr         = float(dna.get("window_wall_ratio", 0.4) or 0.4)
    ceiling_h   = float(dna.get("floor_height", 3.0) or 3.0)

    light_desc = (
        "floor-to-ceiling glazing flooding the space with natural light"
        if wwr > 0.55
        else "well-proportioned windows with warm natural light"
    )
    ceiling_desc = "double-height soaring ceiling" if ceiling_h > 3.6 else "high ceiling"

    prompt = (
        f"Interior photograph of a luxury open-plan living room, "
        f"{style_desc}, {int_mat} flooring, {light_desc}, {ceiling_desc}, "
        f"curated furniture, minimalist decor{_QUALITY}"
    )
    return prompt, _NEG_INTERIOR


def build_aerial_prompt(dna: dict[str, Any], geo_data: dict[str, Any]) -> tuple[str, str]:
    """Aerial/bird's-eye view for the mood board variety."""
    style1  = dna.get("primary_style", "contemporary_minimalist")
    style_d = STYLE_PROMPTS.get(style1, "modern architecture")
    form    = (dna.get("building_form", "rectangular") or "rectangular").replace("_", " ")

    prompt = (
        f"Aerial drone photography of a {form} residential house, {style_d}, "
        f"surrounded by landscaped gardens, bird's-eye view"
        + _QUALITY
    )
    return prompt, _NEG_EXTERIOR


# ─── HF inference call ────────────────────────────────────────────────────────

_MODELS = [
    "stabilityai/stable-diffusion-xl-base-1.0",
    "runwayml/stable-diffusion-v1-5",
    "stabilityai/stable-diffusion-2-1",
]


async def _hf_infer(
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    hf_api_key: str,
) -> bytes | None:
    """Try each model in order; return raw PNG bytes or None on failure."""
    import httpx

    headers = {"Authorization": f"Bearer {hf_api_key}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt":    negative_prompt,
            "width":              width,
            "height":             height,
            "num_inference_steps":28,
            "guidance_scale":     7.5,
        },
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        for model in _MODELS:
            url = f"{HF_API_BASE}/{model}"
            for attempt in range(3):
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        logger.info("image_agent: generated via %s (attempt %d)", model, attempt + 1)
                        return resp.content
                    if resp.status_code == 503:
                        # Model warming up
                        wait = 20 + attempt * 10
                        logger.info("image_agent: model %s loading, waiting %ds…", model, wait)
                        await asyncio.sleep(wait)
                        continue
                    if resp.status_code == 429:
                        logger.warning("image_agent: rate-limited (429), waiting 30s…")
                        await asyncio.sleep(30)
                        continue
                    # 4xx errors — try next model
                    logger.warning(
                        "image_agent: %s returned %d: %s",
                        model, resp.status_code, resp.text[:200],
                    )
                    break
                except Exception as exc:
                    logger.warning("image_agent: request error (%s): %s", model, exc)
                    await asyncio.sleep(5)

    logger.error("image_agent: all models and retries exhausted")
    return None


# ─── Public API ───────────────────────────────────────────────────────────────

async def generate_image(
    prompt: str,
    negative_prompt: str,
    width: int = 768,
    height: int = 512,
    hf_api_key: str = "",
) -> bytes | None:
    """
    Generate a single image.  Returns raw PNG bytes, or None on failure.
    Callers should base64-encode before JSON serialisation.
    """
    if not hf_api_key:
        logger.warning("image_agent: HF_API_KEY not set — returning None")
        return None
    return await _hf_infer(prompt, negative_prompt, width, height, hf_api_key)


async def generate_variant_images(
    dna: dict[str, Any],
    geo_data: dict[str, Any],
    hf_api_key: str = "",
) -> dict[str, Any]:
    """
    Generate exterior + interior + aerial images in parallel.

    Returns
    -------
    {
        "exterior_b64":    "<base64-png or null>",
        "interior_b64":    "<base64-png or null>",
        "aerial_b64":      "<base64-png or null>",
        "exterior_prompt": "…",
        "interior_prompt": "…",
        "aerial_prompt":   "…",
    }
    """
    ext_prompt,  ext_neg  = build_exterior_prompt(dna, geo_data)
    int_prompt,  int_neg  = build_interior_prompt(dna)
    aer_prompt,  aer_neg  = build_aerial_prompt(dna, geo_data)

    logger.info("image_agent: generating 3 images in parallel…")
    ext_bytes, int_bytes, aer_bytes = await asyncio.gather(
        generate_image(ext_prompt, ext_neg, 768, 512, hf_api_key),
        generate_image(int_prompt, int_neg, 768, 512, hf_api_key),
        generate_image(aer_prompt, aer_neg, 768, 512, hf_api_key),
    )

    return {
        "exterior_b64":    base64.b64encode(ext_bytes).decode() if ext_bytes else None,
        "interior_b64":    base64.b64encode(int_bytes).decode() if int_bytes else None,
        "aerial_b64":      base64.b64encode(aer_bytes).decode() if aer_bytes else None,
        "exterior_prompt": ext_prompt,
        "interior_prompt": int_prompt,
        "aerial_prompt":   aer_prompt,
    }
