"""Client Jellyseerr (lecture) — récupère le lien Jellyfin d'un contenu."""

import aiohttp

from config import SEERR_API_KEY, SEERR_URL

_HEADERS = {"X-Api-Key": SEERR_API_KEY}
_TIMEOUT = aiohttp.ClientTimeout(total=10)


async def media_url(media_type: str, tmdb_id: str | int) -> str | None:
    """Lien profond vers la fiche Jellyfin du film/série, via `mediaInfo`."""
    path = "tv" if media_type == "tv" else "movie"
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
            async with s.get(
                f"{SEERR_URL}/api/v1/{path}/{tmdb_id}", headers=_HEADERS
            ) as resp:
                if resp.status != 200:
                    return None
                info = (await resp.json()).get("mediaInfo") or {}
    except (aiohttp.ClientError, TimeoutError):
        return None
    return info.get("mediaUrl") or None
