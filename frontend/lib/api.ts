const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export const apiClient = {
  get: <T = any>(path: string) => request(path, { method: "GET" }) as Promise<T>,
  post: <T = any>(path: string, body?: any) => request(path, { method: "POST", body: JSON.stringify(body) }) as Promise<T>,
  put: <T = any>(path: string, body?: any) => request(path, { method: "PUT", body: JSON.stringify(body) }) as Promise<T>,
  delete: <T = any>(path: string) => request(path, { method: "DELETE" }) as Promise<T>,
};

export default apiClient;
