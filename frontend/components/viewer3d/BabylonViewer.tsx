"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";

declare global {
  interface Window { BABYLON: any; }
}

interface BabylonViewerProps {
  modelUrl: string;
  sceneGraph?: Record<string, unknown>;
  height?: string;
}

export default function BabylonViewer({ modelUrl, sceneGraph, height = "500px" }: BabylonViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<any>(null);
  const [babylonLoaded, setBabylonLoaded] = useState(false);
  const [loadersLoaded, setLoadersLoaded] = useState(false);

  useEffect(() => {
    let destroyed = false;

    const init = () => {
      if (!canvasRef.current || !window.BABYLON || !babylonLoaded || !loadersLoaded) return;
      const BABYLON = window.BABYLON;
      if (engineRef.current) { engineRef.current.dispose(); engineRef.current = null; }
      
      try {
        const engine = new BABYLON.Engine(canvasRef.current, true, { preserveDrawingBuffer: true });
        engineRef.current = engine;

        const createScene = async () => {
          const scene = new BABYLON.Scene(engine);

          // Camera
          const camera = new BABYLON.ArcRotateCamera("cam", -Math.PI / 4, Math.PI / 3.5, 40, BABYLON.Vector3.Zero(), scene);
          camera.attachControl(canvasRef.current, true);
          camera.lowerRadiusLimit = 5;
          camera.upperRadiusLimit = 120;
          camera.wheelPrecision    = 5;

          // Environment
          scene.createDefaultEnvironment({ createGround: true, groundSize: 200, skyboxSize: 200 });
          const hemi = new BABYLON.HemisphericLight("hemi", new BABYLON.Vector3(0, 1, 0), scene);
          hemi.intensity = 0.7;
          const dir = new BABYLON.DirectionalLight("dir", new BABYLON.Vector3(-1, -2, -1), scene);
          dir.intensity  = 0.6;

          if (modelUrl && modelUrl.trim() && BABYLON.SceneLoader) {
            try {
              // Load GLB
              await BABYLON.SceneLoader.AppendAsync("", modelUrl, scene);
              const meshes = scene.meshes.filter((m: any) => m.name !== "BackgroundSkybox" && m.name !== "__root__");
              if (meshes.length > 0 && meshes[0].getBoundingInfo) {
                const bounds = meshes[0].getBoundingInfo().boundingBox;
                camera.target = bounds.centerWorld ?? BABYLON.Vector3.Zero();
                camera.radius = bounds.maximumWorld.subtract(bounds.minimumWorld).length() * 1.6;
              }
            } catch (error) {
              console.warn('[BabylonViewer] Model load failed:', error);
              // Fall back to scene graph rendering
            }
          }
          
          if (!modelUrl || !modelUrl.trim() || sceneGraph) {
            // Render from JSON scene graph
            const sg = sceneGraph as any;
            for (const mesh of (sg?.meshes ?? [])) {
              const box = BABYLON.MeshBuilder.CreateBox(mesh.id ?? "box", {
                width: mesh.scaling?.[0] ?? 1,
                height: mesh.scaling?.[1] ?? 1,
                depth:  mesh.scaling?.[2] ?? 1,
              }, scene);
              box.position = new BABYLON.Vector3(...(mesh.position ?? [0, 0, 0]));
              if (mesh.material) {
                const mat = new BABYLON.StandardMaterial(mesh.id + "_mat", scene);
                const dc  = mesh.material.diffuseColor ?? { r: 0.7, g: 0.7, b: 0.7 };
                mat.diffuseColor = new BABYLON.Color3(dc.r, dc.g, dc.b);
                mat.alpha        = mesh.material.alpha ?? 1;
                box.material     = mat;
              }
            }
            camera.setTarget(BABYLON.Vector3.Zero());
          }

          // WebXR (optional, may fail silently)
          try {
            if (navigator.xr) {
              await scene.createDefaultXRExperienceAsync({ uiOptions: { sessionMode: "immersive-vr" } });
            }
          } catch { /* XR may not be available */ }

          return scene;
        };

        createScene().then((scene) => {
          if (destroyed || !scene) return;
          engine.runRenderLoop(() => { if (!destroyed) scene.render(); });
        }).catch(error => {
          console.warn('[BabylonViewer] Scene creation failed:', error);
        });
      } catch (error) {
        console.warn('[BabylonViewer] Engine creation failed:', error);
      }
    };

    if (babylonLoaded && loadersLoaded) {
      init();
    }

    const handleResize = () => engineRef.current?.resize();
    window.addEventListener("resize", handleResize);

    return () => {
      destroyed = true;
      window.removeEventListener("resize", handleResize);
      engineRef.current?.dispose();
      engineRef.current = null;
    };
  }, [modelUrl, sceneGraph, babylonLoaded, loadersLoaded]);

  const handleDownload = () => {
    if (!modelUrl) return;
    const a = document.createElement("a");
    a.href     = modelUrl;
    a.download = "archai_model.glb";
    a.click();
  };

  return (
    <div className="relative rounded-xl overflow-hidden bg-[#0a0e1a]" style={{ height }}>
      <Script 
        src="https://cdn.babylonjs.com/babylon.js" 
        strategy="afterInteractive"
        onLoad={() => setBabylonLoaded(true)}
      />
      <Script 
        src="https://cdn.babylonjs.com/loaders/babylonjs.loaders.min.js" 
        strategy="afterInteractive"
        onLoad={() => setLoadersLoaded(true)}
      />

      <canvas ref={canvasRef} id="babylon-canvas" style={{ width: "100%", height: "100%", display: "block" }} />

      {/* Controls overlay */}
      <div className="absolute bottom-3 right-3 flex gap-2">
        {modelUrl && (
          <button
            id="btn-download-glb"
            onClick={handleDownload}
            className="px-3 py-1.5 rounded-lg bg-[#0d1117]/80 backdrop-blur border border-white/10 text-xs text-white/70 hover:text-white transition-colors"
          >
            ↓ Download .glb
          </button>
        )}
        <div className="px-3 py-1.5 rounded-lg bg-[#0d1117]/80 backdrop-blur border border-white/10 text-xs text-white/40">
          Drag to orbit · Scroll to zoom
        </div>
      </div>

      {/* Loading overlay */}
      {(!babylonLoaded || !loadersLoaded) && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0a0e1a]">
          <div className="text-center">
            <div className="w-10 h-10 border-2 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-white/50">Loading 3D engine…</p>
          </div>
        </div>
      )}
    </div>
  );
}
