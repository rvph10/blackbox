"""Écouteur HTTP interne pour l'agent Webhook de Jellyseerr (ADR-009 rév.).

Jellyseerr POST `/jellyseerr` à chaque « Media Available ». Le bot poste une
annonce dans #annonces en pinguant le demandeur (ID Discord de son profil
Jellyseerr, repli sur le mapping `jf_username`). Jamais exposé publiquement
(joignable seulement par `seerr → bot:8000` sur le réseau Docker).
"""

import json
import logging

import discord
from aiohttp import web

import db
import jellyfin
import seerr
from config import (
    CONTENT_CHANNEL_ID,
    PUBLIC_STREAM_URL,
    SEERR_WEBHOOK_SECRET,
    TMDB_IMAGE_BASE,
)
from notify import admin_alert

logger = logging.getLogger("blackbox-bot.seerr_hook")

_ANNOUNCED_KEY = "announced_media"
_MAX_TRACKED = 400


async def _already_announced(request_id: str) -> bool:
    raw = await db.get_meta(_ANNOUNCED_KEY)
    return bool(raw) and request_id in json.loads(raw)


async def _remember(request_id: str) -> None:
    raw = await db.get_meta(_ANNOUNCED_KEY)
    ids = json.loads(raw) if raw else []
    ids.append(request_id)
    await db.set_meta(_ANNOUNCED_KEY, json.dumps(ids[-_MAX_TRACKED:]))


async def _requester_label(payload: dict) -> str:
    discord_id = (payload.get("requestedBy_discordId") or "").strip()
    if discord_id.isdigit():
        return f"<@{discord_id}>"
    username = (payload.get("requestedBy_username") or "").strip()
    if username:
        member = await db.get_by_jf_username(username)
        if member:
            return f"<@{member['discord_id']}>"
        return username
    return "quelqu'un"


async def _watch_link(title: str, media_type: str, tmdb_id: str) -> str:
    """Fiche Jellyfin du contenu : via Jellyseerr d'abord (lien exact), puis
    recherche par titre dans Jellyfin, sinon la page d'accueil."""
    if tmdb_id:
        url = await seerr.media_url(media_type, tmdb_id)
        if url:
            return url
    jf_type = "Series" if media_type == "tv" else "Movie"
    item = await jellyfin.find_item(title.split(" (")[0], jf_type)
    if item:
        return f"{PUBLIC_STREAM_URL}/web/#/details?id={item['Id']}"
    return PUBLIC_STREAM_URL


async def _handle(request: web.Request) -> web.Response:
    if SEERR_WEBHOOK_SECRET and request.headers.get("Authorization") != (
        SEERR_WEBHOOK_SECRET
    ):
        return web.Response(status=401, text="unauthorized")

    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        return web.Response(status=400, text="bad json")

    ntype = payload.get("notification_type", "")
    if ntype == "TEST_NOTIFICATION":
        await admin_alert("[OK] Webhook Jellyseerr → bot : test reçu.")
        return web.Response(status=200, text="ok")
    if ntype != "MEDIA_AVAILABLE":
        return web.Response(status=200, text="ignored")

    request_id = str(payload.get("request_id") or payload.get("tmdbId") or "")
    if request_id and await _already_announced(request_id):
        return web.Response(status=200, text="dup")

    client: discord.Client = request.app["client"]
    channel = client.get_channel(CONTENT_CHANNEL_ID)
    if channel is None:
        logger.warning("salon d'annonces (%s) introuvable", CONTENT_CHANNEL_ID)
        return web.Response(status=200, text="no channel")

    title = payload.get("subject") or "Nouveau contenu"
    media_type = payload.get("media_type", "movie")
    label = (
        "Nouvelle série disponible" if media_type == "tv" else "Nouveau film disponible"
    )
    overview = (payload.get("message") or "").strip()
    if len(overview) > 350:
        overview = overview[:347] + "…"
    link = await _watch_link(title, media_type, str(payload.get("tmdbId") or ""))

    embed = discord.Embed(title=title, description=overview or None, url=link)
    image = payload.get("image") or ""
    if image.startswith("http"):
        embed.set_thumbnail(url=image)
    elif image:
        embed.set_thumbnail(url=f"{TMDB_IMAGE_BASE}{image}")
    embed.add_field(
        name="Demandé par", value=await _requester_label(payload), inline=True
    )
    embed.add_field(name="Regarder", value=link, inline=False)

    try:
        await channel.send(content=f"**{label}**", embed=embed)
    except discord.HTTPException as exc:
        logger.warning("annonce non postée : %s", exc)
        return web.Response(status=200, text="send failed")

    if request_id:
        await _remember(request_id)
    logger.info("annonce postée : %s", title)
    return web.Response(status=200, text="ok")


async def _health(_request: web.Request) -> web.Response:
    return web.Response(text="ok")


def make_app(client: discord.Client) -> web.Application:
    app = web.Application()
    app["client"] = client
    app.router.add_post("/jellyseerr", _handle)
    app.router.add_get("/health", _health)
    return app
