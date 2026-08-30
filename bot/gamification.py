"""Attribution des rôles de palier selon le temps de visionnage cumulé.

Recalcul quotidien (ADR-021) : lecture de Jellystat (`getAllUserActivity`,
tout l'historique), calcul du palier, synchro des rôles Discord, `tier`
mis à jour en base.
"""

import logging

import discord

import db
import jellystat
from config import TIER_ROLE_NAMES, tier_for_seconds

logger = logging.getLogger("blackbox-bot.gamification")


async def ensure_tier_roles(guild: discord.Guild) -> dict[str, discord.Role]:
    """Crée les rôles de palier manquants, juste sous le rôle du bot."""
    roles: dict[str, discord.Role] = {}
    me = guild.me
    for name in TIER_ROLE_NAMES:
        role = discord.utils.get(guild.roles, name=name)
        if role is None:
            role = await guild.create_role(
                name=name, reason="Bot Blackbox — palier de visionnage"
            )
            logger.info("rôle de palier créé : %s", name)
        roles[name] = role
    # Placer tous les paliers juste sous le rôle du bot (best effort).
    try:
        target = max(1, me.top_role.position - 1)
        await guild.edit_role_positions({r: target for r in roles.values()})
    except (discord.Forbidden, discord.HTTPException) as exc:
        logger.warning("impossible de repositionner les rôles de palier : %s", exc)
    return roles


async def sync_member_tier(
    member: discord.Member,
    seconds: float,
    tier_roles: dict[str, discord.Role],
) -> str:
    """Aligne les rôles de `member` sur le palier correspondant à `seconds`."""
    target_name = tier_for_seconds(seconds)
    target_role = tier_roles[target_name]

    to_remove = [
        r for r in member.roles if r.name in TIER_ROLE_NAMES and r.id != target_role.id
    ]
    if to_remove:
        await member.remove_roles(*to_remove, reason="Palier de visionnage")
    if target_role not in member.roles:
        await member.add_roles(target_role, reason="Palier de visionnage")

    await db.set_tier(member.id, target_name)
    return target_name


async def recompute_all(guild: discord.Guild) -> int:
    """Recalcule les paliers de tous les membres mappés. Retourne le nb traité."""
    tier_roles = await ensure_tier_roles(guild)
    activity = {
        row["UserId"]: float(row.get("TotalWatchTime") or 0)
        for row in await jellystat.all_user_activity()
    }

    handled = 0
    for entry in await db.all_members():
        member = guild.get_member(entry["discord_id"])
        if member is None:
            continue
        seconds = activity.get(entry["jf_user_id"], 0.0)
        try:
            await sync_member_tier(member, seconds, tier_roles)
            handled += 1
        except (discord.Forbidden, discord.HTTPException) as exc:
            logger.warning("palier non appliqué pour %s : %s", member, exc)
    logger.info("paliers recalculés pour %d membre(s)", handled)
    return handled
