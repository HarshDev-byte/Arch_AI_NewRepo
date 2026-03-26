"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import dynamic from "next/dynamic";
import AgentProgress from "@/components/design/AgentProgress";
import ShareButton from "@/components/ShareButton";

const BabylonViewer = dynamic(() => import("@/components/viewer3d/BabylonViewer"), { ssr: false });

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Types ───────────────────────────────────────────────────────────────────
interface Variant   { id: string; variant_number: number; score: number; dna: Record<string, unknown>; floor_plan_svg?: string; model_url?: string; is_selected: boolean; }
interface CostData  { tier: string; total_cost_inr: number; cost_per_sqft_actual: number; breakdown: Record<string, number>; roi: Record<string, unknown>; }
interface CompData  { passed: boolean; fsi_used: number; fsi_allowed: number; issues: string[]; warnings: string[]; }
interface SustData  { green_score: number; green_rating: string; solar: Record<string, unknown>; ventilation: Record<string, unknown>; recommendations: string[]; }
interface Project   { id: string; name: string; status: string; latitude?: number; longitude?: number; plot_area_sqm?: number; budget_inr?: number; floors?: number; design_variants?: Variant[]; cost_estimates?: CostData[]; compliance_checks?: CompData[]; share_token?: string; is_public?: boolean; }

type Tab = "designs" | "floorplan" | "costs" | "compliance" | "sustainability";

// ─── Helpers ─────────────────────────────────────────────────────────────────
function fmt(n?: number) {
  if (!n) return "—";
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(1)}Cr`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(0)}L`;
  return `₹${n.toLocaleString("en-IN")}`;
}

