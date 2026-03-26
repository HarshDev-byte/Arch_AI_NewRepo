import { createRouteHandlerClient } from "@supabase/auth-helpers-nextjs";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * /auth/callback — OAuth PKCE code exchange.
 *
 * After Google OAuth (or any provider), Supabase redirects here with ?code=...
 * We exchange it for a session, then redirect to /dashboard.
 *
 * Also handles magic-link and email-confirmation flows (same route).
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code  = searchParams.get("code");
  const next  = searchParams.get("next") ?? "/dashboard";   // optional redirect target

  if (code) {
    const cookieStore = cookies();
    const supabase    = createRouteHandlerClient({ cookies: () => cookieStore });
    const { error }   = await supabase.auth.exchangeCodeForSession(code);

    if (error) {
      console.error("[auth/callback] exchangeCodeForSession error:", error.message);
      return NextResponse.redirect(new URL(`/auth?error=${encodeURIComponent(error.message)}`, origin));
    }
  }

  // Redirect to the intended destination (default: /dashboard)
  const dest = next.startsWith("/") ? next : "/dashboard";
  return NextResponse.redirect(new URL(dest, origin));
}
