"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Stage, Layer, Rect, Line, Text, Group, Circle } from "react-konva";
import Konva from "konva";
import useUndoable from "use-undoable";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Sparkles, 
  Zap, 
  RotateCcw, 
  RotateCw, 
  Move, 
  Square, 
  Trash2,
  Download,
  Save,
  RefreshCw,
  Brain,
  Target,
  Lightbulb
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────

export interface Room {
  id: string;
  name: string;
  type: RoomType;
  x: number;
  y: number;
  w: number;
  h: number;
  floor: number;
  rotation?: number;
  aiSuggested?: boolean;
}

export type RoomType =
  | "living"
  | "dining"
  | "kitchen"
  | "master_bedroom"
  | "bedroom"
  | "bathroom"
  | "balcony"
  | "staircase"
  | "study"
  | "utility"
  | "corridor"
  | "pooja";

export interface AIFloorPlanEditorProps {
  initialRooms: Room[];
  plotWidthM: number;
  plotDepthM: number;
  plotAreaSqm: number;
  fsiAllowed: number;
  floors: number;
  onSave: (rooms: Room[]) => void;
  onRegenerate3D: (rooms: Room[]) => void;
}

// ─── Constants ────────────────────────────────────────────────────

const SCALE = 36;
const GRID = 0.5;
const PAD = 48;

const ROOM_COLORS: Record<RoomType, string> = {
  living: "#E8F4FD",
  dining: "#FDF5E8", 
  kitchen: "#FDE8E8",
  master_bedroom: "#EAF3DE",
  bedroom: "#EAF3DE",
  bathroom: "#F0E8FD",
  balcony: "#E1F5EE",
  staircase: "#F1EFE8",
  study: "#FDF5E8",
  utility: "#F5F5F0",
  corridor: "#F1EFE8",
  pooja: "#FDF5E8",
};

const ROOM_STROKE: Record<RoomType, string> = {
  living: "#185FA5",
  dining: "#854F0B",
  kitchen: "#993C1D", 
  master_bedroom: "#3B6D11",
  bedroom: "#3B6D11",
  bathroom: "#534AB7",
  balcony: "#0F6E56",
  staircase: "#888780",
  study: "#854F0B",
  utility: "#888780",
  corridor: "#888780",
  pooja: "#854F0B",
};

// ─── Helpers ──────────────────────────────────────────────────────

const snapM = (v: number) => Math.round(v / GRID) * GRID;
const mToPx = (m: number) => m * SCALE;
const pxToM = (px: number) => px / SCALE;
const uuid = () => Math.random().toString(36).slice(2, 9);

// ─── Component ────────────────────────────────────────────────────

