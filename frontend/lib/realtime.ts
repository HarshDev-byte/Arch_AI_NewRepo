import { supabase } from "./supabase";

export function subscribeToProject(projectId: string, callback: (payload: unknown) => void) {
  return supabase
    .channel(`project-${projectId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "projects", filter: `id=eq.${projectId}` }, callback)
    .subscribe();
}
