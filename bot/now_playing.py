"""Panneau « en direct » des lectures Jellyfin (ADR-022).

Un seul message-embed dans #salle-de-projection, édité en place toutes les
45 s. ID du message persisté en base pour survivre aux redémarrages.
"""

import datetime as dt
import logging

import discord

import db
import jellyfin
from config import DISCORD_GUILD_ID, NOW_PLAYING_CHANNEL_ID

logger = logging.getLogger("blackbox-bot.now_playing")

MESSAGE_ID_KEY = "now_playing_message_id"
_BAR_WIDTH = 12


def _progress_bar(position_ticks: int, runtime_ticks: int) -> str:
    if not runtime_ticks:
        return ""
    ratio = max(0.0, min(1.0, position_ticks / runtime_ticks))
    filled = round(ratio * _BAR_WIDTH)
    return f"{'█' * filled}{'░' * (_BAR_WIDTH - filled)} {ratio * 100:.0f}%"


def _episode_label(item: dict) -> str:
    name = item.get("Name", "un contenu")
    series = item.get("SeriesName")
    if not series:
        year = item.get("ProductionYear")
        return f"{name} ({year})" if year else name
    season = item.get("ParentIndexNumber")
    episode = item.get("IndexNumber")
    if season is not None and episode is not None:
        return f"{series} — S{season:02d}E{episode:02d} · {name}"
    return f"{series} — {name}"


def _play_mode(session: dict) -> str:
    method = session.get("PlayMethod", "")
    if method == "Transcode":
        return "transcodage"
    if method in ("DirectStream", "DirectPlay"):
        return "lecture directe"
    return method or ""


def build_embed(
    sessions: list[dict], names: dict[str, str] | None = None
) -> discord.Embed:
    """`names` : jf_user_id -> nom à afficher (pseudo Discord). Repli sur le
    nom d'utilisateur Jellyfin."""
    names = names or {}
    now = dt.datetime.now(dt.UTC)
    if not sessions:
        embed = discord.Embed(
            title="Salle de projection",
            description="Personne ne regarde en ce moment.",
            colour=0x99AAB5,
            timestamp=now,
        )
        embed.set_footer(text="Mis à jour")
        return embed

    embed = discord.Embed(title="Salle de projection", colour=0x57F287, timestamp=now)
    for session in sessions:
        item = session.get("NowPlayingItem", {})
        state = session.get("PlayState", {})
        paused = " · en pause" if state.get("IsPaused") else ""
        bar = _progress_bar(
            state.get("PositionTicks") or 0, item.get("RunTimeTicks") or 0
        )
        who = names.get(session.get("UserId", "")) or session.get(
            "UserName", "Quelqu’un"
        )
        mode = _play_mode(session)
        value = " · ".join(filter(None, [bar, mode])) + paused
        embed.add_field(
            name=f"{who} — {_episode_label(item)}",
            value=value or "​",
            inline=False,
        )
    embed.set_footer(text="Mis à jour")
    return embed


def presence_text(sessions: list[dict] | None) -> str:
    if not sessions:
        return "personne ne regarde"
    if len(sessions) == 1:
        return f"1 flux · {sessions[0].get('NowPlayingItem', {}).get('Name', '?')}"
    return f"{len(sessions)} flux en cours"


async def _discord_names(client: discord.Client) -> dict[str, str]:
    """jf_user_id -> nom affiché du membre Discord correspondant."""
    guild = client.get_guild(DISCORD_GUILD_ID) if DISCORD_GUILD_ID else None
    if guild is None:
        return {}
    out: dict[str, str] = {}
    for entry in await db.all_members():
        member = guild.get_member(entry["discord_id"])
        if member is not None:
            out[entry["jf_user_id"]] = member.display_name
    return out


async def _resolve_message(
    channel: discord.abc.Messageable,
) -> discord.Message | None:
    stored = await db.get_meta(MESSAGE_ID_KEY)
    if stored:
        try:
            return await channel.fetch_message(int(stored))
        except (discord.NotFound, discord.HTTPException):
            pass
    return None


async def update(client: discord.Client) -> None:
    channel = client.get_channel(NOW_PLAYING_CHANNEL_ID)
    if channel is None:
        logger.warning(
            "salon #salle-de-projection (%s) introuvable", NOW_PLAYING_CHANNEL_ID
        )
        return

    sessions = await jellyfin.active_sessions()
    embed = build_embed(sessions or [], await _discord_names(client))

    message = await _resolve_message(channel)
    try:
        if message is None:
            message = await channel.send(embed=embed)
            await db.set_meta(MESSAGE_ID_KEY, str(message.id))
            try:
                await message.pin()
            except discord.HTTPException:
                pass
        else:
            await message.edit(embed=embed)
    except discord.HTTPException as exc:
        logger.warning("échec mise à jour du panneau live : %s", exc)
        return

    try:
        await client.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name=presence_text(sessions)
            )
        )
    except discord.HTTPException:
        pass
