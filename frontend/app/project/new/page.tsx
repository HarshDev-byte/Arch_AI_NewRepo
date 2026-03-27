"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import dynamic from "next/dynamic";

const PlotSelector = dynamic(() => import("@/components/map/PlotSelector"), { ssr: false });

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Style options ────────────────────────────────────────────────────────────
const STYLES = [
  { id: "contemporary_minimalist", label: "Contemporary Minimalist", emoji: "🏙️" },
  { id: "tropical_modern",         label: "Tropical Modern",         emoji: "🌿" },
  { id: "indo_contemporary",       label: "Indo-Contemporary",       emoji: "🕌" },
  { id: "japanese_wabi_sabi",      label: "Japanese Minimalism",     emoji: "⛩️" },
  { id: "mediterranean_fusion",    label: "Mediterranean",           emoji: "🌊" },
  { id: "biophilic_organic",       label: "Biophilic Organic",       emoji: "🍃" },
  { id: "brutalist_modern",        label: "Brutalist Modern",        emoji: "🏗️" },
  { id: "scandinavian_minimal",    label: "Scandinavian Minimal",    emoji: "❄️" },
];

const UNIT_TYPES = [
  { id: "0-1RK",  label: "0-1 RK",   desc: "Studio / One Room Kitchen",   emoji: "🏠" },
  { id: "1BHK",   label: "1 BHK",    desc: "1 Bedroom, Hall, Kitchen",     emoji: "🛏️" },
  { id: "2BHK",   label: "2 BHK",    desc: "2 Bedrooms, Hall, Kitchen",    emoji: "🛏️🛏️" },
  { id: "3BHK",   label: "3 BHK",    desc: "3 Bedrooms, Hall, Kitchen",    emoji: "🛋️" },
  { id: "4BHK",   label: "4 BHK",    desc: "4 Bedrooms, Hall, Kitchen",    emoji: "🏡" },
  { id: "5BHK+",  label: "5 BHK+",   desc: "5+ Bedrooms — Luxury / Villa", emoji: "🏰" },
] as const;

