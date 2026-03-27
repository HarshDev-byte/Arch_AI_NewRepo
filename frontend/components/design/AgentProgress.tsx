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
  /** Pass true when the project status is already "complete" on page load.
   *  Skips WebSocket and pre-fills every agent card as complete. */
  initiallyComplete?: boolean;
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

// ── Render a single data value nicely ─────────────────────────────────────────
function DataValue({ v }: { v: unknown }) {
  if (v === null || v === undefined) return <span className="text-white/20">—</span>;
  if (typeof v === "boolean") return <span className={v ? "text-emerald-400" : "text-rose-400"}>{v ? "Yes" : "No"}</span>;
  if (typeof v === "number") return <span className="text-violet-300 font-mono">{v.toLocaleString("en-IN")}</span>;
  if (typeof v === "string") return <span className="text-white/70">{v}</span>;
  if (Array.isArray(v)) {
    if (v.length === 0) return <span className="text-white/20">Empty</span>;
    return (
      <ul className="list-none space-y-0.5 mt-0.5">
        {v.slice(0, 6).map((item, i) => (
          <li key={i} className="text-white/60 before:content-['•'] before:mr-1.5 before:text-white/30">
            {typeof item === "object" ? JSON.stringify(item) : String(item)}
          </li>
        ))}
        {v.length > 6 && <li className="text-white/30">+{v.length - 6} more…</li>}
      </ul>
    );
  }
  if (typeof v === "object") {
    const entries = Object.entries(v as Record<string, unknown>).slice(0, 8);
    return (
      <div className="space-y-0.5 mt-0.5">
        {entries.map(([k, val]) => (
          <div key={k} className="flex gap-2 text-[10px]">
            <span className="text-white/30 shrink-0 capitalize">{k.replace(/_/g, " ")}:</span>
            <span className="text-white/60 truncate">{typeof val === "object" ? JSON.stringify(val) : String(val)}</span>
          </div>
        ))}
      </div>
    );
  }
  return <span className="text-white/60">{String(v)}</span>;
}

