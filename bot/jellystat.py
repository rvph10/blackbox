"""Client Jellystat (API REST, header x-api-token) — stats de visionnage.

Couplage assumé à quelques endpoints, voir docs/adr/021-bot-layer3.md.
Toutes les durées renvoyées sont en secondes.
"""

import aiohttp

from config import JELLYSTAT_API_KEY, JELLYSTAT_URL

_HEADERS = {"x-api-token": JELLYSTAT_API_KEY}
_TIMEOUT = aiohttp.ClientTimeout(total=15)


async def _get(path: str, params: dict | None = None):
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
        async with s.get(
            f"{JELLYSTAT_URL}{path}", headers=_HEADERS, params=params
        ) as resp:
            resp.raise_for_status()
            return await resp.json()


async def _post(path: str, body: dict):
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
        async with s.post(
            f"{JELLYSTAT_URL}{path}", headers=_HEADERS, json=body
        ) as resp:
            resp.raise_for_status()
            return await resp.json()


async def all_user_activity() -> list[dict]:
    """Cumul tout l'historique : [{UserId, UserName, TotalWatchTime, TotalPlays}]."""
    return await _get("/stats/getAllUserActivity")


async def user_window_seconds(jf_user_id: str, hours: int) -> tuple[int, int]:
    """(secondes vues, nombre de lectures) pour un user sur les `hours` dernières."""
    data = await _post(
        "/stats/getGlobalUserStats", {"hours": hours, "userid": jf_user_id}
    )
    if not data:
        return 0, 0
    seconds = int(data.get("total_playback_duration") or 0)
    plays = int(data.get("Plays") or 0)
    return seconds, plays


async def most_viewed(days: int, media_type: str) -> list[dict]:
    """media_type ∈ {'Movie', 'Series', 'Audio'}."""
    return await _post("/stats/getMostViewedByType", {"days": days, "type": media_type})


async def last_played(jf_user_id: str) -> list[dict]:
    """Jusqu'à 15 dernières lectures d'un utilisateur (les plus récentes)."""
    try:
        return await _post("/stats/getUserLastPlayed", {"userid": jf_user_id})
    except aiohttp.ClientError:
        return []


async def top_genre(jf_user_id: str) -> str | None:
    try:
        rows = await _get(
            "/stats/getGenreUserStats", {"userid": jf_user_id, "size": 1, "page": 1}
        )
    except aiohttp.ClientError:
        return None
    return rows[0]["genre"] if rows else None


async def trigger_full_sync() -> None:
    await _get("/sync/beginSync")
