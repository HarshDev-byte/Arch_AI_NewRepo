"use client";

/**
 * SunControls.tsx — Solar simulation scrubber UI for the ArchAI 3D viewer.
 *
 * Renders an overlay panel with:
 *   - Time-of-day slider (06:00 – 20:00)
 *   - Month slider (Jan – Dec)
 *   - Animated sun position readout (azimuth°, elevation°)
 *   - Sunrise / solar-noon / sunset markers
 *   - "Animate" toggle that auto-advances time in real-time
 */

import { useState, useEffect, useRef, useCallback } from "react";
import * as THREE from "three";
import { getSunPosition, getSunState, SunState } from "./SunSimulator";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SunControlsProps {
  latitude:    number;
  longitude:   number;
  /** Called whenever the sun position / intensity changes */
  onSunChange: (state: SunState) => void;
  /** Initial hour (6–20), default 12 */
  initialHour?:  number;
  /** Initial month (1–12), default 6 */
  initialMonth?: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

/** Estimate sunrise / solar noon / sunset for a given lat/lon/month. */
function estimateDayTimes(lat: number, lon: number, month: number): {
  sunrise: number; noon: number; sunset: number;
} {
  const noon = 12;
  const dayOfYear = (month - 1) * 30 + 15;
  const declRad   = (23.45 * Math.PI / 180) * Math.sin(
    (2 * Math.PI / 365) * (dayOfYear - 81),
  );
  const latRad = lat * Math.PI / 180;
  const cos_ha = -Math.tan(latRad) * Math.tan(declRad);
  // Clamp — extreme latitudes may have polar day/night
  const ha_deg  = Math.abs(cos_ha) <= 1
    ? (Math.acos(cos_ha) * 180 / Math.PI) / 15
    : cos_ha > 1 ? 0 : 12;
  return {
    sunrise: Math.max(4,  noon - ha_deg),
    noon,
    sunset:  Math.min(20, noon + ha_deg),
  };
}

function fmt(h: number) {
  const hrs  = Math.floor(h);
  const mins = Math.round((h - hrs) * 60);
  return `${String(hrs).padStart(2,"0")}:${String(mins).padStart(2,"0")}`;
}

function toDeg(rad: number) {
  return ((rad * 180) / Math.PI).toFixed(1);
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function SunControls({
  latitude,
  longitude,
  onSunChange,
  initialHour  = 12,
  initialMonth = 6,
}: SunControlsProps) {
  const [hour,     setHour]     = useState(initialHour);
  const [month,    setMonth]    = useState(initialMonth);
  const [animate,  setAnimate]  = useState(false);
  const [sunPos,   setSunPos]   = useState<{ az: number; el: number }>({ az: 0, el: 0 });
  const animRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Compute + emit sun state whenever hour/month changes ─────────────────────
  const updateSun = useCallback((h: number, m: number) => {
    const date  = new Date(2024, m - 1, 15, Math.floor(h), Math.round((h % 1) * 60));
    const pos   = getSunPosition(latitude, longitude, date);
    const state = getSunState(latitude, longitude, date);
    setSunPos({ az: pos.azimuth, el: pos.elevation });
    onSunChange(state);
  }, [latitude, longitude, onSunChange]);

  useEffect(() => { updateSun(hour, month); }, [hour, month, updateSun]);

  // ── Auto-animate ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (animate) {
      animRef.current = setInterval(() => {
        setHour((h) => {
          const next = h + 0.05;                       // ~3 min per tick
          return next > 20 ? 6 : next;
        });
      }, 50);
    } else {
      if (animRef.current) clearInterval(animRef.current);
    }
    return () => { if (animRef.current) clearInterval(animRef.current); };
  }, [animate]);

  const { sunrise, noon, sunset } = estimateDayTimes(latitude, longitude, month);

  // Derived sky colour for the gradient bar
  const skyPct    = Math.max(0, Math.min(1, (hour - sunrise) / (sunset - sunrise)));
  const elevDeg   = parseFloat(toDeg(sunPos.el));
  const isDay     = elevDeg > 0;
  const skyGrad   = isDay
    ? `linear-gradient(90deg, #1a0a08 0%, #f97316 ${Math.round(skyPct * 25)}%, #fed7aa ${Math.round(skyPct * 50)}%, #bfdbfe 70%, #1e3a5f 100%)`
    : "linear-gradient(90deg,#050a14,#0f172a)";

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div
      id="sun-controls-panel"
      style={{
        padding:        "12px 14px",
        borderRadius:   14,
        background:     "rgba(10,14,26,0.82)",
        backdropFilter: "blur(14px)",
        border:         "1px solid rgba(255,255,255,0.09)",
        minWidth:       260,
        display:        "flex",
        flexDirection:  "column",
        gap:            10,
        color:          "white",
        fontFamily:     "'Inter', sans-serif",
      }}
    >
      {/* Title row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 16 }}>{isDay ? "☀️" : "🌙"}</span>
          <span style={{ fontSize: 13, fontWeight: 600 }}>Sun Simulator</span>
        </div>
        <button
          id="sun-animate-btn"
          onClick={() => setAnimate((a) => !a)}
          style={{
            fontSize:   11,
            padding:    "3px 10px",
            borderRadius: 20,
            border:     `1px solid ${animate ? "rgba(251,191,36,0.5)" : "rgba(255,255,255,0.12)"}`,
            background: animate ? "rgba(251,191,36,0.15)" : "rgba(255,255,255,0.06)",
            color:      animate ? "#fbbf24" : "rgba(255,255,255,0.5)",
            cursor:     "pointer",
            fontWeight: 500,
          }}
        >
          {animate ? "⏸ Stop" : "▶ Animate"}
        </button>
      </div>

      {/* Sky gradient bar */}
      <div style={{ height: 6, borderRadius: 3, background: skyGrad, position: "relative" }}>
        {/* Sun indicator */}
        <div style={{
          position:  "absolute",
          top:       "50%",
          left:      `${Math.max(2, Math.min(96, skyPct * 100))}%`,
          transform: "translate(-50%,-50%)",
          width:     12,
          height:    12,
          borderRadius: "50%",
          background: isDay ? "#fbbf24" : "#e2e8f0",
          boxShadow:  isDay ? "0 0 8px #fbbf24" : "0 0 6px #94a3b8",
          transition: "left 0.3s ease",
        }} />
        {/* Sunrise / noon / sunset labels */}
        {[
          { label: "🌅", val: sunrise, align: "flex-start" },
          { label: "🌞", val: noon,    align: "center" },
          { label: "🌇", val: sunset,  align: "flex-end" },
        ].map(({ label, val }) => (
          <button
            key={label}
            title={fmt(val)}
            onClick={() => setHour(val)}
            style={{
              position:   "absolute",
              top:        12,
              left:       `${((val - 4) / 16) * 100}%`,
              transform:  "translateX(-50%)",
              background: "none",
              border:     "none",
              fontSize:   11,
              cursor:     "pointer",
              padding:    0,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div style={{ height: 16 }} /> {/* space for emoji labels */}

      {/* Time slider */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Time of day</span>
          <span style={{ fontSize: 12, fontWeight: 600, color: "#fbbf24" }}>{fmt(hour)}</span>
        </div>
        <input
          id="sun-hour-slider"
          type="range"
          min={4}
          max={20}
          step={0.25}
          value={hour}
          onChange={(e) => { setAnimate(false); setHour(parseFloat(e.target.value)); }}
          style={{ width: "100%", accentColor: "#f59e0b" }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "rgba(255,255,255,0.25)", marginTop: 2 }}>
          <span>04:00</span><span>08:00</span><span>12:00</span><span>16:00</span><span>20:00</span>
        </div>
      </div>

      {/* Month slider */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Month</span>
          <span style={{ fontSize: 12, fontWeight: 600, color: "#60a5fa" }}>{MONTH_NAMES[month - 1]}</span>
        </div>
        <input
          id="sun-month-slider"
          type="range"
          min={1}
          max={12}
          step={1}
          value={month}
          onChange={(e) => setMonth(parseInt(e.target.value))}
          style={{ width: "100%", accentColor: "#3b82f6" }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "rgba(255,255,255,0.25)", marginTop: 2 }}>
          {["Jan","","Mar","","May","","Jul","","Sep","","Nov",""].map((m, i) => (
            <span key={i}>{m}</span>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div style={{
        display:       "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gap:           6,
        padding:       "8px 10px",
        borderRadius:  10,
        background:    "rgba(255,255,255,0.04)",
        border:        "1px solid rgba(255,255,255,0.06)",
      }}>
        {[
          { label: "Elevation", value: `${toDeg(sunPos.el)}°`, color: "#fbbf24" },
          { label: "Azimuth",   value: `${toDeg(sunPos.az)}°`, color: "#60a5fa" },
          { label: "Sunrise",   value: fmt(sunrise),            color: "#34d399" },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ textAlign: "center" }}>
            <p style={{ margin: 0, fontSize: 9, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
            <p style={{ margin: "2px 0 0", fontSize: 13, fontWeight: 600, color }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Location */}
      <p style={{ margin: 0, fontSize: 10, color: "rgba(255,255,255,0.2)", textAlign: "center" }}>
        {latitude.toFixed(4)}°N  {longitude.toFixed(4)}°E
      </p>
    </div>
  );
}
