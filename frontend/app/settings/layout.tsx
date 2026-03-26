import React from "react";

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-5xl mx-auto py-8">
        <h1 className="text-3xl font-semibold mb-6">Settings</h1>
        <div>{children}</div>
      </div>
    </div>
  );
}
