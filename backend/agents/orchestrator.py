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
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional, cast

# Ensure backend root is on sys.path for both IDE and runtime
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from langgraph.graph import END, StateGraph  # type: ignore[import]  # noqa: E402
from typing_extensions import TypedDict  # noqa: E402

from agents.compliance_agent     import check_compliance        # type: ignore[import]  # noqa: E402
from agents.cost_agent           import estimate_costs           # type: ignore[import]  # noqa: E402
from agents.geo_agent            import analyze_geo              # type: ignore[import]  # noqa: E402
from agents.layout_agent         import generate_layout          # type: ignore[import]  # noqa: E402
from agents.sustainability_agent import analyze_sustainability   # type: ignore[import]  # noqa: E402
from core.evolutionary           import evolve_designs, individual_to_dict  # type: ignore[import]  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# State schema
# ─────────────────────────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    # ── Inputs ────────────────────────────────────────────────────────────────
    project_id:        str
    user_id:           Optional[str]
    latitude:          float
    longitude:         float
    plot_area_sqm:     float
    budget_inr:        int
    floors:            int
    style_preferences: list[str]

    # ── Agent outputs ─────────────────────────────────────────────────────────
    geo_data:            Optional[dict[str, Any]]
    design_variants:     Optional[list[dict[str, Any]]]
    best_dna:            Optional[dict[str, Any]]
    design_seed:         Optional[str]
    layout_data:         Optional[dict[str, Any]]
    cost_data:           Optional[dict[str, Any]]
    compliance_data:     Optional[dict[str, Any]]
    sustainability_data:  Optional[dict[str, Any]]
    threed_data:         Optional[dict[str, Any]]
    vr_data:             Optional[dict[str, Any]]

    # ── Status tracking ───────────────────────────────────────────────────────
    current_agent:     str
    completed_agents:  list[str]
    errors:            list[str]

    # ── WebSocket callback (not serialisable — injected at runtime) ───────────
    progress_callback: Any


