import { createMiddlewareClient } from "@supabase/auth-helpers-nextjs";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Next.js edge middleware — Supabase session guard.
 *
 * Behaviour
 * ---------
 *  /dashboard/*  and  /project/*   → require session → redirect to /auth
 *  /auth/*                          → redirect to /dashboard if already signed in
 *  Everything else                  → pass through
 *
 * Session tokens are refreshed automatically on each request so the
 * access token never expires mid-session.
 */
export async function middleware(req: NextRequest) {
  const res = NextResponse.next();

  // If Supabase env isn't configured (local dev), or mock mode enabled, skip middleware checks.
  if (
    process.env.NEXT_PUBLIC_SUPABASE_MOCK === "1" ||
    !process.env.NEXT_PUBLIC_SUPABASE_URL ||
    !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  ) {
    return res;
  }

  const supabase = createMiddlewareClient({ req, res });

  // Refresh session (also sets cookies on response)
  const { data: { session } } = await supabase.auth.getSession();

  const { pathname } = req.nextUrl;

  // ── Protected routes — require auth ───────────────────────────────────────
  const PROTECTED = ["/dashboard", "/project"];
  const isProtected = PROTECTED.some((p) => pathname.startsWith(p));

  if (isProtected && !session) {
    const redirectUrl = req.nextUrl.clone();
    redirectUrl.pathname = "/auth";
    redirectUrl.searchParams.set("next", pathname);   // remember where they wanted to go
    return NextResponse.redirect(redirectUrl);
  }

  // ── Auth routes — skip if already signed in ───────────────────────────────
  const AUTH_PATHS = ["/auth"];
  const isAuthPage = AUTH_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));

  // Don't redirect /auth/callback — that's the OAuth landing page
  if (isAuthPage && !pathname.startsWith("/auth/callback") && session) {
    const redirectUrl = req.nextUrl.clone();
    redirectUrl.pathname = "/dashboard";
    return NextResponse.redirect(redirectUrl);
  }

  return res;
}

export const config = {
  matcher: [
    /*
     * Match all request paths EXCEPT:
     *   - _next/static  (Next.js static files)
     *   - _next/image   (image optimisation)
     *   - favicon.ico
     *   - *.{png,jpg,svg,ico,webp,...}  (public assets)
     * This ensures the middleware only runs on page/API routes.
     */
    "/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:png|jpg|jpeg|gif|webp|svg|ico)).*)",
  ],
};
