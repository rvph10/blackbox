"""Classement bihebdomadaire posté dans #classement (ADR-021 / ADR-022).

Toutes les 15 jours (ancré à la première exécution, état en base `meta`).
Carte-image (podium top 3, couronne sur le n°1) + courte légende qui pingue
le top 3. Transfert du rôle « Tête d'affiche » au n°1.
"""

import datetime as dt
import logging

import discord

import cards
import db
import jellystat
from config import (
    HEADLINER_ROLE_NAME,
    SCOREBOARD_CHANNEL_ID,
    SCOREBOARD_INTERVAL_DAYS,
)

logger = logging.getLogger("blackbox-bot.scoreboard")

_WINDOW_HOURS = SCOREBOARD_INTERVAL_DAYS * 24
LAST_RUN_KEY = "scoreboard_last_run"


def _fmt_hours(seconds: float) -> str:
    hours = seconds / 3600
    return f"{hours:.1f} h" if hours >= 1 else f"{int(seconds // 60)} min"


async def due() -> bool:
    last = await db.get_meta(LAST_RUN_KEY)
    if last is None:
        return True
    last_dt = dt.datetime.fromisoformat(last)
    return dt.datetime.now(dt.UTC) - last_dt >= dt.timedelta(
        days=SCOREBOARD_INTERVAL_DAYS
    )


async def _gather(guild: discord.Guild) -> dict:
    members = await db.all_members()
    ranked: list[tuple[discord.Member, int, int]] = []
    total_seconds = 0
    total_plays = 0
    for entry in members:
        member = guild.get_member(entry["discord_id"])
        if member is None:
            continue
        seconds, plays = await jellystat.user_window_seconds(
            entry["jf_user_id"], _WINDOW_HOURS
        )
        total_seconds += seconds
        total_plays += plays
        if seconds > 0:
            ranked.append((member, seconds, plays))
    ranked.sort(key=lambda x: x[1], reverse=True)

    movie = await jellystat.most_viewed(SCOREBOARD_INTERVAL_DAYS, "Movie")
    return {
        "ranked": ranked[:3],
        "total_seconds": total_seconds,
        "total_plays": total_plays,
        "movie": movie[0].get("Name") if movie else None,
    }


async def _build_card(data: dict) -> discord.File:
    entries = []
    for member, seconds, _plays in data["ranked"]:
        avatar = await cards.fetch_avatar(member.display_avatar.replace(size=256).url)
        entries.append(
            {"name": member.display_name, "avatar": avatar, "seconds": seconds}
        )
    buf = cards.render_scoreboard(
        entries,
        period_days=SCOREBOARD_INTERVAL_DAYS,
        movie=data["movie"],
        total_seconds=data["total_seconds"],
        total_plays=data["total_plays"],
    )
    return discord.File(buf, filename="classement.png")


def _caption(data: dict) -> str:
    if not data["ranked"]:
        return "**Classement de la quinzaine** — personne n'a rien regardé cette fois."
    medals = ["🥇", "🥈", "🥉"]
    lines = ["**Classement de la quinzaine**"]
    for i, (member, seconds, _plays) in enumerate(data["ranked"]):
        lines.append(f"{medals[i]} {member.mention} · {_fmt_hours(seconds)}")
    return "\n".join(lines)


async def _transfer_headliner(
    guild: discord.Guild, winner: discord.Member | None
) -> None:
    role = discord.utils.get(guild.roles, name=HEADLINER_ROLE_NAME)
    if role is None:
        try:
            role = await guild.create_role(
                name=HEADLINER_ROLE_NAME,
                colour=discord.Colour.gold(),
                reason="Bot Blackbox — tête d'affiche",
            )
        except (discord.Forbidden, discord.HTTPException) as exc:
            logger.warning("création du rôle Tête d'affiche impossible : %s", exc)
            return
    for holder in list(role.members):
        if winner is None or holder.id != winner.id:
            await holder.remove_roles(role, reason="Fin de quinzaine")
    if winner is not None and role not in winner.roles:
        await winner.add_roles(role, reason="Tête d'affiche de la quinzaine")


async def post(guild: discord.Guild) -> bool:
    channel = guild.get_channel(SCOREBOARD_CHANNEL_ID)
    if channel is None:
        logger.warning("salon #classement (%s) introuvable", SCOREBOARD_CHANNEL_ID)
        return False

    data = await _gather(guild)
    await channel.send(content=_caption(data), file=await _build_card(data))

    winner = data["ranked"][0][0] if data["ranked"] else None
    await _transfer_headliner(guild, winner)
    await db.set_meta(LAST_RUN_KEY, dt.datetime.now(dt.UTC).isoformat())
    logger.info("classement posté dans #classement")
    return True
