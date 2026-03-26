"use client";

import React, { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import GeminiKeyStatus from "@/components/settings/GeminiKeyStatus";

type APIKey = {
  id: string;
  provider: string;
  label: string;
  key_preview: string;
  is_active: boolean;
};

export default function Page() {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState("openai");
  const [label, setLabel] = useState("");
  const [key, setKey] = useState("");

  async function load() {
    setLoading(true);
    try {
      const data = await apiClient.get<APIKey[]>("/api/users/me/api-keys");
      setKeys(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    try {
      await apiClient.post("/api/users/me/api-keys", { provider, label, key });
      setLabel("");
      setKey("");
      load();
    } catch (err) {
      console.error(err);
      alert("Failed to add key");
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this key?")) return;
    try {
      await apiClient.delete(`/api/users/me/api-keys/${id}`);
      load();
    } catch (err) {
      console.error(err);
      alert("Delete failed");
    }
  }

  async function handleTest(id: string) {
    try {
      await apiClient.post(`/api/users/me/api-keys/${id}/test`);
      alert("Test OK");
    } catch (err) {
      console.error(err);
      alert("Test failed");
    }
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">API Keys</h1>

      <GeminiKeyStatus />

      <form onSubmit={handleAdd} className="mb-6 space-y-2">
        <div>
          <label className="block text-sm font-medium">Provider</label>
          <select value={provider} onChange={(e) => setProvider(e.target.value)} className="mt-1 block w-full">
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="ollama">Ollama (local)</option>
            <option value="groq">Groq</option>
            <option value="gemini">Gemini</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium">Label</label>
          <input value={label} onChange={(e) => setLabel(e.target.value)} className="mt-1 block w-full" />
        </div>
        <div>
          <label className="block text-sm font-medium">Key</label>
          <input value={key} onChange={(e) => setKey(e.target.value)} className="mt-1 block w-full" />
        </div>
        <div>
          <button className="px-4 py-2 bg-sky-600 text-white rounded">Add Key</button>
        </div>
      </form>

      <div>
        <h2 className="text-lg font-semibold mb-2">Your Keys</h2>
        {loading ? (
          <div>Loading...</div>
        ) : (
          <ul className="space-y-2">
            {keys.map((k) => (
              <li key={k.id} className="p-3 border rounded flex justify-between items-center">
                <div>
                  <div className="font-medium">{k.label}</div>
                  <div className="text-sm text-muted-foreground">{k.provider} — {k.key_preview}</div>
                </div>
                <div className="space-x-2">
                  <button onClick={() => handleTest(k.id)} className="px-3 py-1 bg-green-600 text-white rounded">Test</button>
                  <button onClick={() => handleDelete(k.id)} className="px-3 py-1 bg-rose-600 text-white rounded">Delete</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
