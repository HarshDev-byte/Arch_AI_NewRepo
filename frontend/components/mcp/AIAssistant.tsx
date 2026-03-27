"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Sparkles,
  Brain,
  Zap,
  X,
  ChevronDown,
  LayoutPanelLeft,
  ShieldCheck,
  DollarSign,
  Leaf,
  Maximize2,
  Minimize2,
  Clock,
  CheckCircle2,
  Loader,
} from "lucide-react";
import { mcpApi } from "@/lib/mcpApi";

interface Message {
  id: string;
  type: "user" | "ai" | "tool";
  content: string;
  timestamp: Date;
  suggestions?: string[];
  data?: any;
  toolName?: string;
  toolStatus?: "running" | "done" | "error";
}

interface AIAssistantProps {
  projectId: string;
  onSuggestionApply?: (suggestion: any) => void;
}

const QUICK_ACTIONS = [
  { icon: Brain, label: "Analyze Design", msg: "Analyze my current design", color: "from-violet-500 to-purple-500" },
  { icon: LayoutPanelLeft, label: "Optimize Layout", msg: "Optimize my floor plan layout", color: "from-blue-500 to-cyan-500" },
  { icon: ShieldCheck, label: "Check Compliance", msg: "Check building code compliance", color: "from-emerald-500 to-teal-500" },
  { icon: DollarSign, label: "Estimate Costs", msg: "Estimate construction costs", color: "from-amber-500 to-orange-500" },
  { icon: Leaf, label: "Sustainability", msg: "Provide sustainability recommendations", color: "from-green-500 to-lime-500" },
  { icon: Zap, label: "Quick Optimize", msg: "Quickly optimize all aspects of my design", color: "from-fuchsia-500 to-pink-500" },
];