def _s(state: PipelineState) -> dict[str, Any]:
    """Cast PipelineState to a plain mutable dict for safe attribute access."""
    return state  # type: ignore[return-value]


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
    result = cast(Callable[..., Any], cb)(payload)
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
        _s(state)["geo_data"] = geo
        _s(state)["completed_agents"].append("geo")
        await _emit(state, "geo", "complete",
                    f"FSI={geo.get('fsi_allowed')}, zone={geo.get('zoning_type')}", geo)
    except Exception as exc:
        _s(state)["errors"].append(f"geo: {exc}")
        # Sensible defaults so downstream agents can still run
        _s(state)["geo_data"] = {
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
        from core.design_dna import generate_seed      # type: ignore[import]
        from core.memory_store import get_store          # type: ignore[import]

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
            geo_data={**dict(geo_data), "latitude": float(state["latitude"]), "longitude": float(state["longitude"])},
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

        _s(state)["design_variants"] = variants_out
        _s(state)["best_dna"]        = variants_out[0]["dna"] if variants_out else {}
        _s(state)["design_seed"]     = seed
        _s(state)["completed_agents"].append("design")
        best: dict[str, Any] = dict(variants_out[0]) if variants_out else {}
        best_score_raw: Any = best.get("score") or 0
        await _emit(state, "design", "complete",
                    f"Generated {len(variants_out)} unique variants — best score {best_score_raw:.1f}",
                    data={
                        "variants_generated": len(variants_out),
                        "best_score":         int(float(best_score_raw) * 10) / 10,
                        "best_style":         dict(best.get("dna") or {}).get("primary_style", "—"),
                        "best_form":          dict(best.get("dna") or {}).get("building_form", "—"),
                        "green_score":        dict(best.get("dna") or {}).get("green_score", "—"),
                        "floor_height_m":     dict(best.get("dna") or {}).get("floor_height", "—"),
                        "variant_scores":     [int(float(v.get("score") or 0) * 10) / 10 for v in variants_out],
                        "styles":             [dict(v.get("dna") or {}).get("primary_style", "?") for v in variants_out],
                    })
    except Exception as exc:
        _s(state)["errors"].append(f"design: {exc}")
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
        rooms_raw: list[Any] = list(result.get("rooms") or [])
        await _emit(state, "layout", "complete",
                    f"Unit type: {result.get('unit_type','?')}",
                    data={
                        "unit_type":    result.get("unit_type", "—"),
                        "total_rooms":  result.get("total_rooms", "—"),
                        "carpet_area":  result.get("carpet_area_sqm", "—"),
                        "efficiency":   result.get("space_efficiency", "—"),
                        "rooms":        [r.get("name", r.get("type", "?")) for r in cast(list[Any], rooms_raw)[:8]],  # type: ignore[index]
                    })
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
        await _emit(state, "cost", "complete", f"Total estimate: ₹{total:,}",
                    data={
                        "total_cost_inr":      total,
                        "cost_per_sqft":       result.get("cost_per_sqft_actual", "—"),
                        "tier":                result.get("tier", "—"),
                        "roi_years":           (result.get("roi") or {}).get("payback_years", "—"),
                        "rental_yield_pct":    (result.get("roi") or {}).get("rental_yield_pct", "—"),
                        "breakdown":           result.get("breakdown", {}),
                    })
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
        await _emit(state, "compliance", "complete", label,
                    data={
                        "passed":           result.get("passed", False),
                        "fsi_used":         result.get("fsi_used", "—"),
                        "fsi_allowed":      result.get("fsi_allowed", "—"),
                        "issues":           result.get("issues", []),
                        "warnings":         result.get("warnings", []),
                        "parking_required": result.get("parking_required", "—"),
                        "green_area_sqm":   (result.get("green_area") or {}).get("required_sqm", "—"),
                    })
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
        recs_raw: list[Any] = list(result.get("recommendations") or [])
        await _emit(state, "sustainability", "complete",
                    f"Green rating: {result.get('green_rating','?')} (score {result.get('green_score','?')})",
                    data={
                        "green_score":       result.get("green_score", "—"),
                        "green_rating":      result.get("green_rating", "—"),
                        "solar_kwh_per_day": dict(result.get("solar") or {}).get("daily_generation_kwh", "—"),
                        "solar_panels":      dict(result.get("solar") or {}).get("panels_needed", "—"),
                        "ventilation_ach":   dict(result.get("ventilation") or {}).get("ach", "—"),
                        "recommendations":   cast(list[Any], recs_raw)[:5],  # type: ignore[index]
                    })
        return {"sustainability_data": result, "agent": "sustainability", "ok": True}
    except Exception as exc:
        await _emit(state, "sustainability", "error", str(exc))
        return {"sustainability_data": {}, "agent": "sustainability", "ok": False, "error": str(exc)}


async def _threed_task(state: PipelineState) -> dict[str, Any]:
    """Run 3D model generation agent."""
    try:
        await _emit(state, "threed", "running", "Generating 3D models and scene graphs…")
        from agents.threed_agent import run as threed_run  # type: ignore[import]
        
        context = {
            "best_dna": state.get("best_dna", {}),
            "layout": state.get("layout_data", {}),
        }
        result = await threed_run(state["project_id"], context)
        
        await _emit(state, "threed", "complete", "3D models generated successfully",
                    data={
                        "model_url":      result.get("model_url", "—"),
                        "scene_objects":  len((result.get("scene_graph") or {}).get("objects", [])),
                        "format":         result.get("format", "GLB"),
                    })
        return {"agent": "threed", "ok": True, "threed_data": result}
    except Exception as exc:
        await _emit(state, "threed", "error", f"3D generation failed: {str(exc)}")
        return {"agent": "threed", "ok": False, "error": str(exc)}


async def _vr_task(state: PipelineState) -> dict[str, Any]:
    """Run VR experience generation agent."""
    try:
        await _emit(state, "vr", "running", "Creating VR experience…")
        from agents.vr_agent import run as vr_run  # type: ignore[import]
        
        # Get scene graph from threed_data
        threed_raw: Any = state.get("threed_data", {})
        threed_data: dict[str, Any] = cast(dict[str, Any], threed_raw)
        scene_graph = threed_data.get("scene_graph", {})
        
        context = {
            "best_dna": state.get("best_dna", {}),
            "layout": state.get("layout_data", {}),
            "scene_graph": scene_graph,  # VR agent expects this key
            "threed_data": threed_data,
        }
        result = await vr_run(state["project_id"], context)
        
        await _emit(state, "vr", "complete", "VR experience created successfully",
                    data={
                        "vr_url":    result.get("vr_url", "—"),
                        "framework": "A-Frame WebXR",
                        "rooms":     len((result.get("rooms") or [])),
                    })
        return {"agent": "vr", "ok": True, "vr_data": result}
    except Exception as exc:
        await _emit(state, "vr", "error", f"VR generation failed: {str(exc)}")
        return {"agent": "vr", "ok": False, "error": str(exc)}


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

    state_dict: dict[str, Any] = _s(state)
    for res in results:
        if isinstance(res, BaseException):
            state_dict["errors"].append(str(res))
            continue
        res_dict: dict[str, Any] = res if isinstance(res, dict) else {}
        agent: str = str(res_dict.get("agent", "unknown"))
        if res_dict.get("ok"):
            state_dict["completed_agents"].append(agent)
        else:
            state_dict["errors"].append(f"{agent}: {res_dict.get('error', 'unknown error')}")

        # Merge outputs into state
        for key in ("layout_data", "cost_data", "compliance_data", "sustainability_data"):
            val = res_dict.get(key)
            if val:
                state_dict[key] = val

    return state  # type: ignore[return-value]


async def run_3d_vr_stage(state: PipelineState) -> PipelineState:
    """Run 3D model and VR generation sequentially (VR depends on 3D)."""
    await _emit(state, "orchestrator", "running", "Generating 3D models and VR experience…")

    sd = _s(state)

    # Run 3D first
    threed_result = await _threed_task(state)
    if isinstance(threed_result, BaseException):
        sd["errors"].append(str(threed_result))
    else:
        t_agent = str(threed_result.get("agent", "unknown"))
        if threed_result.get("ok"):
            sd["completed_agents"].append(t_agent)
            # Merge 3D data into state for VR to use
            if "threed_data" in threed_result:
                sd["threed_data"] = threed_result["threed_data"]
        else:
            sd["errors"].append(f"{t_agent}: {threed_result.get('error', 'unknown error')}")

    # Run VR second (can use 3D data)
    vr_result = await _vr_task(state)
    if isinstance(vr_result, BaseException):
        sd["errors"].append(str(vr_result))
    else:
        v_agent = str(vr_result.get("agent", "unknown"))
        if vr_result.get("ok"):
            sd["completed_agents"].append(v_agent)
        else:
            sd["errors"].append(f"{v_agent}: {vr_result.get('error', 'unknown error')}")

        # Merge VR data into state
        if "vr_data" in vr_result:
            sd["vr_data"] = vr_result["vr_data"]

    return state


# ─────────────────────────────────────────────────────────────────────────────
# Build & compile LangGraph pipeline
# ─────────────────────────────────────────────────────────────────────────────

def build_pipeline():
    graph: StateGraph = StateGraph(PipelineState)

    graph.add_node("geo",            run_geo_agent)
    graph.add_node("design",         run_design_evolution)
    graph.add_node("parallel_stage", run_parallel_stage)
    graph.add_node("3d_vr_stage",    run_3d_vr_stage)

    graph.set_entry_point("geo")
    graph.add_edge("geo",            "design")
    graph.add_edge("design",         "parallel_stage")
    graph.add_edge("parallel_stage", "3d_vr_stage")
    graph.add_edge("3d_vr_stage",    END)

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
    initial: PipelineState = {  # type: ignore[typeddict-item]
        "project_id":        project_id,
        "user_id":           user_id,
        "latitude":          latitude,
        "longitude":         longitude,
        "plot_area_sqm":     plot_area_sqm,
        "budget_inr":        budget_inr,
        "floors":            floors,
        "style_preferences": style_preferences,

        "geo_data":            None,
        "design_variants":     None,
        "best_dna":            None,
        "design_seed":         None,
        "layout_data":         None,
        "cost_data":           None,
        "compliance_data":     None,
        "sustainability_data":  None,
        "threed_data":         None,
        "vr_data":             None,

        "current_agent":    "starting",
        "completed_agents": [],
        "errors":           [],
        "progress_callback": progress_callback,
    }

    final: dict[str, Any] = dict(await PIPELINE.ainvoke(initial))  # type: ignore[arg-type]

    if progress_callback:
        completed: list[Any] = list(final.get("completed_agents") or [])
        errors_list: list[Any] = list(final.get("errors") or [])
        n_done  = len(completed)
        n_error = len(errors_list)
        payload = {
            "agent":             "orchestrator",
            "status":            "complete",
            "message":           f"Pipeline complete — {n_done} agents succeeded, {n_error} error(s).",
            "completed_agents":  completed,
            "errors":            errors_list,
            "timestamp":         datetime.now(timezone.utc).isoformat(),
        }
        result = progress_callback(payload)
        if asyncio.iscoroutine(result):
            await result

    return final  # type: ignore[return-value]


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
    from database import (         # type: ignore[import]
        AsyncSessionLocal,
        ComplianceCheck,
        CostEstimate,
        DesignVariant,
        GeoAnalysis,
        Project,
    )
    from sqlalchemy import select  # type: ignore[import]

    pid = uuid.UUID(project_id) if isinstance(project_id, str) else project_id

    async def ws_callback(payload: dict) -> None:
        try:
            await app_state.manager.send_update(project_id, payload)
        except Exception:
            pass

    # ── Run pipeline ──────────────────────────────────────────────────────────
    try:
        final_d: dict[str, Any] = dict(await run_pipeline(
            project_id=project_id,
            latitude=float(inputs.get("latitude") or 20.0),
            longitude=float(inputs.get("longitude") or 78.0),
            plot_area_sqm=float(inputs.get("plot_area_sqm") or 1000.0),
            budget_inr=int(inputs.get("budget_inr") or 5_000_000),
            floors=int(inputs.get("floors") or 2),
            style_preferences=list(inputs.get("style_preferences") or []),
            progress_callback=ws_callback,
        ))  # type: ignore[arg-type]
    except Exception as exc:
        async with AsyncSessionLocal() as db:
            r = await db.execute(select(Project).where(Project.id == pid))
            proj = r.scalar_one_or_none()
            if proj:
                proj.status = "error"
                await db.commit()
        await ws_callback({"event": "pipeline_error", "error": str(exc)})
        return

    final = final_d  # single typed reference from here on

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
        geo: dict[str, Any] = cast(dict[str, Any], final.get("geo_data") or {})
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
        threed_data: dict[str, Any] = cast(dict[str, Any], final.get("threed_data") or {})
        model_url   = threed_data.get("model_url")
        scene_graph = threed_data.get("scene_graph")
        _ = scene_graph  # preserve for future use

        for v in cast(list[Any], final.get("design_variants") or []):
            v_dict: dict[str, Any] = cast(dict[str, Any], v) if isinstance(v, dict) else {}
            layout_d: dict[str, Any] = cast(dict[str, Any], final.get("layout_data") or {})
            db.add(DesignVariant(
                project_id=pid,
                variant_number=v_dict.get("variant_number"),
                dna=v_dict.get("dna"),
                score=v_dict.get("score"),
                is_selected=v_dict.get("is_selected", False),
                floor_plan_svg=layout_d.get("floor_plan_svg"),
                model_url=model_url,
            ))

        # CostEstimate
        ce: dict[str, Any] = cast(dict[str, Any], final.get("cost_data") or {})
        if ce:
            db.add(CostEstimate(
                project_id=pid,
                breakdown=ce.get("breakdown"),
                total_cost_inr=ce.get("total_cost_inr"),
                cost_per_sqft=ce.get("cost_per_sqft_actual"),
                roi_estimate=ce.get("roi"),
            ))

        # ComplianceCheck
        comp: dict[str, Any] = cast(dict[str, Any], final.get("compliance_data") or {})
        if comp:
            db.add(ComplianceCheck(
                project_id=pid,
                fsi_used=comp.get("fsi_used"),
                fsi_allowed=comp.get("fsi_allowed"),
                setback_compliance=comp.get("setback_compliance"),
                height_compliance=cast(dict[str, Any], comp.get("height_compliance") or {}).get("ok"),
                parking_required=comp.get("parking_required"),
                green_area_required=cast(dict[str, Any], comp.get("green_area") or {}).get("required_sqm"),
                issues=comp.get("issues", []),
                passed=comp.get("passed"),
            ))

        await db.commit()

    # ── Final WebSocket event ─────────────────────────────────────────────────
    sust: dict[str, Any] = cast(dict[str, Any], final.get("sustainability_data") or {})
    variants_list: list[Any] = cast(list[Any], final.get("design_variants") or [{}])
    first_variant: dict[str, Any] = cast(dict[str, Any], variants_list[0]) if variants_list else {}
    await ws_callback({
        "event":             "pipeline_complete",
        "project_id":        project_id,
        "completed_agents":  cast(list[Any], final.get("completed_agents") or []),
        "errors":            cast(list[Any], final.get("errors") or []),
        "green_score":       sust.get("green_score"),
        "green_rating":      sust.get("green_rating"),
        "best_score":        first_variant.get("score"),
        "total_variants":    len(cast(list[Any], final.get("design_variants") or [])),
        "timestamp":         datetime.now(timezone.utc).isoformat(),
    })
