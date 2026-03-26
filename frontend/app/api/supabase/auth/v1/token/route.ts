import { NextRequest, NextResponse } from 'next/server';

// Reuse same in-memory stores as signup route (module scope per serverless instance)
const users: Record<string, any> = (global as any).__ARCHAI_MOCK_USERS__ || {};
const sessions: Record<string, any> = (global as any).__ARCHAI_MOCK_SESSIONS__ || {};
(global as any).__ARCHAI_MOCK_USERS__ = users;
(global as any).__ARCHAI_MOCK_SESSIONS__ = sessions;

function makeToken() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // password grant
    if (body.grant_type === 'password') {
      const email = body.username || body.email;
      const password = body.password;
      if (!email || !password) return NextResponse.json({ error: 'missing_credentials' }, { status: 400 });
      const found = users[email];
      if (!found || found.password !== password) return NextResponse.json({ error: 'invalid_credentials' }, { status: 400 });

      const access_token = makeToken();
      const refresh_token = makeToken();
      const session = { access_token, refresh_token, expires_in: 60 * 60 * 24 * 7, token_type: 'bearer', user: found.user };
      sessions[access_token] = session;

      return NextResponse.json({ access_token, refresh_token, expires_in: session.expires_in, token_type: 'bearer', user: found.user }, { status: 200 });
    }

    // refresh token grant
    if (body.grant_type === 'refresh_token') {
      const refresh = body.refresh_token;
      const entry = Object.values(sessions).find((s: any) => s.refresh_token === refresh);
      if (!entry) return NextResponse.json({ error: 'invalid_refresh' }, { status: 400 });
      const access_token = makeToken();
      const refresh_token = makeToken();
      const session = { access_token, refresh_token, expires_in: 60 * 60 * 24 * 7, token_type: 'bearer', user: entry.user };
      sessions[access_token] = session;
      return NextResponse.json({ access_token, refresh_token, expires_in: session.expires_in, token_type: 'bearer', user: entry.user }, { status: 200 });
    }

    return NextResponse.json({ error: 'unsupported_grant' }, { status: 400 });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
