/**
 * app/project/[id]/viewer/page.tsx
 *
 * Standalone 3D model viewer page for a project variant.
 * Route: /project/[id]/viewer?variant=<variantId>&model=<glbUrl>
 *
 * This page is designed to work in two modes:
 *   1. With a real GLB URL from Supabase Storage (production)
 *   2. With a demo placeholder cube (development / no Blender setup)
 */

"use client";

import { useState, useEffect, Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";
import ViewerWrapper from "@/components/viewer3d/ViewerWrapper";
import Link from "next/link";
import Image from "next/image";

// ─── Demo fallback ────────────────────────────────────────────────────────────
// A tiny valid GLB (single white cube) encoded as a data-URL.
// Generated with: https://sandbox.babylonjs.com/ → export cube → base64
// Replace with a real generated model in production.
const DEMO_GLB_DATA_URL =
  "data:model/gltf-binary;base64,Z2xURgIAAAC0AQAAZAAAA0pTT057ImFzc2V0Ijp7InZlcnNpb24iOiIyLjAifSwic2NlbmUiOjAsInNjZW5lcyI6W3sibm9kZXMiOlswXX1dLCJub2RlcyI6W3sibWVzaCI6MH1dLCJtZXNoZXMiOlt7InByaW1pdGl2ZXMiOlt7ImF0dHJpYnV0ZXMiOnsiUE9TSVRJT04iOjF9LCJpbmRpY2VzIjowfV19XSwiYWNjZXNzb3JzIjpbeyJidWZmZXJWaWV3IjowLCJjb21wb25lbnRUeXBlIjo1MTIzLCJjb3VudCI6MzYsInR5cGUiOiJTQ0FMQVIifSx7ImJ1ZmZlclZpZXciOjEsImNvbXBvbmVudFR5cGUiOjUxMjYsImNvdW50Ijo4LCJ0eXBlIjoiVkVDMyIsIm1heCI6WzEsMSwxXSwibWluIjpbLTEsLTEsLTFdfV0sImJ1ZmZlclZpZXdzIjpbeyJidWZmZXIiOjAsImJ5dGVPZmZzZXQiOjAsImJ5dGVMZW5ndGgiOjcyfSx7ImJ1ZmZlciI6MCwiYnl0ZU9mZnNldCI6NzIsImJ5dGVMZW5ndGgiOjk2fV0sImJ1ZmZlcnMiOlt7ImJ5dGVMZW5ndGgiOjE2OH1dfQAAAAAAAAAAkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/////wAAAAAAAAAAAAEAAQAAAAIAAAADAAMAAAACAAAABAAAAAUABAAAAAgABgAHAAAACAAJAAAACgAKAAAACwAAAA0ADAAAAAsADgAAAA8ADwAAAA4AAAARABAAAAARABIAAAATAAAAFQAUAAAAFQAWAAAAFwAAABkAGAAAABkAGgAAABsAAAD/gAAAAAAAAID/gAAAAAAAAAAAAIAAAAAAAACAAAAAAAAAgD+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAeAAAAAAAAIA/AAAAAAAAQAAAAAAAAAA=";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ViewerPage() {
  const params       = useParams<{ id: string }>();
  const searchParams = useSearchParams();

  const projectId = params?.id ?? "";
  const variantId = searchParams?.get("variant") ?? "";
  const modelUrl  = searchParams?.get("model")   ?? "";

  // Optional lat/lng injected by the project page when opening the viewer.
  // Falls back to Pune (ArchAI default demo location) so the sun button always
  // appears even for demo models that don't carry coordinates.
  const latitude  = parseFloat(searchParams?.get("lat")  ?? "18.5204");
  const longitude = parseFloat(searchParams?.get("lng")  ?? "73.8567");

  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [loaded,        setLoaded]        = useState(false);

  // Resolve which URL to actually load
  const resolvedUrl = modelUrl || DEMO_GLB_DATA_URL;
  const isDemo      = !modelUrl;

  return (
    <div
      style={{
        minHeight:   "100vh",
        background:  "#080c18",
        color:       "white",
        fontFamily:  "'Inter', sans-serif",
        padding:     "24px",
        display:     "flex",
        flexDirection:"column",
        gap:         20,
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link
            href={projectId ? `/dashboard` : "/"}
            style={{
              display:        "flex",
              alignItems:     "center",
              gap:            6,
              padding:        "6px 12px",
              borderRadius:   10,
              background:     "rgba(255,255,255,0.06)",
              border:         "1px solid rgba(255,255,255,0.1)",
              color:          "rgba(255,255,255,0.7)",
              textDecoration: "none",
              fontSize:       13,
            }}
          >
            ← Back
          </Link>

          <div>
            <h1 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>
              3D Model Viewer
            </h1>
            <p style={{ margin: 0, fontSize: 12, color: "rgba(255,255,255,0.35)" }}>
              {isDemo ? "Demo model — connect Blender pipeline for real output" : `Variant ${variantId.slice(0, 8)}…`}
            </p>
          </div>

          {isDemo && (
            <span
              style={{
                padding:    "3px 10px",
                borderRadius:20,
                background: "rgba(245,158,11,0.15)",
                border:     "1px solid rgba(245,158,11,0.3)",
                color:      "#fbbf24",
                fontSize:   11,
                fontWeight: 600,
              }}
            >
              DEMO
            </span>
          )}
        </div>

        {/* Screenshot preview */}
        {screenshotUrl && (
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Image
              src={screenshotUrl}
              alt="Screenshot"
              width={80}
              height={50}
              style={{
                objectFit:    "cover",
                borderRadius: 8,
                border:       "1px solid rgba(255,255,255,0.12)",
              }}
            />
            <a
              href={screenshotUrl}
              download="archai-screenshot.png"
              style={{
                fontSize:    12,
                color:       "#a78bfa",
                textDecoration:"underline",
                cursor:      "pointer",
              }}
            >
              Save screenshot
            </a>
          </div>
        )}
      </div>

      {/* Viewer */}
      <div style={{ flex: 1 }}>
        <ViewerWrapper
          modelUrl={resolvedUrl}
          height={580}
          onScreenshot={setScreenshotUrl}
          onLoad={() => setLoaded(true)}
          latitude={latitude}
          longitude={longitude}
        />
      </div>

      {/* Info bar */}
      <div
        style={{
          display:   "flex",
          gap:       24,
          padding:   "14px 20px",
          borderRadius:14,
          background:"rgba(255,255,255,0.03)",
          border:    "1px solid rgba(255,255,255,0.07)",
          flexWrap:  "wrap",
        }}
      >
        {[
          { label: "Renderer",  value: "Three.js r162" },
          { label: "Format",    value: "GLTF 2.0 / GLB" },
          { label: "Lighting",  value: "ACES Filmic · PCF Soft Shadows" },
          { label: "Decoder",   value: "Draco (Google 1.5.6)" },
          { label: "Controls",  value: "OrbitControls · Damp 0.06" },
          { label: "Sun sim",   value: `${latitude.toFixed(2)}°N · ${longitude.toFixed(2)}°E` },
          { label: "Status",    value: loaded ? "✅ Loaded" : "⏳ Loading…" },
        ].map(({ label, value }) => (
          <div key={label}>
            <p style={{ margin: 0, fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
            <p style={{ margin: 0, fontSize: 13, color: "rgba(255,255,255,0.75)", fontWeight: 500, marginTop: 2 }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Keyboard shortcuts */}
      <div
        style={{
          display:   "flex",
          gap:       16,
          flexWrap:  "wrap",
          justifyContent: "center",
        }}
      >
        {[
          ["Left-drag",  "Orbit"],
          ["Right-drag", "Pan"],
          ["Scroll",     "Zoom"],
          ["Double-click","Reset"],
        ].map(([key, action]) => (
          <span key={key} style={{ fontSize: 11, color: "rgba(255,255,255,0.25)" }}>
            <kbd style={{
              padding:      "1px 6px",
              borderRadius: 4,
              background:   "rgba(255,255,255,0.07)",
              border:       "1px solid rgba(255,255,255,0.12)",
              fontFamily:   "monospace",
              fontSize:     10,
            }}>{key}</kbd>
            {" "}
            {action}
          </span>
        ))}
      </div>
    </div>
  );
}
