import { NextRequest } from "next/server";

export async function GET(req: NextRequest) {
  // WebSocket bridge – upgrade handled by edge runtime
  return new Response("WebSocket bridge endpoint", { status: 200 });
}
