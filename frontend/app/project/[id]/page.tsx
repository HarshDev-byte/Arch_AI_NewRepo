"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import dynamic from "next/dynamic";
import AgentProgress from "@/components/design/AgentProgress";
import ShareButton from "@/components/ShareButton";
import ConfettiEffect from "@/components/ui/ConfettiEffect";

const BabylonViewer = dynamic(() => import("@/components/viewer3d/BabylonViewer"), { ssr: false });
const AIAssistant = dynamic(() => import("@/components/mcp/AIAssistant"), { ssr: false });
const MCPStatusBar = dynamic(() => import("@/components/mcp/MCPStatusBar"), { ssr: false });
const SmartDesignPanel = dynamic(() => import("@/components/mcp/SmartDesignPanel"), { ssr: false });

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
        {/* Primary Action Buttons */}
        <div className="space-y-2 mb-6">
          {/* Compare button */}
          {variants.length > 1 && (
            <Link
              href={`/project/${project?.id}/compare`}
              className="flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
            >
              <span className="text-base">🔄</span>
              Compare All Variants ({variants.length})
            </Link>
          )}
          
          {/* Layout Editor button */}
          <Link
            href={`/project/${project?.id}/layout`}
            className="flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all border border-violet-500/30 bg-gradient-to-r from-violet-500/10 to-cyan-500/10 text-violet-400 hover:from-violet-500/20 hover:to-cyan-500/20"
          >
            <span className="text-base">🤖</span>
            AI Floor Plan Editor
          </Link>
        </div>
        
        {/* Variant Selection */}
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-white/40 uppercase tracking-wider mb-3">Design Variants</h4>
          {variants.map((v) => {
            const style = String(v.dna?.primary_style ?? "").replace(/_/g, " ");
            const form  = String(v.dna?.building_form ?? "").replace(/_/g, " ");
            const active = v.id === selectedId;
            return (
              <button key={v.id} id={`variant-${v.variant_number}`} onClick={() => onSelect(v.id)}
                className={`w-full text-left p-4 rounded-xl transition-all border ${active ? "border-violet-500/50 bg-violet-500/10 shadow-lg shadow-violet-500/20" : "border-white/8 bg-white/3 hover:border-white/15 hover:bg-white/5"}`}>
                <div className="flex justify-between items-start">
                  <span className="text-xs font-bold text-white/40 uppercase tracking-wider">Variant {v.variant_number}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-bold ${active ? "text-violet-400" : "text-white/40"}`}>{v.score?.toFixed(1)}/100</span>
                    {active && <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse"></span>}
                  </div>
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
      </div>

      {/* 3D / details panel */}
      {sel && (
        <div className="space-y-4">
          <BabylonViewer sceneGraph={sel.dna?.scene_graph as any} modelUrl={sel.model_url ?? ""} height="380px" />

          {/* ── Primary Action Buttons ────────── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Open in full Three.js viewer (with Sun Simulator) */}
            {sel.model_url && sel.model_url.trim() && (
              <Link
                href={viewerHref(sel)}
                id="open-3d-viewer-btn"
                className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold transition-all bg-gradient-to-r from-amber-500/15 to-orange-500/15 border border-amber-500/25 text-amber-400 hover:border-amber-500/40 hover:from-amber-500/20 hover:to-orange-500/20"
              >
                <span className="text-lg">🏗️</span>
                <div className="text-left">
                  <div className="font-bold">3D Structure Viewer</div>
                  <div className="text-xs text-amber-400/70">Interactive + Sun Simulator</div>
                </div>
              </Link>
            )}
            
            {/* Floor Plan Editor */}
            <Link
              href={`/project/${project?.id}/layout`}
              className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold transition-all bg-gradient-to-r from-violet-500/15 to-cyan-500/15 border border-violet-500/25 text-violet-400 hover:border-violet-500/40 hover:from-violet-500/20 hover:to-cyan-500/20"
            >
              <span className="text-lg">📐</span>
              <div className="text-left">
                <div className="font-bold">Floor Plan Editor</div>
                <div className="text-xs text-violet-400/70">AI-Powered Design Tools</div>
              </div>
            </Link>
          </div>

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
  const [pdfLoading, setPdfLoading] = useState(false);
  const [rerunning, setRerunning]   = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);

  const handleRerunPipeline = async () => {
    setRerunning(true);
    try {
      await axios.post(`${API}/api/generate/start/${id}`);
      refetch();
    } catch (e: any) {
      alert(e?.response?.data?.detail ?? "Failed to start pipeline.");
    } finally {
      setRerunning(false);
    }
  };

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
    // Poll every 3s while processing; stop once complete to avoid unnecessary traffic
    refetchInterval: (data: any) =>
      data?.status === "complete" || data?.status === "error" ? false : 3000,
  });

  const processing   = project?.status === "processing" || project?.status === "pending";
  const complete     = project?.status === "complete";
  // Derive pipelineDone directly — never stale, no extra render tick needed
  const pipelineDone = complete;
  const variants     = useMemo(() => project?.design_variants ?? [], [project?.design_variants]);
  const costs        = project?.cost_estimates?.[0];
  const compliance   = project?.compliance_checks?.[0];

  // Sustainability & compliance from separate endpoints
  const { data: sust } = useQuery<SustData>({
    queryKey: ["sust", id],
    queryFn:  async () => (await axios.get(`${API}/api/projects/${id}/sustainability`)).data,
    enabled:  complete,   // fires as soon as project is complete
  });

  useEffect(() => {
    if (variants.length && !selectedVariant) setSelectedVariant(variants[0].id);
  }, [variants, selectedVariant]);

  // Trigger confetti when project completes
  useEffect(() => {
    if (complete && !showConfetti) {
      setShowConfetti(true);
    }
  }, [complete, showConfetti]);

  const TABS: { id: Tab; label: string; icon: string }[] = [
    { id: "designs",       label: "Designs",       icon: "🧬" },
    { id: "floorplan",     label: "Floor Plan",    icon: "📐" },
    { id: "costs",         label: "Costs",         icon: "💰" },
    { id: "compliance",    label: "Compliance",    icon: "✅" },
    { id: "sustainability",label: "Sustainability", icon: "♻️" },
  ];

  return (
    <div className="min-h-screen bg-[#080C14] text-white font-sans">
      {/* ── Sticky nav */}
      <nav className="sticky top-0 z-40 flex items-center gap-4 px-6 py-4 backdrop-blur-xl bg-[#080C14]/80 border-b border-white/5">
        <Link href="/dashboard" className="text-white/40 hover:text-white transition-colors text-sm">← Projects</Link>
        <span className="text-white/20">/</span>
        <span className="text-sm font-semibold truncate">{project?.name ?? "Loading…"}</span>
        <div className="ml-auto flex items-center gap-3">
          {/* MCP badge */}
          <span className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-violet-500/10 border border-violet-500/25 text-violet-300 text-xs font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
            MCP Active
          </span>
          <span className={`px-3 py-1 rounded-full text-xs font-bold ${
            complete   ? "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30" :
            processing ? "bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/30" :
                         "bg-rose-500/15 text-rose-400 ring-1 ring-rose-500/30"
          }`}>
            {complete ? "Complete" : processing ? "Processing…" : project?.status ?? "—"}
          </span>
          {/* Re-run / Export buttons */}
          {complete && (
            <button
              onClick={handleExportPdf}
              disabled={pdfLoading}
              className="px-3 py-1 text-xs font-semibold bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-colors disabled:opacity-50"
            >
              {pdfLoading ? "Generating..." : "📄 Export PDF"}
            </button>
          )}
          {(project?.status === "pending" || project?.status === "error") && (
            <button
              id="rerun-pipeline-btn"
              onClick={handleRerunPipeline}
              disabled={rerunning}
              className="px-3 py-1 text-xs font-semibold bg-violet-600/20 hover:bg-violet-600/40 border border-violet-500/40 text-violet-300 rounded-lg transition-colors disabled:opacity-50"
            >
              {rerunning ? "Starting…" : "▶ Run Pipeline"}
            </button>
          )}
        </div>
      </nav>

      <div className="flex">
        {/* ── Main content area */}
        <div className="flex-1 min-w-0 max-w-full px-6 py-8 space-y-8" style={{ maxWidth: complete ? "calc(100% - 336px)" : "100%" }}>

          {/* Agent progress — shown while running AND after completion */}
          <AnimatePresence>
            {(processing || complete) && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <h2 className="text-lg font-bold mb-4">
                  {complete ? "🎉 All agents complete!" : "🤖 Agent Pipeline"}
                </h2>
                <AgentProgress
                  projectId={id}
                  initiallyComplete={complete}
                  onComplete={() => refetch()}
                />
                
                {/* Completion Call-to-Action */}
                {complete && variants.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                    className="mt-6 p-6 rounded-2xl bg-gradient-to-br from-emerald-500/10 via-violet-500/10 to-cyan-500/10 border border-emerald-500/20"
                  >
                    <div className="text-center mb-6">
                      <h3 className="text-xl font-bold text-emerald-400 mb-2">🎉 Your designs are ready!</h3>
                      <p className="text-white/60 mb-4">Scroll down to explore your designs, or jump directly to:</p>
                      
                      {/* Scroll indicator */}
                      <motion.div
                        animate={{ y: [0, 8, 0] }}
                        transition={{ repeat: Infinity, duration: 2 }}
                        className="flex justify-center mb-4"
                      >
                        <div className="flex flex-col items-center gap-1 text-white/30">
                          <span className="text-xs">Scroll to explore</span>
                          <div className="w-4 h-6 border border-white/20 rounded-full flex justify-center">
                            <div className="w-1 h-2 bg-white/30 rounded-full mt-1"></div>
                          </div>
                        </div>
                      </motion.div>
                    </div>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                      {/* 3D Viewer Button */}
                      {variants[0]?.model_url && (
                        <Link
                          href={`/project/${id}/viewer?variant=${variants[0].id}${variants[0].model_url ? `&model=${encodeURIComponent(variants[0].model_url)}` : ''}${project?.latitude ? `&lat=${project.latitude}` : ''}${project?.longitude ? `&lng=${project.longitude}` : ''}`}
                          className="group flex flex-col items-center gap-3 p-6 rounded-xl bg-gradient-to-br from-amber-500/15 to-orange-500/15 border border-amber-500/25 hover:border-amber-500/40 transition-all hover:scale-105"
                        >
                          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center text-white text-xl group-hover:scale-110 transition-transform">
                            🏗️
                          </div>
                          <div className="text-center">
                            <h4 className="font-bold text-amber-400 mb-1">3D Structure</h4>
                            <p className="text-xs text-white/50">Interactive 3D viewer with sun simulator</p>
                          </div>
                        </Link>
                      )}
                      
                      {/* Floor Plan Editor Button */}
                      <Link
                        href={`/project/${id}/layout`}
                        className="group flex flex-col items-center gap-3 p-6 rounded-xl bg-gradient-to-br from-violet-500/15 to-cyan-500/15 border border-violet-500/25 hover:border-violet-500/40 transition-all hover:scale-105"
                      >
                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center text-white text-xl group-hover:scale-110 transition-transform">
                          📐
                        </div>
                        <div className="text-center">
                          <h4 className="font-bold text-violet-400 mb-1">Floor Plan Design</h4>
                          <p className="text-xs text-white/50">AI-powered interactive floor plan editor</p>
                        </div>
                      </Link>
                      
                      {/* PDF Export Button */}
                      <button
                        onClick={handleExportPdf}
                        disabled={pdfLoading}
                        className="group flex flex-col items-center gap-3 p-6 rounded-xl bg-gradient-to-br from-emerald-500/15 to-teal-500/15 border border-emerald-500/25 hover:border-emerald-500/40 transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center text-white text-xl group-hover:scale-110 transition-transform">
                          {pdfLoading ? "⏳" : "📄"}
                        </div>
                        <div className="text-center">
                          <h4 className="font-bold text-emerald-400 mb-1">
                            {pdfLoading ? "Generating..." : "Export PDF"}
                          </h4>
                          <p className="text-xs text-white/50">Download complete project report</p>
                        </div>
                      </button>
                    </div>
                    
                    <div className="mt-6 text-center">
                      <p className="text-sm text-white/40">
                        💡 <strong>Tip:</strong> Use the AI Floor Plan Editor to customize your design, then regenerate the 3D model
                      </p>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Pending / error state — show re-run prompt */}
          <AnimatePresence>
            {(project?.status === "pending" || project?.status === "error") && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`p-6 rounded-2xl border text-center ${
                  project.status === "error"
                    ? "border-rose-500/30 bg-rose-500/5"
                    : "border-violet-500/20 bg-violet-500/5"
                }`}
              >
                <div className="text-3xl mb-3">{project.status === "error" ? "⚠️" : "🚀"}</div>
                <h3 className="font-bold text-base mb-1">
                  {project.status === "error" ? "Pipeline encountered an error" : "Pipeline not started yet"}
                </h3>
                <p className="text-sm text-white/40 mb-4">
                  {project.status === "error"
                    ? "Something went wrong. You can re-run the pipeline to try again."
                    : "Click below to launch the 8-agent AI design pipeline for this project."}
                </p>
                <button
                  onClick={handleRerunPipeline}
                  disabled={rerunning}
                  className="px-6 py-2.5 rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 font-bold text-sm transition-all disabled:opacity-50"
                >
                  {rerunning ? "Starting…" : project.status === "error" ? "🔄 Re-run Pipeline" : "▶ Start Pipeline"}
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Tabs */}
          {(complete || variants.length > 0 || pipelineDone) && (
            <div>
              <div className="flex gap-1 border-b border-white/8 mb-6 overflow-x-auto">
                {TABS.map((t) => {
                  if (t.id === "floorplan") {
                    return (
                      <Link key={t.id} href={`/project/${id}/layout`}
                        className="flex items-center gap-1.5 px-4 py-3 text-sm font-semibold whitespace-nowrap transition-all border-b-2 border-transparent text-white/40 hover:text-white hover:border-violet-500/50">
                        {t.icon} {t.label}
                      </Link>
                    );
                  }
                  return (
                    <button key={t.id} id={`tab-${t.id}`} onClick={() => setActiveTab(t.id)}
                      className={`flex items-center gap-1.5 px-4 py-3 text-sm font-semibold whitespace-nowrap transition-all border-b-2 ${
                        activeTab === t.id ? "border-violet-500 text-white" : "border-transparent text-white/40 hover:text-white"
                      }`}>
                      {t.icon} {t.label}
                    </button>
                  );
                })}
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

          {/* Share Button */}
          {complete && project && (
            <ShareButton
              projectId={project.id}
              projectName={project.name}
              initialShareToken={project.share_token}
              initialIsPublic={project.is_public}
            />
          )}
        </div>

        {/* ── Smart Design Sidebar (desktop, completed projects only) */}
        {complete && (
          <motion.aside
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="hidden xl:block w-80 flex-shrink-0 py-8 pr-6 sticky top-[73px] self-start h-[calc(100vh-73px)] overflow-y-auto"
          >
            <SmartDesignPanel
              projectId={id}
              currentDesign={variants.find(v => v.id === selectedVariant)?.dna}
              onDesignUpdate={(update) => console.log("Design update from MCP:", update)}
            />
          </motion.aside>
        )}
      </div>

      {/* ── Floating AI Assistant (always visible) */}
      <AIAssistant projectId={id} />

      {/* ── MCP Status Bar (above AI assistant) */}
      <MCPStatusBar projectId={id} />

      {/* ── Confetti Effect */}
      <ConfettiEffect trigger={showConfetti} />
    </div>
  );
}
