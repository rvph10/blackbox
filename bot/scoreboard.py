"""Classement bihebdomadaire posté dans #classement (ADR-021).

Toutes les 15 jours (ancré à la première exécution, état en base `meta`).
Top 3 pingé, film/série de la quinzaine, nouveaux membres, total serveur,
transfert du rôle « Tête d'affiche » au n°1.
"""

import datetime as dt
import logging

import discord

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


async def _member_top_title(jf_user_id: str) -> str | None:
    rows = await jellystat.last_played(jf_user_id)
    counts: dict[str, int] = {}
    for r in rows:
        name = r.get("SeriesName") or r.get("NowPlayingItemName") or r.get("Name")
        if name:
            counts[name] = counts.get(name, 0) + 1
    return max(counts, key=counts.get) if counts else None


async def build_embed(
    guild: discord.Guild,
) -> tuple[discord.Embed, discord.Member | None]:
    members = await db.all_members()

    ranked: list[tuple[dict, discord.Member, int, int]] = []
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
            ranked.append((entry, member, seconds, plays))

    ranked.sort(key=lambda x: x[2], reverse=True)

    embed = discord.Embed(
        title="Classement de la quinzaine",
        description=f"Les {SCOREBOARD_INTERVAL_DAYS} derniers jours sur Blackbox.",
        colour=0x5865F2,
    )

    if ranked:
        medals = ["1.", "2.", "3."]
        lines = []
        for i, (entry, member, seconds, _plays) in enumerate(ranked[:3]):
            title = await _member_top_title(entry["jf_user_id"])
            extra = f" — surtout *{title}*" if title else ""
            lines.append(f"{medals[i]} {member.mention} · {_fmt_hours(seconds)}{extra}")
        embed.add_field(name="Top 3", value="\n".join(lines), inline=False)
    else:
        embed.add_field(
            name="Top 3",
            value="Personne n'a rien regardé cette quinzaine.",
            inline=False,
        )

    movie = await jellystat.most_viewed(SCOREBOARD_INTERVAL_DAYS, "Movie")
    series = await jellystat.most_viewed(SCOREBOARD_INTERVAL_DAYS, "Series")
    highlights = []
    if movie:
        highlights.append(f"Film : **{movie[0].get('Name', '?')}**")
    if series:
        highlights.append(f"Série : **{series[0].get('Name', '?')}**")
    if highlights:
        embed.add_field(
            name="À l'affiche cette quinzaine",
            value="\n".join(highlights),
            inline=False,
        )

    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=SCOREBOARD_INTERVAL_DAYS)
    newcomers = [
        guild.get_member(e["discord_id"])
        for e in members
        if e.get("created_at") and dt.datetime.fromisoformat(e["created_at"]) >= cutoff
    ]
    newcomers = [m for m in newcomers if m]
    if newcomers:
        embed.add_field(
            name="Nouveaux membres",
            value=", ".join(m.mention for m in newcomers),
            inline=False,
        )

    embed.add_field(
        name="Total serveur",
        value=f"{_fmt_hours(total_seconds)} regardées · {total_plays} lectures",
        inline=False,
    )

    headliner = ranked[0][1] if ranked else None
    if headliner:
        embed.set_footer(
            text=f"Tête d'affiche de la quinzaine : {headliner.display_name}"
        )
    return embed, headliner


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
    embed, winner = await build_embed(guild)
    await channel.send(embed=embed)
    await _transfer_headliner(guild, winner)
    await db.set_meta(LAST_RUN_KEY, dt.datetime.now(dt.UTC).isoformat())
    logger.info("classement posté dans #classement")
    return True
