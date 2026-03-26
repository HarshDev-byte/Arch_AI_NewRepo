/**
 * lib/useAgentProgress.ts
 *
 * React hook that:
 *  1. Opens a WebSocket to /ws/{projectId} for real-time agent updates
 *  2. Sends a keep-alive ping every 20 s (backend's receive_text loop)
 *  3. Auto-reconnects up to MAX_RETRIES times on unexpected close
 *  4. Falls back to HTTP polling /api/generate/status/{projectId}
 *     whenever the WebSocket is disconnected
 *  5. Exposes per-agent state, overall isComplete flag, and any error string
 */

import { useCallback, useEffect, useRef, useState } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export type AgentStatus = "pending" | "running" | "complete" | "error";

export interface AgentUpdate {
  agent:      string;
  status:     AgentStatus;
  message:    string;
  data?:      Record<string, unknown>;
  timestamp?: string;
  event?:     string;
}

export type AgentStateMap = Record<string, AgentUpdate>;

export interface UseAgentProgressResult {
  /** Per-agent latest update, keyed by agent name */
  agentStates:   AgentStateMap;
  /** True once the "pipeline_complete" / system:complete event arrives */
  isComplete:    boolean;
  /** Error string — set on WS error or system:error event */
  error:         string | null;
  /** Whether the WebSocket is currently open */
  isConnected:   boolean;
  /** Ordered list of all events received (newest first, max 100) */
  eventLog:      string[];
  /** Manually reset state and reconnect */
  reconnect:     () => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const MAX_RETRIES     = 5;
const BASE_BACKOFF_MS = 1_000;   // doubles each retry: 1s, 2s, 4s, 8s, 16s
const PING_INTERVAL   = 20_000;  // keep-alive ping
const POLL_INTERVAL   = 6_000;   // HTTP fallback while disconnected

const AGENTS_ORDERED = [
  "geo", "design", "layout", "cost", "compliance", "sustainability", "threed", "vr",
];

function initialStates(): AgentStateMap {
  return Object.fromEntries(
    AGENTS_ORDERED.map((a) => [
      a,
      { agent: a, status: "pending" as AgentStatus, message: "" },
    ])
  );
}

// ─── Helper ───────────────────────────────────────────────────────────────────

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
}

function wsBase(): string {
  return apiBase().replace(/^http/, "ws");
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAgentProgress(projectId: string): UseAgentProgressResult {
  const [agentStates, setAgentStates] = useState<AgentStateMap>(initialStates);
  const [isComplete,  setIsComplete]  = useState(false);
  const [error,       setError]       = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [eventLog,    setEventLog]    = useState<string[]>([]);

  // Refs so callbacks always see fresh values without re-triggering useEffect
  const wsRef         = useRef<WebSocket | null>(null);
  const retriesRef    = useRef(0);
  const pingTimerRef  = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollTimerRef  = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef    = useRef(true);
  const isCompleteRef = useRef(false);

  // ── Helpers ─────────────────────────────────────────────────────────────────

  const pushEvent = useCallback((text: string) => {
    const ts = new Date().toLocaleTimeString();
    setEventLog((prev) => [`[${ts}] ${text}`, ...prev.slice(0, 99)]);
  }, []);

  const applyUpdate = useCallback((payload: AgentUpdate) => {
    const { agent, status, message, event } = payload;

    // Pipeline complete signals
    if (
      event === "pipeline_complete" ||
      (agent === "system" && status === "complete") ||
      (agent === "orchestrator" && status === "complete")
    ) {
      isCompleteRef.current = true;
      setIsComplete(true);
    }

    // Error signal
    if (agent === "system" && status === "error") {
      setError(message ?? "Unknown pipeline error");
    }

    // Update the named agent
    if (agent && agent in initialStates()) {
      setAgentStates((prev) => ({
        ...prev,
        [agent]: { ...prev[agent], ...payload },
      }));
    }

    pushEvent(`${agent}: ${message ?? event ?? status}`);
  }, [pushEvent]);

  // ── HTTP status poll (fallback while WS is disconnected) ─────────────────────

  const startPoll = useCallback(() => {
    if (pollTimerRef.current) return;
    pollTimerRef.current = setInterval(async () => {
      if (!mountedRef.current || isCompleteRef.current) return;
      try {
        const res  = await fetch(`${apiBase()}/api/generate/status/${projectId}`);
        if (!res.ok) return;
        const data = await res.json() as {
          project_status: string;
          agents: { agent_name: string; status: AgentStatus; error?: string }[];
        };
        data.agents.forEach((a) => {
          applyUpdate({ agent: a.agent_name, status: a.status, message: a.error ?? "" });
        });
        if (data.project_status === "complete") {
          isCompleteRef.current = true;
          setIsComplete(true);
        }
      } catch { /* network error — keep polling */ }
    }, POLL_INTERVAL);
  }, [projectId, applyUpdate]);

  const stopPoll = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  // ── WebSocket connection ──────────────────────────────────────────────────────

  const connect = useCallback(() => {
    if (!projectId || !mountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${wsBase()}/ws/${projectId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) { ws.close(); return; }
      retriesRef.current = 0;
      setIsConnected(true);
      setError(null);
      stopPoll();               // WS connected — stop HTTP fallback
      pushEvent("WebSocket connected");

      // Keep-alive ping
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, PING_INTERVAL);
    };

    ws.onmessage = (evt) => {
      try {
        const payload = JSON.parse(evt.data) as AgentUpdate;
        applyUpdate(payload);

        if (isCompleteRef.current) ws.close();
      } catch { /* ignore malformed frames */ }
    };

    ws.onerror = () => {
      pushEvent("WebSocket error");
    };

    ws.onclose = (evt) => {
      if (!mountedRef.current) return;
      setIsConnected(false);
      if (pingTimerRef.current) { clearInterval(pingTimerRef.current); pingTimerRef.current = null; }

      // If pipeline is done, don't reconnect
      if (isCompleteRef.current) return;

      // Start HTTP fallback immediately
      startPoll();

      // Backoff reconnect
      if (retriesRef.current < MAX_RETRIES) {
        const delay = BASE_BACKOFF_MS * Math.pow(2, retriesRef.current);
        retriesRef.current += 1;
        pushEvent(`WS closed (code ${evt.code}) — reconnecting in ${delay / 1000}s (attempt ${retriesRef.current}/${MAX_RETRIES})`);
        setTimeout(() => { if (mountedRef.current) connect(); }, delay);
      } else {
        pushEvent("Max WS retries reached — using HTTP polling");
        setError("Real-time connection lost. Polling for updates.");
      }
    };
  }, [projectId, applyUpdate, pushEvent, startPoll, stopPoll]);

  // ── Lifecycle ─────────────────────────────────────────────────────────────────

  const reconnect = useCallback(() => {
    retriesRef.current    = 0;
    isCompleteRef.current = false;
    setIsComplete(false);
    setError(null);
    setAgentStates(initialStates());
    setEventLog([]);
    wsRef.current?.close();
    connect();
  }, [connect]);

  useEffect(() => {
    mountedRef.current = true;

    // Don't bother connecting if already complete (e.g. revisiting a done project)
    if (!isCompleteRef.current) connect();

    return () => {
      mountedRef.current = false;
      wsRef.current?.close();
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      stopPoll();
    };
  }, [connect, stopPoll]);

  return { agentStates, isComplete, error, isConnected, eventLog, reconnect };
}