// ─── Tab content: Designs ────────────────────────────────────────────────────
function DesignsTab({
  variants, selectedId, onSelect, project,
}: {
  variants: Variant[];
  selectedId: string;
  onSelect: (id: string) => void;
  project?: Project;
}) {
  const sel = variants.find((v) => v.id === selectedId) ?? variants[0];

  /** Build the viewer URL, threading lat/lng so Sun Simulator works. */
  function viewerHref(v: Variant): string {
    const params = new URLSearchParams({ variant: v.id });
    if (v.model_url) params.set("model", v.model_url);
    if (project?.latitude  != null) params.set("lat", String(project.latitude));
    if (project?.longitude != null) params.set("lng", String(project.longitude));
    return `/project/${project?.id ?? ""}/viewer?${params.toString()}`;
  }

  return (
    <div className="grid lg:grid-cols-[280px_1fr] gap-6">
      {/* Variant list */}
      <div className="space-y-3">
        {/* Compare button */}
        {variants.length > 1 && (
          <Link
            href={`/project/${project?.id}/compare`}
            className="flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 mb-4"
          >
            🔄 Compare Variants ({variants.length})
          </Link>
        )}
        
        {variants.map((v) => {
          const style = String(v.dna?.primary_style ?? "").replace(/_/g, " ");
          const form  = String(v.dna?.building_form ?? "").replace(/_/g, " ");
          const active = v.id === selectedId;
          return (
            <button key={v.id} id={`variant-${v.variant_number}`} onClick={() => onSelect(v.id)}
              className={`w-full text-left p-4 rounded-xl transition-all border ${active ? "border-violet-500/50 bg-violet-500/10" : "border-white/8 bg-white/3 hover:border-white/15"}`}>
              <div className="flex justify-between items-start">
                <span className="text-xs font-bold text-white/40 uppercase tracking-wider">Variant {v.variant_number}</span>
                <span className={`text-xs font-bold ${active ? "text-violet-400" : "text-white/40"}`}>{v.score?.toFixed(1)}/100</span>
              </div>
              <p className="mt-1 text-sm font-semibold capitalize">{style}</p>
              <p className="text-xs text-white/40 capitalize">{form} form</p>
              <div className="mt-2 h-1 rounded-full bg-white/8">
                <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-500" style={{ width: `${v.score ?? 0}%` }} />
              </div>
            </button>
          );
        })}
      </div>

      {/* 3D / details panel */}
      {sel && (
        <div className="space-y-4">
          <BabylonViewer sceneGraph={sel.dna?.scene_graph as any} modelUrl={sel.model_url ?? ""} height="380px" />

          {/* ── Open in full Three.js viewer (with Sun Simulator) ────────── */}
          <Link
            href={viewerHref(sel)}
            id="open-3d-viewer-btn"
            className="flex items-center justify-center gap-2 py-2 rounded-xl text-sm font-semibold transition-all"
            style={{
              background: "rgba(251,191,36,0.12)",
              border:     "1px solid rgba(251,191,36,0.25)",
              color:      "#fbbf24",
            }}
          >
            ☀️ Open in 3D Viewer — Sun Simulator
          </Link>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "Style",       value: String(sel.dna?.primary_style ?? "—").replace(/_/g, " ") },
              { label: "Form",        value: String(sel.dna?.building_form ?? "—").replace(/_/g, " ") },
              { label: "Floor ht",    value: `${sel.dna?.floor_height ?? "—"}m` },
              { label: "Green score", value: `${sel.dna?.green_score ?? "—"}` },
            ].map((s) => (
              <div key={s.label} className="p-3 rounded-xl bg-white/5 text-center">
                <p className="text-[10px] text-white/35 uppercase tracking-wider">{s.label}</p>
                <p className="text-sm font-semibold mt-1 capitalize">{s.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Tab content: Floor plan ──────────────────────────────────────────────────
function FloorPlanTab({ variants }: { variants: Variant[] }) {
  const [selIdx, setSelIdx] = useState(0);
  const v = variants[selIdx];
  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap">
        {variants.map((v, i) => (
          <button key={v.id} id={`floorplan-variant-${v.variant_number}`} onClick={() => setSelIdx(i)}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${i === selIdx ? "bg-violet-600" : "bg-white/5 hover:bg-white/10 text-white/50"}`}>
            Variant {v.variant_number}
          </button>
        ))}
      </div>
      {v?.floor_plan_svg ? (
        <div className="p-4 rounded-2xl bg-white/5 border border-white/8 overflow-auto"
          dangerouslySetInnerHTML={{ __html: v.floor_plan_svg }} />
      ) : (
        <div className="py-16 text-center text-white/30 text-sm">Floor plan SVG will appear here once generation completes.</div>
      )}
    </div>
  );
}

// ─── Tab content: Costs ──────────────────────────────────────────────────────
function CostsTab({ costs }: { costs?: CostData }) {
  if (!costs) return <div className="py-16 text-center text-white/30 text-sm">Cost analysis pending…</div>;
  const bd = costs.breakdown ?? {};
  const total = costs.total_cost_inr ?? 0;
  const roi = (costs.roi ?? {}) as any;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {[
          { label: "Total cost",       val: fmt(total) },
          { label: "Cost / sqft",      val: `₹${costs.cost_per_sqft_actual ?? "—"}` },
          { label: "Quality tier",     val: costs.tier ?? "—" },
          { label: "Rental / month",   val: fmt(roi.estimated_rental_per_month) },
          { label: "5yr resale",       val: fmt(roi.resale_value_5yr) },
          { label: "Appreciation",     val: `${roi.appreciation_rate_percent ?? "—"}% / yr` },
        ].map((s) => (
          <div key={s.label} className="p-4 rounded-xl bg-white/5 border border-white/8">
            <p className="text-xs text-white/35">{s.label}</p>
            <p className="text-lg font-bold mt-1">{s.val}</p>
          </div>
        ))}
      </div>
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider">Breakdown</h3>
        {Object.entries(bd).map(([k, v]) => (
          <div key={k} className="flex justify-between text-sm">
            <span className="text-white/45 capitalize">{k.replace(/_/g, " ")}</span>
            <span className="font-medium">{fmt(v as number)}</span>
          </div>
        ))}
      </div>
      {roi.recommendation && (
        <div className="p-4 rounded-xl bg-blue-500/10 ring-1 ring-blue-500/20 text-sm text-blue-300">
          💡 {roi.recommendation}
        </div>
      )}
    </div>
  );
}

// ─── Tab content: Compliance ──────────────────────────────────────────────────
function ComplianceTab({ comp }: { comp?: CompData }) {
  if (!comp) return <div className="py-16 text-center text-white/30 text-sm">Compliance check pending…</div>;
  return (
    <div className="space-y-6">
      <div className={`p-5 rounded-2xl ring-1 flex items-center gap-4 ${comp.passed ? "ring-emerald-500/30 bg-emerald-500/10" : "ring-rose-500/30 bg-rose-500/10"}`}>
        <span className="text-4xl">{comp.passed ? "✅" : "⚠️"}</span>
        <div>
          <p className={`text-lg font-bold ${comp.passed ? "text-emerald-400" : "text-rose-400"}`}>
            {comp.passed ? "Compliant with UDCPR 2020 / NBC 2016" : `${comp.issues.length} compliance issue(s) found`}
          </p>
          <p className="text-sm text-white/45 mt-0.5">FSI used: {comp.fsi_used} / allowed: {comp.fsi_allowed}</p>
        </div>
      </div>
      {comp.issues.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-rose-400 uppercase tracking-wider">Issues</h3>
          {comp.issues.map((iss, i) => <p key={i} className="text-sm text-white/60 p-3 rounded-lg bg-rose-500/8">{iss}</p>)}
        </div>
      )}
      {comp.warnings.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-amber-400 uppercase tracking-wider">Warnings</h3>
          {comp.warnings.map((w, i) => <p key={i} className="text-sm text-white/60 p-3 rounded-lg bg-amber-500/8">{w}</p>)}
        </div>
      )}
    </div>
  );
}

// ─── Tab content: Sustainability ─────────────────────────────────────────────
function SustainabilityTab({ sust }: { sust?: SustData }) {
  if (!sust) return <div className="py-16 text-center text-white/30 text-sm">Sustainability analysis pending…</div>;
  const RATING_COLOR: Record<string, string> = { Platinum: "text-cyan-400", Gold: "text-amber-400", Silver: "text-slate-300", Bronze: "text-orange-400" };
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-6 p-6 rounded-2xl bg-emerald-500/10 ring-1 ring-emerald-500/20">
        <div className="text-center">
          <p className="text-5xl font-black text-emerald-400">{sust.green_score}</p>
          <p className="text-xs text-white/40 mt-1">Green score</p>
        </div>
        <div>
          <p className={`text-2xl font-extrabold ${RATING_COLOR[sust.green_rating] ?? "text-white"}`}>{sust.green_rating} Rating</p>
          <p className="text-sm text-white/45 mt-1">IGBC / GRIHA equivalent</p>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[
          { label: "☀️ Solar",       val: `${(sust.solar as any)?.annual_generation_kwh ?? "—"} kWh/yr` },
          { label: "💰 Solar saving", val: fmt((sust.solar as any)?.monthly_savings_inr) + "/mo" },
          { label: "🌬️ AC reduction", val: `${(sust.ventilation as any)?.ac_reduction_percent ?? "—"}%` },
          { label: "🌧️ Payback",     val: `${(sust.solar as any)?.payback_years ?? "—"} yr` },
        ].map((s) => (
          <div key={s.label} className="p-4 rounded-xl bg-white/5 border border-white/8">
            <p className="text-xs text-white/35">{s.label}</p>
            <p className="text-lg font-bold mt-1">{s.val}</p>
          </div>
        ))}
      </div>
      {sust.recommendations.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Recommendations</h3>
          {sust.recommendations.map((r, i) => <p key={i} className="text-sm text-white/60 p-3 rounded-lg bg-emerald-500/6">• {r}</p>)}
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab]   = useState<Tab>("designs");
  const [selectedVariant, setSelectedVariant] = useState<string>("");
  const [pipelineDone, setPipelineDone] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);

  const handleExportPdf = async () => {
    setPdfLoading(true);
    try {
      const variantParam = selectedVariant ? `?variant_id=${selectedVariant}` : "";
      const res = await fetch(`${API}/api/projects/${id}/export/pdf${variantParam}`, {
        headers: { Accept: "application/pdf" },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        alert(`PDF export failed: ${body.detail ?? res.statusText}`);
        return;
      }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `archai-${id.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("Network error while generating PDF. Is the backend running?");
    } finally {
      setPdfLoading(false);
    }
  };

  const { data: project, refetch } = useQuery<Project>({
    queryKey: ["project", id],
    queryFn:  async () => (await axios.get(`${API}/api/projects/${id}`)).data,
    refetchInterval: pipelineDone ? false : 5000,
  });

  // Sustainability & compliance from separate endpoints
  const { data: sust } = useQuery<SustData>({
    queryKey: ["sust", id],
    queryFn:  async () => (await axios.get(`${API}/api/projects/${id}/sustainability`)).data,
    enabled:  pipelineDone,
  });

  const processing = project?.status === "processing" || project?.status === "pending";
  const complete   = project?.status === "complete";
  const variants   = project?.design_variants ?? [];
  const costs      = project?.cost_estimates?.[0];
  const compliance = project?.compliance_checks?.[0];

  useEffect(() => {
    if (complete) { setPipelineDone(true); }
    if (variants.length && !selectedVariant) setSelectedVariant(variants[0].id);
  }, [project, variants, selectedVariant, complete]);

  const TABS: { id: Tab; label: string; icon: string }[] = [
    { id: "designs",       label: "Designs",       icon: "🧬" },
    { id: "floorplan",     label: "Floor Plan",    icon: "📐" },
    { id: "costs",         label: "Costs",         icon: "💰" },
    { id: "compliance",    label: "Compliance",    icon: "✅" },
    { id: "sustainability",label: "Sustainability", icon: "♻️" },
  ];

  return (
    <div className="min-h-screen bg-[#080C14] text-white font-sans">
      <nav className="sticky top-0 z-40 flex items-center gap-4 px-6 py-4 backdrop-blur-xl bg-[#080C14]/80 border-b border-white/5">
        <Link href="/dashboard" className="text-white/40 hover:text-white transition-colors text-sm">← Projects</Link>
        <span className="text-white/20">/</span>
        <span className="text-sm font-semibold truncate">{project?.name ?? "Loading…"}</span>
        <div className="ml-auto flex items-center gap-4">
          <span className={`px-3 py-1 rounded-full text-xs font-bold ${
            complete   ? "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30" :
            processing ? "bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/30" :
                         "bg-rose-500/15 text-rose-400 ring-1 ring-rose-500/30"
          }`}>
            {complete ? "Complete" : processing ? "Processing…" : project?.status ?? "—"}
          </span>
          
          {/* Export PDF button */}
          {complete && (
            <button
              onClick={handleExportPdf}
              disabled={pdfLoading}
              className="px-3 py-1 text-xs font-semibold bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-colors disabled:opacity-50"
            >
              {pdfLoading ? "Generating..." : "📄 Export PDF"}
            </button>
          )}
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">

        {/* ── Agent progress (while running) */}
        <AnimatePresence>
          {processing && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <h2 className="text-lg font-bold mb-4">🤖 Agent Pipeline</h2>
              <AgentProgress projectId={id} onComplete={() => { setPipelineDone(true); refetch(); }} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Tabs (once we have variants) */}
        {(complete || variants.length > 0) && (
          <div>
            {/* Tab bar */}
            <div className="flex gap-1 border-b border-white/8 mb-6 overflow-x-auto">
              {TABS.map((t) => (
                <button key={t.id} id={`tab-${t.id}`} onClick={() => setActiveTab(t.id)}
                  className={`flex items-center gap-1.5 px-4 py-3 text-sm font-semibold whitespace-nowrap transition-all border-b-2 ${
                    activeTab === t.id ? "border-violet-500 text-white" : "border-transparent text-white/40 hover:text-white"
                  }`}>
                  {t.icon} {t.label}
                </button>
              ))}
              <Link href={`/project/${id}/layout`} className="ml-3 flex items-center gap-1.5 px-4 py-3 text-sm font-semibold whitespace-nowrap transition-all text-white/40 hover:text-white border-l border-white/6">
                ✏️ Edit floor plan
              </Link>
            </div>

            <AnimatePresence mode="wait">
              <motion.div key={activeTab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
                {activeTab === "designs"        && <DesignsTab variants={variants} selectedId={selectedVariant} onSelect={setSelectedVariant} project={project} />}
                {activeTab === "floorplan"      && <FloorPlanTab variants={variants} />}
                {activeTab === "costs"          && <CostsTab costs={costs} />}
                {activeTab === "compliance"     && <ComplianceTab comp={compliance} />}
                {activeTab === "sustainability" && <SustainabilityTab sust={sust} />}
              </motion.div>
            </AnimatePresence>
          </div>
        )}

        {/* ── Share Button (when project is complete) */}
        {complete && project && (
          <ShareButton 
            projectId={project.id} 
            projectName={project.name}
            initialShareToken={project.share_token}
            initialIsPublic={project.is_public}
          />
        )}
      </div>
    </div>
  );
}
