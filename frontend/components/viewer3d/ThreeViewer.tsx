"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/examples/jsm/loaders/DRACOLoader.js";
import SunControls from "./SunControls";
import type { SunState } from "./SunSimulator";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ThreeViewerProps {
  modelUrl:       string;
  height?:        number;
  onScreenshot?:  (dataUrl: string) => void;
  onLoad?:        () => void;
  className?:     string;
  /** Project latitude — enables sun simulation panel */
  latitude?:      number;
  /** Project longitude — enables sun simulation panel */
  longitude?:     number;
}

type MaterialKey = "default" | "concrete" | "glass" | "wood" | "brick" | "steel";
type ViewMode    = "orbit"   | "top"      | "front"  | "side";
type EnvMode     = "day"     | "dusk"     | "night";

// ─── Material presets ─────────────────────────────────────────────────────────

const MAT_PRESETS: Record<MaterialKey, Partial<THREE.MeshStandardMaterialParameters> | null> = {
  default:  null,
  concrete: { color: 0xc2bbb0, roughness: 0.85, metalness: 0.0 },
  glass:    { color: 0x9ecfed, roughness: 0.02, metalness: 0.05, transparent: true, opacity: 0.45 },
  wood:     { color: 0x9c7240, roughness: 0.88, metalness: 0.0 },
  brick:    { color: 0xaa5533, roughness: 0.95, metalness: 0.0 },
  steel:    { color: 0xd0d8e0, roughness: 0.2,  metalness: 0.9 },
};

// ─── Environment presets ──────────────────────────────────────────────────────

