"use client";
import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api";

interface KeyStatus {
  key_label:      string;
  key_preview:    string;
  daily_used:     number;
  daily_limit:    number;
  per_min_used:   number;
  per_min_limit:  number;
  available:      boolean;
}

export default function GeminiKeyStatus() {
  const [keys, setKeys]       = useState<KeyStatus[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const data = await apiClient.get("/api/keys/gemini-status");
      setKeys(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000); // refresh every 30s
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>Loading key status...</div>;

  const totalDaily    = keys.reduce((s, k) => s + k.daily_used, 0);
  const totalCapacity = keys.reduce((s, k) => s + k.daily_limit, 0) || 4500;

  return (
    <div style={{ marginBottom: 32 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <h2 style={{ fontSize: 15, fontWeight: 500, margin: 0 }}>Gemini API Keys</h2>
        <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          {totalDaily} / {totalCapacity} calls used today
        </span>
      </div>

      {/* Total usage bar */}
      <div style={{ height: 4, background: "var(--color-background-secondary)", borderRadius: 2, marginBottom: 16 }}>
        <div style={{
          height: "100%", borderRadius: 2,
          width: `${Math.min(100, (totalDaily / totalCapacity) * 100)}%`,
          background: totalDaily / totalCapacity > 0.85 ? "#E24B4A" : "#1D9E75",
          transition: "width 0.5s"
        }} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {keys.map((k) => {
          const pct = (k.daily_used / k.daily_limit) * 100;
          return (
            <div key={k.key_label} style={{
              background: "var(--color-background-primary)",
              border: `0.5px solid ${k.available ? "var(--color-border-tertiary)" : "#F09595"}`,
              borderRadius: "var(--border-radius-lg)",
              padding: "12px 16px"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 14, fontWeight: 500 }}>{k.key_label}</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 12,
                    color: "var(--color-text-secondary)" }}>...{k.key_preview}</span>
                </div>
                <span style={{
                  fontSize: 11, padding: "2px 8px", borderRadius: 20,
                  background: k.available ? "#E1F5EE" : "#FCEBEB",
                  color: k.available ? "#0F6E56" : "#A32D2D"
                }}>
                  {k.available ? "Available" : "Rate limited"}
                </span>
              </div>
              <div style={{ display: "flex", gap: 16, fontSize: 12, color: "var(--color-text-secondary)" }}>
                <span>Daily: {k.daily_used} / {k.daily_limit}</span>
                <span>Per min: {k.per_min_used} / {k.per_min_limit}</span>
              </div>
              <div style={{ marginTop: 6, height: 3, background: "var(--color-background-secondary)", borderRadius: 2 }}>
                <div style={{
                  height: "100%", borderRadius: 2,
                  width: `${Math.min(100, pct)}%`,
                  background: pct > 90 ? "#E24B4A" : pct > 70 ? "#EF9F27" : "#1D9E75"
                }} />
              </div>
            </div>
          );
        })}

        {keys.length === 0 && (
          <div style={{ padding: 16, fontSize: 13, color: "var(--color-text-secondary)",
            background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-md)" }}>
            No Gemini keys found. Add GEMINI_KEY_A, GEMINI_KEY_B, GEMINI_KEY_C to your .env file.
          </div>
        )}
      </div>

      <p style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 12 }}>
        Get free keys at{" "}
        <a href="https://aistudio.google.com" target="_blank" rel="noopener" style={{ color: "var(--color-text-info)" }}>
          aistudio.google.com
        </a>
        {" "}— 1,500 free calls/day per Google account, no card needed.
      </p>
    </div>
  );
}
