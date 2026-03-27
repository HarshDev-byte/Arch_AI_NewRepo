"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────
interface Project {
  id: string;
  name: string;
  status: "pending" | "processing" | "complete" | "error";
  latitude?: number;
  longitude?: number;
  plot_area_sqm?: number;
  budget_inr?: number;
  floors?: number;
  style_preferences?: string[];
  design_dna?: { green_score?: number; primary_style?: string };
  created_at: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const STATUS_CONFIG = {
  pending:    { label: "Pending",    color: "text-slate-400",  ring: "ring-slate-500/30",  bg: "bg-slate-500/10"  },
  processing: { label: "Processing", color: "text-blue-400",   ring: "ring-blue-500/30",   bg: "bg-blue-500/10"   },
  complete:   { label: "Complete",   color: "text-emerald-400",ring: "ring-emerald-500/30", bg: "bg-emerald-500/10"},
  error:      { label: "Error",      color: "text-rose-400",   ring: "ring-rose-500/30",   bg: "bg-rose-500/10"   },
};

function formatBudget(n?: number) {
  if (!n) return "—";
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(1)}Cr`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(0)}L`;
  return `₹${n.toLocaleString("en-IN")}`;
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const d = Math.floor(diff / 86400000);
  const h = Math.floor(diff / 3600000);
  const m = Math.floor(diff / 60000);
  if (d > 0) return `${d}d ago`;
  if (h > 0) return `${h}h ago`;
  return `${m}m ago`;
}

