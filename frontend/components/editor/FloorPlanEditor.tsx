"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Stage, Layer, Rect, Line, Text, Group, Circle } from "react-konva";
import Konva from "konva";
import useUndoable from "use-undoable";

// ─── Types ────────────────────────────────────────────────────────

export interface Room {
  id: string;
  name: string;
  type: RoomType;
  x: number; // metres from plot origin
  y: number;
  w: number; // width in metres
  h: number; // depth in metres
  floor: number;
  rotation?: number;
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

export interface FloorPlanEditorProps {
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

const SCALE = 36; // pixels per metre
const GRID = 0.5; // snap grid in metres
const PAD = 48; // canvas padding in pixels

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

const ROOM_TYPE_OPTIONS: RoomType[] = [
  "living",
  "dining",
  "kitchen",
  "master_bedroom",
  "bedroom",
  "bathroom",
  "balcony",
  "staircase",
  "study",
  "utility",
  "corridor",
  "pooja"
];

// ─── Helpers ──────────────────────────────────────────────────────

const snapM = (v: number) => Math.round(v / GRID) * GRID;
const mToPx = (m: number) => m * SCALE;
const pxToM = (px: number) => px / SCALE;
const uuid = () => Math.random().toString(36).slice(2, 9);
// ─── Component ────────────────────────────────────────────────────

export default function FloorPlanEditor({
  initialRooms,
  plotWidthM,
  plotDepthM,
  plotAreaSqm,
  fsiAllowed,
  floors,
  onSave,
  onRegenerate3D
}: FloorPlanEditorProps) {
  const [rooms, setRooms, { undo, redo, canUndo, canRedo }] = useUndoable<Room[]>(initialRooms);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tool, setTool] = useState<"select" | "draw" | "delete">("select");
  const [activeFloor, setActiveFloor] = useState(0);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawPreview, setDrawPreview] = useState<Room | null>(null);
  const [compliance, setCompliance] = useState<ComplianceResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [propPanel, setPropPanel] = useState<Room | null>(null);

  const stageRef = useRef<Konva.Stage>(null);
  const visibleRooms = rooms.filter(r => r.floor === activeFloor);
  const allRooms = rooms;

  // Live stats
  const totalBuiltUp = allRooms.reduce((s: number, r: Room) => s + r.w * r.h, 0) * floors;
  const fsiUsed = totalBuiltUp / plotAreaSqm;

  // ─── Compliance check ─────────────────────────────────────────

  interface ComplianceResult {
    passed: boolean;
    fsiOk: boolean;
    fsiUsed: number;
    fsiAllowed: number;
    issues: string[];
    warnings: string[];
  }

  const checkCompliance = useCallback((): ComplianceResult => {
    const issues: string[] = [];
    const warnings: string[] = [];

    const fsiOk = fsiUsed <= fsiAllowed;
    if (!fsiOk) {
      const excess = ((fsiUsed - fsiAllowed) * plotAreaSqm).toFixed(1);
      issues.push(`FSI ${fsiUsed.toFixed(2)} exceeds limit ${fsiAllowed} — reduce by ${excess} m²`);
    }

    // Check for overlapping rooms
    for (let i = 0; i < visibleRooms.length; i++) {
      for (let j = i + 1; j < visibleRooms.length; j++) {
        const a = visibleRooms[i], b = visibleRooms[j];
        const overlap = a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
        if (overlap) issues.push(`"${a.name}" overlaps with "${b.name}"`);
      }
    }

    // Check rooms inside plot
    for (const r of visibleRooms) {
      if (r.x < 0 || r.y < 0 || r.x + r.w > plotWidthM || r.y + r.h > plotDepthM) {
        issues.push(`"${r.name}" extends outside plot boundary`);
      }
    }

    if (!visibleRooms.some((r: Room) => r.type === "staircase") && floors > 1) {
      warnings.push("No staircase defined — required for multi-floor building");
    }

    if (!visibleRooms.some((r: Room) => ["bathroom", "master_bedroom"].includes(r.type))) {
      warnings.push("No bathroom found on this floor");
    }

    return {
      passed: issues.length === 0,
      fsiOk,
      fsiUsed,
      fsiAllowed,
      issues,
      warnings
    };
  }, [fsiUsed, fsiAllowed, plotAreaSqm, plotWidthM, plotDepthM, floors, visibleRooms]);