function ToolCallBubble({ toolName, status }: { toolName: string; status: "running" | "done" | "error" }) {
  const labels: Record<string, string> = {
    analyze_project: "Analyzing project…",
    generate_design_suggestions: "Generating suggestions…",
    validate_compliance: "Validating compliance…",
    estimate_costs: "Estimating costs…",
    optimize_layout: "Optimizing layout…",
  };

  const doneLabels: Record<string, string> = {
    analyze_project: "Analysis complete",
    generate_design_suggestions: "Suggestions ready",
    validate_compliance: "Compliance checked",
    estimate_costs: "Costs estimated",
    optimize_layout: "Optimization done",
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9, x: -10 }}
      animate={{ opacity: 1, scale: 1, x: 0 }}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium w-fit ${
        status === "running"
          ? "bg-violet-500/15 border border-violet-500/30 text-violet-300"
          : status === "done"
          ? "bg-emerald-500/15 border border-emerald-500/30 text-emerald-300"
          : "bg-rose-500/15 border border-rose-500/30 text-rose-300"
      }`}
    >
      {status === "running" ? (
        <Loader className="w-3 h-3 animate-spin" />
      ) : status === "done" ? (
        <CheckCircle2 className="w-3 h-3" />
      ) : (
        <X className="w-3 h-3" />
      )}
      <span className="font-mono">{status === "done" ? doneLabels[toolName] : labels[toolName] ?? toolName}</span>
    </motion.div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1.5 px-4 py-3 bg-white/5 rounded-2xl rounded-bl-sm border border-white/8">
        {[0, 0.2, 0.4].map((delay, i) => (
          <motion.div
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-violet-400"
            animate={{ y: [0, -4, 0], opacity: [0.5, 1, 0.5] }}
            transition={{ repeat: Infinity, duration: 0.8, delay }}
          />
        ))}
      </div>
    </div>
  );
}

export default function AIAssistant({ projectId, onSuggestionApply }: AIAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      type: "ai",
      content:
        "Hi! I'm your **AI architectural assistant** powered by MCP. I can analyze your design, optimize floor plans, check compliance, estimate costs, and more. What would you like to work on?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (isExpanded) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isExpanded]);

  const addMessage = (msg: Omit<Message, "id" | "timestamp">) => {
    setMessages((prev) => [
      ...prev,
      { ...msg, id: Date.now().toString() + Math.random(), timestamp: new Date() },
    ]);
  };

  const handleSendMessage = async (message: string) => {
    if (!message.trim() || isLoading) return;
    setShowQuickActions(false);
    setInput("");
    setIsLoading(true);

    addMessage({ type: "user", content: message });

    // Determine which MCP tool to call
    const lowerMsg = message.toLowerCase();
    let toolName: string | undefined;
    if (lowerMsg.includes("analyz") || lowerMsg.includes("design")) toolName = "analyze_project";
    else if (lowerMsg.includes("optim") || lowerMsg.includes("layout") || lowerMsg.includes("improve")) toolName = "optimize_layout";
    else if (lowerMsg.includes("complian") || lowerMsg.includes("code") || lowerMsg.includes("fsi")) toolName = "validate_compliance";
    else if (lowerMsg.includes("cost") || lowerMsg.includes("estimat") || lowerMsg.includes("price")) toolName = "estimate_costs";
    else if (lowerMsg.includes("suggest") || lowerMsg.includes("recommend") || lowerMsg.includes("sustain")) toolName = "generate_design_suggestions";

    // Show tool call bubble if relevant
    const toolMsgId = Date.now().toString() + "tool";
    if (toolName) {
      setMessages((prev) => [
        ...prev,
        {
          id: toolMsgId,
          type: "tool",
          content: "",
          timestamp: new Date(),
          toolName,
          toolStatus: "running",
        },
      ]);
    }

    try {
      const aiResponse = await mcpApi.chatWithAI(projectId, message);

      // Update tool bubble to done
      if (toolName) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === toolMsgId ? { ...m, toolStatus: "done" as const } : m
          )
        );
      }

      addMessage({
        type: "ai",
        content: aiResponse.response,
        suggestions: aiResponse.suggestions,
        data: aiResponse.data,
      });
    } catch (error) {
      if (toolName) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === toolMsgId ? { ...m, toolStatus: "error" as const } : m
          )
        );
      }
      addMessage({
        type: "ai",
        content: "I encountered an error connecting to the MCP server. Please ensure the backend is running and try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const formatContent = (text: string) => {
    return text
      .replace(/\*\*(.+?)\*\*/g, "<strong class='text-white font-semibold'>$1</strong>")
      .replace(/•\s/g, "<span class='text-violet-400 mr-1'>•</span> ")
      .replace(/\n/g, "<br/>");
  };

  const panelW = isFullscreen ? "w-[640px]" : "w-[400px]";
  const panelH = isFullscreen ? "h-[600px]" : "h-[500px]";

  return (
    <div className={`fixed bottom-6 right-6 z-50`} style={{ zIndex: 55 }}>
      <AnimatePresence mode="wait">
        {isExpanded && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, scale: 0.92, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 20 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className={`mb-4 ${panelW} ${panelH} flex flex-col overflow-hidden`}
            style={{
              background: "linear-gradient(135deg, rgba(10,10,25,0.97) 0%, rgba(15,15,35,0.97) 100%)",
              backdropFilter: "blur(24px)",
              border: "1px solid rgba(139,92,246,0.25)",
              borderRadius: "20px",
              boxShadow: "0 25px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04), inset 0 1px 0 rgba(255,255,255,0.06)",
            }}
          >
            {/* ── Header */}
            <div className="flex items-center gap-3 px-5 py-4 border-b border-white/6">
              <div className="relative">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 via-purple-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-violet-500/30">
                  <Brain className="w-5 h-5 text-white" />
                </div>
                <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-emerald-400 border-2 border-[#0a0a19] shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-white text-sm">AI Architect</h3>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-violet-500/20 border border-violet-500/30 text-violet-300 font-mono">MCP</span>
                </div>
                <p className="text-xs text-white/40">Powered by archai-mcp server</p>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setIsFullscreen(!isFullscreen)}
                  className="p-1.5 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/5 transition-all"
                >
                  {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                </button>
                <button
                  onClick={() => setIsExpanded(false)}
                  className="p-1.5 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/5 transition-all"
                >
                  <ChevronDown className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* ── Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 scroll-smooth">
              {messages.map((message) => {
                if (message.type === "tool") {
                  return (
                    <div key={message.id} className="flex justify-start pl-2">
                      <ToolCallBubble
                        toolName={message.toolName!}
                        status={message.toolStatus!}
                      />
                    </div>
                  );
                }

                return (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[88%] ${
                        message.type === "user"
                          ? "bg-gradient-to-br from-violet-600 to-fuchsia-600 text-white rounded-2xl rounded-br-sm px-4 py-3"
                          : "bg-white/6 border border-white/8 text-white rounded-2xl rounded-bl-sm px-4 py-3"
                      }`}
                    >
                      <div
                        className="text-sm leading-relaxed"
                        dangerouslySetInnerHTML={{
                          __html: formatContent(message.content),
                        }}
                      />

                      {message.suggestions && message.suggestions.length > 0 && (
                        <div className="mt-3 flex flex-col gap-1.5">
                          {message.suggestions.map((s, idx) => (
                            <motion.button
                              key={idx}
                              onClick={() => handleSendMessage(s)}
                              whileHover={{ x: 2 }}
                              className="text-left text-xs px-3 py-2 bg-white/6 hover:bg-violet-500/20 rounded-xl border border-white/8 hover:border-violet-500/30 transition-all text-white/70 hover:text-violet-300 flex items-center gap-2"
                            >
                              <span className="text-violet-400 text-[10px]">→</span>
                              {s}
                            </motion.button>
                          ))}
                        </div>
                      )}

                      <div className="flex items-center gap-1 mt-2 opacity-0 hover:opacity-100 transition-opacity">
                        <Clock className="w-2.5 h-2.5 text-white/25" />
                        <span className="text-[10px] text-white/25">
                          {message.timestamp.toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  </motion.div>
                );
              })}

              {isLoading && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>

            {/* ── Quick Actions */}
            <AnimatePresence>
              {showQuickActions && (
                <motion.div
                  initial={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="px-4 pb-2 pt-1">
                    <p className="text-[10px] text-white/30 uppercase tracking-widest mb-2">Quick Actions</p>
                    <div className="grid grid-cols-3 gap-1.5">
                      {QUICK_ACTIONS.map((action) => (
                        <motion.button
                          key={action.label}
                          onClick={() => handleSendMessage(action.msg)}
                          whileHover={{ scale: 1.04 }}
                          whileTap={{ scale: 0.96 }}
                          className="flex flex-col items-center gap-1.5 p-2.5 rounded-xl bg-white/4 border border-white/6 hover:bg-white/8 hover:border-white/12 transition-all"
                        >
                          <div className={`w-7 h-7 rounded-lg bg-gradient-to-br ${action.color} flex items-center justify-center`}>
                            <action.icon className="w-3.5 h-3.5 text-white" />
                          </div>
                          <span className="text-[10px] text-white/60 font-medium text-center leading-tight">{action.label}</span>
                        </motion.button>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* ── Input */}
            <div className="px-4 py-3 border-t border-white/6">
              <div className="flex gap-2 items-end">
                <div className="flex-1 relative">
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage(input);
                      }
                    }}
                    placeholder="Ask anything about your design…"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-violet-500/50 focus:bg-white/8 transition-all"
                  />
                </div>
                <motion.button
                  onClick={() => handleSendMessage(input)}
                  disabled={!input.trim() || isLoading}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="w-10 h-10 flex-shrink-0 rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center shadow-lg shadow-violet-500/30 transition-all"
                >
                  <Send className="w-4 h-4 text-white" />
                </motion.button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Toggle Fab */}
      <motion.button
        onClick={() => setIsExpanded(!isExpanded)}
        whileHover={{ scale: 1.06 }}
        whileTap={{ scale: 0.94 }}
        className="relative w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-600 via-purple-600 to-fuchsia-600 flex items-center justify-center shadow-2xl shadow-violet-500/40"
        style={{
          boxShadow: "0 8px 32px rgba(139,92,246,0.45), 0 0 0 1px rgba(255,255,255,0.08)",
        }}
      >
        {/* Glow ring */}
        <motion.div
          className="absolute inset-0 rounded-2xl bg-gradient-to-br from-violet-400/20 to-transparent"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ repeat: Infinity, duration: 2 }}
        />

        <AnimatePresence mode="wait">
          {isExpanded ? (
            <motion.div
              key="close"
              initial={{ rotate: -90, opacity: 0, scale: 0.5 }}
              animate={{ rotate: 0, opacity: 1, scale: 1 }}
              exit={{ rotate: 90, opacity: 0, scale: 0.5 }}
              transition={{ duration: 0.2 }}
            >
              <X className="w-5 h-5 text-white" />
            </motion.div>
          ) : (
            <motion.div
              key="open"
              initial={{ rotate: -90, opacity: 0, scale: 0.5 }}
              animate={{ rotate: 0, opacity: 1, scale: 1 }}
              exit={{ rotate: 90, opacity: 0, scale: 0.5 }}
              transition={{ duration: 0.2 }}
            >
              <Sparkles className="w-6 h-6 text-white" />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Notification dot when closed */}
        {!isExpanded && (
          <motion.span
            className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-400 border-2 border-[#080C14]"
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ repeat: Infinity, duration: 2 }}
          />
        )}
      </motion.button>
    </div>
  );
}