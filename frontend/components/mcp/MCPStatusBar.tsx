"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, Zap, Brain, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

interface MCPTool {
  name: string;
  label: string;
  status: "idle" | "running" | "done" | "error";
  lastRun?: string;
}

interface MCPStatusBarProps {
  projectId?: string;
}

const TOOLS: MCPTool[] = [
  { name: "analyze_project", label: "Analyze", status: "idle" },
  { name: "generate_design_suggestions", label: "Suggest", status: "idle" },
  { name: "validate_compliance", label: "Compliance", status: "idle" },
  { name: "estimate_costs", label: "Costs", status: "idle" },
  { name: "optimize_layout", label: "Optimize", status: "idle" },
];

export default function MCPStatusBar({ projectId }: MCPStatusBarProps) {
  const [connected, setConnected] = useState(false);
  const [tools, setTools] = useState<MCPTool[]>(TOOLS);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [callCount, setCallCount] = useState(0);

  // Simulate MCP server connection check
  useEffect(() => {
    const timer = setTimeout(() => setConnected(true), 800);
    return () => clearTimeout(timer);
  }, []);

  const runTool = async (toolName: string) => {
    if (!connected || !projectId || activeTool) return;
    setActiveTool(toolName);
    setCallCount((c) => c + 1);

    setTools((prev) =>
      prev.map((t) =>
        t.name === toolName ? { ...t, status: "running" } : t
      )
    );

    try {
      const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const endpointMap: Record<string, string> = {
        analyze_project: `/api/mcp/analyze`,
        generate_design_suggestions: `/api/mcp/suggest`,
        validate_compliance: `/api/mcp/validate-compliance`,
        estimate_costs: `/api/mcp/estimate-costs`,
        optimize_layout: `/api/mcp/optimize`,
      };

      const endpoint = endpointMap[toolName];
      if (endpoint) {
        await fetch(`${API}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project_id: projectId }),
        });
      } else {
        await new Promise((r) => setTimeout(r, 1500));
      }

      setTools((prev) =>
        prev.map((t) =>
          t.name === toolName
            ? { ...t, status: "done", lastRun: new Date().toLocaleTimeString() }
            : t
        )
      );
    } catch {
      setTools((prev) =>
        prev.map((t) =>
          t.name === toolName ? { ...t, status: "error" } : t
        )
      );
    } finally {
      setActiveTool(null);
      setTimeout(() => {
        setTools((prev) =>
          prev.map((t) =>
            t.name === toolName ? { ...t, status: "idle" } : t
          )
        );
      }, 4000);
    }
  };

  const getStatusIcon = (status: MCPTool["status"]) => {
    switch (status) {
      case "running":
        return <Loader2 className="w-3 h-3 animate-spin text-violet-400" />;
      case "done":
        return <CheckCircle className="w-3 h-3 text-emerald-400" />;
      case "error":
        return <AlertCircle className="w-3 h-3 text-rose-400" />;
      default:
        return <div className="w-2 h-2 rounded-full bg-white/20" />;
    }
  };

  return (
    <div className="fixed bottom-24 right-6 z-40">
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            className="mb-3 w-72 bg-gray-950/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/8 flex items-center gap-3">
              <div
                className={`w-2 h-2 rounded-full ${
                  connected ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" : "bg-amber-400"
                } animate-pulse`}
              />
              <span className="text-sm font-semibold text-white">MCP Server</span>
              <span className="text-xs text-white/40 ml-auto">archai-mcp v1.0</span>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 divide-x divide-white/5 border-b border-white/5">
              {[
                { label: "Status", value: connected ? "Online" : "Connecting", color: connected ? "text-emerald-400" : "text-amber-400" },
                { label: "Tools", value: "5 active", color: "text-violet-400" },
                { label: "Calls", value: callCount.toString(), color: "text-cyan-400" },
              ].map((s) => (
                <div key={s.label} className="px-3 py-2 text-center">
                  <p className={`text-sm font-bold ${s.color}`}>{s.value}</p>
                  <p className="text-[10px] text-white/30 mt-0.5">{s.label}</p>
                </div>
              ))}
            </div>

            {/* Tools list */}
            <div className="p-3 space-y-1">
              <p className="text-[10px] text-white/30 uppercase tracking-widest px-1 mb-2">Available Tools</p>
              {tools.map((tool) => (
                <motion.button
                  key={tool.name}
                  onClick={() => runTool(tool.name)}
                  disabled={!connected || !projectId || !!activeTool}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all ${
                    tool.status === "running"
                      ? "bg-violet-500/15 border border-violet-500/30"
                      : tool.status === "done"
                      ? "bg-emerald-500/10 border border-emerald-500/20"
                      : tool.status === "error"
                      ? "bg-rose-500/10 border border-rose-500/20"
                      : "bg-white/4 border border-white/6 hover:bg-white/8 hover:border-white/12"
                  } disabled:opacity-40 disabled:cursor-not-allowed`}
                  whileHover={!activeTool && connected && projectId ? { x: 2 } : {}}
                >
                  {getStatusIcon(tool.status)}
                  <span className="flex-1 text-left text-white/80 font-medium">{tool.label}</span>
                  {tool.status === "done" && tool.lastRun && (
                    <span className="text-[10px] text-emerald-400/70">{tool.lastRun}</span>
                  )}
                  {tool.status === "idle" && (
                    <span className="text-[10px] text-white/25">Run →</span>
                  )}
                </motion.button>
              ))}
            </div>

            {!projectId && (
              <div className="px-4 py-3 border-t border-white/5 text-center">
                <p className="text-xs text-white/30">Open a project to run tools</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toggle button */}
      <motion.button
        onClick={() => setExpanded(!expanded)}
        className="relative flex items-center gap-2 px-4 py-2.5 bg-gray-950/90 backdrop-blur-xl border border-white/10 rounded-full shadow-xl hover:border-white/20 transition-all"
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.97 }}
      >
        <div className="relative">
          <Activity className="w-4 h-4 text-violet-400" />
          {connected && (
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.9)]" />
          )}
        </div>
        <span className="text-sm font-semibold text-white/80">MCP</span>
        {activeTool && (
          <span className="flex items-center gap-1 text-xs text-violet-400">
            <Loader2 className="w-3 h-3 animate-spin" />
            Running…
          </span>
        )}
        {callCount > 0 && !activeTool && (
          <span className="text-xs text-white/30">{callCount} calls</span>
        )}
      </motion.button>
    </div>
  );
}
