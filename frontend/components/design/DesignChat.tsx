"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Message {
  id:        string;
  role:      "user" | "assistant";
  content:   string;
  intent?:   string;
  mutations?: Record<string, unknown>;
  agentsRerun?: string[];
  ts:        string;
}

interface ChatResult {
  explanation:       string;
  intent:            string;
  updated_dna:       Record<string, unknown>;
  mutations_applied: Record<string, unknown>;
  agents_rerun:      string[];
  agent_results:     Record<string, unknown>;
  variant_id:        string;
}

interface Props {
  projectId: string;
  variantId: string;
  onUpdate?: (result: ChatResult) => void;
  apiBase?: string;
}

// ─── Quick command suggestions ────────────────────────────────────────────────

const QUICK_COMMANDS = [
  { label: "More minimalist",     icon: "◻️" },
  { label: "Add rooftop garden",  icon: "🌿" },
  { label: "Japanese influence",  icon: "⛩️" },
  { label: "Larger windows",      icon: "🪟" },
  { label: "Add a courtyard",     icon: "🏛️" },
  { label: "Butterfly roof",      icon: "🦋" },
  { label: "Eco-friendly",        icon: "♻️" },
  { label: "Double-height living",icon: "🏠" },
];

// Human-readable field labels for mutation summary
const FIELD_LABELS: Record<string, string> = {
  primary_style:                "primary style",
  secondary_style:              "secondary style",
  building_form:                "building form",
  roof_form:                    "roof",
  facade_material_palette:      "materials",
  facade_pattern:               "facade pattern",
  window_style:                 "window style",
  window_wall_ratio:            "window ratio",
  floor_height:                 "floor height",
  has_courtyard:                "courtyard",
  double_height_spaces:         "double-height spaces",
  rooftop_utility:              "rooftop",
  natural_ventilation_strategy: "ventilation",
  shading_coefficient:          "shading",
};

function formatMutations(mutations: Record<string, unknown>): string[] {
  return Object.entries(mutations)
    .filter(([, v]) => v !== null && v !== undefined)
    .map(([k, v]) => {
      const label = FIELD_LABELS[k] ?? k.replace(/_/g, " ");
      const val   = typeof v === "boolean" ? (v ? "yes" : "no") : String(v);
      return `${label}: ${val}`;
    });
}

