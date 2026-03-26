"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

export type AgentStatus = "pending" | "running" | "complete" | "error";

export interface AgentState {
  agent:   string;
  status:  AgentStatus;
  message: string;
  data?:   Record<string, unknown>;
}

interface AgentProgressProps {
  projectId: string;
  onComplete?: (finalState: Record<string, AgentState>) => void;
}

const AGENT_META: Record<string, { icon: string; label: string; description: string }> = {
  geo:            { icon: "🌍", label: "Geo Analysis",    description: "Location, zoning & climate"    },
  design:         { icon: "🧬", label: "Design DNA",      description: "Evolutionary design generation" },
  layout:         { icon: "📐", label: "Floor Plans",     description: "AI-generated room layouts"      },
  cost:           { icon: "💰", label: "Cost Estimation", description: "Construction costs & ROI"        },
  compliance:     { icon: "✅", label: "Compliance",      description: "FSI & building codes"            },
  sustainability: { icon: "♻️", label: "Sustainability",  description: "Solar & green analytics"         },
  threed:         { icon: "🏛️", label: "3D Model",        description: "Babylon.js scene generation"    },
  vr:             { icon: "🥽", label: "VR Experience",   description: "A-Frame WebXR scene"             },
};

const STATUS: Record<AgentStatus, { label: string; ring: string; bg: string; text: string; dotClass: string }> = {
  pending:  { label: "Pending",  ring: "ring-white/10",       bg: "bg-white/5",        text: "text-white/35",    dotClass: "bg-white/20"                      },
  running:  { label: "Running",  ring: "ring-blue-500/40",    bg: "bg-blue-500/10",    text: "text-blue-400",    dotClass: "bg-blue-400 animate-ping"         },
  complete: { label: "Complete", ring: "ring-emerald-500/40", bg: "bg-emerald-500/10", text: "text-emerald-400", dotClass: "bg-emerald-400"                   },
  error:    { label: "Error",    ring: "ring-rose-500/40",    bg: "bg-rose-500/10",    text: "text-rose-400",    dotClass: "bg-rose-400"                      },
};

function AgentCard({ agentKey, state }: { agentKey: string; state: AgentState }) {
  const meta = AGENT_META[agentKey] ?? { icon: "🤖", label: agentKey, description: "" };
  const s    = STATUS[state.status];
  return (
    <motion.div layout initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
      className={`relative p-5 rounded-2xl ring-1 ${s.ring} ${s.bg} transition-all duration-500 overflow-hidden`}>
      {state.status === "running" && (
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute inset-y-0 -left-full w-1/2 bg-gradient-to-r from-transparent via-blue-400/8 to-transparent animate-shimmer" />
        </div>
      )}
      <div className="relative flex items-start gap-3">
        <span className="text-2xl mt-0.5">{meta.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <h3 className="font-bold text-sm">{meta.label}</h3>
            <span className={`flex items-center gap-1.5 text-xs font-semibold ${s.text}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${s.dotClass}`} />
              {s.label}
            </span>
          </div>
          <p className="text-xs text-white/35 mt-0.5">{meta.description}</p>
        </div>
      </div>
      <AnimatePresence mode="wait">
        {state.message && (
          <motion.p key={state.message} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.25 }}
            className="relative mt-3 text-xs text-white/50 pl-2 border-l-2 border-white/10 leading-relaxed">
            {state.message}
          </motion.p>
        )}
      </AnimatePresence>
      {state.status === "complete" && (
        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }}
          className="absolute top-4 right-4 w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center">
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </motion.div>
      )}
    </motion.div>
  );
}

export default function AgentProgress({ projectId, onComplete }: AgentProgressProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [states, setStates] = useState<Record<string, AgentState>>(() =>
    Object.fromEntries(Object.keys(AGENT_META).map((k) => [k, { agent: k, status: "pending" as AgentStatus, message: "" }]))
  );
  const [events, setEvents] = useState<string[]>([]);
  const [done, setDone] = useState(false);
  const statesRef = useRef(states);
  statesRef.current = states;

  const completed = Object.values(states).filter((s) => s.status === "complete").length;
  const total     = Object.keys(AGENT_META).length;
  const progress  = Math.round((completed / total) * 100);

  useEffect(() => {
    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const wsUrl = API.replace(/^http/, "ws") + `/api/ws/${projectId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    ws.onopen  = () => setConnected(true);
    ws.onclose = () => { setConnected(false); wsRef.current = null; };
    ws.onmessage = (evt) => {
      try {
        const payload = JSON.parse(evt.data) as { agent?: string; status?: AgentStatus; message?: string; event?: string; data?: unknown };
        const agentKey = payload.agent ?? "";
        if (agentKey && agentKey in AGENT_META) {
          setStates((prev) => ({
            ...prev,
            [agentKey]: { agent: agentKey, status: payload.status ?? prev[agentKey]?.status ?? "pending", message: payload.message ?? "", data: payload.data as Record<string, unknown> | undefined },
          }));
        }
        setEvents((prev) => [`[${new Date().toLocaleTimeString()}] ${agentKey}: ${payload.message ?? payload.event ?? "update"}`, ...prev.slice(0, 49)]);
        if (payload.event === "pipeline_complete" || (payload.status === "complete" && agentKey === "orchestrator")) {
          setDone(true);
          onComplete?.(statesRef.current);
          ws.close();
        }
      } catch { /* ignore */ }
    };
    return () => { ws.close(); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400 animate-pulse" : "bg-rose-400"}`} />
          <span className="text-xs text-white/50 font-medium">{connected ? "Live stream connected" : "Connecting…"}</span>
        </div>
        <span className="text-xs font-mono text-white/30">{completed}/{total} agents</span>
      </div>

      <div>
        <div className="h-2 rounded-full bg-white/8 overflow-hidden">
          <motion.div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-500"
            animate={{ width: `${progress}%` }} transition={{ duration: 0.5, ease: "easeOut" }} />
        </div>
        <div className="flex justify-between text-[10px] text-white/35 mt-1.5">
          <span>Pipeline progress</span><span>{progress}%</span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {Object.keys(AGENT_META).map((key) => <AgentCard key={key} agentKey={key} state={states[key]} />)}
      </div>

      {events.length > 0 && (
        <div className="rounded-xl bg-white/3 border border-white/6 p-4 max-h-36 overflow-y-auto">
          <p className="text-[10px] font-bold text-white/30 uppercase tracking-widest mb-2">Event log</p>
          {events.map((e, i) => <p key={i} className="text-[11px] font-mono text-white/40 leading-5">{e}</p>)}
        </div>
      )}

      <AnimatePresence>
        {done && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            className="p-5 rounded-2xl bg-emerald-500/10 ring-1 ring-emerald-500/30 text-center">
            <p className="text-emerald-400 font-bold text-lg">🎉 All agents complete!</p>
            <p className="text-white/50 text-sm mt-1">Scroll down to explore your designs.</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
