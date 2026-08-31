"""Client Jellyfin — lecture (statut, sessions) et écriture (comptes).

L'écriture (création d'utilisateur, policy, mot de passe, désactivation)
est nouvelle en Layer 3 (ADR-021). La clé API Jellyfin n'est pas scopable :
une clé = accès complet.
"""

import aiohttp

from config import JELLYFIN_API_KEY, JELLYFIN_URL, NEW_USER_POLICY

_HEADERS = {"X-Emby-Token": JELLYFIN_API_KEY}
_TIMEOUT = aiohttp.ClientTimeout(total=10)


class JellyfinError(RuntimeError):
    pass


async def is_online() -> bool:
    url = f"{JELLYFIN_URL}/System/Info/Public"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as s:
            async with s.get(url) as resp:
                return resp.status == 200
    except (aiohttp.ClientError, TimeoutError):
        return False


async def active_sessions() -> list[dict] | None:
    """Sessions avec une lecture en cours, ou None si Jellyfin injoignable."""
    url = f"{JELLYFIN_URL}/Sessions"
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
            async with s.get(url, headers=_HEADERS) as resp:
                if resp.status != 200:
                    return None
                sessions = await resp.json()
    except (aiohttp.ClientError, TimeoutError):
        return None
    return [x for x in sessions if x.get("NowPlayingItem")]


def describe_session(session: dict) -> str:
    user = session.get("UserName", "Quelqu'un")
    item = session.get("NowPlayingItem", {})
    title = item.get("Name", "un contenu")
    series = item.get("SeriesName")
    label = f"{series} — {title}" if series else title
    return f"{user} regarde {label}"


async def random_unplayed_movie(user_id: str) -> dict | None:
    """Un film de la bibliothèque que `user_id` n'a pas encore vu, au hasard."""
    params = {
        "IncludeItemTypes": "Movie",
        "Recursive": "true",
        "IsPlayed": "false",
        "SortBy": "Random",
        "Limit": "1",
        "Fields": "Overview,ProductionYear",
    }
    url = f"{JELLYFIN_URL}/Users/{user_id}/Items"
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
        async with s.get(url, headers=_HEADERS, params=params) as resp:
            resp.raise_for_status()
            items = (await resp.json()).get("Items", [])
    return items[0] if items else None


async def find_item(name: str, item_type: str) -> dict | None:
    """Premier item de la bibliothèque correspondant au titre (best effort)."""
    params = {
        "searchTerm": name,
        "IncludeItemTypes": item_type,
        "Recursive": "true",
        "Limit": "1",
    }
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
            async with s.get(
                f"{JELLYFIN_URL}/Items", headers=_HEADERS, params=params
            ) as resp:
                resp.raise_for_status()
                items = (await resp.json()).get("Items", [])
    except (aiohttp.ClientError, TimeoutError):
        return None
    return items[0] if items else None


async def list_users() -> list[dict]:
    url = f"{JELLYFIN_URL}/Users"
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
        async with s.get(url, headers=_HEADERS) as resp:
            resp.raise_for_status()
            return await resp.json()


async def username_taken(name: str) -> bool:
    lowered = name.casefold()
    return any(u.get("Name", "").casefold() == lowered for u in await list_users())


async def create_user(name: str, password: str) -> dict:
    """Crée l'utilisateur, applique la policy Layer 3, retourne l'objet user."""
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
        async with s.post(
            f"{JELLYFIN_URL}/Users/New",
            headers=_HEADERS,
            json={"Name": name, "Password": password},
        ) as resp:
            if resp.status not in (200, 204):
                raise JellyfinError(
                    f"création user {name!r} : HTTP {resp.status} {await resp.text()}"
                )
            user = await resp.json()

        user_id = user["Id"]
        # Certaines versions ignorent Password dans /Users/New : on force.
        await _set_password(s, user_id, password)
        await _apply_policy(s, user_id)
        await _apply_default_prefs(s, user_id)
    return user


# Défauts orientés VOSTFR : audio VF quand elle existe, sinon VO + sous-titres
# FR automatiques. Qui veut la VO permanente passe l'audio sur "Anglais".
_DEFAULT_PREFS = {
    "AudioLanguagePreference": "fre",
    "PlayDefaultAudioTrack": False,
    "SubtitleLanguagePreference": "fre",
    "SubtitleMode": "Smart",
}


async def _apply_default_prefs(session: aiohttp.ClientSession, user_id: str) -> None:
    async with session.get(f"{JELLYFIN_URL}/Users/{user_id}", headers=_HEADERS) as resp:
        resp.raise_for_status()
        config = (await resp.json()).get("Configuration", {})
    config.update(_DEFAULT_PREFS)
    async with session.post(
        f"{JELLYFIN_URL}/Users/{user_id}/Configuration",
        headers=_HEADERS,
        json=config,
    ) as resp:
        if resp.status not in (200, 204):
            raise JellyfinError(
                f"préférences user {user_id} : HTTP {resp.status} {await resp.text()}"
            )


async def reset_password(user_id: str, new_password: str) -> None:
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
        await _set_password(s, user_id, new_password)


async def set_disabled(user_id: str, disabled: bool) -> None:
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
        policy = await _get_policy(s, user_id)
        policy["IsDisabled"] = disabled
        await _post_policy(s, user_id, policy)


async def delete_user(user_id: str) -> None:
    """Suppression définitive du compte Jellyfin (irréversible)."""
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
        async with s.delete(
            f"{JELLYFIN_URL}/Users/{user_id}", headers=_HEADERS
        ) as resp:
            if resp.status not in (200, 204):
                raise JellyfinError(
                    f"suppression user {user_id} : HTTP {resp.status} "
                    f"{await resp.text()}"
                )


async def _set_password(
    session: aiohttp.ClientSession, user_id: str, new_password: str
) -> None:
    async with session.post(
        f"{JELLYFIN_URL}/Users/{user_id}/Password",
        headers=_HEADERS,
        json={"NewPw": new_password, "ResetPassword": False},
    ) as resp:
        if resp.status not in (200, 204):
            raise JellyfinError(
                f"mot de passe user {user_id} : HTTP {resp.status} {await resp.text()}"
            )


async def _get_policy(session: aiohttp.ClientSession, user_id: str) -> dict:
    async with session.get(f"{JELLYFIN_URL}/Users/{user_id}", headers=_HEADERS) as resp:
        resp.raise_for_status()
        return (await resp.json()).get("Policy", {})


async def _post_policy(
    session: aiohttp.ClientSession, user_id: str, policy: dict
) -> None:
    async with session.post(
        f"{JELLYFIN_URL}/Users/{user_id}/Policy", headers=_HEADERS, json=policy
    ) as resp:
        if resp.status not in (200, 204):
            raise JellyfinError(
                f"policy user {user_id} : HTTP {resp.status} {await resp.text()}"
            )


async def _apply_policy(session: aiohttp.ClientSession, user_id: str) -> None:
    policy = await _get_policy(session, user_id)
    policy.update(NEW_USER_POLICY)
    await _post_policy(session, user_id, policy)
