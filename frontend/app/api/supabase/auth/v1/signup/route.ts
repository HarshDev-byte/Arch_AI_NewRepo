import { NextRequest, NextResponse } from 'next/server';

// Very small in-memory mock for dev only — persisted on global to survive module reloads
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
    const email = body.email || (body.user && body.user.email);
    const password = body.password || (body.user && body.user.password);
    if (!email || !password) return NextResponse.json({ error: 'missing_email_or_password' }, { status: 400 });

    if (users[email]) {
      return NextResponse.json({ error: 'User already registered' }, { status: 400 });
    }

    const id = makeToken();
    const user = { id, email, aud: 'authenticated', role: 'authenticated', created_at: new Date().toISOString() };
    users[email] = { user, password };

    // create session
    const access_token = makeToken();
    const refresh_token = makeToken();
    const session = { access_token, refresh_token, expires_in: 60 * 60 * 24 * 7, token_type: 'bearer', user };
    sessions[access_token] = session;

    return NextResponse.json({ data: { user }, session, error: null }, { status: 200 });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
