"use client";
import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import FloorPlanEditor, { Room } from "@/components/editor/FloorPlanEditor";
import { useAgentProgress } from "@/lib/useAgentProgress";

export default function LayoutEditorPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject]   = useState<any>(null);
  const [rooms, setRooms]       = useState<Room[]>([]);
  const [saved, setSaved]       = useState(false);
  const [regen, setRegen]       = useState(false);
  const [modelUrl, setModelUrl] = useState<string | null>(null);
  const { agentStates }         = useAgentProgress(id);

  useEffect(() => {
    fetch(`/api/projects/${id}`).then(r => r.json()).then(data => {
      setProject(data);
      const variant = data.design_variants?.find((v: any) => v.is_selected) || data.design_variants?.[0];
      if (variant?.dna?.user_edited_rooms) {
        setRooms(variant.dna.user_edited_rooms);
      } else if (data.layout_data?.floor_plan?.rooms) {
        setRooms(data.layout_data.floor_plan.rooms);
      }
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
    await fetch(`/api/projects/${id}/layout`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rooms: editedRooms, active_floor: 0 }),
    });
    setRooms(editedRooms);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleRegenerate3D = async (editedRooms: Room[]) => {
    setRegen(true);
    await fetch(`/api/projects/${id}/regenerate-3d`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rooms: editedRooms, active_floor: 0 }),
    });
  };

  if (!project) return <div style={{ padding: 32 }}>Loading...</div>;

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "2rem 1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, margin: 0 }}>Floor plan editor</h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: 14, margin: "4px 0 0" }}>
            {project.name} · {project.plot_area_sqm} m² plot · {project.floors} floors
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {saved && <span style={{ fontSize: 12, color: "var(--color-text-success)" }}>Saved</span>}
          {regen && (
            <span style={{ fontSize: 12, color: "var(--color-text-info)" }}>
              {agentStates["threed"]?.message || "Regenerating 3D..."}
            </span>
          )}
          {modelUrl && !regen && (
            <a href={`/project/${id}/viewer?model=${encodeURIComponent(modelUrl)}`}
              style={{ fontSize: 13, padding: "6px 14px", background: "#E6F1FB", color: "#0C447C", border: "0.5px solid #185FA5", borderRadius: 8, textDecoration: "none" }}>
              View 3D model
            </a>
          )}
        </div>
      </div>

      <FloorPlanEditor
        initialRooms={rooms}
        plotWidthM={Math.sqrt(project.plot_area_sqm) * 1.2}
        plotDepthM={Math.sqrt(project.plot_area_sqm) * 0.9}
        plotAreaSqm={project.plot_area_sqm}
        fsiAllowed={project.fsi_allowed || 1.5}
        floors={project.floors}
        onSave={handleSave}
        onRegenerate3D={handleRegenerate3D}
      />
    </div>
  );
}