const INTENT_COLOR: Record<string, string> = {
  modify_style:          "rgba(139,92,246,0.15)",
  modify_form:           "rgba(59,130,246,0.15)",
  modify_materials:      "rgba(245,158,11,0.15)",
  modify_spaces:         "rgba(16,185,129,0.15)",
  modify_sustainability: "rgba(34,197,94,0.15)",
  rerun_full:            "rgba(239,68,68,0.15)",
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function AgentBadge({ name }: { name: string }) {
  const colors: Record<string, string> = {
    layout:         "bg-blue-500/20 text-blue-300",
    compliance:     "bg-amber-500/20 text-amber-300",
    sustainability: "bg-green-500/20 text-green-300",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium ${colors[name] ?? "bg-white/10 text-white/60"}`}>
      {name}
    </span>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser     = msg.role === "user";
  const intentBg   = msg.intent ? INTENT_COLOR[msg.intent] : undefined;
  const mutList    = msg.mutations ? formatMutations(msg.mutations) : [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center text-[10px] mr-2 mt-1 flex-shrink-0">
          ✦
        </div>
      )}
      <div className="max-w-[82%] space-y-1.5">
        <div
          className="rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed"
          style={{
            background: isUser
              ? "rgba(124,58,237,0.25)"
              : (intentBg ?? "rgba(255,255,255,0.06)"),
            border: `1px solid ${isUser ? "rgba(124,58,237,0.4)" : "rgba(255,255,255,0.08)"}`,
            color: "rgba(255,255,255,0.92)",
          }}
        >
          {msg.content}
        </div>

        {/* Mutation summary */}
        {mutList.length > 0 && (
          <div
            className="rounded-xl px-3 py-2 text-[11px] leading-relaxed"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}
          >
            <span className="text-white/40 uppercase tracking-wider text-[9px] font-semibold">
              Changes applied
            </span>
            <ul className="mt-1 space-y-0.5">
              {mutList.map((m) => (
                <li key={m} className="text-cyan-300/80">• {m}</li>
              ))}
            </ul>
            {msg.agentsRerun && msg.agentsRerun.length > 0 && (
              <div className="mt-2 flex gap-1 flex-wrap">
                {msg.agentsRerun.map((a) => <AgentBadge key={a} name={a} />)}
                <span className="text-white/30 text-[10px] self-center ml-1">re-run</span>
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}

function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex items-center gap-2 text-white/40 text-sm px-1"
    >
      <div className="w-6 h-6 rounded-full bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center text-[10px]">✦</div>
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-violet-400"
            animate={{ y: [0, -4, 0] }}
            transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.12 }}
          />
        ))}
      </div>
      <span className="text-[12px]">Updating design…</span>
    </motion.div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function DesignChat({ projectId, variantId, onUpdate, apiBase = "" }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id:      "welcome",
      role:    "assistant",
      content: "I can modify this design with natural language. Try: \"Make it more minimalist\", \"Add a rooftop garden\", or \"Give it a Japanese influence\".",
      ts:      new Date().toISOString(),
    },
  ]);
  const [input,   setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setError(null);
    const userMsg: Message = {
      id:      crypto.randomUUID(),
      role:    "user",
      content: trimmed,
      ts:      new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${apiBase}/api/chat/${projectId}/message`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ message: trimmed, variant_id: variantId }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }

      const result: ChatResult = await res.json();

      const assistantMsg: Message = {
        id:          crypto.randomUUID(),
        role:        "assistant",
        content:     result.explanation,
        intent:      result.intent,
        mutations:   result.mutations_applied,
        agentsRerun: result.agents_rerun,
        ts:          new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      onUpdate?.(result);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Something went wrong.";
      setError(msg);
      setMessages((prev) => [
        ...prev,
        {
          id:      crypto.randomUUID(),
          role:    "assistant",
          content: `⚠️ ${msg}`,
          ts:      new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [loading, projectId, variantId, apiBase, onUpdate]);

  const handleKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div
      id="design-chat-panel"
      className="flex flex-col h-[520px] rounded-2xl overflow-hidden"
      style={{
        background: "rgba(255,255,255,0.03)",
        border:     "1px solid rgba(255,255,255,0.08)",
        backdropFilter: "blur(12px)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 flex-shrink-0"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}
      >
        <div className="flex items-center gap-2">
          <span
            className="w-7 h-7 rounded-lg flex items-center justify-center text-sm"
            style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}
          >
            ✦
          </span>
          <div>
            <p className="text-[13px] font-semibold text-white">Design Assistant</p>
            <p className="text-[10px] text-white/40">AI-powered design mutation</p>
          </div>
        </div>
        <span
          className="text-[10px] px-2 py-0.5 rounded-full font-medium"
          style={{ background: "rgba(139,92,246,0.2)", color: "#a78bfa" }}
        >
          Live
        </span>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 scroll-smooth">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} />
          ))}
        </AnimatePresence>

        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Quick commands */}
      <div
        className="px-4 pt-3 pb-2 flex-shrink-0"
        style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
      >
        <p className="text-[10px] text-white/30 uppercase tracking-wider mb-2 font-medium">Quick commands</p>
        <div className="flex gap-2 flex-wrap">
          {QUICK_COMMANDS.slice(0, 4).map(({ label, icon }) => (
            <button
              key={label}
              id={`quick-cmd-${label.toLowerCase().replace(/\s+/g, "-")}`}
              onClick={() => sendMessage(label)}
              disabled={loading}
              className="text-[11px] flex items-center gap-1 px-2.5 py-1 rounded-full transition-all duration-150 disabled:opacity-40"
              style={{
                background: "rgba(255,255,255,0.05)",
                border:     "1px solid rgba(255,255,255,0.09)",
                color:      "rgba(255,255,255,0.6)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = "rgba(124,58,237,0.2)";
                (e.currentTarget as HTMLButtonElement).style.color      = "#c4b5fd";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.05)";
                (e.currentTarget as HTMLButtonElement).style.color      = "rgba(255,255,255,0.6)";
              }}
            >
              <span>{icon}</span>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Input bar */}
      <div
        className="px-4 pb-4 flex-shrink-0"
      >
        <div
          className="flex items-center gap-2 rounded-xl px-3 py-2 transition-all"
          style={{
            background: "rgba(255,255,255,0.05)",
            border:     error ? "1px solid rgba(239,68,68,0.5)" : "1px solid rgba(255,255,255,0.10)",
          }}
        >
          <input
            ref={inputRef}
            id="design-chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Describe a change… (Enter to send)"
            disabled={loading}
            className="flex-1 bg-transparent text-[13px] text-white placeholder:text-white/25 outline-none disabled:opacity-50"
          />
          <button
            id="design-chat-send"
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-sm transition-all disabled:opacity-30"
            style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}
          >
            {loading ? (
              <span className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              "↑"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
