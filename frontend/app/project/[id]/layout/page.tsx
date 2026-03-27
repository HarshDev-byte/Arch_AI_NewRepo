"use client";
import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { useAgentProgress } from "@/lib/useAgentProgress";
import { Room } from "@/components/editor/FloorPlanEditor";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";


// Dynamically import components to avoid SSR issues
const AIFloorPlanEditor = dynamic(() => import("@/components/mcp/AIFloorPlanEditor"), {
  ssr: false,
  loading: () => <div className="flex items-center justify-center h-96 bg-gray-900/50 rounded-xl"><div className="text-white">Loading AI Floor Plan Editor...</div></div>
});

const AIAssistant = dynamic(() => import("@/components/mcp/AIAssistant"), {
  ssr: false
});

const SmartDesignPanel = dynamic(() => import("@/components/mcp/SmartDesignPanel"), {
  ssr: false
});

export default function LayoutEditorPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<any>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [saved, setSaved] = useState(false);
  const [regen, setRegen] = useState(false);
  const [modelUrl, setModelUrl] = useState<string | null>(null);
  const [aiMode, setAiMode] = useState(true);
  const { agentStates } = useAgentProgress(id);

  useEffect(() => {
    fetch(`${API}/api/projects/${id}`).then(r => r.json()).then(data => {
      setProject(data);
      
      // Extract rooms from design DNA or design variants
      let roomsToLoad: Room[] = [];
      
      // First check if there are user-edited rooms in the project's design DNA
      if (data.design_dna?.user_edited_rooms) {
        roomsToLoad = data.design_dna.user_edited_rooms;
      }
      // Then check the selected variant's DNA
      else {
        const variant = data.design_variants?.find((v: any) => v.is_selected) || data.design_variants?.[0];
        if (variant?.dna?.user_edited_rooms) {
          roomsToLoad = variant.dna.user_edited_rooms;
        } else if (variant?.dna?.rooms) {
          roomsToLoad = variant.dna.rooms;
        }
      }
      
      // If no rooms found, create default layout
      if (roomsToLoad.length === 0) {
        const plotSize = Math.sqrt(data.plot_area_sqm || 300);
        roomsToLoad = [
          {
            id: "living-1",
            name: "Living Room",
            type: "living",
            x: 2,
            y: 2,
            w: Math.min(6, plotSize * 0.4),
            h: Math.min(4, plotSize * 0.3),
            floor: 0
          },
          {
            id: "kitchen-1", 
            name: "Kitchen",
            type: "kitchen",
            x: Math.min(8, plotSize * 0.6),
            y: 2,
            w: Math.min(4, plotSize * 0.25),
            h: Math.min(3, plotSize * 0.2),
            floor: 0
          },
          {
            id: "bedroom-1",
            name: "Master Bedroom", 
            type: "master_bedroom",
            x: 2,
            y: Math.min(7, plotSize * 0.6),
            w: Math.min(5, plotSize * 0.35),
            h: Math.min(4, plotSize * 0.3),
            floor: 0
          },
          {
            id: "bathroom-1",
            name: "Bathroom",
            type: "bathroom", 
            x: Math.min(8, plotSize * 0.6),
            y: Math.min(7, plotSize * 0.6),
            w: Math.min(3, plotSize * 0.2),
            h: Math.min(3, plotSize * 0.2),
            floor: 0
          }
        ];
      }
      
      setRooms(roomsToLoad);
    }).catch(error => {
      console.error("Failed to load project:", error);
    });
  }, [id]);

  // Listen for 3D regen completion via WebSocket
  useEffect(() => {
    const state = agentStates["threed"];
    if (state?.status === "complete" && state?.data?.model_url) {
      setModelUrl(state.data.model_url as string);
      setRegen(false);
    }
  }, [agentStates]);

  const handleSave = async (editedRooms: Room[]) => {
    try {
      const response = await fetch(`${API}/api/projects/${id}/layout`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rooms: editedRooms, active_floor: 0 }),
      });
      
      if (response.ok) {
        const result = await response.json();
        setRooms(editedRooms);
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
        console.log("Layout saved:", result);
      } else {
        const error = await response.json();
        console.error("Failed to save layout:", error);
        alert(`Failed to save layout: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error("Failed to save floor plan:", error);
      alert("Failed to save floor plan. Please try again.");
    }
  };

  const handleRegenerate3D = async (editedRooms: Room[]) => {
    try {
      setRegen(true);
      const response = await fetch(`${API}/api/projects/${id}/regenerate-3d`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rooms: editedRooms, active_floor: 0 }),
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log("3D regeneration started:", result);
      } else {
        const error = await response.json();
        console.error("Failed to regenerate 3D model:", error);
        alert(`Failed to regenerate 3D model: ${error.detail || 'Unknown error'}`);
        setRegen(false);
      }
    } catch (error) {
      console.error("Failed to regenerate 3D model:", error);
      alert("Failed to regenerate 3D model. Please try again.");
      setRegen(false);
    }
  };

  const handleDesignUpdate = (update: any) => {
    console.log("AI Design Update:", update);
    // Handle AI-suggested design updates
    if (update.type === "layout_optimization" && update.data?.changes) {
      // Apply AI suggestions to the layout
      const updatedRooms = rooms.map((room: Room) => {
        const change = update.data.changes.find((c: any) => c.room === room.type);
        if (change) {
          return { ...room, aiSuggested: true };
        }
        return room;
      });
      setRooms(updatedRooms);
    }
  };

  if (!project) return (
    <div className="min-h-screen bg-[#080C14] flex items-center justify-center">
      <div className="text-white">Loading project...</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#080C14] text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-gray-900/50 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => window.history.back()}
                className="text-white/60 hover:text-white transition-colors"
              >
                ← Back to Project
              </button>
              <div>
                <h1 className="text-xl font-semibold">AI Floor Plan Editor</h1>
                <p className="text-sm text-white/60">
                  {project.name} · {project.plot_area_sqm} m² plot · {project.floors} floors
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <button
                onClick={() => setAiMode(!aiMode)}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  aiMode 
                    ? "bg-gradient-to-r from-violet-600 to-cyan-600 text-white" 
                    : "bg-white/10 text-white/60 hover:text-white"
                }`}
              >
                {aiMode ? "🤖 AI Mode" : "Manual Mode"}
              </button>
              
              {saved && <span className="text-emerald-400 text-sm">✓ Saved</span>}
              {regen && (
                <span className="text-blue-400 text-sm">
                  {agentStates["threed"]?.message || "Regenerating 3D..."}
                </span>
              )}
              {modelUrl && !regen && (
                <a 
                  href={`/project/${id}/viewer?model=${encodeURIComponent(modelUrl)}`}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-sm font-medium transition-colors"
                >
                  View 3D Model
                </a>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto p-6">
        <div className="flex gap-6">
          {/* Editor */}
          <div className="flex-1">
            {aiMode ? (
              <AIFloorPlanEditor
                initialRooms={rooms}
                plotWidthM={project.plot_width_m || Math.sqrt(project.plot_area_sqm) * 1.2}
                plotDepthM={project.plot_depth_m || Math.sqrt(project.plot_area_sqm) * 0.9}
                plotAreaSqm={project.plot_area_sqm}
                fsiAllowed={project.fsi_allowed || 2.0}
                floors={project.floors}
                onSave={handleSave}
                onRegenerate3D={handleRegenerate3D}
              />
            ) : (
              <div className="bg-gray-900/50 rounded-xl p-8 text-center">
                <p className="text-white/60 mb-4">Switch to AI Mode for enhanced editing experience</p>
                <button
                  onClick={() => setAiMode(true)}
                  className="px-6 py-3 bg-gradient-to-r from-violet-600 to-cyan-600 rounded-lg font-medium"
                >
                  Enable AI Mode
                </button>
              </div>
            )}
          </div>

          {/* Smart Design Panel */}
          {aiMode && (
            <SmartDesignPanel
              projectId={id}
              currentDesign={{ rooms, project }}
              onDesignUpdate={handleDesignUpdate}
            />
          )}
        </div>
      </div>

      {/* AI Assistant */}
      {aiMode && (
        <AIAssistant
          projectId={id}
          onSuggestionApply={handleDesignUpdate}
        />
      )}
    </div>
  );
}
