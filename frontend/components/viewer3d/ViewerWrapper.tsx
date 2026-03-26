"use client";

/**
 * ViewerWrapper.tsx
 *
 * Three.js uses browser-only APIs (WebGL, ResizeObserver, requestAnimationFrame).
 * Next.js 14 renders components on the server by default — importing Three.js
 * there will crash with "window is not defined".
 *
 * This wrapper uses next/dynamic with ssr:false to guarantee the heavy
 * ThreeViewer is only ever instantiated in the browser.
 *
 * Usage:
 *   import ViewerWrapper from "@/components/viewer3d/ViewerWrapper";
 *   <ViewerWrapper modelUrl="/models/house.glb" />
 */

import dynamic from "next/dynamic";
import { ThreeViewerProps } from "./ThreeViewer";

// Skeleton shown while the component bundle is loading
function ViewerSkeleton() {
  return (
    <div
      style={{
        display:        "flex",
        flexDirection:  "column",
        alignItems:     "center",
        justifyContent: "center",
        gap:            16,
        height:         540,
        borderRadius:   16,
        background:     "rgba(255,255,255,0.03)",
        border:         "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {/* Spinning ring */}
      <div
        style={{
          width:        52,
          height:       52,
          borderRadius: "50%",
          border:       "3px solid rgba(124,58,237,0.18)",
          borderTop:    "3px solid #7c3aed",
          animation:    "spin 0.9s linear infinite",
        }}
      />
      <p style={{ color: "rgba(255,255,255,0.35)", fontSize: 13, margin: 0 }}>
        Loading 3D viewer…
      </p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

const ThreeViewer = dynamic<ThreeViewerProps>(
  () => import("./ThreeViewer").then((mod) => mod.default),
  {
    ssr:     false,
    loading: () => <ViewerSkeleton />,
  },
);

export default ThreeViewer;

// Re-export props type so consumers can import from this single file
export type { ThreeViewerProps };
