"use client";

import { useCallback, useState } from "react";
import Map, { Marker, NavigationControl, ScaleControl } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

export interface PlotSelectorProps {
  onSelect: (lat: number, lng: number) => void;
  selectedLat?: number;
  selectedLng?: number;
  height?: string;
}

const MAP_STYLES = [
  { id: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json", label: "Light" },
  { id: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json", label: "Dark" },
  { id: "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json", label: "Street" },
] as const;

export default function PlotSelector({
  onSelect,
  selectedLat,
  selectedLng,
  height = "420px",
}: PlotSelectorProps) {
  const [viewState, setViewState] = useState({
    longitude: 73.8567,
    latitude:  18.5204,
    zoom:      14,
  });
  const [styleIdx, setStyleIdx] = useState(0);
  const [searching, setSearching] = useState(false);
  const [searchInput, setSearchInput] = useState("");

  const handleClick = useCallback(
    (event: { lngLat: { lng: number; lat: number } }) => {
      const { lng, lat } = event.lngLat;
      onSelect(lat, lng);
    },
    [onSelect]
  );

  const handleSearch = async () => {
    if (!searchInput.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(searchInput)}&format=json&limit=1`,
        { headers: { "User-Agent": "ArchAI/1.0" } }
      );
      const data = await res.json();
      if (data.length > 0) {
        const { lat, lon } = data[0];
        setViewState((v) => ({
          ...v,
          latitude:  parseFloat(lat),
          longitude: parseFloat(lon),
          zoom:      16,
        }));
        onSelect(parseFloat(lat), parseFloat(lon));
      }
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="relative" style={{ height, borderRadius: 16, overflow: "hidden" }}>
      {/* Search bar overlay */}
      <div className="absolute top-3 left-3 right-3 z-10 flex gap-2">
        <input
          id="plot-search-input"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search city, area or address…"
          className="flex-1 px-4 py-2.5 rounded-xl bg-[#0d1117]/90 backdrop-blur border border-white/10 text-sm text-white placeholder-white/35 outline-none focus:border-violet-500/60 transition-colors shadow-xl"
        />
        <button
          id="plot-search-btn"
          onClick={handleSearch}
          disabled={searching}
          className="px-4 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-sm font-semibold transition-colors shadow-xl disabled:opacity-50"
        >
          {searching ? "…" : "Go"}
        </button>

        {/* Style switcher */}
        <div className="flex rounded-xl overflow-hidden border border-white/10 shadow-xl bg-[#0d1117]/90 backdrop-blur">
          {MAP_STYLES.map((s, i) => (
            <button
              key={s.id}
              id={`map-style-${s.label.toLowerCase()}`}
              onClick={() => setStyleIdx(i)}
              className={`px-3 py-2 text-xs font-semibold transition-colors ${
                i === styleIdx ? "bg-violet-600 text-white" : "text-white/50 hover:text-white"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <Map
        {...viewState}
        onMove={(e) => setViewState(e.viewState)}
        onClick={handleClick}
        style={{ width: "100%", height: "100%" }}
        mapStyle={MAP_STYLES[styleIdx].id}
        cursor="crosshair"
      >
        <NavigationControl position="bottom-right" />
        <ScaleControl position="bottom-left" unit="metric" />

        {selectedLat != null && selectedLng != null && (
          <Marker longitude={selectedLng} latitude={selectedLat} anchor="bottom">
            <div className="flex flex-col items-center">
              <div
                id="plot-marker"
                className="w-10 h-10 rounded-full bg-violet-600 border-2 border-white flex items-center justify-center text-lg shadow-[0_4px_20px_rgba(139,92,246,0.6)] animate-bounce"
                style={{ animationDuration: "1.4s", animationIterationCount: 2 }}
              >
                📍
              </div>
              <div className="mt-1 px-2 py-1 rounded-md bg-[#0d1117]/90 text-[10px] text-white/80 font-mono whitespace-nowrap shadow-lg">
                {selectedLat.toFixed(5)}, {selectedLng.toFixed(5)}
              </div>
            </div>
          </Marker>
        )}
      </Map>

      {/* Instruction overlay (bottom) */}
      {!selectedLat && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 px-4 py-2 rounded-full bg-[#0d1117]/80 backdrop-blur border border-white/10 text-xs text-white/55 pointer-events-none">
          🖱️ Click anywhere on the map to select your plot location
        </div>
      )}

      {selectedLat != null && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 px-4 py-2 rounded-full bg-emerald-600/80 backdrop-blur text-xs text-white font-semibold pointer-events-none flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-white" />
          Plot selected · click to move
        </div>
      )}
    </div>
  );
}
