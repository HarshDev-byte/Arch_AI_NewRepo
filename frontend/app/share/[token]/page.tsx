"use client";

/**
 * app/share/[token]/page.tsx
 * 
 * Public read-only project view accessible via shareable links.
 * No authentication required - displays project data for public viewing.
 */

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import ViewerWrapper from "@/components/viewer3d/ViewerWrapper";

interface SharedProject {
  id: string;
  name: string;
  plot_area_sqm?: number;
  floors?: number;
  budget_inr?: number;
  latitude?: number;
  longitude?: number;
  design_variants?: Array<{
    id: string;
    variant_number: number;
    model_url?: string;
    score?: number;
    dna?: any;
  }>;
  cost_estimate?: {
    total_cost_inr?: number;
    breakdown?: Record<string, number>;
    cost_per_sqft?: number;
  };
  compliance_check?: {
    passed?: boolean;
    fsi_used?: number;
    fsi_allowed?: number;
    issues?: string[];
  };
}

export default function SharedProjectPage() {
  const params = useParams<{ token: string }>();
  const [project, setProject] = useState<SharedProject | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params?.token) return;

    const fetchProject = async () => {
      try {
        const response = await fetch(`/api/projects/shared/${params.token}`);
        if (!response.ok) {
          throw new Error("Share link not found or expired");
        }
        const data = await response.json();
        setProject(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load project");
      } finally {
        setLoading(false);
      }
    };

    fetchProject();
  }, [params?.token]);

  if (loading) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#080c18",
        color: "white",
      }}>
        <div style={{ textAlign: "center" }}>
          <div style={{
            width: 40,
            height: 40,
            border: "3px solid rgba(124,58,237,0.2)",
            borderTop: "3px solid #7c3aed",
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
            margin: "0 auto 16px",
          }} />
          <p>Loading shared project...</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#080c18",
        color: "white",
        padding: "2rem",
      }}>
        <div style={{ textAlign: "center", maxWidth: 400 }}>
          <span style={{ fontSize: 48, marginBottom: 16, display: "block" }}>🔗</span>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 8px" }}>
            Link Not Found
          </h1>
          <p style={{ color: "rgba(255,255,255,0.6)", marginBottom: 24 }}>
            This share link has expired or doesn&apos;t exist.
          </p>
          <Link
            href="/auth"
            style={{
              display: "inline-block",
              padding: "8px 16px",
              background: "#7c3aed",
              color: "white",
              textDecoration: "none",
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 500,
            }}
          >
            Create Your Own Design
          </Link>
        </div>
      </div>
    );
  }

  const selectedVariant = project.design_variants?.[0];
  const hasModel = selectedVariant?.model_url;

  return (
    <div style={{
      minHeight: "100vh",
      background: "#080c18",
      color: "white",
      fontFamily: "'Inter', sans-serif",
    }}>
      {/* Header */}
      <div style={{
        maxWidth: 1200,
        margin: "0 auto",
        padding: "2rem 1rem",
      }}>
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 32,
          flexWrap: "wrap",
          gap: 16,
        }}>
          <div>
            <h1 style={{ fontSize: 28, fontWeight: 600, margin: 0 }}>
              {project.name}
            </h1>
            <p style={{
              color: "rgba(255,255,255,0.6)",
              fontSize: 16,
              margin: "8px 0 0",
            }}>
              {project.plot_area_sqm}sqm · {project.floors} floors · Shared view
            </p>
          </div>
          
          <Link
            href="/auth"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 20px",
              background: "rgba(124,58,237,0.15)",
              border: "1px solid rgba(124,58,237,0.3)",
              borderRadius: 12,
              color: "#c4b5fd",
              textDecoration: "none",
              fontSize: 14,
              fontWeight: 500,
              transition: "all 0.2s",
            }}
          >
            Create My Own Design ↗
          </Link>
        </div>

        {/* 3D Viewer */}
        {hasModel && (
          <div style={{ marginBottom: 32 }}>
            <ViewerWrapper
              modelUrl={selectedVariant.model_url!}
              height={500}
              latitude={project.latitude}
              longitude={project.longitude}
            />
          </div>
        )}

        {/* Project Stats Grid */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: 20,
          marginBottom: 32,
        }}>
          {/* Design Info */}
          <div style={{
            padding: 20,
            background: "rgba(255,255,255,0.05)",
            borderRadius: 16,
            border: "1px solid rgba(255,255,255,0.1)",
          }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 16px" }}>
              Design Details
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "rgba(255,255,255,0.6)" }}>Plot Area</span>
                <span>{project.plot_area_sqm}sqm</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "rgba(255,255,255,0.6)" }}>Floors</span>
                <span>{project.floors}</span>
              </div>
              {selectedVariant?.score && (
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "rgba(255,255,255,0.6)" }}>Design Score</span>
                  <span style={{ color: "#22c55e" }}>{selectedVariant.score.toFixed(1)}/100</span>
                </div>
              )}
            </div>
          </div>

          {/* Cost Estimate */}
          {project.cost_estimate && (
            <div style={{
              padding: 20,
              background: "rgba(255,255,255,0.05)",
              borderRadius: 16,
              border: "1px solid rgba(255,255,255,0.1)",
            }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 16px" }}>
                Cost Estimate
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "rgba(255,255,255,0.6)" }}>Total Cost</span>
                  <span style={{ color: "#fbbf24" }}>
                    ₹{(project.cost_estimate.total_cost_inr || 0).toLocaleString()}
                  </span>
                </div>
                {project.cost_estimate.cost_per_sqft && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "rgba(255,255,255,0.6)" }}>Per Sqft</span>
                    <span>₹{project.cost_estimate.cost_per_sqft.toLocaleString()}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Compliance */}
          {project.compliance_check && (
            <div style={{
              padding: 20,
              background: "rgba(255,255,255,0.05)",
              borderRadius: 16,
              border: "1px solid rgba(255,255,255,0.1)",
            }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 16px" }}>
                Compliance
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "rgba(255,255,255,0.6)" }}>Status</span>
                  <span style={{
                    color: project.compliance_check.passed ? "#22c55e" : "#ef4444"
                  }}>
                    {project.compliance_check.passed ? "✅ Passed" : "❌ Issues"}
                  </span>
                </div>
                {project.compliance_check.fsi_used && project.compliance_check.fsi_allowed && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "rgba(255,255,255,0.6)" }}>FSI Usage</span>
                    <span>
                      {project.compliance_check.fsi_used.toFixed(2)} / {project.compliance_check.fsi_allowed.toFixed(2)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* CTA Section */}
        <div style={{
          padding: 32,
          background: "rgba(124,58,237,0.1)",
          borderRadius: 20,
          border: "1px solid rgba(124,58,237,0.2)",
          textAlign: "center",
        }}>
          <h2 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 8px" }}>
            Want Your Own AI-Generated Building Design?
          </h2>
          <p style={{
            color: "rgba(255,255,255,0.7)",
            fontSize: 16,
            margin: "0 0 24px",
          }}>
            Create custom architectural designs with AI in minutes
          </p>
          <Link
            href="/auth"
            style={{
              display: "inline-block",
              padding: "12px 24px",
              background: "#7c3aed",
              color: "white",
              textDecoration: "none",
              borderRadius: 12,
              fontSize: 16,
              fontWeight: 600,
              transition: "all 0.2s",
            }}
          >
            Start for Free on ArchAI ↗
          </Link>
        </div>
      </div>
    </div>
  );
}