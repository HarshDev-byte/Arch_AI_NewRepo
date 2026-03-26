"""
orchestrator.py — LangGraph master orchestrator for ArchAI.

Graph topology (LangGraph 1.x compatible):
  geo → design_evolution → parallel_stage → END
                              │
                       (single node that concurrently
                        runs layout + cost + compliance
                        + sustainability via asyncio.gather)

True fan-out with multiple terminal edges is not supported in LangGraph 1.x
StateGraph, so stages 3–6 are parallelised *inside* a single node.
The graph still gives us:
  - Persistent PipelineState across nodes
  - Per-node error isolation
  - Resumable / inspectable graph via LangGraph Studio
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from agents.compliance_agent   import check_compliance
from agents.cost_agent         import estimate_costs
from agents.geo_agent          import analyze_geo
from agents.layout_agent       import generate_layout
from agents.sustainability_agent import analyze_sustainability
from core.evolutionary         import evolve_designs, individual_to_dict


# ─────────────────────────────────────────────────────────────────────────────
# State schema
# ─────────────────────────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    # ── Inputs ────────────────────────────────────────────────────────────────
    project_id:        str
    user_id:           Optional[str]   # None for anonymous / unauthenticated sessions
    latitude:          float
    longitude:         float
    plot_area_sqm:     float
    budget_inr:        int
    floors:            int
    style_preferences: list[str]

    # ── Agent outputs ─────────────────────────────────────────────────────────
    geo_data:           Optional[dict[str, Any]]
    design_variants:    Optional[list[dict[str, Any]]]
    best_dna:           Optional[dict[str, Any]]
    design_seed:        Optional[str]
    layout_data:        Optional[dict[str, Any]]
    cost_data:          Optional[dict[str, Any]]
    compliance_data:    Optional[dict[str, Any]]
    sustainability_data: Optional[dict[str, Any]]

    # ── Status tracking ───────────────────────────────────────────────────────
    current_agent:    str
    completed_agents: list[str]
    errors:           list[str]

    # ── WebSocket callback (not serialisable — injected at runtime) ───────────
    progress_callback: Any


# ─────────────────────────────────────────────────────────────────────────────
# Progress helper
# ─────────────────────────────────────────────────────────────────────────────

async def _emit(
    state: PipelineState,
    agent: str,
    status: str,
    message: str,
    data: dict | None = None,
) -> None:
    cb = state.get("progress_callback")
    if cb is None:
        return
    payload = {
        "agent":      agent,
        "status":     status,
        "message":    message,
        "data":       data or {},
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "project_id": state.get("project_id", ""),
    }
    result = cb(payload)
    if asyncio.iscoroutine(result):
        await result


# ─────────────────────────────────────────────────────────────────────────────
# Node 1 — Geo analysis
# ─────────────────────────────────────────────────────────────────────────────

async def run_geo_agent(state: PipelineState) -> PipelineState:
    await _emit(state, "geo", "running", "Analysing location, zoning and climate…")
    try:
        geo = await analyze_geo(
            latitude=state["latitude"],
            longitude=state["longitude"],
            plot_area=state["plot_area_sqm"],
        )
        state["geo_data"] = geo
        state["completed_agents"].append("geo")
        await _emit(state, "geo", "complete",
                    f"FSI={geo.get('fsi_allowed')}, zone={geo.get('zoning_type')}", geo)
    except Exception as exc:
        state["errors"].append(f"geo: {exc}")
        # Sensible defaults so downstream agents can still run
        state["geo_data"] = {
            "latitude":  state["latitude"],
            "longitude": state["longitude"],
            "fsi_allowed":     1.5,
            "zoning_type":     "residential_suburban",
            "nearby_amenities": {"total": {"count": 0}},
            "road_access":     {},
            "location_context": {},
            "optimal_solar_orientation": 180.0 if state["latitude"] > 0 else 0.0,
            "annual_rainfall_mm": 800,
            "solar_irradiance_kwh_m2_day": 5.0,
        }
        await _emit(state, "geo", "error", str(exc))
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Node 2 — Evolutionary design generation
# ─────────────────────────────────────────────────────────────────────────────

async def run_design_evolution(state: PipelineState) -> PipelineState:
    await _emit(state, "design", "running", "Evolving unique Design DNA variants…")

    async def design_progress(payload: dict) -> None:
        await _emit(state, "design", "running",
                    payload.get("message", "Evolving…"), payload)

    try:
        from core.design_dna import generate_seed
        from core.memory_store import get_store

        geo_data = state.get("geo_data") or {}
        user_id  = state.get("user_id")
        memory   = await get_store(state["project_id"], user_id=user_id)
        prior    = await memory.get_all()

        seed = generate_seed(
            latitude=state["latitude"],
            longitude=state["longitude"],
            plot_area=state["plot_area_sqm"],
            budget=state["budget_inr"],
            style_prefs=state["style_preferences"],
            extra_entropy=state["project_id"],
        )

        ranked = await evolve_designs(
            plot_area=state["plot_area_sqm"],
            floors=state["floors"],
            budget=state["budget_inr"],
            style_prefs=state["style_preferences"],
            geo_data={**geo_data, "latitude": state["latitude"], "longitude": state["longitude"]},
            progress_callback=design_progress,
            population_size=10,
            generations=3,
            survivors_per_gen=3,
            final_variants=5,
            memory_store=prior,
            user_id=state.get("user_id"),
        )

        # Record fingerprints
        variants_out = []
        for rank, ind in enumerate(ranked, start=1):
            await memory.record(ind["dna"].fingerprint())
            variants_out.append(individual_to_dict(ind, rank))

        state["design_variants"] = variants_out
        state["best_dna"]        = variants_out[0]["dna"] if variants_out else {}
        state["design_seed"]     = seed
        state["completed_agents"].append("design")
        await _emit(state, "design", "complete",
                    f"Generated {len(ranked)} unique variants — best score {ranked[0]['score']:.1f}")
    except Exception as exc:
        state["errors"].append(f"design: {exc}")
        await _emit(state, "design", "error", str(exc))
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Node 3 — Parallel stage (layout + cost + compliance + sustainability)
# ─────────────────────────────────────────────────────────────────────────────

async def _layout_task(state: PipelineState) -> dict[str, Any]:
    await _emit(state, "layout", "running", "Generating floor plans…")
    try:
        result = await generate_layout(
            plot_area_sqm=state["plot_area_sqm"],
            floors=state["floors"],
            budget_inr=state["budget_inr"],
            design_dna=state.get("best_dna") or {},
            geo_data=state.get("geo_data") or {},
            user_id=state.get("user_id"),
        )
        await _emit(state, "layout", "complete",
                    f"Unit type: {result.get('unit_type','?')}")
        return {"layout_data": result, "agent": "layout", "ok": True}
    except Exception as exc:
        await _emit(state, "layout", "error", str(exc))
        return {"layout_data": {}, "agent": "layout", "ok": False, "error": str(exc)}


async def _cost_task(state: PipelineState) -> dict[str, Any]:
    await _emit(state, "cost", "running", "Calculating construction costs and ROI…")
    try:
        result = await estimate_costs(
            plot_area_sqm=state["plot_area_sqm"],
            floors=state["floors"],
            budget_inr=state["budget_inr"],
            geo_data=state.get("geo_data") or {},
            design_dna=state.get("best_dna") or {},
            user_id=state.get("user_id"),
        )
        total = result.get("total_cost_inr", 0)
        await _emit(state, "cost", "complete", f"Total estimate: ₹{total:,}")
        return {"cost_data": result, "agent": "cost", "ok": True}
    except Exception as exc:
        await _emit(state, "cost", "error", str(exc))
        return {"cost_data": {}, "agent": "cost", "ok": False, "error": str(exc)}


async def _compliance_task(state: PipelineState) -> dict[str, Any]:
    await _emit(state, "compliance", "running", "Checking FSI & zoning compliance…")
    try:
        result = await check_compliance(
            plot_area_sqm=state["plot_area_sqm"],
            floors=state["floors"],
            design_dna=state.get("best_dna") or {},
            geo_data=state.get("geo_data") or {},
        )
        label = "✓ Compliant" if result.get("passed") else f"⚠ {len(result.get('issues', []))} issue(s)"
        await _emit(state, "compliance", "complete", label)
        return {"compliance_data": result, "agent": "compliance", "ok": True}
    except Exception as exc:
        await _emit(state, "compliance", "error", str(exc))
        return {"compliance_data": {}, "agent": "compliance", "ok": False, "error": str(exc)}


async def _sustainability_task(state: PipelineState) -> dict[str, Any]:
    await _emit(state, "sustainability", "running", "Analysing solar, ventilation & water…")
    try:
        result = await analyze_sustainability(
            latitude=state["latitude"],
            longitude=state["longitude"],
            plot_area_sqm=state["plot_area_sqm"],
            floors=state["floors"],
            design_dna=state.get("best_dna") or {},
            geo_data=state.get("geo_data") or {},
        )
        await _emit(state, "sustainability", "complete",
                    f"Green rating: {result.get('green_rating','?')} (score {result.get('green_score','?')})")
        return {"sustainability_data": result, "agent": "sustainability", "ok": True}
    except Exception as exc:
        await _emit(state, "sustainability", "error", str(exc))
        return {"sustainability_data": {}, "agent": "sustainability", "ok": False, "error": str(exc)}


async def run_parallel_stage(state: PipelineState) -> PipelineState:
    """Run layout + cost + compliance + sustainability concurrently."""
    await _emit(state, "orchestrator", "running",
                "Running layout, cost, compliance & sustainability in parallel…")

    results = await asyncio.gather(
        _layout_task(state),
        _cost_task(state),
        _compliance_task(state),
        _sustainability_task(state),
        return_exceptions=True,
    )

    for res in results:
        if isinstance(res, BaseException):
            state["errors"].append(str(res))
            continue
        agent = res.get("agent", "unknown")
        if res.get("ok"):
            state["completed_agents"].append(agent)
        else:
            state["errors"].append(f"{agent}: {res.get('error','unknown error')}")

        # Merge outputs into state
        for key in ("layout_data", "cost_data", "compliance_data", "sustainability_data"):
            if key in res and res[key]:
                state[key] = res[key]

    return state


# ─────────────────────────────────────────────────────────────────────────────
# Build & compile LangGraph pipeline
# ─────────────────────────────────────────────────────────────────────────────

def build_pipeline():
    graph: StateGraph = StateGraph(PipelineState)

    graph.add_node("geo",            run_geo_agent)
    graph.add_node("design",         run_design_evolution)
    graph.add_node("parallel_stage", run_parallel_stage)

    graph.set_entry_point("geo")
    graph.add_edge("geo",            "design")
    graph.add_edge("design",         "parallel_stage")
    graph.add_edge("parallel_stage", END)

    return graph.compile()


PIPELINE = build_pipeline()


# ─────────────────────────────────────────────────────────────────────────────
# Public API — invoke the compiled graph
# ─────────────────────────────────────────────────────────────────────────────

async def run_pipeline(
    project_id: str,
    latitude: float,
    longitude: float,
    plot_area_sqm: float,
    budget_inr: int,
    floors: int,
    style_preferences: list[str],
    progress_callback: Any = None,
    user_id: str | None = None,
) -> PipelineState:
    """
    Invoke the LangGraph pipeline and return the final state.

    ``progress_callback`` receives dicts::

        {"agent", "status", "message", "data", "timestamp", "project_id"}

    and may be async or sync.
    """
    initial: PipelineState = {
        "project_id":        project_id,
        "user_id":           user_id,
        "latitude":          latitude,
        "longitude":         longitude,
        "plot_area_sqm":     plot_area_sqm,
        "budget_inr":        budget_inr,
        "floors":            floors,
        "style_preferences": style_preferences,

        "geo_data":           None,
        "design_variants":    None,
        "best_dna":           None,
        "design_seed":        None,
        "layout_data":        None,
        "cost_data":          None,
        "compliance_data":    None,
        "sustainability_data": None,

        "current_agent":    "starting",
        "completed_agents": [],
        "errors":           [],
        "progress_callback": progress_callback,
    }

    final: PipelineState = await PIPELINE.ainvoke(initial)

    if progress_callback:
        n_done  = len(final.get("completed_agents", []))
        n_error = len(final.get("errors", []))
        payload = {
            "agent":             "orchestrator",
            "status":            "complete",
            "message":           f"Pipeline complete — {n_done} agents succeeded, {n_error} error(s).",
            "completed_agents":  final.get("completed_agents", []),
            "errors":            final.get("errors", []),
            "timestamp":         datetime.now(timezone.utc).isoformat(),
        }
        result = progress_callback(payload)
        if asyncio.iscoroutine(result):
            await result

    return final


# ─────────────────────────────────────────────────────────────────────────────
# DB-persisting wrapper (called from routes/generate.py background task)
# ─────────────────────────────────────────────────────────────────────────────

async def run_and_persist(
    project_id: str,
    inputs: dict[str, Any],
    app_state: Any,
) -> None:
    """
    Run the full LangGraph pipeline and persist all outputs to the database.
    Sends WebSocket events through ``app_state.manager``.
    """
    from database import (
        AsyncSessionLocal,
        ComplianceCheck,
        CostEstimate,
        DesignVariant,
        GeoAnalysis,
        Project,
    )
    from sqlalchemy import select

    pid = uuid.UUID(project_id) if isinstance(project_id, str) else project_id

    async def ws_callback(payload: dict) -> None:
        try:
            await app_state.manager.send_update(project_id, payload)
        except Exception:
            pass

    # ── Run pipeline ──────────────────────────────────────────────────────────
    try:
        final = await run_pipeline(
            project_id=project_id,
            latitude=float(inputs.get("latitude",      20.0)),
            longitude=float(inputs.get("longitude",    78.0)),
            plot_area_sqm=float(inputs.get("plot_area_sqm", 1000.0)),
            budget_inr=int(inputs.get("budget_inr",    5_000_000)),
            floors=int(inputs.get("floors",            2)),
            style_preferences=list(inputs.get("style_preferences", [])),
            progress_callback=ws_callback,
        )
    except Exception as exc:
        async with AsyncSessionLocal() as db:
            r = await db.execute(select(Project).where(Project.id == pid))
            proj = r.scalar_one_or_none()
            if proj:
                proj.status = "error"
                await db.commit()
        await ws_callback({"event": "pipeline_error", "error": str(exc)})
        return

    # ── Persist results ───────────────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Project).where(Project.id == pid))
        proj = r.scalar_one_or_none()
        if proj is None:
            return

        proj.status      = "complete" if not final.get("errors") else "error"
        proj.design_seed = final.get("design_seed")
        proj.design_dna  = final.get("best_dna")

        # GeoAnalysis
        geo = final.get("geo_data") or {}
        db.add(GeoAnalysis(
            project_id=pid,
            plot_data=geo,
            zoning_type=geo.get("zoning_type"),
            fsi_allowed=geo.get("fsi_allowed"),
            road_access=geo.get("road_access"),
            nearby_amenities=geo.get("nearby_amenities"),
            solar_irradiance=geo.get("solar_irradiance_kwh_m2_day"),
        ))

        # DesignVariants
        for v in (final.get("design_variants") or []):
            db.add(DesignVariant(
                project_id=pid,
                variant_number=v.get("variant_number"),
                dna=v.get("dna"),
                score=v.get("score"),
                is_selected=v.get("is_selected", False),
                floor_plan_svg=(final.get("layout_data") or {}).get("floor_plan_svg"),
            ))

        # CostEstimate
        ce = final.get("cost_data") or {}
        if ce:
            db.add(CostEstimate(
                project_id=pid,
                breakdown=ce.get("breakdown"),
                total_cost_inr=ce.get("total_cost_inr"),
                cost_per_sqft=ce.get("cost_per_sqft_actual"),
                roi_estimate=ce.get("roi"),
            ))

        # ComplianceCheck
        comp = final.get("compliance_data") or {}
        if comp:
            db.add(ComplianceCheck(
                project_id=pid,
                fsi_used=comp.get("fsi_used"),
                fsi_allowed=comp.get("fsi_allowed"),
                setback_compliance=comp.get("setback_compliance"),
                height_compliance=(comp.get("height_compliance") or {}).get("ok"),
                parking_required=comp.get("parking_required"),
                green_area_required=(comp.get("green_area") or {}).get("required_sqm"),
                issues=comp.get("issues", []),
                passed=comp.get("passed"),
            ))

        await db.commit()

    # ── Final WebSocket event ─────────────────────────────────────────────────
    sust = final.get("sustainability_data") or {}
    await ws_callback({
        "event":             "pipeline_complete",
        "project_id":        project_id,
        "completed_agents":  final.get("completed_agents", []),
        "errors":            final.get("errors", []),
        "green_score":       sust.get("green_score"),
        "green_rating":      sust.get("green_rating"),
        "best_score":        (final.get("design_variants") or [{}])[0].get("score"),
        "total_variants":    len(final.get("design_variants") or []),
        "timestamp":         datetime.now(timezone.utc).isoformat(),
    })
