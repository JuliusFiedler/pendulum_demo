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
    import platform  # pygbag: platform.window / platform.jsiter bridge JS async

# The apikey is passed as a query parameter because pygbag's Fetch.GET/POST
# helpers can't set custom headers. Supabase's gateway accepts ?apikey=... .
_AUTH = f"apikey={_KEY}"


def _js(obj):
    """Python dict/list -> real JS object (pygbag has no direct dict marshaling)."""
    return platform.window.JSON.parse(json.dumps(obj))


async def submit(game, name, time_s):
    """Insert one score. No-op on native. Never raises (network is best-effort)."""
    if not IS_WEB:
        return
    name = (str(name).strip() or "anon")[:20]
    body = json.dumps({"game": game, "name": name, "time_s": float(time_s)})
    # pygbag's Fetch.POST sets no Content-Type (Supabase then 400s) but forwards
    # a 3rd `flags` arg to fetch(); pass method/headers/body through it. jsiter
    # bridges the JS generator to an awaitable (a bare fetch() promise hangs).
    flags = _js({"method": "POST",
                 "headers": {"Content-Type": "application/json"},
                 "body": body})
    try:
        await platform.jsiter(platform.window.Fetch.POST(f"{_URL}?{_AUTH}", "", flags))
    except Exception as e:  # noqa: BLE001 -- a failed submit must not kill the game
        print("leaderboard submit failed:", e, flush=True)


async def top(game, ascending, limit=17):
    """Return [{'name', 'time_s'}, ...] best-first. [] on native or on error."""
    if not IS_WEB:
        return []
    order = "asc" if ascending else "desc"
    url = (f"{_URL}?game=eq.{game}&select=name,time_s"
           f"&order=time_s.{order}&limit={limit}&{_AUTH}")
    try:
        text = await platform.jsiter(platform.window.Fetch.GET(url))
        data = json.loads(str(text))
        # a Supabase error is a dict, not a list -> treat as empty board
        return data if isinstance(data, list) else []
    except Exception as e:  # noqa: BLE001
        print("leaderboard fetch failed:", e, flush=True)
        return []
