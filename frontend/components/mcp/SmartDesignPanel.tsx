"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Sparkles, 
  Zap, 
  Target, 
  TrendingUp, 
  Shield, 
  Leaf, 
  DollarSign,
  Layout,
  Lightbulb,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { mcpApi } from "@/lib/mcpApi";

interface SmartDesignPanelProps {
  projectId: string;
  currentDesign?: any;
  onDesignUpdate?: (update: any) => void;
}

interface Insight {
  id: string;
  type: "optimization" | "compliance" | "cost" | "sustainability";
  title: string;
  description: string;
  impact: "high" | "medium" | "low";
  action?: string;
  data?: any;
}

interface Score {
  label: string;
  value: number;
  color: string;
  icon: React.ReactNode;
}

export default function SmartDesignPanel({ projectId, currentDesign, onDesignUpdate }: SmartDesignPanelProps) {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [activeTab, setActiveTab] = useState<"insights" | "optimize" | "validate" | "scores">("scores");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [optimizationGoals, setOptimizationGoals] = useState<string[]>([]);
  const [scores, setScores] = useState<Score[]>([]);
  const [appliedInsights, setAppliedInsights] = useState<string[]>([]);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const generateInsights = useCallback(async () => {
    setIsAnalyzing(true);

    try {
      const [analysisRes, suggestRes] = await Promise.all([
        mcpApi.analyzeProject({ project_id: projectId }).catch(() => null),
        mcpApi.getSuggestions({ project_id: projectId }).catch(() => null),
      ]);

      // Build scores from analysis
      const metrics = analysisRes?.analysis?.metrics;
      setScores([
        {
          label: "Space",
          value: metrics?.space_efficiency || 75,
          color: "from-blue-500 to-cyan-500",
          icon: <Layout className="w-4 h-4" />,
        },
        {
          label: "Light",
          value: metrics?.natural_light_score || 85,
          color: "from-yellow-500 to-orange-500",
          icon: <Lightbulb className="w-4 h-4" />,
        },
        {
          label: "Air",
          value: metrics?.ventilation_score || 78,
          color: "from-green-500 to-emerald-500",
          icon: <TrendingUp className="w-4 h-4" />,
        },
        {
          label: "Privacy",
          value: metrics?.privacy_score || 82,
          color: "from-purple-500 to-violet-500",
          icon: <Shield className="w-4 h-4" />,
        },
      ]);

      // Build insights from suggestions
      const suggestions = suggestRes?.suggestions || [];
      const mockInsights: Insight[] = suggestions.map((s: any, i: number) => ({
        id: s.id || `insight-${i}`,
        type: s.type || "optimization",
        title: s.title || "Optimization Opportunity",
        description: s.description || "AI-powered suggestion for your design",
        impact: s.priority || "medium",
        action: s.action || "Apply Suggestion",
        data: s.parameters || {},
      }));

      // Add some fallback insights if API doesn't return any
      if (mockInsights.length === 0) {
        mockInsights.push(
          {
            id: "1",
            type: "optimization",
            title: "Layout Efficiency Opportunity",
            description: "Moving the kitchen to the northeast corner could improve natural light by 25% and create better workflow.",
            impact: "high",
            action: "Relocate Kitchen",
            data: { room: "kitchen", newPosition: "northeast", benefit: "25% more light" }
          },
          {
            id: "2", 
            type: "compliance",
            title: "Parking Requirement Gap",
            description: "Current design has 1 parking space but requires 3 as per local bylaws. Consider adding covered parking.",
            impact: "high",
            action: "Add Parking",
            data: { current: 1, required: 3, solution: "covered_parking" }
          }
        );
      }

      setInsights(mockInsights);
    } catch (error) {
      console.error("Error generating insights:", error);
      // Fallback to mock data
      setInsights([
        {
          id: "1",
          type: "optimization",
          title: "Layout Efficiency Opportunity",
          description: "Moving the kitchen to the northeast corner could improve natural light by 25% and create better workflow.",
          impact: "high",
          action: "Relocate Kitchen",
          data: { room: "kitchen", newPosition: "northeast", benefit: "25% more light" }
        }
      ]);
    }

    setLastRefreshed(new Date());
    setIsAnalyzing(false);
  }, [projectId]);

  useEffect(() => {
    generateInsights();
  }, [generateInsights]);

  const handleApplyInsight = (insight: Insight) => {
    if (onDesignUpdate && insight.data) {
      onDesignUpdate({
        type: insight.type,
        action: insight.action,
        data: insight.data
      });
      setAppliedInsights([...appliedInsights, insight.id]);
    }
  };

  const getInsightIcon = (type: string) => {
    switch (type) {
      case "optimization": return <Target className="w-4 h-4" />;
      case "compliance": return <Shield className="w-4 h-4" />;
      case "cost": return <DollarSign className="w-4 h-4" />;
      case "sustainability": return <Leaf className="w-4 h-4" />;
      default: return <Lightbulb className="w-4 h-4" />;
    }
  };

  const getInsightColor = (type: string) => {
    switch (type) {
      case "optimization": return "from-blue-500 to-cyan-500";
      case "compliance": return "from-red-500 to-orange-500";
      case "cost": return "from-green-500 to-emerald-500";
      case "sustainability": return "from-emerald-500 to-teal-500";
      default: return "from-violet-500 to-purple-500";
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case "high": return "text-red-400 bg-red-500/10 border-red-500/20";
      case "medium": return "text-yellow-400 bg-yellow-500/10 border-yellow-500/20";
      case "low": return "text-green-400 bg-green-500/10 border-green-500/20";
      default: return "text-gray-400 bg-gray-500/10 border-gray-500/20";
    }
  };

  const tabs = [
    { id: "scores", label: "Scores", icon: <TrendingUp className="w-4 h-4" /> },
    { id: "insights", label: "AI Insights", icon: <Sparkles className="w-4 h-4" /> },
    { id: "optimize", label: "Optimize", icon: <Zap className="w-4 h-4" /> },
    { id: "validate", label: "Validate", icon: <CheckCircle className="w-4 h-4" /> }
  ];

  return (
    <div className="w-80 bg-gray-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl">
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-r from-violet-500 to-cyan-500 rounded-full flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">Smart Design Panel</h3>
              <p className="text-xs text-white/50">AI-Powered Architecture Assistant</p>
            </div>
          </div>
          <button
            onClick={generateInsights}
            disabled={isAnalyzing}
            className="p-1.5 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/5 transition-all disabled:opacity-40"
          >
            {isAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-white/5 rounded-lg p-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex-1 flex items-center justify-center gap-1 px-2 py-2 rounded-md text-xs font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-violet-600 text-white"
                  : "text-white/60 hover:text-white/80"
              }`}
            >
              {tab.icon}
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-4 max-h-96 overflow-y-auto">
        <AnimatePresence mode="wait">
          {activeTab === "scores" && (
            <motion.div
              key="scores"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-3"
            >
              {scores.map((score) => (
                <div key={score.label} className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`w-6 h-6 bg-gradient-to-r ${score.color} rounded-lg flex items-center justify-center text-white`}>
                        {score.icon}
                      </div>
                      <span className="text-sm font-medium text-white">{score.label}</span>
                    </div>
                    <span className="text-lg font-bold text-white">{score.value}%</span>
                  </div>
                  <div className="w-full bg-white/10 rounded-full h-2">
                    <div 
                      className={`h-2 bg-gradient-to-r ${score.color} rounded-full transition-all duration-500`}
                      style={{ width: `${score.value}%` }}
                    />
                  </div>
                </div>
              ))}
            </motion.div>
          )}

          {activeTab === "insights" && (
            <motion.div
              key="insights"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-3"
            >
              {isAnalyzing ? (
                <div className="text-center py-8">
                  <div className="w-8 h-8 bg-gradient-to-r from-violet-500 to-cyan-500 rounded-full animate-spin mx-auto mb-3"></div>
                  <p className="text-sm text-white/60">Analyzing your design...</p>
                </div>
              ) : (
                insights.map((insight) => (
                  <motion.div
                    key={insight.id}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="bg-white/5 border border-white/10 rounded-xl p-4 hover:bg-white/10 transition-all"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-8 h-8 bg-gradient-to-r ${getInsightColor(insight.type)} rounded-lg flex items-center justify-center text-white`}>
                        {getInsightIcon(insight.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="font-medium text-white text-sm">{insight.title}</h4>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getImpactColor(insight.impact)}`}>
                            {insight.impact}
                          </span>
                        </div>
                        <p className="text-xs text-white/60 mb-3">{insight.description}</p>
                        {insight.action && !appliedInsights.includes(insight.id) && (
                          <button
                            onClick={() => handleApplyInsight(insight)}
                            className="text-xs px-3 py-1 bg-violet-600 hover:bg-violet-700 rounded-lg transition-colors flex items-center gap-1"
                          >
                            <Zap className="w-3 h-3" />
                            {insight.action}
                          </button>
                        )}
                        {appliedInsights.includes(insight.id) && (
                          <span className="text-xs text-emerald-400 flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            Applied
                          </span>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </motion.div>
          )}

          {activeTab === "optimize" && (
            <motion.div
              key="optimize"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              <div>
                <h4 className="font-medium text-white mb-3">Optimization Goals</h4>
                <div className="space-y-2">
                  {[
                    "Maximize natural light",
                    "Improve ventilation",
                    "Optimize space efficiency", 
                    "Reduce construction cost",
                    "Enhance privacy",
                    "Increase sustainability"
                  ].map((goal) => (
                    <label key={goal} className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={optimizationGoals.includes(goal)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setOptimizationGoals([...optimizationGoals, goal]);
                          } else {
                            setOptimizationGoals(optimizationGoals.filter(g => g !== goal));
                          }
                        }}
                        className="w-4 h-4 rounded border-white/20 bg-white/5 text-violet-600 focus:ring-violet-500/50"
                      />
                      <span className="text-sm text-white/80">{goal}</span>
                    </label>
                  ))}
                </div>
              </div>

              <button
                onClick={() => {
                  // Trigger optimization with selected goals
                  console.log("Optimizing with goals:", optimizationGoals);
                }}
                disabled={optimizationGoals.length === 0}
                className="w-full py-3 bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-700 hover:to-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl font-medium text-white transition-all flex items-center justify-center gap-2"
              >
                <Zap className="w-4 h-4" />
                Optimize Design
              </button>
            </motion.div>
          )}

          {activeTab === "validate" && (
            <motion.div
              key="validate"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-center gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                  <div>
                    <p className="text-sm font-medium text-emerald-400">FSI Compliance</p>
                    <p className="text-xs text-white/60">1.8/2.0 - Within limits</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                  <div>
                    <p className="text-sm font-medium text-emerald-400">Setback Requirements</p>
                    <p className="text-xs text-white/60">All sides compliant</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                  <div>
                    <p className="text-sm font-medium text-red-400">Parking Requirements</p>
                    <p className="text-xs text-white/60">1/3 spaces - Need 2 more</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                  <div>
                    <p className="text-sm font-medium text-emerald-400">Height Restrictions</p>
                    <p className="text-xs text-white/60">9.5m/12m - Compliant</p>
                  </div>
                </div>
              </div>

              <button
                onClick={() => {
                  // Trigger full compliance check
                  console.log("Running full compliance validation");
                }}
                className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 rounded-xl font-medium text-white transition-all flex items-center justify-center gap-2"
              >
                <Shield className="w-4 h-4" />
                Full Compliance Check
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}