// ─── Project card ─────────────────────────────────────────────────────────────
function ProjectCard({
  project, index, onDelete, onHide,
}: {
  project: Project;
  index: number;
  onDelete: (id: string) => void;
  onHide: (id: string) => void;
}) {
  const cfg = STATUS_CONFIG[project.status] ?? STATUS_CONFIG.pending;
  const style = project.design_dna?.primary_style?.replace(/_/g, " ") ?? "—";
  const greenScore = project.design_dna?.green_score;
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirming) { setConfirming(true); return; }
    onDelete(project.id);
    setMenuOpen(false);
    setConfirming(false);
  };

  const handleHide = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onHide(project.id);
    setMenuOpen(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ delay: index * 0.06, duration: 0.4 }}
      whileHover={{ y: -3, scale: 1.01 }}
      className="group relative"
    >
      {/* ⋮ menu button — absolute, sits above the Link */}
      <div className="absolute top-4 right-4 z-20">
        <button
          id={`project-menu-${project.id.slice(0, 8)}`}
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); setMenuOpen((o) => !o); setConfirming(false); }}
          className="w-7 h-7 rounded-lg flex items-center justify-center bg-white/0 hover:bg-white/10 text-white/30 hover:text-white transition-all opacity-0 group-hover:opacity-100"
        >
          ⋮
        </button>

        <AnimatePresence>
          {menuOpen && (
            <motion.div
              initial={{ opacity: 0, scale: 0.92, y: -4 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.92, y: -4 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-8 w-44 rounded-xl border border-white/10 bg-[#11161f] shadow-xl shadow-black/40 overflow-hidden z-30"
              onMouseLeave={() => { setMenuOpen(false); setConfirming(false); }}
            >
              <button
                onClick={handleHide}
                className="flex items-center gap-2.5 w-full px-4 py-3 text-sm text-white/70 hover:bg-white/5 hover:text-white transition-colors text-left"
              >
                👁 Hide from list
              </button>
              <div className="h-px bg-white/5" />
              <button
                onClick={handleDelete}
                className={`flex items-center gap-2.5 w-full px-4 py-3 text-sm transition-colors text-left ${
                  confirming
                    ? "bg-rose-500/20 text-rose-300 font-semibold"
                    : "text-rose-400/80 hover:bg-rose-500/10 hover:text-rose-300"
                }`}
              >
                🗑 {confirming ? "Tap again to confirm" : "Delete project"}
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <Link href={`/project/${project.id}`} id={`project-card-${project.id.slice(0, 8)}`}>
        <div className="relative p-6 rounded-2xl border border-white/8 bg-white/3 hover:bg-white/5 hover:border-white/15 transition-all duration-300 overflow-hidden cursor-pointer">
          {/* Subtle gradient */}
          <div className="absolute inset-0 bg-gradient-to-br from-violet-600/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

          {/* Header — right-padded to avoid ⋮ overlap */}
          <div className="relative flex items-start justify-between gap-3 pr-6">
            <div className="min-w-0">
              <h3 className="font-bold text-base truncate">{project.name}</h3>
              <p className="text-xs text-white/40 mt-0.5">{timeAgo(project.created_at)}</p>
            </div>
            <span className={`shrink-0 flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ring-1 ${cfg.ring} ${cfg.bg} ${cfg.color}`}>
              {project.status === "processing" && (
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              )}
              {cfg.label}
            </span>
          </div>

          {/* Stats row */}
          <div className="relative mt-5 grid grid-cols-4 gap-2 text-center">
            {[
              { label: "Area",    value: project.plot_area_sqm ? `${project.plot_area_sqm}m²` : "—" },
              { label: "Floors",  value: project.floors ?? "—" },
              { label: "Budget",  value: formatBudget(project.budget_inr) },
              { label: "Style",   value: style.split(" ").slice(0,2).join(" ") },
            ].map((s) => (
              <div key={s.label} className="bg-white/5 rounded-xl px-2 py-2">
                <p className="text-[10px] text-white/35 uppercase tracking-wider">{s.label}</p>
                <p className="text-xs font-semibold mt-1 truncate">{String(s.value)}</p>
              </div>
            ))}
          </div>

          {/* Green score bar */}
          {greenScore !== undefined && (
            <div className="relative mt-4">
              <div className="flex justify-between text-xs text-white/40 mb-1.5">
                <span>Green Score</span>
                <span className="font-semibold text-emerald-400">{greenScore}/100</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/8">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400"
                  initial={{ width: 0 }}
                  animate={{ width: `${greenScore}%` }}
                  transition={{ delay: index * 0.06 + 0.3, duration: 0.8, ease: "easeOut" }}
                />
              </div>
            </div>
          )}

          {/* View arrow */}
          <div className="relative mt-4 flex justify-end">
            <span className="text-xs text-white/30 group-hover:text-violet-400 transition-colors font-medium">
              View project →
            </span>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="col-span-full flex flex-col items-center justify-center py-24 text-center"
    >
      <div className="text-6xl mb-6">🏗️</div>
      <h3 className="text-xl font-bold mb-2">No projects yet</h3>
      <p className="text-white/45 text-sm mb-8 max-w-sm">
        Start your first AI-designed home. Drop a pin, set your budget, and let 8 agents do the rest.
      </p>
      <Link
        href="/project/new"
        id="dashboard-new-project-empty"
        className="px-6 py-3 rounded-full bg-violet-600 hover:bg-violet-500 font-semibold transition-colors"
      >
        Create your first project
      </Link>
    </motion.div>
  );
}

const HIDDEN_KEY = "archai_hidden_projects";

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { data: projects, isLoading, isError, refetch } = useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/projects`);
      return res.data;
    },
    refetchInterval: 8000,
  });

  const [hiddenIds, setHiddenIds] = useState<Set<string>>(() => {
    if (typeof window === "undefined") return new Set();
    try { return new Set(JSON.parse(localStorage.getItem(HIDDEN_KEY) ?? "[]")); }
    catch { return new Set(); }
  });
  const [showHidden, setShowHidden] = useState(false);

  const persistHidden = (ids: Set<string>) => {
    setHiddenIds(ids);
    localStorage.setItem(HIDDEN_KEY, JSON.stringify([...ids]));
  };

  const handleHide = (id: string) => {
    persistHidden(new Set([...hiddenIds, id]));
  };

  const handleDelete = async (id: string) => {
    try {
      await axios.delete(`${API}/api/projects/${id}`);
      refetch();
    } catch {
      alert("Failed to delete project. Is the backend running?");
    }
  };

  const visible = projects?.filter((p) => showHidden || !hiddenIds.has(p.id)) ?? [];
  const hiddenCount = projects?.filter((p) => hiddenIds.has(p.id)).length ?? 0;

  const counts = {
    total:      visible.length,
    complete:   visible.filter((p) => p.status === "complete").length,
    processing: visible.filter((p) => p.status === "processing").length,
  };


  return (
    <div className="min-h-screen bg-[#080C14] text-white font-sans">

      {/* ── NAV ───────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-40 flex items-center justify-between px-6 py-4 backdrop-blur-xl bg-[#080C14]/80 border-b border-white/5">
        <Link href="/" className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
          ArchAI
        </Link>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="p-2 rounded-lg hover:bg-white/5 text-white/40 hover:text-white transition-colors"
            title="Refresh"
          >
            ↻
          </button>
          <Link
            href="/project/new"
            id="dashboard-new-project"
            className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 font-semibold text-sm transition-all shadow-[0_0_20px_rgba(139,92,246,0.3)] hover:shadow-[0_0_30px_rgba(139,92,246,0.5)]"
          >
            <span>+</span> New Project
          </Link>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-10">

        {/* ── Header ──────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-10"
        >
          <h1 className="text-3xl font-extrabold">Your Projects</h1>
          <p className="mt-2 text-white/45 text-sm">
            AI-generated architectural designs for your plots
          </p>
        </motion.div>

        {/* ── MCP Tools Banner ─────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8 p-4 rounded-2xl border border-violet-500/20 bg-gradient-to-r from-violet-500/8 to-cyan-500/5"
        >
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-violet-500/25 flex-shrink-0">
                <span className="text-base">🔌</span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white">MCP Server Active</span>
                  <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Online
                  </span>
                </div>
                <p className="text-xs text-white/40 mt-0.5">5 AI tools available via Model Context Protocol · Open a project to use them</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {[
                { label: "Analyze", icon: "🧠" },
                { label: "Optimize", icon: "⚡" },
                { label: "Compliance", icon: "🛡️" },
                { label: "Costs", icon: "💰" },
                { label: "Suggest", icon: "✨" },
              ].map((tool) => (
                <span
                  key={tool.label}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 border border-white/8 text-xs font-medium text-white/60"
                >
                  {tool.icon} {tool.label}
                </span>
              ))}
            </div>
          </div>
        </motion.div>

        {/* ── Summary pills ────────────────────────────────────────────── */}
        {!isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-wrap items-center gap-3 mb-8"
          >
            {[
              { label: "Total",      value: counts.total,      color: "border-white/10 text-white/60"        },
              { label: "Complete",   value: counts.complete,   color: "border-emerald-500/30 text-emerald-400"},
              { label: "Processing", value: counts.processing, color: "border-blue-500/30 text-blue-400"     },
            ].map((pill) => (
              <span key={pill.label} className={`px-4 py-1.5 rounded-full border text-xs font-semibold ${pill.color}`}>
                {pill.value} {pill.label}
              </span>
            ))}
            {/* Show hidden toggle */}
            {hiddenCount > 0 && (
              <button
                onClick={() => setShowHidden((v) => !v)}
                className={`ml-auto px-4 py-1.5 rounded-full border text-xs font-semibold transition-colors ${
                  showHidden
                    ? "border-violet-500/50 bg-violet-500/10 text-violet-300"
                    : "border-white/10 text-white/30 hover:text-white/60"
                }`}
              >
                {showHidden ? "👁 Showing hidden" : `Show hidden (${hiddenCount})`}
              </button>
            )}
          </motion.div>
        )}

        {/* ── Grid ─────────────────────────────────────────────────────── */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-52 rounded-2xl bg-white/3 animate-pulse" />
            ))}
          </div>
        ) : isError ? (
          <div className="text-center py-20">
            <p className="text-rose-400 text-sm">Failed to load projects. Is the backend running?</p>
            <button onClick={() => refetch()} className="mt-4 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm transition-colors">
              Retry
            </button>
          </div>
        ) : (
          <AnimatePresence mode="popLayout">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {visible.length > 0
                ? visible.map((p, i) => (
                    <ProjectCard
                      key={p.id}
                      project={p}
                      index={i}
                      onDelete={handleDelete}
                      onHide={handleHide}
                    />
                  ))
                : <EmptyState />}
            </div>
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}