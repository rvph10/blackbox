"""Persistance SQLite du bot — mapping Discord ↔ Jellyfin + méta du cycle.

Une seule responsabilité : stocker le lien entre un membre Discord et son
compte Jellyfin, plus quelques clés/valeurs (date du dernier classement,
ancre du cycle). Voir docs/adr/021-bot-layer3.md.
"""

import datetime as dt

import aiosqlite

from config import BOT_DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS members (
    discord_id   INTEGER PRIMARY KEY,
    jf_user_id   TEXT NOT NULL,
    jf_username  TEXT NOT NULL,
    display_name TEXT,
    created_at   TEXT NOT NULL,
    tier         TEXT,
    note         TEXT
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


async def init() -> None:
    async with aiosqlite.connect(BOT_DB_PATH) as conn:
        await conn.executescript(SCHEMA)
        await conn.commit()


async def add_member(
    discord_id: int,
    jf_user_id: str,
    jf_username: str,
    display_name: str | None = None,
    note: str | None = None,
) -> None:
    async with aiosqlite.connect(BOT_DB_PATH) as conn:
        await conn.execute(
            """INSERT INTO members
               (discord_id, jf_user_id, jf_username, display_name, created_at, note)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(discord_id) DO UPDATE SET
                 jf_user_id=excluded.jf_user_id,
                 jf_username=excluded.jf_username,
                 display_name=excluded.display_name,
                 note=excluded.note""",
            (
                discord_id,
                jf_user_id,
                jf_username,
                display_name,
                dt.datetime.now(dt.UTC).isoformat(),
                note,
            ),
        )
        await conn.commit()


async def get_member(discord_id: int) -> dict | None:
    async with aiosqlite.connect(BOT_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM members WHERE discord_id = ?", (discord_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_by_jf_user_id(jf_user_id: str) -> dict | None:
    async with aiosqlite.connect(BOT_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM members WHERE jf_user_id = ?", (jf_user_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def all_members() -> list[dict]:
    async with aiosqlite.connect(BOT_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM members")
        return [dict(r) for r in await cur.fetchall()]


async def set_tier(discord_id: int, tier: str) -> None:
    async with aiosqlite.connect(BOT_DB_PATH) as conn:
        await conn.execute(
            "UPDATE members SET tier = ? WHERE discord_id = ?", (tier, discord_id)
        )
        await conn.commit()


async def append_note(discord_id: int, text: str) -> None:
    async with aiosqlite.connect(BOT_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT note FROM members WHERE discord_id = ?", (discord_id,)
        )
        row = await cur.fetchone()
        stamp = dt.date.today().isoformat()
        prefix = (row["note"] + " | ") if row and row["note"] else ""
        await conn.execute(
            "UPDATE members SET note = ? WHERE discord_id = ?",
            (f"{prefix}{stamp}: {text}", discord_id),
        )
        await conn.commit()


async def get_meta(key: str) -> str | None:
    async with aiosqlite.connect(BOT_DB_PATH) as conn:
        cur = await conn.execute("SELECT value FROM meta WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row[0] if row else None


async def set_meta(key: str, value: str) -> None:
    async with aiosqlite.connect(BOT_DB_PATH) as conn:
        await conn.execute(
            """INSERT INTO meta (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )
        await conn.commit()
