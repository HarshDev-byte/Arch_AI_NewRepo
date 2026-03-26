"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ImageData {
  exterior_b64?:    string | null;
  interior_b64?:    string | null;
  aerial_b64?:      string | null;
  exterior_url?:    string | null;
  interior_url?:    string | null;
  aerial_url?:      string | null;
  exterior_prompt?: string | null;
  interior_prompt?: string | null;
  aerial_prompt?:   string | null;
  variant_id?:      string;
}

interface Props {
  variantId:   string;
  projectId?:  string;
  initialData?: ImageData;
  apiBase?:    string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function imgSrc(b64?: string | null, url?: string | null): string | null {
  if (url)  return url;
  if (b64)  return `data:image/png;base64,${b64}`;
  return null;
}

function downloadImage(src: string, filename: string) {
  const a   = document.createElement("a");
  a.href    = src;
  a.download = filename;
  a.click();
}

function truncate(str: string | null | undefined, max = 140): string {
  if (!str) return "";
  return str.length > max ? str.slice(0, max) + "…" : str;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function ImageCard({
  label,
  icon,
  src,
  prompt,
  filename,
  loading,
}: {
  label:    string;
  icon:     string;
  src:      string | null;
  prompt?:  string | null;
  filename: string;
  loading:  boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="rounded-2xl overflow-hidden flex flex-col"
      style={{
        background: "rgba(255,255,255,0.04)",
        border:     "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {/* Image area */}
      <div className="relative aspect-[3/2] overflow-hidden bg-black/40">
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div
              key="skeleton"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex flex-col items-center justify-center gap-3"
              style={{ background: "rgba(0,0,0,0.5)" }}
            >
              {/* Animated shimmer */}
              <motion.div
                className="w-12 h-12 rounded-full"
                style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}
                animate={{ scale: [1, 1.15, 1], opacity: [0.6, 1, 0.6] }}
                transition={{ duration: 1.4, repeat: Infinity }}
              />
              <p className="text-white/50 text-xs">Generating {label.toLowerCase()}…</p>
              <p className="text-white/30 text-[10px]">This may take 30–60 seconds</p>
            </motion.div>
          ) : src ? (
            <motion.img
              key="image"
              src={src}
              alt={label}
              initial={{ opacity: 0, scale: 1.04 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4 }}
              className="w-full h-full object-cover"
            />
          ) : (
            <motion.div
              key="placeholder"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="absolute inset-0 flex flex-col items-center justify-center gap-2"
            >
              <span className="text-3xl opacity-30">{icon}</span>
              <p className="text-white/25 text-xs">No image yet</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Download button overlay */}
        {src && !loading && (
          <button
            id={`download-${filename}`}
            onClick={() => downloadImage(src, filename)}
            className="absolute top-2 right-2 flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-[11px] font-medium transition-all"
            style={{
              background: "rgba(0,0,0,0.65)",
              border:     "1px solid rgba(255,255,255,0.15)",
              color:      "rgba(255,255,255,0.85)",
              backdropFilter: "blur(8px)",
            }}
          >
            ↓ Save
          </button>
        )}

        {/* Label badge */}
        <div
          className="absolute bottom-2 left-2 flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[11px] font-medium"
          style={{
            background: "rgba(0,0,0,0.65)",
            border:     "1px solid rgba(255,255,255,0.10)",
            color:      "rgba(255,255,255,0.75)",
            backdropFilter: "blur(8px)",
          }}
        >
          {icon} {label}
        </div>
      </div>

      {/* Prompt inspiration */}
      {prompt && (
        <div className="px-3 py-2.5">
          <button
            onClick={() => setExpanded((e) => !e)}
            className="w-full text-left"
          >
            <p className="text-[10px] text-white/35 uppercase tracking-wider font-semibold mb-1">
              Inspiration prompt {expanded ? "▲" : "▼"}
            </p>
            <AnimatePresence>
              {expanded ? (
                <motion.p
                  key="full"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="text-[11px] text-white/50 leading-relaxed"
                >
                  {prompt}
                </motion.p>
              ) : (
                <p className="text-[11px] text-white/40 leading-relaxed">
                  {truncate(prompt)}
                </p>
              )}
            </AnimatePresence>
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function MoodBoard({ variantId, initialData, apiBase = "" }: Props) {
  const [data,      setData]      = useState<ImageData>(initialData ?? {});
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState<string | null>(null);
  const [generated, setGenerated] = useState(!!initialData?.exterior_b64 || !!initialData?.exterior_url);

  const generate = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${apiBase}/api/images/${variantId}/generate`, {
        method: "POST",
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }

      const result: ImageData = await res.json();
      setData(result);
      setGenerated(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed.");
    } finally {
      setLoading(false);
    }
  }, [variantId, apiBase]);

  const cards = [
    {
      key:      "exterior",
      label:    "Exterior",
      icon:     "🏛️",
      src:      imgSrc(data.exterior_b64, data.exterior_url),
      prompt:   data.exterior_prompt,
      filename: `${variantId}-exterior.png`,
    },
    {
      key:      "interior",
      label:    "Interior",
      icon:     "🛋️",
      src:      imgSrc(data.interior_b64, data.interior_url),
      prompt:   data.interior_prompt,
      filename: `${variantId}-interior.png`,
    },
    {
      key:      "aerial",
      label:    "Aerial",
      icon:     "🛰️",
      src:      imgSrc(data.aerial_b64, data.aerial_url),
      prompt:   data.aerial_prompt,
      filename: `${variantId}-aerial.png`,
    },
  ];

  return (
    <div
      id="mood-board-panel"
      className="rounded-2xl overflow-hidden"
      style={{
        background:     "rgba(255,255,255,0.02)",
        border:         "1px solid rgba(255,255,255,0.07)",
        backdropFilter: "blur(12px)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-3.5"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}
      >
        <div className="flex items-center gap-2.5">
          <span
            className="w-8 h-8 rounded-xl flex items-center justify-center"
            style={{ background: "linear-gradient(135deg,#f59e0b,#ef4444)" }}
          >
            🎨
          </span>
          <div>
            <p className="text-[14px] font-semibold text-white">AI Mood Board</p>
            <p className="text-[10px] text-white/40">
              Stable Diffusion XL · Photorealistic renders
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {generated && (
            <span className="text-[10px] text-white/30">
              3 images
            </span>
          )}
          <button
            id="moodboard-generate-btn"
            onClick={generate}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-[13px] font-medium transition-all disabled:opacity-50"
            style={{
              background: loading
                ? "rgba(255,255,255,0.06)"
                : "linear-gradient(135deg,#f59e0b,#ef4444)",
              color: "white",
              border: loading ? "1px solid rgba(255,255,255,0.1)" : "none",
            }}
            onMouseEnter={(e) => {
              if (!loading)
                (e.currentTarget as HTMLButtonElement).style.opacity = "0.88";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.opacity = "1";
            }}
          >
            {loading ? (
              <>
                <span className="w-3.5 h-3.5 border border-white border-t-transparent rounded-full animate-spin" />
                Generating…
              </>
            ) : generated ? (
              <>🔄 Regenerate</>
            ) : (
              <>✨ Generate Renders</>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-5">
        {/* Error banner */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mb-4 px-4 py-3 rounded-xl text-[13px]"
              style={{
                background: "rgba(239,68,68,0.12)",
                border:     "1px solid rgba(239,68,68,0.3)",
                color:      "#fca5a5",
              }}
            >
              ⚠️ {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty state */}
        {!generated && !loading && (
          <div className="flex flex-col items-center justify-center py-12 gap-4">
            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 2.5, repeat: Infinity }}
              className="text-5xl"
            >
              🎨
            </motion.div>
            <p className="text-white/50 text-sm text-center max-w-xs">
              Generate AI photorealistic renders of your design — exterior, interior, and aerial views.
            </p>
            <p className="text-white/25 text-[11px] text-center max-w-xs">
              Powered by Stable Diffusion XL · Requires HF_API_KEY in .env (free)
            </p>
          </div>
        )}

        {/* Image grid */}
        {(generated || loading) && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {cards.map(({ key, label, icon, src, prompt, filename }) => (
              <ImageCard
                key={key}
                label={label}
                icon={icon}
                src={loading ? null : src}
                prompt={prompt}
                filename={filename}
                loading={loading}
              />
            ))}
          </div>
        )}

        {/* Attribution */}
        {generated && !loading && (
          <p className="mt-4 text-center text-[10px] text-white/20">
            Images generated via Hugging Face Inference API (Stable Diffusion XL) ·{" "}
            <a
              href="https://huggingface.co/settings/tokens"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-white/40 transition-colors"
            >
              Get your free token
            </a>
          </p>
        )}
      </div>
    </div>
  );
}
