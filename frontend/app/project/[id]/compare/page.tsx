"use client";

/**
 * app/project/[id]/compare/page.tsx
 * 
 * Side-by-side design variant comparison view.
 * Shows up to 3 variants with floor plans, 3D models, scores, and DNA differences.
 */

import { useState, useEffect, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import Link from "next/link";
import Image from "next/image";
import { Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend } from 'chart.js';
import { Radar } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Types ───────────────────────────────────────────────────────────────────

interface Variant {
  id: string;
  variant_number: number;
  score?: number;
  dna?: Record<string, any>;
  floor_plan_svg?: string;
  model_url?: string;
  thumbnail_url?: string;
  is_selected: boolean;
}

interface Project {
  id: string;
  name: string;
  design_variants?: Variant[];
  cost_estimates?: Array<{
    total_cost_inr?: number;
    cost_per_sqft?: number;
  }>;
}

// ─── DNA Diff Component ──────────────────────────────────────────────────────

function DNADiff({ variants }: { variants: Variant[] }) {
  const DNA_FIELDS = [
    { key: "primary_style", label: "Primary style" },
    { key: "secondary_style", label: "Secondary style" },
    { key: "building_form", label: "Building form" },
    { key: "roof_form", label: "Roof form" },
    { key: "facade_material_palette", label: "Materials" },
    { key: "facade_pattern", label: "Facade pattern" },
    { key: "floor_height", label: "Floor height", unit: "m" },
    { key: "window_wall_ratio", label: "Window/wall ratio", format: (v: number) => `${Math.round(v * 100)}%` },
    { key: "natural_ventilation_strategy", label: "Ventilation" },
    { key: "rooftop_utility", label: "Rooftop use" },
    { key: "solar_orientation", label: "Solar orientation", unit: "°", format: (v: number) => v?.toFixed(0) || "—" },
  ];

  const allSame = (field: string) =>
    variants.every(v => v.dna?.[field] === variants[0]?.dna?.[field]);

  return (
    <div style={{
      background: "rgba(255,255,255,0.03)",
      borderRadius: 12,
      border: "1px solid rgba(255,255,255,0.1)",
      overflow: "hidden",
    }}>
      <div style={{
        padding: "12px 16px",
        borderBottom: "1px solid rgba(255,255,255,0.1)",
        background: "rgba(255,255,255,0.05)",
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>
          DNA Comparison
        </h3>
        <p style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", margin: "4px 0 0" }}>
          Highlighted rows show differences between variants
        </p>
      </div>
      
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr>
            <th style={{
              textAlign: "left",
              padding: "12px 16px",
              color: "rgba(255,255,255,0.6)",
              fontWeight: 500,
              background: "rgba(255,255,255,0.02)",
            }}>
              Attribute
            </th>
            {variants.map((v, i) => (
              <th key={i} style={{
                textAlign: "center",
                padding: "12px 16px",
                fontWeight: 600,
                background: "rgba(255,255,255,0.02)",
              }}>
                Variant {v.variant_number}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {DNA_FIELDS.map(field => {
            const isDifferent = !allSame(field.key);
            return (
              <tr key={field.key} style={{
                background: isDifferent ? "rgba(251,191,36,0.1)" : "transparent",
                borderLeft: isDifferent ? "3px solid #fbbf24" : "3px solid transparent",
              }}>
                <td style={{
                  padding: "10px 16px",
                  color: "rgba(255,255,255,0.7)",
                  fontWeight: isDifferent ? 500 : 400,
                }}>
                  {field.label}
                </td>
                {variants.map((v, i) => {
                  const raw = v.dna?.[field.key];
                  const display = field.format 
                    ? field.format(raw) 
                    : String(raw || "—").replace(/_/g, " ");
                  
                  return (
                    <td key={i} style={{
                      padding: "10px 16px",
                      textAlign: "center",
                      fontWeight: isDifferent ? 500 : 400,
                      color: isDifferent ? "white" : "rgba(255,255,255,0.8)",
                    }}>
                      {display}{field.unit || ""}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── Radar Chart Component ───────────────────────────────────────────────────

function VariantRadarChart({ variants }: { variants: Variant[] }) {
  const data = {
    labels: [
      'Design Score',
      'Cost Efficiency',
      'Sustainability',
      'Compliance',
      'Space Efficiency'
    ],
    datasets: variants.map((variant, index) => {
      const colors = [
        'rgba(124, 58, 237, 0.6)',
        'rgba(251, 191, 36, 0.6)',
        'rgba(34, 197, 94, 0.6)',
      ];
      const borderColors = [
        'rgba(124, 58, 237, 1)',
        'rgba(251, 191, 36, 1)',
        'rgba(34, 197, 94, 1)',
      ];

      return {
        label: `Variant ${variant.variant_number}`,
        data: [
          variant.score || 0,
          Math.random() * 100, // Mock cost efficiency
          Math.random() * 100, // Mock sustainability
          Math.random() * 100, // Mock compliance
          Math.random() * 100, // Mock space efficiency
        ],
        backgroundColor: colors[index % colors.length],
        borderColor: borderColors[index % borderColors.length],
        borderWidth: 2,
        pointBackgroundColor: borderColors[index % borderColors.length],
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: borderColors[index % borderColors.length],
      };
    })
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          color: 'rgba(255,255,255,0.8)',
          font: {
            size: 12,
          },
        },
      },
    },
    scales: {
      r: {
        angleLines: {
          color: 'rgba(255,255,255,0.1)',
        },
        grid: {
          color: 'rgba(255,255,255,0.1)',
        },
        pointLabels: {
          color: 'rgba(255,255,255,0.7)',
          font: {
            size: 11,
          },
        },
        ticks: {
          color: 'rgba(255,255,255,0.5)',
          backdropColor: 'transparent',
          font: {
            size: 10,
          },
        },
        min: 0,
        max: 100,
      },
    },
  };

  return (
    <div style={{ height: 300 }}>
      <Radar data={data} options={options} />
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function ComparePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [selectedVariants, setSelectedVariants] = useState<string[]>([]);

  const { data: project } = useQuery<Project>({
    queryKey: ["project", id],
    queryFn: async () => (await axios.get(`${API}/api/projects/${id}`)).data,
  });

  const variants = useMemo(() => project?.design_variants || [], [project?.design_variants]);
  const compareVariants = variants.filter(v => selectedVariants.includes(v.id));

  // Auto-select first 2 variants on load
  useEffect(() => {
    if (variants.length > 0 && selectedVariants.length === 0) {
      setSelectedVariants(variants.slice(0, Math.min(2, variants.length)).map(v => v.id));
    }
  }, [variants, selectedVariants.length]);

  const toggleVariant = (variantId: string) => {
    setSelectedVariants(prev => {
      if (prev.includes(variantId)) {
        return prev.filter(id => id !== variantId);
      } else if (prev.length < 3) {
        return [...prev, variantId];
      } else {
        // Replace the first selected variant
        return [prev[1], prev[2], variantId];
      }
    });
  };

  const selectVariant = async (variantId: string) => {
    try {
      await axios.post(`${API}/api/projects/${id}/variants/${variantId}/select`);
      router.push(`/project/${id}`);
    } catch (error) {
      console.error("Error selecting variant:", error);
    }
  };

  if (!project) {
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
          <p>Loading project...</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: "100vh",
      background: "#080c18",
      color: "white",
      fontFamily: "'Inter', sans-serif",
    }}>
      {/* Header */}
      <nav style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: "16px 24px",
        borderBottom: "1px solid rgba(255,255,255,0.1)",
        background: "rgba(8,12,24,0.8)",
        backdropFilter: "blur(12px)",
      }}>
        <Link
          href={`/project/${id}`}
          style={{
            color: "rgba(255,255,255,0.6)",
            textDecoration: "none",
            fontSize: 14,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          ← Back to Project
        </Link>
        <span style={{ color: "rgba(255,255,255,0.3)" }}>/</span>
        <h1 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>
          Compare Variants
        </h1>
        <div style={{ marginLeft: "auto", fontSize: 12, color: "rgba(255,255,255,0.5)" }}>
          {compareVariants.length} of {variants.length} variants selected
        </div>
      </nav>

      <div style={{ padding: "24px" }}>
        {/* Variant Selector */}
        <div style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
            Select Variants to Compare (up to 3)
          </h2>
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
            gap: 12,
          }}>
            {variants.map((variant) => {
              const isSelected = selectedVariants.includes(variant.id);
              return (
                <button
                  key={variant.id}
                  onClick={() => toggleVariant(variant.id)}
                  style={{
                    padding: 16,
                    borderRadius: 12,
                    border: `2px solid ${isSelected ? "#7c3aed" : "rgba(255,255,255,0.1)"}`,
                    background: isSelected ? "rgba(124,58,237,0.1)" : "rgba(255,255,255,0.03)",
                    color: "white",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "all 0.2s",
                  }}
                >
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: 8,
                  }}>
                    <span style={{ fontSize: 14, fontWeight: 600 }}>
                      Variant {variant.variant_number}
                    </span>
                    <div style={{
                      width: 20,
                      height: 20,
                      borderRadius: "50%",
                      border: `2px solid ${isSelected ? "#7c3aed" : "rgba(255,255,255,0.3)"}`,
                      background: isSelected ? "#7c3aed" : "transparent",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}>
                      {isSelected && (
                        <span style={{ fontSize: 12, color: "white" }}>✓</span>
                      )}
                    </div>
                  </div>
                  <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)" }}>
                    Score: {variant.score?.toFixed(1) || "—"}/100
                  </div>
                  <div style={{ fontSize: 11, color: "rgba(255,255,255,0.5)" }}>
                    {variant.dna?.primary_style?.replace(/_/g, " ") || "No style"}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {compareVariants.length === 0 && (
          <div style={{
            textAlign: "center",
            padding: 64,
            color: "rgba(255,255,255,0.5)",
          }}>
            <p>Select variants above to start comparing</p>
          </div>
        )}

        {compareVariants.length > 0 && (
          <>
            {/* Side-by-side Comparison */}
            <div style={{
              display: "grid",
              gridTemplateColumns: `repeat(${compareVariants.length}, 1fr)`,
              gap: 24,
              marginBottom: 32,
            }}>
              {compareVariants.map((variant) => (
                <div key={variant.id} style={{
                  background: "rgba(255,255,255,0.03)",
                  borderRadius: 16,
                  border: "1px solid rgba(255,255,255,0.1)",
                  overflow: "hidden",
                }}>
                  {/* Header */}
                  <div style={{
                    padding: 16,
                    borderBottom: "1px solid rgba(255,255,255,0.1)",
                    background: "rgba(255,255,255,0.05)",
                  }}>
                    <div style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: 8,
                    }}>
                      <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
                        Variant {variant.variant_number}
                      </h3>
                      <span style={{
                        fontSize: 14,
                        fontWeight: 600,
                        color: "#22c55e",
                      }}>
                        {variant.score?.toFixed(1) || "—"}/100
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)" }}>
                      {variant.dna?.primary_style?.replace(/_/g, " ") || "No style"}
                    </div>
                  </div>

                  {/* Floor Plan */}
                  <div style={{ padding: 16 }}>
                    <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: "rgba(255,255,255,0.7)" }}>
                      Floor Plan
                    </h4>
                    <div style={{
                      height: 200,
                      background: "rgba(255,255,255,0.05)",
                      borderRadius: 8,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      border: "1px solid rgba(255,255,255,0.1)",
                    }}>
                      {variant.floor_plan_svg ? (
                        <div
                          dangerouslySetInnerHTML={{ __html: variant.floor_plan_svg }}
                          style={{ width: "100%", height: "100%" }}
                        />
                      ) : (
                        <span style={{ color: "rgba(255,255,255,0.4)", fontSize: 12 }}>
                          No floor plan available
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 3D Thumbnail */}
                  <div style={{ padding: "0 16px 16px" }}>
                    <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: "rgba(255,255,255,0.7)" }}>
                      3D Model
                    </h4>
                    <div style={{
                      height: 150,
                      background: "rgba(255,255,255,0.05)",
                      borderRadius: 8,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      border: "1px solid rgba(255,255,255,0.1)",
                    }}>
                      {variant.thumbnail_url ? (
                        <Image
                          src={variant.thumbnail_url}
                          alt={`Variant ${variant.variant_number} 3D model`}
                          width={300}
                          height={150}
                          style={{
                            objectFit: "cover",
                            borderRadius: 8,
                            width: "100%",
                            height: "100%",
                          }}
                        />
                      ) : (
                        <span style={{ color: "rgba(255,255,255,0.4)", fontSize: 12 }}>
                          🏗️ 3D Model
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Select Button */}
                  <div style={{ padding: 16, paddingTop: 0 }}>
                    <button
                      onClick={() => selectVariant(variant.id)}
                      style={{
                        width: "100%",
                        padding: "8px 16px",
                        borderRadius: 8,
                        border: "1px solid #7c3aed",
                        background: variant.is_selected ? "#7c3aed" : "rgba(124,58,237,0.1)",
                        color: "white",
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: "pointer",
                        transition: "all 0.2s",
                      }}
                    >
                      {variant.is_selected ? "✓ Selected" : "Select This Variant"}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Radar Chart */}
            <div style={{
              background: "rgba(255,255,255,0.03)",
              borderRadius: 16,
              border: "1px solid rgba(255,255,255,0.1)",
              padding: 24,
              marginBottom: 32,
            }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
                Performance Comparison
              </h3>
              <VariantRadarChart variants={compareVariants} />
            </div>

            {/* DNA Diff Table */}
            <DNADiff variants={compareVariants} />

            {/* Cost Comparison */}
            {project.cost_estimates && project.cost_estimates.length > 0 && (
              <div style={{
                background: "rgba(255,255,255,0.03)",
                borderRadius: 16,
                border: "1px solid rgba(255,255,255,0.1)",
                padding: 24,
                marginTop: 32,
              }}>
                <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
                  Cost Comparison
                </h3>
                <div style={{
                  display: "grid",
                  gridTemplateColumns: `repeat(${compareVariants.length}, 1fr)`,
                  gap: 24,
                }}>
                  {compareVariants.map((variant, index) => (
                    <div key={variant.id} style={{
                      textAlign: "center",
                      padding: 16,
                      background: "rgba(255,255,255,0.05)",
                      borderRadius: 12,
                    }}>
                      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", marginBottom: 8 }}>
                        Variant {variant.variant_number}
                      </div>
                      <div style={{ fontSize: 18, fontWeight: 600, color: "#fbbf24", marginBottom: 4 }}>
                        ₹{(project.cost_estimates?.[0]?.total_cost_inr || 0).toLocaleString()}
                      </div>
                      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)" }}>
                        ₹{(project.cost_estimates?.[0]?.cost_per_sqft || 0).toLocaleString()}/sqft
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}