const ENV_PRESETS: Record<EnvMode, {
  bg:       number;
  fog:      number;
  ambient:  number;
  sunColor: number;
  sunInt:   number;
  fillColor:number;
  fillInt:  number;
  sunPos:   [number,number,number];
}> = {
  day: {
    bg: 0xdde8f5, fog: 0xdde8f5,
    ambient: 0.45, sunColor: 0xfff4d6, sunInt: 2.8,
    fillColor: 0xb0c8ff, fillInt: 0.9,
    sunPos: [40, 60, 30],
  },
  dusk: {
    bg: 0x2a1530, fog: 0x2a1530,
    ambient: 0.15, sunColor: 0xff8844, sunInt: 1.8,
    fillColor: 0x4433aa, fillInt: 0.5,
    sunPos: [60, 15, 40],
  },
  night: {
    bg: 0x0a0e1a, fog: 0x0a0e1a,
    ambient: 0.08, sunColor: 0x4466cc, sunInt: 0.6,
    fillColor: 0x222255, fillInt: 0.3,
    sunPos: [-20, 30, -10],
  },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function positionCamera(
  camera:   THREE.PerspectiveCamera,
  controls: OrbitControls,
  box:      THREE.Box3,
  view:     ViewMode,
) {
  const size   = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const d      = Math.max(size.x, size.y, size.z) * 2;

  controls.target.set(center.x, center.y, center.z);

  switch (view) {
    case "top":
      camera.position.set(center.x, center.y + d, center.z + 0.01);
      break;
    case "front":
      camera.position.set(center.x, center.y, center.z + d);
      break;
    case "side":
      camera.position.set(center.x + d, center.y, center.z);
      break;
    default: // orbit
      camera.position.set(center.x + d * 0.8, center.y + d * 0.55, center.z + d * 0.8);
  }
  controls.update();
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function ThreeViewer({
  modelUrl,
  height    = 540,
  onScreenshot,
  onLoad,
  className = "",
  latitude,
  longitude,
}: ThreeViewerProps) {
  const canvasRef    = useRef<HTMLCanvasElement>(null);
  const rendererRef  = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef    = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef  = useRef<OrbitControls | null>(null);
  const sceneRef     = useRef<THREE.Scene | null>(null);
  const sunRef       = useRef<THREE.DirectionalLight | null>(null);
  const fillRef      = useRef<THREE.DirectionalLight | null>(null);
  const ambientRef   = useRef<THREE.AmbientLight | null>(null);
  const modelRef     = useRef<THREE.Group | null>(null);
  const boxRef       = useRef<THREE.Box3 | null>(null);
  const animRef      = useRef<number>(0);
  const origMatsRef  = useRef<Map<number, THREE.Material | THREE.Material[]>>(new Map());

  const [loading,    setLoading]    = useState(true);
  const [progress,   setProgress]   = useState(0);
  const [loadError,  setLoadError]  = useState<string | null>(null);
  const [matKey,     setMatKey]     = useState<MaterialKey>("default");
  const [wireframe,  setWireframe]  = useState(false);
  const [viewMode,   setViewMode]   = useState<ViewMode>("orbit");
  const [envMode,    setEnvMode]    = useState<EnvMode>("day");
  const [autoRotate, setAutoRotate] = useState(false);
  const [showShadow, setShowShadow] = useState(true);
  const [showSun,    setShowSun]    = useState(false);

  // ── Scene bootstrap ─────────────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !modelUrl || !modelUrl.trim()) {
      setLoadError("No 3D model available for this variant.");
      setLoading(false);
      return;
    }

    // Renderer
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type    = THREE.PCFSoftShadowMap;
    renderer.outputColorSpace  = THREE.SRGBColorSpace;
    renderer.toneMapping       = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;
    rendererRef.current = renderer;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(ENV_PRESETS.day.bg);
    scene.fog        = new THREE.FogExp2(ENV_PRESETS.day.fog, 0.004);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(42, canvas.clientWidth / canvas.clientHeight, 0.1, 1000);
    camera.position.set(30, 22, 30);
    cameraRef.current = camera;

    // Controls
    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping  = true;
    controls.dampingFactor  = 0.06;
    controls.minDistance    = 2;
    controls.maxDistance    = 400;
    controls.maxPolarAngle  = Math.PI / 2.02;
    controls.screenSpacePanning = false;
    controlsRef.current = controls;

    // Lights
    const ambient = new THREE.AmbientLight(0xffffff, ENV_PRESETS.day.ambient);
    ambientRef.current = ambient;
    scene.add(ambient);

    const sun = new THREE.DirectionalLight(ENV_PRESETS.day.sunColor, ENV_PRESETS.day.sunInt);
    sun.position.set(...ENV_PRESETS.day.sunPos);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.near   = 1;
    sun.shadow.camera.far    = 400;
    sun.shadow.camera.left   = -80;
    sun.shadow.camera.right  = 80;
    sun.shadow.camera.top    = 80;
    sun.shadow.camera.bottom = -80;
    sun.shadow.bias          = -0.001;
    sunRef.current = sun;
    scene.add(sun);

    const fill = new THREE.DirectionalLight(ENV_PRESETS.day.fillColor, ENV_PRESETS.day.fillInt);
    fill.position.set(-25, 15, -20);
    fillRef.current = fill;
    scene.add(fill);

    // Ground
    const groundGeo = new THREE.PlaneGeometry(400, 400, 1, 1);
    const groundMat = new THREE.MeshStandardMaterial({
      color:    0x3d6b32,
      roughness:1.0,
      metalness:0.0,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x  = -Math.PI / 2;
    ground.position.y  = 0;
    ground.receiveShadow = true;
    scene.add(ground);

    // Grid
    const grid = new THREE.GridHelper(200, 80, 0x000000, 0x000000);
    (grid.material as THREE.Material).opacity     = 0.04;
    (grid.material as THREE.Material).transparent = true;
    scene.add(grid);

    // ── Load GLTF ─────────────────────────────────────────────────────────────
    const dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath("https://www.gstatic.com/draco/versioned/decoders/1.5.6/");

    const loader = new GLTFLoader();
    loader.setDRACOLoader(dracoLoader);

    setLoading(true);
    setLoadError(null);
    setProgress(0);

    loader.load(
      modelUrl,
      (gltf) => {
        const model = gltf.scene;
        const box   = new THREE.Box3().setFromObject(model);
        const center= box.getCenter(new THREE.Vector3());
        const size  = box.getSize(new THREE.Vector3());

        // Centre on ground
        model.position.set(-center.x, -box.min.y, -center.z);
        box.setFromObject(model);  // recompute after repositioning

        // Shadows + store original materials
        model.traverse((child) => {
          const mesh = child as THREE.Mesh;
          if (!mesh.isMesh) return;
          mesh.castShadow    = true;
          mesh.receiveShadow = true;
          origMatsRef.current.set(mesh.id, mesh.material);
        });

        modelRef.current = model;
        boxRef.current   = box;
        scene.add(model);

        // Fit shadow camera to model
        const maxDim = Math.max(size.x, size.y, size.z);
        const pad    = maxDim * 0.7;
        sun.shadow.camera.left   = -maxDim - pad;
        sun.shadow.camera.right  =  maxDim + pad;
        sun.shadow.camera.top    =  maxDim + pad;
        sun.shadow.camera.bottom = -maxDim - pad;
        sun.shadow.camera.far    =  maxDim * 10;
        sun.shadow.camera.updateProjectionMatrix();

        positionCamera(camera, controls, box, "orbit");
        setLoading(false);
        onLoad?.();
      },
      (evt) => {
        if (evt.total > 0)
          setProgress(Math.round((evt.loaded / evt.total) * 100));
      },
      (err) => {
        console.error("[ThreeViewer] GLB load error:", err);
        setLoadError("Failed to load 3D model. The model file may be corrupted or too large.");
        setLoading(false);
      },
    );

    // ── Render loop ───────────────────────────────────────────────────────────
    const animate = () => {
      animRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // ── Resize ────────────────────────────────────────────────────────────────
    const handleResize = () => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
    };
    const ro = new ResizeObserver(handleResize);
    ro.observe(canvas);

    return () => {
      cancelAnimationFrame(animRef.current);
      ro.disconnect();
      loader.manager.onError = null as unknown as (url: string) => void;
      renderer.dispose();
      dracoLoader.dispose();
    };
  }, [modelUrl]);   // eslint-disable-line react-hooks/exhaustive-deps

  // ── Material preset ──────────────────────────────────────────────────────────
  useEffect(() => {
    const model = modelRef.current;
    if (!model) return;

    model.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (!mesh.isMesh) return;

      const preset = MAT_PRESETS[matKey];
      if (preset === null) {
        // Restore original
        const orig = origMatsRef.current.get(mesh.id);
        if (orig) mesh.material = orig;
      } else {
        mesh.material = new THREE.MeshStandardMaterial({
          ...preset,
          wireframe,
        });
      }
    });
  }, [matKey]);   // eslint-disable-line react-hooks/exhaustive-deps

  // ── Wireframe toggle ─────────────────────────────────────────────────────────
  useEffect(() => {
    const model = modelRef.current;
    if (!model) return;
    model.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (!mesh.isMesh) return;
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      mats.forEach((m) => {
        (m as THREE.MeshStandardMaterial).wireframe = wireframe;
      });
    });
  }, [wireframe]);

  // ── Camera view ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!cameraRef.current || !controlsRef.current || !boxRef.current) return;
    positionCamera(cameraRef.current, controlsRef.current, boxRef.current, viewMode);
  }, [viewMode]);

  // ── Environment ───────────────────────────────────────────────────────────────
  useEffect(() => {
    const scene   = sceneRef.current;
    const sun     = sunRef.current;
    const fill    = fillRef.current;
    const ambient = ambientRef.current;
    if (!scene || !sun || !fill || !ambient) return;

    const p = ENV_PRESETS[envMode];
    scene.background = new THREE.Color(p.bg);
    (scene.fog as THREE.FogExp2).color.set(p.fog);
    ambient.intensity  = p.ambient;
    sun.color.set(p.sunColor);
    sun.intensity      = p.sunInt;
    sun.position.set(...p.sunPos);
    fill.color.set(p.fillColor);
    fill.intensity     = p.fillInt;
  }, [envMode]);

  // ── Auto-rotate ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (controlsRef.current) controlsRef.current.autoRotate      = autoRotate;
    if (controlsRef.current) controlsRef.current.autoRotateSpeed = 0.8;
  }, [autoRotate]);

  // ── Shadows ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (rendererRef.current) rendererRef.current.shadowMap.enabled = showShadow;
  }, [showShadow]);

  // ── Sun simulation callback ──────────────────────────────────────────────────
  // Called by SunControls whenever the user moves a slider or the animate loop ticks.
  // Directly mutates the THREE light refs — no React re-render needed for perf.
  const handleSunChange = useCallback((state: SunState) => {
    const sun     = sunRef.current;
    const ambient = ambientRef.current;
    const scene   = sceneRef.current;
    if (!sun || !ambient || !scene) return;

    sun.position.copy(state.position);
    sun.intensity = state.intensity;
    sun.color.copy(state.color);

    // Darken ambient proportionally so night feels dark
    ambient.intensity = Math.max(0.05, state.intensity * 0.18);

    // Sky background colour: blend from night (0x0a0e1a) → day (0xdde8f5)
    const t  = Math.min(1, state.intensity / 2.8);
    const bg = new THREE.Color(0x0a0e1a).lerp(new THREE.Color(0xdde8f5), t);
    scene.background = bg;
    (scene.fog as THREE.FogExp2).color.copy(bg);
  }, []);

  // ── Screenshot ────────────────────────────────────────────────────────────────
  const takeScreenshot = useCallback(() => {
    const renderer = rendererRef.current;
    const scene    = sceneRef.current;
    const camera   = cameraRef.current;
    if (!renderer || !scene || !camera) return;
    renderer.render(scene, camera);                         // ensure latest frame
    const dataUrl = renderer.domElement.toDataURL("image/png");
    onScreenshot?.(dataUrl);
    const a      = document.createElement("a");
    a.href       = dataUrl;
    a.download   = "archai-design.png";
    a.click();
  }, [onScreenshot]);

  // ─── UI ───────────────────────────────────────────────────────────────────────

  const btnStyle = (active = false): React.CSSProperties => ({
    fontSize:   11,
    padding:    "3px 10px",
    borderRadius: 8,
    border:     `1px solid ${active ? "rgba(124,58,237,0.5)" : "rgba(255,255,255,0.12)"}`,
    background: active ? "rgba(124,58,237,0.25)" : "rgba(255,255,255,0.07)",
    color:      active ? "#c4b5fd" : "rgba(255,255,255,0.65)",
    cursor:     "pointer",
    transition: "all 0.15s",
    fontWeight: active ? 600 : 400,
    whiteSpace: "nowrap" as const,
  });

  const dividerStyle: React.CSSProperties = {
    width: 1, height: 18,
    background: "rgba(255,255,255,0.12)",
    flexShrink: 0,
  };

  return (
    <div
      id="three-viewer-root"
      className={className}
      style={{
        position:   "relative",
        borderRadius: 16,
        overflow:   "hidden",
        background: "#0a0e1a",
        border:     "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {/* Loading overlay */}
      {loading && (
        <div style={{
          position:       "absolute", inset: 0, zIndex: 20,
          display:        "flex", flexDirection: "column",
          alignItems:     "center", justifyContent: "center", gap: 16,
          background:     "rgba(10,14,26,0.92)",
          backdropFilter: "blur(8px)",
        }}>
          {/* Animated ring */}
          <div style={{
            width: 56, height: 56, borderRadius: "50%",
            border: "3px solid rgba(124,58,237,0.2)",
            borderTop: "3px solid #7c3aed",
            animation: "spin 0.9s linear infinite",
          }} />

          <div style={{ textAlign: "center" }}>
            <p style={{ color: "rgba(255,255,255,0.8)", fontSize: 14, fontWeight: 500, margin: 0 }}>
              Loading 3D model
            </p>
            <p style={{ color: "rgba(255,255,255,0.35)", fontSize: 12, marginTop: 4 }}>
              {progress > 0 ? `${progress}%` : "Initialising…"}
            </p>
          </div>

          {/* Progress bar */}
          <div style={{
            width: 200, height: 3, borderRadius: 2,
            background: "rgba(255,255,255,0.08)",
          }}>
            <div style={{
              height: "100%", borderRadius: 2,
              background: "linear-gradient(90deg,#7c3aed,#06b6d4)",
              width: `${Math.max(progress, 4)}%`,
              transition: "width 0.3s ease",
            }} />
          </div>

          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Error overlay */}
      {loadError && !loading && (
        <div style={{
          position: "absolute", inset: 0, zIndex: 20,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: 12,
          background: "rgba(10,14,26,0.95)",
        }}>
          <span style={{ fontSize: 36 }}>⚠️</span>
          <p style={{ color: "#fca5a5", fontSize: 14, textAlign: "center", maxWidth: 280, margin: 0 }}>
            {loadError}
          </p>
          <a
            href={modelUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "#a78bfa", fontSize: 12, textDecoration: "underline" }}
          >
            Try opening directly ↗
          </a>
        </div>
      )}

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        id="three-viewer-canvas"
        style={{ width: "100%", height, display: "block" }}
      />

      {/* ── Toolbar ────────────────────────────────────────────────────────────── */}
      {!loading && !loadError && (
        <div style={{
          position:       "absolute",
          bottom:         12,
          left:           12,
          right:          12,
          display:        "flex",
          alignItems:     "center",
          flexWrap:       "wrap" as const,
          gap:            6,
          padding:        "8px 10px",
          background:     "rgba(10,14,26,0.75)",
          backdropFilter: "blur(12px)",
          borderRadius:   12,
          border:         "1px solid rgba(255,255,255,0.09)",
        }}>

          {/* Material presets */}
          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.05em", marginRight: 2 }}>Mat</span>
            {(Object.keys(MAT_PRESETS) as MaterialKey[]).map((k) => (
              <button
                key={k}
                id={`mat-${k}`}
                onClick={() => setMatKey(k)}
                style={btnStyle(matKey === k)}
              >
                {k}
              </button>
            ))}
          </div>

          <div style={dividerStyle} />

          {/* Camera views */}
          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.05em", marginRight: 2 }}>View</span>
            {(["orbit","top","front","side"] as ViewMode[]).map((v) => (
              <button key={v} id={`view-${v}`} onClick={() => setViewMode(v)} style={btnStyle(viewMode === v)}>
                {v}
              </button>
            ))}
          </div>

          <div style={dividerStyle} />

          {/* Environment */}
          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.05em", marginRight: 2 }}>Env</span>
            {(["day","dusk","night"] as EnvMode[]).map((e) => (
              <button key={e} id={`env-${e}`} onClick={() => setEnvMode(e)} style={btnStyle(envMode === e)}>
                {e === "day" ? "☀️" : e === "dusk" ? "🌆" : "🌙"} {e}
              </button>
            ))}
          </div>

          <div style={dividerStyle} />

          {/* Toggles */}
          <button id="toggle-wireframe" onClick={() => setWireframe((w) => !w)} style={btnStyle(wireframe)}>
            {wireframe ? "◻ Solid" : "⬡ Wire"}
          </button>
          <button id="toggle-autorotate" onClick={() => setAutoRotate((a) => !a)} style={btnStyle(autoRotate)}>
            {autoRotate ? "⏸ Stop" : "↻ Spin"}
          </button>
          <button id="toggle-shadow" onClick={() => setShowShadow((s) => !s)} style={btnStyle(showShadow)}>
            {showShadow ? "🌑 Shadow" : "○ No shadow"}
          </button>
          {(latitude !== undefined && longitude !== undefined) && (
            <button id="toggle-sun" onClick={() => setShowSun((s) => !s)} style={btnStyle(showSun)}>
              ☀️ Sun
            </button>
          )}

          {/* Actions */}
          <div style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
            <button
              id="viewer-screenshot"
              onClick={takeScreenshot}
              style={{
                ...btnStyle(),
                background: "rgba(124,58,237,0.2)",
                border:     "1px solid rgba(124,58,237,0.4)",
                color:      "#c4b5fd",
              }}
            >
              📷 Screenshot
            </button>

            <a
              id="viewer-download-glb"
              href={modelUrl}
              download="archai-model.glb"
              style={{
                ...btnStyle(),
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
              }}
            >
              ⬇ GLB
            </a>
          </div>
        </div>
      )}

      {/* Top-right badge */}
      {!loading && !loadError && (
        <div style={{
          position: "absolute", top: 12, right: 12,
          padding:  "4px 10px", borderRadius: 20,
          background: "rgba(10,14,26,0.7)",
          border:   "1px solid rgba(255,255,255,0.08)",
          backdropFilter: "blur(8px)",
          display: "flex", alignItems: "center", gap: 6,
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: "50%",
            background: "#22c55e",
            boxShadow: "0 0 6px #22c55e",
          }} />
          <span style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", fontWeight: 500 }}>
            THREE.js · GLB
          </span>
        </div>
      )}

      {/* Keyboard hint */}
      {!loading && !loadError && (
        <div style={{
          position: "absolute", top: 12, left: 12,
          padding:  "4px 10px", borderRadius: 20,
          background: "rgba(10,14,26,0.5)",
          fontSize: 10, color: "rgba(255,255,255,0.25)",
        }}>
          Drag to orbit · Scroll to zoom · Right-drag to pan
        </div>
      )}

      {/* ── Sun simulation overlay ─────────────────────────────────────────────── */}
      {showSun && !loading && !loadError && latitude !== undefined && longitude !== undefined && (
        <div style={{
          position: "absolute",
          bottom:   72,           // sits above the toolbar
          right:    12,
          zIndex:   15,
        }}>
          <SunControls
            latitude={latitude}
            longitude={longitude}
            onSunChange={handleSunChange}
            initialHour={12}
            initialMonth={6}
          />
        </div>
      )}
    </div>
  );
}