function formatBudget(v: number) {
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(2)}Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(0)}L`;
  return `₹${v.toLocaleString("en-IN")}`;
}

// ─── Step indicator ───────────────────────────────────────────────────────────
function StepBar({ step }: { step: number }) {
  const steps = ["Plot Location", "Requirements", "Review & Generate"];
  return (
    <div className="flex items-center gap-2 mb-10">
      {steps.map((label, i) => (
        <div key={i} className="flex items-center gap-2">
          <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-all ${
            i === step ? "bg-violet-600 text-white" :
            i < step   ? "bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30" :
                         "bg-white/5 text-white/30"
          }`}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
              i < step ? "bg-emerald-500 text-white" : i === step ? "bg-white text-violet-700" : "bg-white/10 text-white/30"
            }`}>
              {i < step ? "✓" : i + 1}
            </span>
            <span className="hidden sm:inline">{label}</span>
          </div>
          {i < steps.length - 1 && (
            <div className={`flex-1 h-px w-8 ${i < step ? "bg-emerald-500/40" : "bg-white/10"}`} />
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Budget input + slider ────────────────────────────────────────────────────
function BudgetSlider({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const MIN = 1_500_000, MAX = 500_000_000;
  const pct  = Math.min(100, Math.max(0, ((value - MIN) / (MAX - MIN)) * 100));

  const handleType = (raw: string) => {
    const n = Number(raw);
    if (!isNaN(n) && n > 0) onChange(Math.min(MAX, Math.max(MIN, n)));
  };

  return (
    <div className="space-y-3">
      {/* Manual entry row */}
      <div className="flex items-center gap-2">
        <span className="text-white/40 text-sm">₹</span>
        <input
          id="budget-input"
          type="number"
          min={MIN}
          max={MAX}
          step={100_000}
          value={value}
          onChange={(e) => handleType(e.target.value)}
          className="flex-1 px-4 py-3 rounded-xl bg-white/5 border border-white/10 focus:border-violet-500/60 outline-none text-sm text-white transition-colors"
          placeholder="Enter budget in ₹"
        />
        <span className="text-violet-300 font-bold text-sm w-20 text-right shrink-0">
          {formatBudget(value)}
        </span>
      </div>
      {/* Slider */}
      <div>
        <div className="flex justify-between text-[10px] text-white/30 mb-1.5">
          <span>₹15L</span><span>₹50Cr+</span>
        </div>
        <div className="relative h-2 rounded-full bg-white/10">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500"
            style={{ width: `${pct}%` }}
          />
          <input
            id="budget-slider"
            type="range"
            min={MIN} max={MAX} step={100_000}
            value={value}
            onChange={(e) => onChange(Number(e.target.value))}
            className="absolute inset-0 w-full opacity-0 cursor-pointer h-2"
          />
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function NewProjectPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [lat, setLat]     = useState<number | null>(null);
  const [lng, setLng]     = useState<number | null>(null);
  const [area, setArea]   = useState(1000);
  const [budget, setBudget] = useState(5_000_000);
  const [floors, setFloors] = useState(2);
  const [styles, setStyles] = useState<string[]>([]);
  const [name,   setName]  = useState("My ArchAI Project");
  // unitConfigs: { "0-1RK": 2, "2BHK": 1, ... }  — zero means not selected
  const [unitConfigs, setUnitConfigs] = useState<Record<string, number>>({});

  const totalUnits = Object.values(unitConfigs).reduce((s, n) => s + n, 0);

  const changeUnit = (id: string, delta: number) =>
    setUnitConfigs(prev => {
      const next = (prev[id] ?? 0) + delta;
      if (next <= 0) {
        const { [id]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [id]: next };
    });

  const toggleStyle = (id: string) =>
    setStyles((prev) => prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]);

  const handleSubmit = async () => {
    if (!lat || !lng) { setError("Please select a plot location."); return; }
    setSubmitting(true);
    setError("");
    try {
      const { data } = await axios.post(`${API}/api/projects`, {
        name,
        latitude:              lat,
        longitude:             lng,
        plot_area_sqm:         area,
        budget_inr:            budget,
        floors,
        style_preferences:     styles.length ? styles : ["contemporary_minimalist"],
        unit_configurations:   Object.keys(unitConfigs).length ? unitConfigs : undefined,
      });
      // Auto-start generation
      await axios.post(`${API}/api/generate/start/${data.id}`);
      router.push(`/project/${data.id}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to create project. Is the backend running?");
      setSubmitting(false);
    }
  };

  const fadeSlide = {
    initial:  { opacity: 0, x: 20  },
    animate:  { opacity: 1, x: 0   },
    exit:     { opacity: 0, x: -20 },
    transition: { duration: 0.3 },
  };

  return (
    <div className="min-h-screen bg-[#080C14] text-white font-sans">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-white/5">
        <a href="/" className="text-xl font-extrabold bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">ArchAI</a>
        <span className="text-sm text-white/40">New Project Wizard</span>
      </nav>

      <div className="max-w-3xl mx-auto px-6 py-10">
        <StepBar step={step} />

        <AnimatePresence mode="wait">
          {/* ── STEP 0: Plot ─────────────────────────────────────────── */}
          {step === 0 && (
            <motion.div key="step0" {...fadeSlide} className="space-y-6">
              <div>
                <h2 className="text-2xl font-extrabold">Select your plot</h2>
                <p className="text-white/45 text-sm mt-1">Click the map to drop a pin on your land parcel.</p>
              </div>
              <PlotSelector onSelect={(la, ln) => { setLat(la); setLng(ln); }} selectedLat={lat ?? undefined} selectedLng={lng ?? undefined} />
              {lat && lng && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 ring-1 ring-emerald-500/30">
                  <span className="text-2xl">📍</span>
                  <div>
                    <p className="text-sm font-semibold text-emerald-400">Plot selected</p>
                    <p className="text-xs text-white/50 font-mono">{lat.toFixed(6)}, {lng.toFixed(6)}</p>
                  </div>
                </motion.div>
              )}
              <button id="step0-next" disabled={!lat} onClick={() => setStep(1)}
                className="w-full py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 font-bold text-sm disabled:opacity-40 disabled:cursor-not-allowed transition-all">
                Analyse this plot →
              </button>
            </motion.div>
          )}

          {/* ── STEP 1: Requirements ─────────────────────────────────── */}
          {step === 1 && (
            <motion.div key="step1" {...fadeSlide} className="space-y-8">
              <div>
                <h2 className="text-2xl font-extrabold">Set requirements</h2>
                <p className="text-white/45 text-sm mt-1">Tell us about your project.</p>
              </div>

              {/* Project name */}
              <div>
                <label className="block text-xs font-semibold text-white/50 uppercase tracking-wider mb-2">Project name</label>
                <input id="input-name" value={name} onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 focus:border-violet-500/60 outline-none text-sm transition-colors" />
              </div>

              {/* Area */}
              <div>
                <label className="block text-xs font-semibold text-white/50 uppercase tracking-wider mb-2">Plot area (sqm)</label>
                <div className="flex items-center gap-3">
                  <input id="input-area" type="number" min={50} max={10000} value={area} onChange={(e) => setArea(Number(e.target.value))}
                    className="flex-1 px-4 py-3 rounded-xl bg-white/5 border border-white/10 focus:border-violet-500/60 outline-none text-sm transition-colors" />
                  <span className="text-white/40 text-sm w-16">{(area * 10.764).toFixed(0)} sqft</span>
                </div>
              </div>

              {/* Budget */}
              <div>
                <label className="block text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">Budget</label>
                <BudgetSlider value={budget} onChange={setBudget} />
              </div>

              {/* Unit configuration */}
              <div>
                <label className="block text-xs font-semibold text-white/50 uppercase tracking-wider mb-1">
                  Unit configuration
                </label>
                <p className="text-xs text-white/30 mb-3">Select the mix of units to build. Add multiples of the same type.</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  {UNIT_TYPES.map((u) => {
                    const count = unitConfigs[u.id] ?? 0;
                    const selected = count > 0;
                    return (
                      <div
                        key={u.id}
                        className={`p-3 rounded-xl border transition-all ${
                          selected
                            ? "border-violet-500/50 bg-violet-500/10"
                            : "border-white/8 bg-white/3"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-1 mb-1">
                          <div>
                            <div className="text-lg leading-none mb-0.5">{u.emoji}</div>
                            <div className="text-xs font-bold text-white/90">{u.label}</div>
                            <div className="text-[10px] text-white/35 leading-tight mt-0.5">{u.desc}</div>
                          </div>
                          {/* counter */}
                          <div className="flex items-center gap-1 shrink-0">
                            {selected && (
                              <>
                                <button
                                  id={`unit-minus-${u.id}`}
                                  onClick={() => changeUnit(u.id, -1)}
                                  className="w-6 h-6 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm font-bold flex items-center justify-center transition-colors"
                                >
                                  −
                                </button>
                                <span className="text-sm font-bold text-violet-300 w-4 text-center">{count}</span>
                              </>
                            )}
                            <button
                              id={`unit-add-${u.id}`}
                              onClick={() => changeUnit(u.id, 1)}
                              className="w-6 h-6 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-bold flex items-center justify-center transition-colors"
                            >
                              +
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                {totalUnits > 0 && (
                  <p className="text-xs text-violet-300 mt-2">
                    {totalUnits} unit{totalUnits !== 1 ? "s" : ""} selected ·{" "}
                    {Object.entries(unitConfigs).map(([k, v]) => `${v}×${k}`).join(", ")}
                  </p>
                )}
              </div>

              {/* Floors */}
              <div>
                <label className="block text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">
                  Number of floors
                </label>
                <input
                  id="input-floors"
                  type="number"
                  min={1}
                  max={50}
                  value={floors}
                  onChange={(e) => setFloors(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
                  className="w-32 px-4 py-3 rounded-xl bg-white/5 border border-white/10 focus:border-violet-500/60 outline-none text-sm text-white transition-colors"
                />
              </div>

              {/* Styles */}
              <div>
                <label className="block text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">
                  Architectural style preferences <span className="text-white/30">(choose up to 3)</span>
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  {STYLES.map((s) => {
                    const sel = styles.includes(s.id);
                    return (
                      <button key={s.id} id={`style-${s.id}`} onClick={() => toggleStyle(s.id)}
                        disabled={!sel && styles.length >= 3}
                        className={`p-3 rounded-xl text-left transition-all border ${
                          sel ? "border-violet-500/50 bg-violet-500/15 text-white" : "border-white/8 bg-white/3 text-white/50 hover:border-white/20 disabled:opacity-30"
                        }`}>
                        <div className="text-xl mb-1">{s.emoji}</div>
                        <div className="text-xs font-semibold leading-tight">{s.label}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex gap-3">
                <button onClick={() => setStep(0)} className="flex-1 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-sm font-semibold transition-colors">← Back</button>
                <button id="step1-next" onClick={() => setStep(2)}
                  className="flex-[2] py-3 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 font-bold text-sm transition-all">
                  Review →
                </button>
              </div>
            </motion.div>
          )}

          {/* ── STEP 2: Review ───────────────────────────────────────── */}
          {step === 2 && (
            <motion.div key="step2" {...fadeSlide} className="space-y-6">
              <div>
                <h2 className="text-2xl font-extrabold">Review & generate</h2>
                <p className="text-white/45 text-sm mt-1">Confirm details and launch the 8-agent pipeline.</p>
              </div>

              <div className="p-6 rounded-2xl border border-white/8 bg-white/3 space-y-4">
                {[
                  { label: "Project name",   value: name },
                  { label: "Location",       value: lat && lng ? `${lat.toFixed(5)}, ${lng.toFixed(5)}` : "—" },
                  { label: "Plot area",      value: `${area} m² (${(area * 10.764).toFixed(0)} sqft)` },
                  { label: "Budget",         value: formatBudget(budget) },
                  { label: "Floors",         value: `${floors} floor${floors !== 1 ? "s" : ""}` },
                  { label: "Unit mix",       value: totalUnits > 0 ? Object.entries(unitConfigs).map(([k, v]) => `${v}×${k}`).join(", ") : "Not specified" },
                  { label: "Styles",         value: styles.length ? styles.map((s) => STYLES.find((x) => x.id === s)?.label).join(", ") : "Default (Contemporary)" },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between gap-4 text-sm">
                    <span className="text-white/40">{row.label}</span>
                    <span className="text-right font-medium">{row.value}</span>
                  </div>
                ))}
              </div>

              <div className="p-4 rounded-xl bg-violet-500/10 ring-1 ring-violet-500/20 text-sm text-violet-300">
                🤖 <strong>8 AI agents will run in parallel</strong>: Geo analysis → Design DNA evolution → Floor plans, Costs, Compliance & Sustainability → 3D model → VR scene
              </div>

              {error && (
                <div className="p-4 rounded-xl bg-rose-500/10 ring-1 ring-rose-500/30 text-rose-400 text-sm">{error}</div>
              )}

              <div className="flex gap-3">
                <button onClick={() => setStep(1)} className="flex-1 py-3.5 rounded-xl bg-white/5 hover:bg-white/10 font-semibold text-sm transition-colors">← Back</button>
                <button id="btn-generate" onClick={handleSubmit} disabled={submitting}
                  className="flex-[2] py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 font-bold text-sm disabled:opacity-60 transition-all shadow-[0_0_24px_rgba(139,92,246,0.4)]">
                  {submitting ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Launching pipeline…
                    </span>
                  ) : "🚀 Generate My Designs"}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
