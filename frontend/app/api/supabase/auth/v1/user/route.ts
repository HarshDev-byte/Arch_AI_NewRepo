import { NextRequest, NextResponse } from 'next/server';

const sessions: Record<string, any> = (global as any).__ARCHAI_MOCK_SESSIONS__ || {};
(global as any).__ARCHAI_MOCK_SESSIONS__ = sessions;

export async function GET(req: NextRequest) {
  try {
    const auth = req.headers.get('authorization') || '';
    const m = auth.match(/Bearer (.+)/);
    if (!m) return NextResponse.json({ data: null }, { status: 200 });
    const token = m[1];
    const session = sessions[token];
    if (!session) return NextResponse.json({ data: null }, { status: 200 });
    return NextResponse.json({ data: session.user }, { status: 200 });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
