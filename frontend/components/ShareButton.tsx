"use client";

import { useState, useEffect } from "react";
import { QRCodeSVG } from "qrcode.react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";


interface ShareButtonProps {
  projectId: string;
  projectName: string;
  initialShareToken?: string;
  initialIsPublic?: boolean;
}

interface ShareData {
  share_url?: string;
  token?: string;
  is_public?: boolean;
}

export default function ShareButton({ 
  projectId, 
  projectName, 
  initialShareToken, 
  initialIsPublic = false 
}: ShareButtonProps) {
  const [shareData, setShareData] = useState<ShareData | null>(null);
  
  // Initialize share data on client side
  useEffect(() => {
    if (initialShareToken && typeof window !== 'undefined') {
      setShareData({
        share_url: `${window.location.origin}/share/${initialShareToken}`,
        token: initialShareToken,
        is_public: initialIsPublic
      });
    }
  }, [initialShareToken, initialIsPublic]);
  const [loading, setLoading] = useState(false);
  const [showQR, setShowQR] = useState(false);
  const [copied, setCopied] = useState(false);

  // Check if project is already shared
  useEffect(() => {
    // This would need to be added to the project API response
    // For now, we'll assume it's not shared initially
  }, [projectId]);

  const createShareLink = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API}/api/projects/${projectId}/share`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include", // Include cookies for auth
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setShareData({ ...data, is_public: true });
    } catch (error) {
      console.error("Error creating share link:", error);
      const message = error instanceof Error ? error.message : "Failed to create share link";
      alert(`Error: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const revokeShareLink = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API}/api/projects/${projectId}/share`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include", // Include cookies for auth
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      setShareData(null);
      setShowQR(false);
    } catch (error) {
      console.error("Error revoking share link:", error);
      const message = error instanceof Error ? error.message : "Failed to revoke share link";
      alert(`Error: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async () => {
    if (!shareData?.share_url) return;

    try {
      await navigator.clipboard.writeText(shareData.share_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy:", error);
      // Fallback for older browsers
      const textArea = document.createElement("textarea");
      textArea.value = shareData.share_url;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isShared = shareData?.is_public;

  return (
    <div style={{
      padding: 16,
      background: "rgba(255,255,255,0.05)",
      borderRadius: 12,
      border: "1px solid rgba(255,255,255,0.1)",
    }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: 12,
      }}>
        <div>
          <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>
            Public Sharing
          </h3>
          <p style={{
            fontSize: 12,
            color: "rgba(255,255,255,0.6)",
            margin: "4px 0 0",
          }}>
            {isShared ? "Project is publicly accessible" : "Project is private"}
          </p>
        </div>

        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}>
          <span style={{
            fontSize: 10,
            padding: "2px 8px",
            borderRadius: 12,
            background: isShared ? "rgba(34,197,94,0.2)" : "rgba(156,163,175,0.2)",
            color: isShared ? "#22c55e" : "#9ca3af",
            fontWeight: 500,
          }}>
            {isShared ? "PUBLIC" : "PRIVATE"}
          </span>

          <button
            onClick={isShared ? revokeShareLink : createShareLink}
            disabled={loading}
            style={{
              padding: "6px 12px",
              fontSize: 12,
              fontWeight: 500,
              borderRadius: 8,
              border: "1px solid rgba(255,255,255,0.2)",
              background: isShared ? "rgba(239,68,68,0.1)" : "rgba(124,58,237,0.1)",
              color: isShared ? "#ef4444" : "#c4b5fd",
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? "..." : isShared ? "Revoke" : "Share"}
          </button>
        </div>
      </div>

      {isShared && shareData?.share_url && (
        <div style={{
          padding: 12,
          background: "rgba(255,255,255,0.05)",
          borderRadius: 8,
          border: "1px solid rgba(255,255,255,0.1)",
        }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 8,
          }}>
            <input
              type="text"
              value={shareData.share_url}
              readOnly
              style={{
                flex: 1,
                padding: "6px 8px",
                fontSize: 12,
                background: "rgba(255,255,255,0.1)",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: 6,
                color: "white",
                fontFamily: "monospace",
              }}
            />
            <button
              onClick={copyToClipboard}
              style={{
                padding: "6px 12px",
                fontSize: 12,
                fontWeight: 500,
                borderRadius: 6,
                border: "1px solid rgba(255,255,255,0.2)",
                background: copied ? "rgba(34,197,94,0.2)" : "rgba(255,255,255,0.1)",
                color: copied ? "#22c55e" : "white",
                cursor: "pointer",
                minWidth: 60,
              }}
            >
              {copied ? "✓" : "Copy"}
            </button>
          </div>

          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}>
            <button
              onClick={() => setShowQR(!showQR)}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                fontWeight: 500,
                borderRadius: 6,
                border: "1px solid rgba(255,255,255,0.2)",
                background: "rgba(255,255,255,0.05)",
                color: "rgba(255,255,255,0.7)",
                cursor: "pointer",
              }}
            >
              {showQR ? "Hide QR" : "Show QR"}
            </button>

            <span style={{
              fontSize: 10,
              color: "rgba(255,255,255,0.4)",
            }}>
              Anyone with this link can view
            </span>
          </div>

          {showQR && (
            <div style={{
              marginTop: 12,
              padding: 12,
              background: "white",
              borderRadius: 8,
              display: "flex",
              justifyContent: "center",
            }}>
              <QRCodeSVG
                value={shareData.share_url}
                size={120}
                level="M"
                includeMargin={true}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}