  // Run compliance whenever rooms change
  useEffect(() => {
    setCompliance(checkCompliance());
  }, [rooms, checkCompliance]);
  // ─── Canvas event handlers ──────────────────────────────────────

  const handleStageMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (tool !== "draw") return;
    const stage = stageRef.current!;
    const pos = stage.getPointerPosition()!;
    const mx = snapM(pxToM(pos.x - PAD));
    const my = snapM(pxToM(pos.y - PAD));
    setDrawStart({ x: mx, y: my });
  };

  const handleStageMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (tool !== "draw" || !drawStart) return;
    const pos = stageRef.current!.getPointerPosition()!;
    const mx = snapM(pxToM(pos.x - PAD));
    const my = snapM(pxToM(pos.y - PAD));

    const x = Math.min(drawStart.x, mx);
    const y = Math.min(drawStart.y, my);
    const w = Math.abs(mx - drawStart.x);
    const h = Math.abs(my - drawStart.y);

    if (w > GRID && h > GRID) {
      setDrawPreview({
        id: "preview",
        name: "New room",
        type: "bedroom",
        x, y, w, h,
        floor: activeFloor
      });
    }
  };

  const handleStageMouseUp = () => {
    if (tool !== "draw" || !drawPreview) {
      setDrawStart(null);
      setDrawPreview(null);
      return;
    }

    const newRoom: Room = {
      ...drawPreview,
      id: uuid(),
      name: "New room"
    };

    setRooms([...rooms, newRoom]);
    setSelectedId(newRoom.id);
    setPropPanel(newRoom);
    setDrawStart(null);
    setDrawPreview(null);
  };

  // ─── Room drag ──────────────────────────────────────────────────

  const handleDragEnd = (id: string, e: Konva.KonvaEventObject<DragEvent>) => {
    const node = e.target;
    const newX = snapM(pxToM(node.x()));
    const newY = snapM(pxToM(node.y()));
    setRooms(rooms.map((r: Room) => r.id === id ? { ...r, x: newX, y: newY } : r));
  };

  // ─── Room click ─────────────────────────────────────────────────

  const handleRoomClick = (room: Room) => {
    if (tool === "delete") {
      setRooms(rooms.filter((r: Room) => r.id !== room.id));
      setSelectedId(null);
      setPropPanel(null);
      return;
    }
    setSelectedId(room.id);
    setPropPanel(room);
  };

  // ─── Property panel updates ─────────────────────────────────────

  const updateRoom = (id: string, patch: Partial<Room>) => {
    const updated = rooms.map((r: Room) => r.id === id ? { ...r, ...patch } : r);
    setRooms(updated);
    const r = updated.find((r: Room) => r.id === id);
    if (r) setPropPanel(r);
  };

  // ─── Save & regenerate ──────────────────────────────────────────

  const handleSave = async () => {
    setSaving(true);
    await onSave(rooms);
    setSaving(false);
  };
  // ─── Dimension label helper ─────────────────────────────────────

  const DimLabel = ({ room }: { room: Room }) => {
    return (
      <>
        <Text
          x={mToPx(room.x)}
          y={mToPx(room.y) - 14}
          width={mToPx(room.w)}
          text={`${room.w.toFixed(1)}m`}
          fontSize={9}
          fill="#185FA5"
          align="center"
        />
        <Text
          x={mToPx(room.x) - 24}
          y={mToPx(room.y)}
          width={22}
          height={mToPx(room.h)}
          text={`${room.h.toFixed(1)}m`}
          fontSize={9}
          fill="#185FA5"
          verticalAlign="middle"
          align="right"
        />
      </>
    );
  };

  const stageW = mToPx(plotWidthM) + PAD * 2;
  const stageH = mToPx(plotDepthM) + PAD * 2;

  // ─── Render ─────────────────────────────────────────────────────

  return (
    <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
      {/* ── Canvas area ── */}
      <div>
        {/* Toolbar */}
        <div style={{ display: "flex", gap: 8, marginBottom: 10, alignItems: "center", flexWrap: "wrap" }}>
          {(["select", "draw", "delete"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTool(t)}
              style={{
                padding: "4px 12px",
                fontSize: 12,
                borderRadius: 8,
                cursor: "pointer",
                border: tool === t ? "0.5px solid #185FA5" : "0.5px solid var(--color-border-secondary)",
                background: tool === t ? "#E6F1FB" : "var(--color-background-secondary)",
                color: tool === t ? "#0C447C" : "var(--color-text-secondary)"
              }}
            >
              {t === "select" ? "Select" : t === "draw" ? "+ Draw room" : "Delete"}
            </button>
          ))}

          <div style={{ width: 1, height: 20, background: "var(--color-border-tertiary)" }} />

          <button
            onClick={undo}
            disabled={!canUndo}
            style={{
              padding: "4px 10px",
              fontSize: 12,
              borderRadius: 8,
              cursor: canUndo ? "pointer" : "default",
              border: "0.5px solid var(--color-border-secondary)",
              background: "var(--color-background-secondary)",
              opacity: canUndo ? 1 : 0.4,
              color: "var(--color-text-secondary)"
            }}
          >
            Undo
          </button>

          <button
            onClick={redo}
            disabled={!canRedo}
            style={{
              padding: "4px 10px",
              fontSize: 12,
              borderRadius: 8,
              cursor: canRedo ? "pointer" : "default",
              border: "0.5px solid var(--color-border-secondary)",
              background: "var(--color-background-secondary)",
              opacity: canRedo ? 1 : 0.4,
              color: "var(--color-text-secondary)"
            }}
          >
            Redo
          </button>

          <div style={{ width: 1, height: 20, background: "var(--color-border-tertiary)" }} />

          {Array.from({ length: floors }).map((_, i) => (
            <button
              key={i}
              onClick={() => setActiveFloor(i)}
              style={{
                padding: "4px 10px",
                fontSize: 12,
                borderRadius: 8,
                cursor: "pointer",
                border: activeFloor === i ? "0.5px solid #185FA5" : "0.5px solid var(--color-border-secondary)",
                background: activeFloor === i ? "#E6F1FB" : "var(--color-background-secondary)",
                color: activeFloor === i ? "#0C447C" : "var(--color-text-secondary)"
              }}
            >
              Floor {i + 1}
            </button>
          ))}
        </div>
        {/* Konva Stage */}
        <div style={{ border: "0.5px solid var(--color-border-secondary)", borderRadius: 12, overflow: "hidden" }}>
          <Stage
            ref={stageRef}
            width={stageW}
            height={stageH}
            style={{
              background: "#faf9f6",
              cursor: tool === "draw" ? "crosshair" : tool === "delete" ? "not-allowed" : "default"
            }}
            onMouseDown={handleStageMouseDown}
            onMouseMove={handleStageMouseMove}
            onMouseUp={handleStageMouseUp}
            onClick={() => {
              if (tool === "select") {
                setSelectedId(null);
                setPropPanel(null);
              }
            }}
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
              {visibleRooms.map(room => {
                const isSel = selectedId === room.id;
                return (
                  <Group
                    key={room.id}
                    x={PAD + mToPx(room.x)}
                    y={PAD + mToPx(room.y)}
                    draggable={tool === "select"}
                    onDragEnd={e => handleDragEnd(room.id, e)}
                    dragBoundFunc={pos => ({
                      x: Math.max(PAD, Math.min(PAD + mToPx(plotWidthM - room.w), snapM(pxToM(pos.x - PAD)) * SCALE + PAD)),
                      y: Math.max(PAD, Math.min(PAD + mToPx(plotDepthM - room.h), snapM(pxToM(pos.y - PAD)) * SCALE + PAD)),
                    })}
                    onClick={e => {
                      e.cancelBubble = true;
                      handleRoomClick(room);
                    }}
                  >
                    <Rect
                      width={mToPx(room.w)}
                      height={mToPx(room.h)}
                      fill={ROOM_COLORS[room.type as RoomType]}
                      stroke={isSel ? "#185FA5" : ROOM_STROKE[room.type as RoomType]}
                      strokeWidth={isSel ? 2 : 1}
                      cornerRadius={2}
                    />

                    {/* Selection handles */}
                    {isSel && [[0,0],[mToPx(room.w),0],[0,mToPx(room.h)],[mToPx(room.w),mToPx(room.h)]].map(([hx,hy],i) => (
                      <Circle key={i} x={hx} y={hy} radius={4} fill="#185FA5" />
                    ))}
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

                    {/* Dimension labels when selected */}
                    {isSel && <DimLabel room={{ ...room, x: 0, y: 0 }} />}
                  </Group>
                );
              })}

              {/* Draw preview */}
              {drawPreview && (
                <Rect
                  x={PAD + mToPx(drawPreview.x)}
                  y={PAD + mToPx(drawPreview.y)}
                  width={mToPx(drawPreview.w)}
                  height={mToPx(drawPreview.h)}
                  fill="rgba(24,95,165,0.1)"
                  stroke="#185FA5"
                  strokeWidth={1.5}
                  dash={[4, 4]}
                />
              )}

              {/* Scale bar */}
              <Line
                points={[PAD, PAD + mToPx(plotDepthM) + 18, PAD + mToPx(5), PAD + mToPx(plotDepthM) + 18]}
                stroke="rgba(0,0,0,0.25)"
                strokeWidth={1}
              />
              <Text
                x={PAD}
                y={PAD + mToPx(plotDepthM) + 22}
                width={mToPx(5)}
                text="5 m"
                fontSize={9}
                fill="rgba(0,0,0,0.35)"
                align="center"
              />

              {/* Compass */}
              <Text
                x={PAD + 4}
                y={PAD + 4}
                text="N ↑"
                fontSize={9}
                fill="rgba(0,0,0,0.3)"
              />
            </Layer>
          </Stage>
        </div>
      </div>
      {/* ── Side panel ── */}
      <div style={{ minWidth: 200, display: "flex", flexDirection: "column", gap: 10 }}>
        {/* Stats */}
        {[
          { label: "Built-up area", value: `${totalBuiltUp.toFixed(1)} m²` },
          { label: `FSI used / ${fsiAllowed}`, value: fsiUsed.toFixed(2), warn: fsiUsed > fsiAllowed },
          { label: "Rooms on floor", value: `${visibleRooms.length}` },
        ].map((s: { label: string; value: string; warn?: boolean }) => (
          <div key={s.label} style={{ background: "var(--color-background-secondary)", borderRadius: 8, padding: "10px 12px" }}>
            <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginBottom: 2 }}>{s.label}</div>
            <div style={{ fontSize: 18, fontWeight: 500, color: s.warn ? "var(--color-text-danger)" : "var(--color-text-primary)" }}>{s.value}</div>
          </div>
        ))}

        {/* Compliance */}
        {compliance && (
          <div style={{
            background: compliance.passed ? "#EAF3DE" : "#FCEBEB",
            border: `0.5px solid ${compliance.passed ? "#97C459" : "#F09595"}`,
            borderRadius: 8,
            padding: "10px 12px"
          }}>
            <div style={{
              fontSize: 13,
              fontWeight: 500,
              color: compliance.passed ? "#27500a" : "#791f1f",
              marginBottom: 5
            }}>
              {compliance.passed ? "Compliant" : `${compliance.issues.length} issue${compliance.issues.length > 1 ? "s" : ""}`}
            </div>
            {compliance.issues.map((iss, i) => (
              <div key={i} style={{ fontSize: 11, color: "#791f1f", marginBottom: 3 }}>{iss}</div>
            ))}
            {compliance.warnings.map((w, i) => (
              <div key={i} style={{ fontSize: 11, color: "#633806", marginBottom: 3 }}>{w}</div>
            ))}
            {compliance.passed && <div style={{ fontSize: 11, color: "#3B6D11" }}>Layout is valid and ready to export.</div>}
          </div>
        )}
        {/* Room properties panel */}
        {propPanel && (
          <div style={{
            background: "var(--color-background-primary)",
            border: "0.5px solid var(--color-border-tertiary)",
            borderRadius: 8,
            padding: 12
          }}>
            <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 10 }}>Room properties</div>

            <label style={{ fontSize: 11, color: "var(--color-text-secondary)", display: "block", marginBottom: 4 }}>Name</label>
            <input
              value={propPanel.name}
              onChange={e => updateRoom(propPanel.id, { name: e.target.value })}
              style={{ width: "100%", marginBottom: 10, fontSize: 13 }}
            />

            <label style={{ fontSize: 11, color: "var(--color-text-secondary)", display: "block", marginBottom: 4 }}>Type</label>
            <select
              value={propPanel.type}
              onChange={e => updateRoom(propPanel.id, { type: e.target.value as RoomType })}
              style={{ width: "100%", marginBottom: 10, fontSize: 13 }}
            >
              {ROOM_TYPE_OPTIONS.map(t => (
                <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
              ))}
            </select>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 8 }}>
              {(["w", "h"] as const).map(dim => (
                <div key={dim}>
                  <label style={{ fontSize: 11, color: "var(--color-text-secondary)", display: "block", marginBottom: 4 }}>
                    {dim === "w" ? "Width (m)" : "Depth (m)"}
                  </label>
                  <input
                    type="number"
                    step={GRID}
                    min={GRID}
                    value={propPanel[dim].toFixed(1)}
                    onChange={e => updateRoom(propPanel.id, { [dim]: snapM(parseFloat(e.target.value) || GRID) })}
                    style={{ width: "100%", fontSize: 13 }}
                  />
                </div>
              ))}
            </div>

            <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 8 }}>
              Area: {(propPanel.w * propPanel.h).toFixed(1)} m²
            </div>

            <button
              onClick={() => {
                setRooms(rooms.filter(r => r.id !== propPanel.id));
                setSelectedId(null);
                setPropPanel(null);
              }}
              style={{
                width: "100%",
                padding: "6px",
                fontSize: 12,
                borderRadius: 8,
                border: "0.5px solid var(--color-border-danger)",
                background: "transparent",
                color: "var(--color-text-danger)",
                cursor: "pointer"
              }}
            >
              Delete room
            </button>
          </div>
        )}
        {/* Actions */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              padding: "8px",
              fontSize: 13,
              borderRadius: 8,
              border: "0.5px solid var(--color-border-secondary)",
              background: "var(--color-background-secondary)",
              cursor: "pointer",
              color: "var(--color-text-primary)"
            }}
          >
            {saving ? "Saving..." : "Save layout"}
          </button>

          <button
            onClick={() => onRegenerate3D(rooms)}
            disabled={!compliance?.passed}
            style={{
              padding: "8px",
              fontSize: 13,
              borderRadius: 8,
              border: compliance?.passed ? "0.5px solid #185FA5" : "0.5px solid var(--color-border-tertiary)",
              background: compliance?.passed ? "#E6F1FB" : "var(--color-background-secondary)",
              cursor: compliance?.passed ? "pointer" : "default",
              color: compliance?.passed ? "#0C447C" : "var(--color-text-secondary)"
            }}
          >
            Regenerate 3D model
          </button>

          <button
            onClick={() => exportDXF(rooms, plotWidthM, plotDepthM)}
            style={{
              padding: "8px",
              fontSize: 13,
              borderRadius: 8,
              border: "0.5px solid var(--color-border-secondary)",
              background: "transparent",
              cursor: "pointer",
              color: "var(--color-text-secondary)"
            }}
          >
            Export DXF
          </button>
        </div>
      </div>
    </div>
  );
}
// ─── Client-side DXF export (lightweight, no backend needed) ───

function exportDXF(rooms: Room[], _plotW: number, _plotH: number) {
  const scale = 1000; // mm
  let dxf = `0\nSECTION\n2\nENTITIES\n`;

  rooms.forEach((r: Room) => {
    const x1 = r.x * scale, y1 = r.y * scale;
    const x2 = (r.x + r.w) * scale, y2 = (r.y + r.h) * scale;

    dxf += `0\nLWPOLYLINE\n8\n${r.type.toUpperCase()}\n90\n4\n70\n1\n`;
    dxf += `10\n${x1}\n20\n${y1}\n`;
    dxf += `10\n${x2}\n20\n${y1}\n`;
    dxf += `10\n${x2}\n20\n${y2}\n`;
    dxf += `10\n${x1}\n20\n${y2}\n`;

    dxf += `0\nTEXT\n8\n${r.type.toUpperCase()}\n10\n${(x1+x2)/2}\n20\n${(y1+y2)/2}\n40\n200\n1\n${r.name} ${(r.w*r.h).toFixed(1)}sqm\n`;
  });

  dxf += `0\nENDSEC\n0\nEOF\n`;

  const blob = new Blob([dxf], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "archai-floorplan.dxf";
  a.click();
}