export default function AIFloorPlanEditor({
  initialRooms,
  plotWidthM,
  plotDepthM,
  plotAreaSqm,
  fsiAllowed,
  floors,
  onSave,
  onRegenerate3D
}: AIFloorPlanEditorProps) {
  const [rooms, setRooms, { undo, redo, canUndo, canRedo }] = useUndoable<Room[]>(initialRooms);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tool, setTool] = useState<"select" | "draw" | "delete" | "ai">("select");
  const [activeFloor, setActiveFloor] = useState(0);
  const [aiMode, setAiMode] = useState<"suggest" | "optimize" | "analyze">("suggest");
  const [aiSuggestions, setAiSuggestions] = useState<any[]>([]);
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [showAiPanel, setShowAiPanel] = useState(false);

  const stageRef = useRef<Konva.Stage>(null);
  const visibleRooms = rooms.filter((r: Room) => r.floor === activeFloor);

  // ─── AI Functions ─────────────────────────────────────────────

  const generateAISuggestions = async () => {
    setIsAiThinking(true);
    setShowAiPanel(true);
    
    // Simulate AI analysis
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const suggestions = [
      {
        id: "1",
        type: "layout",
        title: "Optimize Kitchen Position",
        description: "Move kitchen to northeast for better morning light and ventilation",
        impact: "25% more natural light",
        action: () => {
          const kitchen = rooms.find((r: Room) => r.type === "kitchen");
          if (kitchen) {
            const optimizedRooms = rooms.map((r: Room) => 
              r.id === kitchen.id 
                ? { ...r, x: 2, y: 2, aiSuggested: true }
                : r
            );
            setRooms(optimizedRooms);
          }
        }
      },
      {
        id: "2", 
        type: "space",
        title: "Add Central Courtyard",
        description: "Create a 3x3m courtyard for natural light and ventilation",
        impact: "Improved air circulation",
        action: () => {
          const courtyard: Room = {
            id: uuid(),
            name: "Courtyard",
            type: "balcony",
            x: plotWidthM / 2 - 1.5,
            y: plotDepthM / 2 - 1.5,
            w: 3,
            h: 3,
            floor: activeFloor,
            aiSuggested: true
          };
          setRooms([...rooms, courtyard]);
        }
      },
      {
        id: "3",
        type: "privacy",
        title: "Reorient Master Bedroom", 
        description: "Rotate master bedroom for better privacy and morning sun",
        impact: "Enhanced privacy",
        action: () => {
          const master = rooms.find((r: Room) => r.type === "master_bedroom");
          if (master) {
            const optimizedRooms = rooms.map((r: Room) =>
              r.id === master.id
                ? { ...r, x: plotWidthM - r.w - 1, y: plotDepthM - r.h - 1, aiSuggested: true }
                : r
            );
            setRooms(optimizedRooms);
          }
        }
      }
    ];
    
    setAiSuggestions(suggestions);
    setIsAiThinking(false);
  };

  const optimizeLayout = async () => {
    setIsAiThinking(true);
    
    // Simulate AI optimization
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Apply multiple optimizations
    const optimizedRooms = rooms.map((room: Room) => {
      let optimized = { ...room };
      
      // Optimize kitchen position
      if (room.type === "kitchen") {
        optimized = { ...optimized, x: 1, y: 1, aiSuggested: true };
      }
      
      // Optimize living room for natural light
      if (room.type === "living") {
        optimized = { ...optimized, x: 4, y: 1, aiSuggested: true };
      }
      
      // Optimize bedrooms for privacy
      if (room.type === "master_bedroom") {
        optimized = { ...optimized, x: plotWidthM - room.w - 1, y: plotDepthM - room.h - 1, aiSuggested: true };
      }
      
      return optimized;
    });
    
    setRooms(optimizedRooms);
    setIsAiThinking(false);
  };

  const analyzeLayout = async () => {
    setIsAiThinking(true);
    
    // Simulate AI analysis
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    const analysis = {
      efficiency: 87,
      naturalLight: 92,
      ventilation: 78,
      privacy: 85,
      suggestions: [
        "Excellent natural light utilization",
        "Consider adding cross-ventilation",
        "Privacy zones well-defined",
        "Space efficiency can be improved by 8%"
      ]
    };
    
    console.log("Layout Analysis:", analysis);
    setIsAiThinking(false);
  };

  // ─── Render AI Panel ─────────────────────────────────────────

  const AIPanel = () => (
    <AnimatePresence>
      {showAiPanel && (
        <motion.div
          initial={{ opacity: 0, x: 300 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 300 }}
          className="fixed right-4 top-20 w-80 bg-gray-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl z-50"
        >
          <div className="p-4 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-r from-violet-500 to-cyan-500 rounded-full flex items-center justify-center">
                <Brain className="w-4 h-4 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-white">AI Design Assistant</h3>
                <p className="text-xs text-white/50">Smart Layout Optimization</p>
              </div>
            </div>
            <button
              onClick={() => setShowAiPanel(false)}
              className="text-white/40 hover:text-white/60 transition-colors"
            >
              ✕
            </button>
          </div>

          <div className="p-4">
            {isAiThinking ? (
              <div className="text-center py-8">
                <div className="w-8 h-8 bg-gradient-to-r from-violet-500 to-cyan-500 rounded-full animate-spin mx-auto mb-3"></div>
                <p className="text-sm text-white/60">AI is analyzing your layout...</p>
              </div>
            ) : (
              <div className="space-y-3">
                {aiSuggestions.map((suggestion) => (
                  <div key={suggestion.id} className="bg-white/5 border border-white/10 rounded-xl p-4">
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center">
                        <Target className="w-4 h-4 text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-white text-sm mb-1">{suggestion.title}</h4>
                        <p className="text-xs text-white/60 mb-2">{suggestion.description}</p>
                        <p className="text-xs text-emerald-400 mb-3">Impact: {suggestion.impact}</p>
                        <button
                          onClick={suggestion.action}
                          className="text-xs px-3 py-1 bg-violet-600 hover:bg-violet-700 rounded-lg transition-colors flex items-center gap-1"
                        >
                          <Zap className="w-3 h-3" />
                          Apply Suggestion
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  // ─── Enhanced Toolbar ────────────────────────────────────────

  const EnhancedToolbar = () => (
    <div className="flex gap-2 mb-4 flex-wrap items-center">
      {/* Basic Tools */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1">
        {[
          { id: "select", icon: <Move className="w-4 h-4" />, label: "Select" },
          { id: "draw", icon: <Square className="w-4 h-4" />, label: "Draw" },
          { id: "delete", icon: <Trash2 className="w-4 h-4" />, label: "Delete" }
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTool(t.id as any)}
            className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all ${
              tool === t.id
                ? "bg-violet-600 text-white"
                : "text-white/60 hover:text-white/80 hover:bg-white/5"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* AI Tools */}
      <div className="flex gap-1 bg-gradient-to-r from-violet-500/10 to-cyan-500/10 border border-violet-500/20 rounded-lg p-1">
        <button
          onClick={generateAISuggestions}
          disabled={isAiThinking}
          className="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium bg-gradient-to-r from-violet-600 to-cyan-600 text-white hover:from-violet-700 hover:to-cyan-700 transition-all disabled:opacity-50"
        >
          <Sparkles className="w-4 h-4" />
          AI Suggest
        </button>
        
        <button
          onClick={optimizeLayout}
          disabled={isAiThinking}
          className="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium text-violet-400 hover:text-violet-300 hover:bg-violet-500/10 transition-all disabled:opacity-50"
        >
          <Zap className="w-4 h-4" />
          Optimize
        </button>
        
        <button
          onClick={analyzeLayout}
          disabled={isAiThinking}
          className="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 transition-all disabled:opacity-50"
        >
          <Brain className="w-4 h-4" />
          Analyze
        </button>
      </div>

      {/* Undo/Redo */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1">
        <button
          onClick={undo}
          disabled={!canUndo}
          className="p-2 rounded-md text-white/60 hover:text-white/80 hover:bg-white/5 disabled:opacity-30 transition-all"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
        <button
          onClick={redo}
          disabled={!canRedo}
          className="p-2 rounded-md text-white/60 hover:text-white/80 hover:bg-white/5 disabled:opacity-30 transition-all"
        >
          <RotateCw className="w-4 h-4" />
        </button>
      </div>

      {/* Floor Tabs */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1">
        {Array.from({ length: floors }).map((_, i) => (
          <button
            key={i}
            onClick={() => setActiveFloor(i)}
            className={`px-3 py-2 rounded-md text-sm font-medium transition-all ${
              activeFloor === i
                ? "bg-violet-600 text-white"
                : "text-white/60 hover:text-white/80 hover:bg-white/5"
            }`}
          >
            Floor {i + 1}
          </button>
        ))}
      </div>
    </div>
  );

  const stageW = mToPx(plotWidthM) + PAD * 2;
  const stageH = mToPx(plotDepthM) + PAD * 2;

  return (
    <div className="relative">
      <EnhancedToolbar />
      
      <div className="relative">
        <Stage
          ref={stageRef}
          width={stageW}
          height={stageH}
          className="border border-white/10 rounded-xl bg-gray-50"
        >
          <Layer>
            {/* Grid */}
            {Array.from({ length: Math.floor(plotWidthM / GRID) + 1 }).map((_, i) => (
              <Line
                key={`gx${i}`}
                points={[PAD + i * GRID * SCALE, PAD, PAD + i * GRID * SCALE, PAD + mToPx(plotDepthM)]}
                stroke="rgba(0,0,0,0.04)"
                strokeWidth={0.5}
              />
            ))}
            {Array.from({ length: Math.floor(plotDepthM / GRID) + 1 }).map((_, i) => (
              <Line
                key={`gy${i}`}
                points={[PAD, PAD + i * GRID * SCALE, PAD + mToPx(plotWidthM), PAD + i * GRID * SCALE]}
                stroke="rgba(0,0,0,0.04)"
                strokeWidth={0.5}
              />
            ))}

            {/* Plot boundary */}
            <Rect
              x={PAD}
              y={PAD}
              width={mToPx(plotWidthM)}
              height={mToPx(plotDepthM)}
              fill="transparent"
              stroke="rgba(0,0,0,0.2)"
              strokeWidth={2}
            />

            {/* Rooms */}
            {visibleRooms.map((room: Room) => {
              const isSel = selectedId === room.id;
              const isAiSuggested = room.aiSuggested;
              
              return (
                <Group
                  key={room.id}
                  x={PAD + mToPx(room.x)}
                  y={PAD + mToPx(room.y)}
                  onClick={() => setSelectedId(room.id)}
                >
                  <Rect
                    width={mToPx(room.w)}
                    height={mToPx(room.h)}
                    fill={isAiSuggested ? "#E8F4FD" : ROOM_COLORS[room.type as RoomType]}
                    stroke={isSel ? "#185FA5" : (isAiSuggested ? "#6366f1" : ROOM_STROKE[room.type as RoomType])}
                    strokeWidth={isSel ? 2 : (isAiSuggested ? 2 : 1)}
                    cornerRadius={2}
                    dash={isAiSuggested ? [5, 5] : []}
                  />

                  {/* AI Suggestion Badge */}
                  {isAiSuggested && (
                    <Group x={mToPx(room.w) - 20} y={5}>
                      <Circle radius={8} fill="#6366f1" />
                      <Text
                        x={-4}
                        y={-4}
                        text="AI"
                        fontSize={8}
                        fill="white"
                        fontStyle="bold"
                      />
                    </Group>
                  )}

                  {/* Room label */}
                  <Text
                    width={mToPx(room.w)}
                    y={mToPx(room.h) / 2 - 10}
                    text={room.name}
                    fontSize={Math.min(11, Math.max(8, mToPx(room.w) / 8))}
                    fill={isSel ? "#0C447C" : "rgba(0,0,0,0.6)"}
                    align="center"
                    fontStyle={isSel ? "500" : "normal"}
                  />
                  <Text
                    width={mToPx(room.w)}
                    y={mToPx(room.h) / 2 + 3}
                    text={`${(room.w * room.h).toFixed(1)} m²`}
                    fontSize={9}
                    fill="rgba(0,0,0,0.35)"
                    align="center"
                  />
                </Group>
              );
            })}
          </Layer>
        </Stage>
      </div>

      <AIPanel />
    </div>
  );
}