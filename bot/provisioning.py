"""Provisioning des comptes Jellyfin à l'arrivée d'un membre Discord.

Flux (ADR-021) :
  on_member_join → username dérivé du pseudo → mot de passe aléatoire →
  création Jellyfin + policy → mapping en base → MP au membre.
  Si le MP échoue → alerte admin avec les identifiants pour remise en main.
Seerr : rien, auto-import au premier login.
"""

import logging
import re
import secrets
import string

import discord

import db
import jellyfin
from config import PUBLIC_REQUESTS_URL, PUBLIC_STREAM_URL
from notify import admin_alert

logger = logging.getLogger("blackbox-bot.provisioning")

_PW_ALPHABET = string.ascii_letters + string.digits


def clean_username(raw: str) -> str:
    """Pseudo Discord → identifiant Jellyfin : minuscules, [a-z0-9] uniquement."""
    cleaned = re.sub(r"[^a-z0-9]", "", raw.casefold())
    return cleaned or "membre"


def generate_password(length: int = 20) -> str:
    return "".join(secrets.choice(_PW_ALPHABET) for _ in range(length))


async def _unique_username(base: str) -> str:
    candidate = base
    suffix = 2
    while await jellyfin.username_taken(candidate):
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


def welcome_message(username: str, password: str) -> str:
    return (
        f"Bienvenue sur **Blackbox** !\n\n"
        f"Ton compte est prêt. Garde ce message, le mot de passe n'est affiché "
        f"qu'une fois (tu pourras le changer dans ton profil Jellyfin).\n\n"
        f"**Identifiant :** `{username}`\n"
        f"**Mot de passe :** `{password}`\n\n"
        f"**Regarder** — {PUBLIC_STREAM_URL}\n"
        f"Apps : Jellyfin (officielle, Android/iOS/TV), Findroid (Android), "
        f"Streamyfin, ou Infuse (Apple).\n\n"
        f"**Demander un film ou une série** — {PUBLIC_REQUESTS_URL}\n"
        f"Connecte-toi avec les mêmes identifiants (le compte se crée tout seul "
        f"à la première connexion).\n\n"
        f"Un souci ? Le salon `#bugs-et-problèmes` sur le Discord."
    )


async def provision_member(
    member: discord.abc.User, *, manual_by: str | None = None
) -> dict:
    """Crée le compte Jellyfin d'un membre et tente le MP. Retourne un résumé.

    Idempotent : si un mapping existe déjà, ne recrée rien.
    """
    existing = await db.get_member(member.id)
    if existing:
        await admin_alert(
            f"[INFO] {member.mention} a déjà un compte Jellyfin "
            f"(`{existing['jf_username']}`), rien de créé."
        )
        return {"status": "already", "jf_username": existing["jf_username"]}

    username = await _unique_username(clean_username(member.name))
    password = generate_password()

    try:
        user = await jellyfin.create_user(username, password)
    except jellyfin.JellyfinError as exc:
        logger.exception("échec création compte pour %s", member)
        await admin_alert(
            f"[ALERTE] Création du compte Jellyfin de {member.mention} échouée : {exc}"
        )
        return {"status": "error", "error": str(exc)}

    display = getattr(member, "display_name", member.name)
    note = "créé à l'arrivée" if not manual_by else f"créé manuellement par {manual_by}"
    await db.add_member(
        member.id, user["Id"], username, display_name=display, note=note
    )

    dm_ok = await _try_dm(member, welcome_message(username, password))
    if dm_ok:
        await admin_alert(
            f"[OK] Compte Jellyfin `{username}` créé pour {member.mention}, "
            f"identifiants envoyés en MP."
        )
        return {"status": "ok", "jf_username": username, "dm": True}

    await admin_alert(
        f"[ALERTE] Compte Jellyfin `{username}` créé pour {member.mention} mais le MP "
        f"a échoué (MP fermés). À transmettre en main propre :\n"
        f"`{username}` / `{password}`"
    )
    return {"status": "ok", "jf_username": username, "dm": False, "password": password}


async def _try_dm(member: discord.abc.User, content: str) -> bool:
    try:
        await member.send(content)
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False
