"""Shared online leaderboard backed by Supabase (web build only).

On the native (booth) build this is inert -- highscores stay in local JSON
files. In the browser (pygbag, sys.platform == "emscripten") scores are read
from / written to a Supabase table via its REST API using the public anon key.

The anon key is meant to be public: Row-Level Security on the table restricts it
to SELECT + INSERT only (no update/delete, no other tables). See README.

Table (create once in the Supabase SQL editor):

    create table highscores (
      id bigint generated always as identity primary key,
      game text not null check (game in ('balance','swingup')),
      name text not null check (char_length(name) between 1 and 20),
      time_s double precision not null check (time_s >= 0),
      created_at timestamptz default now()
    );
    alter table highscores enable row level security;
    create policy "public read"   on highscores for select using (true);
    create policy "public insert" on highscores for insert with check (true);
"""

import json
import sys

IS_WEB = sys.platform == "emscripten"

_PROJECT = "rnsalsbllsmlufagdeup"
_URL = f"https://{_PROJECT}.supabase.co/rest/v1/highscores"
_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJuc2Fsc2JsbHNtbHVmYWdkZXVwIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3ODQ4OTA5NzcsImV4cCI6MjEwMDQ2Njk3N30."
    "9TVCWldC99BpFb2bihyUGWXvQejJF5FzIdERugQjCmM"
)

if IS_WEB:
    import platform  # pygbag: platform.window is the JS window proxy


def _opts(method, body=None):
    """Build a JS fetch options object from Python via JSON.parse (pygbag-safe)."""
    o = {"method": method, "headers": {"apikey": _KEY, "Authorization": f"Bearer {_KEY}"}}
    if body is not None:
        o["headers"]["Content-Type"] = "application/json"
        o["headers"]["Prefer"] = "return=minimal"
        o["body"] = body
    return platform.window.JSON.parse(json.dumps(o))


async def submit(game, name, time_s):
    """Insert one score. No-op on native. Never raises (network is best-effort)."""
    if not IS_WEB:
        return
    name = (str(name).strip() or "anon")[:20]
    row = json.dumps({"game": game, "name": name, "time_s": float(time_s)})
    try:
        await platform.window.fetch(_URL, _opts("POST", row))
    except Exception as e:  # noqa: BLE001 -- a failed submit must not kill the game
        print("leaderboard submit failed:", e, flush=True)


async def top(game, ascending, limit=17):
    """Return [{'name', 'time_s'}, ...] best-first. [] on native or on error."""
    if not IS_WEB:
        return []
    order = "asc" if ascending else "desc"
    url = f"{_URL}?game=eq.{game}&select=name,time_s&order=time_s.{order}&limit={limit}"
    try:
        resp = await platform.window.fetch(url, _opts("GET"))
        text = await resp.text()
        return json.loads(str(text))
    except Exception as e:  # noqa: BLE001
        print("leaderboard fetch failed:", e, flush=True)
        return []
