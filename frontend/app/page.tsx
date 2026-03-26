"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, useInView, useMotionValue, useSpring } from "framer-motion";

// ─── Animated counter ────────────────────────────────────────────────────────
function AnimatedNumber({ to, suffix = "" }: { to: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const mv = useMotionValue(0);
  const spring = useSpring(mv, { stiffness: 60, damping: 18 });
  const [display, setDisplay] = useState("0");

  useEffect(() => {
    if (inView) mv.set(to);
  }, [inView, mv, to]);

  useEffect(() =>
    spring.on("change", (v) => setDisplay(Math.round(v).toString())),
    [spring]
  );

  return <span ref={ref}>{display}{suffix}</span>;
}

// ─── Data ─────────────────────────────────────────────────────────────────────
const STATS = [
  { label: "Minutes to first design", value: 10, suffix: "" },
  { label: "Unique variants generated", value: 5, suffix: "" },
  { label: "FSI compliant — always", value: 100, suffix: "%" },
];

const FEATURES = [
  {
    icon: "🌍",
    title: "Geo Intelligence",
    description:
      "OpenStreetMap + Open-Meteo data: zoning, elevation, solar irradiance, and road access — all free, all real.",
    color: "from-emerald-500/20 to-teal-500/10",
    border: "border-emerald-500/30",
  },
  {
    icon: "🧬",
    title: "Design DNA Engine",
    description:
      "28-gene evolutionary algorithm guarantees every design is 100 % unique — no two sites ever get the same result.",
    color: "from-violet-500/20 to-purple-500/10",
    border: "border-violet-500/30",
  },
  {
    icon: "📐",
    title: "AI Floor Plans",
    description:
      "Claude Sonnet generates optimised room-by-room layouts rendered as crisp interactive SVG floor plans.",
    color: "from-blue-500/20 to-cyan-500/10",
    border: "border-blue-500/30",
  },
  {
    icon: "💰",
    title: "Cost & ROI",
    description:
      "Detailed Indian construction cost breakdown (2024 rates) with AI-powered rental yield and appreciation forecast.",
    color: "from-amber-500/20 to-orange-500/10",
    border: "border-amber-500/30",
  },
  {
    icon: "✅",
    title: "Compliance Check",
    description:
      "UDCPR 2020 / NBC 2016 checks for FSI, setbacks, height, parking and green area — before you lift a brick.",
    color: "from-green-500/20 to-lime-500/10",
    border: "border-green-500/30",
  },
  {
    icon: "♻️",
    title: "Sustainability Score",
    description:
      "PVGIS solar analytics, rainwater harvesting potential, ventilation effectiveness — rated Platinum to Bronze.",
    color: "from-teal-500/20 to-green-500/10",
    border: "border-teal-500/30",
  },
  {
    icon: "🏛️",
    title: "3D Babylon.js Viewer",
    description:
      "Photorealistic 3D model from your DNA. Explore every angle in-browser with WebXR VR support on any headset.",
    color: "from-indigo-500/20 to-blue-500/10",
    border: "border-indigo-500/30",
  },
  {
    icon: "🤖",
    title: "8-Agent LangGraph",
    description:
      "A LangGraph pipeline of 8 specialised async agents running in parallel — real-time progress via WebSocket.",
    color: "from-rose-500/20 to-pink-500/10",
    border: "border-rose-500/30",
  },
];

const STYLES = [
  { name: "Contemporary Minimalist", emoji: "🏙️" },
  { name: "Tropical Modern",         emoji: "🌿" },
  { name: "Indo-Contemporary",       emoji: "🕌" },
  { name: "Japanese Wabi-Sabi",      emoji: "⛩️" },
  { name: "Mediterranean",           emoji: "🌊" },
  { name: "Biophilic Organic",       emoji: "🍃" },
];

const STEPS = [
  { n: "01", label: "Drop a pin",        desc: "Click any plot on the map — we auto-fetch zoning, solar & road data." },
  { n: "02", label: "Set requirements",  desc: "Enter area, budget, floors and style preferences." },
  { n: "03", label: "Watch agents work", desc: "8 AI agents run in parallel and stream live progress to your screen." },
  { n: "04", label: "Pick your design",  desc: "Choose from 5 evolutionarily-optimised unique variants." },
];

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function LandingPage() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const fadeUp = {
    hidden: { opacity: 0, y: 32 },
    show:   { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } },
  };

  return (
    <div className="min-h-screen bg-[#080C14] text-white font-sans overflow-x-hidden">

      {/* ── NAV ─────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 inset-x-0 z-50 flex items-center justify-between px-6 py-4 backdrop-blur-xl bg-[#080C14]/70 border-b border-white/5">
        <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
          ArchAI
        </span>
        <div className="flex items-center gap-6 text-sm font-medium text-white/60">
          <a href="#features" className="hover:text-white transition-colors">Features</a>
          <a href="#how"      className="hover:text-white transition-colors">How it works</a>
          <a href="#styles"   className="hover:text-white transition-colors">Styles</a>
          <Link
            href="/dashboard"
            className="px-4 py-2 rounded-full bg-violet-600 hover:bg-violet-500 text-white transition-colors"
          >
            Open App
          </Link>
          <Link href="/settings/api-keys" className="text-sm text-gray-600 hover:text-gray-900">Settings</Link>
        </div>
      </nav>

      {/* ── HERO ────────────────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex flex-col items-center justify-center text-center px-6 pt-24">
        {/* Background blobs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-violet-600/15 blur-[120px]" />
          <div className="absolute top-1/3 right-0 w-[500px] h-[500px] rounded-full bg-cyan-500/10 blur-[100px]" />
          <div className="absolute bottom-0 left-1/4 w-[400px] h-[400px] rounded-full bg-emerald-500/8 blur-[90px]" />
          {/* Grid */}
          <div
            className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage:
                "linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)",
              backgroundSize: "60px 60px",
            }}
          />
        </div>

        {mounted && (
          <motion.div
            initial="hidden"
            animate="show"
            variants={{ show: { transition: { staggerChildren: 0.12 } } }}
            className="relative max-w-5xl"
          >
            <motion.div variants={fadeUp}>
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-violet-500/40 bg-violet-500/10 text-violet-300 text-sm font-medium mb-8">
                <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
                8 AI Agents · Real-time · Free APIs only
              </span>
            </motion.div>

            <motion.h1
              variants={fadeUp}
              className="text-5xl sm:text-7xl font-extrabold leading-[1.05] tracking-tight"
            >
              Design Your{" "}
              <span className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-cyan-400 bg-clip-text text-transparent">
                Dream Home
              </span>
              <br />in Minutes, Not Months
            </motion.h1>

            <motion.p
              variants={fadeUp}
              className="mt-6 text-lg sm:text-xl text-white/55 max-w-2xl mx-auto leading-relaxed"
            >
              Drop a pin on the map. ArchAI&apos;s 8-agent LangGraph pipeline analyses your
              plot, evolves 5 unique architectural designs, checks FSI compliance, estimates
              costs, and renders an interactive 3D model — all in under 10 minutes.
            </motion.p>

            <motion.div variants={fadeUp} className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/project/new"
                id="cta-start-designing"
                className="group inline-flex items-center gap-2 px-8 py-4 rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 font-semibold text-lg shadow-[0_0_40px_rgba(139,92,246,0.4)] transition-all duration-300 hover:shadow-[0_0_60px_rgba(139,92,246,0.6)] hover:-translate-y-0.5"
              >
                Start Designing
                <span className="group-hover:translate-x-1 transition-transform">→</span>
              </Link>
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 px-8 py-4 rounded-full border border-white/15 hover:border-white/30 bg-white/5 hover:bg-white/10 font-semibold text-lg transition-all duration-300"
              >
                View Projects
              </Link>
            </motion.div>
          </motion.div>
        )}

        {/* ── Scroll chevron ──────────────────────────────────────────── */}
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
          animate={{ y: [0, 10, 0] }}
          transition={{ repeat: Infinity, duration: 2 }}
        >
          <div className="w-6 h-10 rounded-full border-2 border-white/20 flex items-start justify-center pt-2">
            <div className="w-1 h-2.5 rounded-full bg-white/40" />
          </div>
        </motion.div>
      </section>

      {/* ── STATS ───────────────────────────────────────────────────────── */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-6">
          {STATS.map((s) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="relative text-center p-8 rounded-2xl border border-white/8 bg-white/3 backdrop-blur-sm overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-violet-500/5 to-transparent" />
              <p className="relative text-5xl font-black bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
                <AnimatedNumber to={s.value} suffix={s.suffix} />
              </p>
              <p className="relative mt-2 text-sm text-white/50 font-medium">{s.label}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── FEATURES ────────────────────────────────────────────────────── */}
      <section id="features" className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl sm:text-5xl font-extrabold">
              Every agent. Every detail.
            </h2>
            <p className="mt-4 text-white/50 max-w-xl mx-auto">
              Eight specialised AI agents work in parallel — each an expert in its domain.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 28 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.07 }}
                whileHover={{ y: -4, scale: 1.02 }}
                className={`relative p-6 rounded-2xl border ${f.border} bg-gradient-to-br ${f.color} backdrop-blur-sm cursor-default`}
              >
                <div className="text-3xl mb-3">{f.icon}</div>
                <h3 className="font-bold text-base mb-2">{f.title}</h3>
                <p className="text-sm text-white/50 leading-relaxed">{f.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ────────────────────────────────────────────────── */}
      <section id="how" className="py-24 px-6 bg-white/[0.02]">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl sm:text-5xl font-extrabold">How it works</h2>
            <p className="mt-4 text-white/50">Four steps. Ten minutes. Five unique designs.</p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {STEPS.map((step, i) => (
              <motion.div
                key={step.n}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="relative"
              >
                {i < STEPS.length - 1 && (
                  <div className="hidden lg:block absolute top-8 left-full w-full h-px bg-gradient-to-r from-violet-500/40 to-transparent z-10" />
                )}
                <div className="p-6 rounded-2xl border border-white/8 bg-white/3 h-full">
                  <span className="text-4xl font-black bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
                    {step.n}
                  </span>
                  <h3 className="mt-3 font-bold text-base">{step.label}</h3>
                  <p className="mt-2 text-sm text-white/50 leading-relaxed">{step.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── STYLES ──────────────────────────────────────────────────────── */}
      <section id="styles" className="py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl sm:text-5xl font-extrabold">15 architectural styles</h2>
            <p className="mt-4 text-white/50">
              Mix and match — the evolutionary engine blends your preferences into a unique DNA.
            </p>
          </motion.div>

          <div className="flex flex-wrap justify-center gap-3">
            {STYLES.map((s, i) => (
              <motion.div
                key={s.name}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
                whileHover={{ scale: 1.05 }}
                className="flex items-center gap-2 px-5 py-3 rounded-full border border-white/10 bg-white/5 text-sm font-medium cursor-default"
              >
                <span>{s.emoji}</span>
                {s.name}
              </motion.div>
            ))}
            <div className="flex items-center gap-2 px-5 py-3 rounded-full border border-violet-500/30 bg-violet-500/10 text-violet-300 text-sm font-medium">
              +9 more →
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA BANNER ──────────────────────────────────────────────────── */}
      <section className="py-24 px-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="max-w-3xl mx-auto text-center p-12 rounded-3xl border border-violet-500/20 bg-gradient-to-br from-violet-900/30 to-fuchsia-900/20 relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-violet-600/10 to-cyan-600/5 pointer-events-none" />
          <h2 className="relative text-4xl font-extrabold">Ready to design?</h2>
          <p className="relative mt-4 text-white/55 text-lg">
            No credit card. No CAD software. Just a plot location and a vision.
          </p>
          <Link
            href="/project/new"
            id="cta-banner-design"
            className="relative mt-8 inline-flex items-center gap-2 px-10 py-4 rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 font-bold text-lg shadow-[0_0_40px_rgba(139,92,246,0.5)] transition-all hover:-translate-y-0.5"
          >
            Start Designing Free →
          </Link>
        </motion.div>
      </section>

      {/* ── FOOTER ──────────────────────────────────────────────────────── */}
      <footer className="py-8 px-6 border-t border-white/5 text-center text-sm text-white/30">
        <p>ArchAI — AI-powered architectural design for India · Built with LangGraph, Claude & Open-Meteo</p>
      </footer>
    </div>
  );
}