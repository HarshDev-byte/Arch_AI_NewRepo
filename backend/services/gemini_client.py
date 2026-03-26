"""
Gemini multi-key client with automatic rotation.
Spreads requests across up to 3 keys to stay within the 15 req/min limit per key.
Falls back to Ollama (local llama3) if all keys hit rate limits.
"""
import os
import asyncio
import time
import httpx
from typing import Optional

# Load up to 3 Gemini keys from environment
GEMINI_KEYS = [k for k in [
    os.getenv("GEMINI_KEY_A"),
    os.getenv("GEMINI_KEY_B"),
    os.getenv("GEMINI_KEY_C"),
] if k]

# Default model — always use Flash, not Pro (Flash has 1,500/day free)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

class KeyState:
    """Tracks usage per key to avoid rate limits."""
    def __init__(self, key: str):
        self.key        = key
        self.requests   = []       # timestamps of recent requests
        self.daily_count = 0
        self.last_reset = time.time()

    def reset_daily_if_needed(self):
        if time.time() - self.last_reset > 86400:  # 24 hours
            self.daily_count = 0
            self.last_reset  = time.time()

    def can_use(self) -> bool:
        self.reset_daily_if_needed()
        if self.daily_count >= 1450:   # Leave 50 buffer from the 1,500 limit
            return False
        # Check per-minute rate (15/min per key)
        now   = time.time()
        self.requests = [t for t in self.requests if now - t < 60]
        return len(self.requests) < 14  # Leave 1 buffer from the 15/min limit

    def record_use(self):
        self.requests.append(time.time())
        self.daily_count += 1

# Global key states (in-memory — resets on server restart, which is fine)
_key_states: list[KeyState] = [KeyState(k) for k in GEMINI_KEYS]
_current_key_idx = 0
_lock = asyncio.Lock()

async def _pick_key() -> Optional[KeyState]:
    """Round-robin key selection, skipping exhausted keys."""
    global _current_key_idx
    async with _lock:
        if not _key_states:
            return None
        start = _current_key_idx
        for _ in range(len(_key_states)):
            state = _key_states[_current_key_idx % len(_key_states)]
            _current_key_idx = (_current_key_idx + 1) % len(_key_states)
            if state.can_use():
                return state
        return None   # All keys exhausted — will fall back to Ollama

async def call_gemini(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """
    Main entry point. Tries each Gemini key in rotation.
    Falls back to Ollama if all keys are rate-limited.
    """
    key_state = await _pick_key()

    if key_state is None:
        # All Gemini keys exhausted — use local Ollama
        return await _call_ollama(prompt, system)

    url = GEMINI_API_URL.format(model=GEMINI_MODEL)
    body = {
        "contents": [{"parts": [{"text": f"{system}\n\n{prompt}" if system else prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.7,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                url,
                params={"key": key_state.key},
                json=body
            )
            if r.status_code == 429:
                # This key is rate limited right now — try next key
                key_state.daily_count = 1450  # Mark as exhausted temporarily
                return await call_gemini(prompt, system, max_tokens)

            if r.status_code != 200:
                raise ValueError(f"Gemini error {r.status_code}: {r.text}")

            key_state.record_use()
            data = r.json()
            # Defensive path in case structure differs
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                return str(data)

    except httpx.TimeoutException:
        # Network timeout — fall back to Ollama
        return await _call_ollama(prompt, system)

async def _call_ollama(prompt: str, system: str) -> str:
    """
    Completely free fallback — runs llama3 locally via Ollama.
    Install: https://ollama.com → then run: ollama pull llama3
    """
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": f"{system}\n\n{prompt}" if system else prompt,
                    "stream": False
                }
            )
            r.raise_for_status()
            return r.json().get("response", "")
    except Exception:
        return (
            '{"error": "No AI provider available. '
            'Add GEMINI_KEY_A to .env or run: ollama pull llama3"}'
        )

async def get_key_status() -> list[dict]:
    """Returns status of all keys — used by the settings UI."""
    status = []
    for i, ks in enumerate(_key_states):
        ks.reset_daily_if_needed()
        now = time.time()
        recent = [t for t in ks.requests if now - t < 60]
        status.append({
            "key_label":    f"KEY-{'ABC'[i]}",
            "key_preview":  ks.key[-4:],
            "daily_used":   ks.daily_count,
            "daily_limit":  1500,
            "per_min_used": len(recent),
            "per_min_limit": 15,
            "available":    ks.can_use(),
        })
    return status