function AgentCard({ agentKey, state }: { agentKey: string; state: AgentState }) {
  const meta = AGENT_META[agentKey] ?? { icon: "🤖", label: agentKey, description: "" };
  const s    = STATUS[state.status];
  const [open, setOpen] = useState(false);
  const clickable = state.status === "complete" || state.status === "error";

  const dataEntries = state.data ? Object.entries(state.data) : [];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={clickable ? { y: -2, scale: 1.02 } : {}}
      onClick={() => clickable && setOpen((o) => !o)}
      className={`relative rounded-2xl ring-1 ${s.ring} ${s.bg} transition-all duration-300 overflow-hidden
        ${clickable ? "cursor-pointer" : "cursor-default"}
        ${open ? "shadow-lg shadow-black/30" : ""}
      `}
    >
      {/* Hover glow for complete cards */}
      {clickable && (
        <div className={`absolute inset-0 opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none
          ${state.status === "complete"
            ? "bg-gradient-to-br from-emerald-500/5 to-transparent"
            : "bg-gradient-to-br from-rose-500/5 to-transparent"
          }`}
        />
      )}

      {/* Running shimmer */}
      {state.status === "running" && (
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute inset-y-0 -left-full w-1/2 bg-gradient-to-r from-transparent via-blue-400/8 to-transparent animate-shimmer" />
        </div>
      )}

      {/* Card header */}
      <div className="relative p-5">
        <div className="flex items-start gap-3">
          <span className="text-2xl mt-0.5">{meta.icon}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <h3 className="font-bold text-sm">{meta.label}</h3>
              <div className="flex items-center gap-2">
                <span className={`flex items-center gap-1.5 text-xs font-semibold ${s.text}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${s.dotClass}`} />
                  {s.label}
                </span>
                {/* Chevron */}
                {clickable && (
                  <motion.span
                    animate={{ rotate: open ? 180 : 0 }}
                    transition={{ duration: 0.2 }}
                    className="text-white/25 text-xs leading-none"
                  >
                    ▾
                  </motion.span>
                )}
              </div>
            </div>
            <p className="text-xs text-white/35 mt-0.5">{meta.description}</p>
          </div>
        </div>

        {/* Summary message */}
        <AnimatePresence mode="wait">
          {state.message && state.message !== "Completed" && (
            <motion.p
              key={state.message}
              initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.25 }}
              className="relative mt-3 text-xs text-white/50 pl-2 border-l-2 border-white/10 leading-relaxed"
            >
              {state.message}
            </motion.p>
          )}
        </AnimatePresence>

        {/* Complete checkmark */}
        {state.status === "complete" && (
          <motion.div
            initial={{ scale: 0 }} animate={{ scale: 1 }}
            className="absolute top-4 right-4 w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center"
          >
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </motion.div>
        )}
      </div>

      {/* Expanded detail panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 border-t border-white/8 pt-4 space-y-2">
              {dataEntries.length > 0 ? (
                dataEntries.map(([key, val]) => (
                  <div key={key} className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
                    <span className="text-white/35 capitalize pt-0.5 shrink-0">
                      {key.replace(/_/g, " ")}
                    </span>
                    <DataValue v={val} />
                  </div>
                ))
              ) : (
                <p className="text-xs text-white/30 italic">
                  {state.status === "complete" ? "Agent completed — no structured data captured." : state.message}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function AgentProgress({ projectId, onComplete, initiallyComplete = false }: AgentProgressProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [usePolling, setUsePolling] = useState(false);

  // If the project is already complete, prefill every agent as "complete"
  const makeInitialStates = () =>
    Object.fromEntries(
      Object.keys(AGENT_META).map((k) => [
        k,
        {
          agent: k,
          status: (initiallyComplete ? "complete" : "pending") as AgentStatus,
          message: initiallyComplete ? "Completed" : "",
        },
      ])
    );

  const [states, setStates] = useState<Record<string, AgentState>>(makeInitialStates);
  const [events, setEvents] = useState<string[]>([]);
  const [done, setDone] = useState(initiallyComplete);   // already done if pre-complete
  const statesRef = useRef(states);
  statesRef.current = states;

  const completed = Object.values(states).filter((s) => s.status === "complete").length;
  const total     = Object.keys(AGENT_META).length;
  const progress  = Math.round((completed / total) * 100);

  useEffect(() => {
    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    if (initiallyComplete) {
      let isMounted = true;
      fetch(`${API}/api/generate/status/${projectId}`)
        .then((res) => res.json())
        .then((data) => {
          if (!isMounted) return;
          setStates((prev) => {
            const next = { ...prev };
            for (const agent of data.agents || []) {
              if (next[agent.agent_name]) {
                next[agent.agent_name] = {
                  ...next[agent.agent_name],
                  status: agent.status,
                  message: agent.error || "Completed",
                  data: agent.data,
                };
              }
            }
            return next;
          });
        })
        .catch(() => {});
      return () => { isMounted = false; };
    }

    const wsUrl = API.replace(/^http/, "ws") + `/ws/${projectId}`;

    let isMounted = true;          // guards against StrictMode double-invoke
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 3;
    let pollingInterval: NodeJS.Timeout | null = null;
    let reconnectTimer: NodeJS.Timeout | null = null;

    const startPolling = () => {
      if (!isMounted) return;
      setUsePolling(true);
      setEvents(prev => [`[${new Date().toLocaleTimeString()}] Switched to polling mode (WebSocket unavailable)`, ...prev.slice(0, 49)]);

      pollingInterval = setInterval(async () => {
        if (!isMounted) return;
        try {
          const response = await fetch(`${API}/api/generate/status/${projectId}`);
          if (response.ok) {
            const data = await response.json();
            if (data.agents) {
              Object.entries(data.agents).forEach(([agentKey, agentData]: [string, any]) => {
                if (agentKey in AGENT_META) {
                  setStates(prev => ({
                    ...prev,
                    [agentKey]: { agent: agentKey, status: agentData.status || "pending", message: agentData.message || "", data: agentData.data }
                  }));
                }
              });
            }
          }
        } catch (error) {
          // silently swallow polling errors
        }
      }, 2000);
    };

    const connectWebSocket = () => {
      if (!isMounted) return;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMounted) { ws.close(); return; }
        setConnected(true);
        setUsePolling(false);
        reconnectAttempts = 0;

        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send("ping");
          else clearInterval(pingInterval);
        }, 30000);
        (ws as any).pingInterval = pingInterval;
      };

      ws.onclose = (event) => {
        if ((ws as any).pingInterval) clearInterval((ws as any).pingInterval);
        if (!isMounted) return;           // StrictMode teardown — ignore silently

        setConnected(false);
        wsRef.current = null;

        if (reconnectAttempts < maxReconnectAttempts && !done) {
          reconnectAttempts++;
          console.log(`Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts})...`);
          reconnectTimer = setTimeout(connectWebSocket, 2000 * reconnectAttempts);
        } else if (!done) {
          startPolling();
        }
      };

      ws.onerror = () => {
        // Only log if we're still mounted — suppress StrictMode teardown noise
        if (isMounted) setConnected(false);
      };

      ws.onmessage = (evt) => {
        if (!isMounted) return;
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
        } catch {
          // ignore malformed messages
        }
      };
    };

    connectWebSocket();

    return () => {
      isMounted = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (pollingInterval) clearInterval(pollingInterval);
      const ws = wsRef.current;
      if (ws) {
        if ((ws as any).pingInterval) clearInterval((ws as any).pingInterval);
        // Only close if past CONNECTING state — avoids StrictMode "closed before established" error
        if (ws.readyState !== WebSocket.CONNECTING) {
          ws.close();
        } else {
          // Let it open then immediately close — more graceful
          ws.onopen = () => ws.close();
          ws.onerror = () => {};
        }
        wsRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);


  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400 animate-pulse" : usePolling ? "bg-yellow-400" : "bg-rose-400"}`} />
          <span className="text-xs text-white/50 font-medium">
            {connected ? "Live stream connected" : usePolling ? "Polling mode" : "Connecting…"}
          </span>
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
