"""Slash commands du bot.

Publiques : /status /streams /moncompte /messtats /roulette
Admin (rôle SysAdmin) : /creer-compte /lier /desactiver
"""

import logging

import discord
from discord import app_commands

import db
import jellyfin
import jellystat
import provisioning
from config import ADMIN_ROLE_NAME, next_tier, tier_for_seconds
from notify import admin_alert

logger = logging.getLogger("blackbox-bot.commands")


def _is_admin(interaction: discord.Interaction) -> bool:
    user = interaction.user
    if isinstance(user, discord.Member):
        if user.guild_permissions.administrator:
            return True
        return any(r.name == ADMIN_ROLE_NAME for r in user.roles)
    return False


admin_only = app_commands.check(lambda i: _is_admin(i))


def register(tree: app_commands.CommandTree) -> None:
    @tree.command(name="status", description="Jellyfin est-il en ligne ?")
    async def status(interaction: discord.Interaction):
        online = await jellyfin.is_online()
        await interaction.response.send_message("En ligne" if online else "Hors ligne")

    @tree.command(name="streams", description="Qui regarde quoi en ce moment")
    async def streams(interaction: discord.Interaction):
        sessions = await jellyfin.active_sessions()
        if sessions is None:
            await interaction.response.send_message(
                "Jellyfin est injoignable pour le moment."
            )
            return
        if not sessions:
            await interaction.response.send_message(
                "Personne ne regarde rien en ce moment."
            )
            return
        await interaction.response.send_message(
            "\n".join(jellyfin.describe_session(s) for s in sessions)
        )

    @tree.command(
        name="moncompte",
        description="Rappel de ton identifiant, ou réinitialise ton mot de passe",
    )
    @app_commands.describe(
        reinitialiser="Génère un nouveau mot de passe et te l'envoie en MP"
    )
    async def moncompte(interaction: discord.Interaction, reinitialiser: bool = False):
        entry = await db.get_member(interaction.user.id)
        if entry is None:
            await interaction.response.send_message(
                "Je ne trouve pas de compte lié au tien. Préviens un admin.",
                ephemeral=True,
            )
            return
        if not reinitialiser:
            await interaction.response.send_message(
                f"Ton identifiant Jellyfin : `{entry['jf_username']}`.\n"
                f"Pour un nouveau mot de passe : `/moncompte reinitialiser:True`.",
                ephemeral=True,
            )
            return

        new_pw = provisioning.generate_password()
        try:
            await jellyfin.reset_password(entry["jf_user_id"], new_pw)
        except jellyfin.JellyfinError as exc:
            logger.exception("reset mdp échoué pour %s", interaction.user)
            await interaction.response.send_message(
                "Échec de la réinitialisation, un admin a été prévenu.",
                ephemeral=True,
            )
            await admin_alert(f"❌ Reset mdp de {interaction.user.mention} : {exc}")
            return
        try:
            await interaction.user.send(
                f"Nouveau mot de passe Jellyfin (`{entry['jf_username']}`) : "
                f"`{new_pw}`"
            )
            await interaction.response.send_message(
                "Nouveau mot de passe envoyé en MP.", ephemeral=True
            )
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message(
                "Tes MP sont fermés — ouvre-les et relance la commande.",
                ephemeral=True,
            )

    @tree.command(name="messtats", description="Ton temps de visionnage et ton palier")
    async def messtats(interaction: discord.Interaction):
        entry = await db.get_member(interaction.user.id)
        if entry is None:
            await interaction.response.send_message(
                "Aucun compte lié au tien. Préviens un admin.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)

        activity = {
            r["UserId"]: float(r.get("TotalWatchTime") or 0)
            for r in await jellystat.all_user_activity()
        }
        seconds = activity.get(entry["jf_user_id"], 0.0)
        ranking = sorted(activity.values(), reverse=True)
        rank = ranking.index(seconds) + 1 if seconds in ranking else len(ranking) + 1
        genre = await jellystat.top_genre(entry["jf_user_id"])

        lines = [
            f"**Temps total :** {seconds / 3600:.1f} h",
            f"**Palier :** {tier_for_seconds(seconds)}",
        ]
        nxt = next_tier(seconds)
        if nxt:
            lines.append(f"**Prochain palier :** {nxt[0]} dans {nxt[1] / 3600:.1f} h")
        if genre:
            lines.append(f"**Genre le plus regardé :** {genre}")
        lines.append(f"**Rang :** {rank} / {len(ranking)}")
        await interaction.followup.send("\n".join(lines), ephemeral=True)

    @tree.command(
        name="roulette", description="Un film au hasard que tu n'as pas encore vu"
    )
    async def roulette(interaction: discord.Interaction):
        entry = await db.get_member(interaction.user.id)
        if entry is None:
            await interaction.response.send_message(
                "Aucun compte lié au tien. Préviens un admin.", ephemeral=True
            )
            return
        await interaction.response.defer()
        try:
            movie = await jellyfin.random_unplayed_movie(entry["jf_user_id"])
        except Exception:
            logger.exception("roulette : échec Jellyfin")
            await interaction.followup.send("Jellyfin n'a pas répondu, réessaie.")
            return
        if movie is None:
            await interaction.followup.send(
                "Tu as déjà tout vu, ou la bibliothèque est vide. 🍿"
            )
            return
        year = movie.get("ProductionYear")
        title = movie["Name"] + (f" ({year})" if year else "")
        overview = (movie.get("Overview") or "").strip()
        if len(overview) > 300:
            overview = overview[:297] + "…"
        embed = discord.Embed(title=f"🎲 {title}", description=overview or None)
        await interaction.followup.send(embed=embed)

    # --- admin ---------------------------------------------------------------
    @tree.command(name="creer-compte", description="[admin] Provisionne un membre")
    @admin_only
    async def creer_compte(interaction: discord.Interaction, membre: discord.Member):
        await interaction.response.defer(ephemeral=True)
        result = await provisioning.provision_member(
            membre, manual_by=str(interaction.user)
        )
        await interaction.followup.send(
            f"Résultat : `{result['status']}`", ephemeral=True
        )

    @tree.command(
        name="lier", description="[admin] Lie un membre à un compte Jellyfin existant"
    )
    @admin_only
    async def lier(
        interaction: discord.Interaction,
        membre: discord.Member,
        utilisateur_jellyfin: str,
    ):
        await interaction.response.defer(ephemeral=True)
        users = await jellyfin.list_users()
        match = next(
            (
                u
                for u in users
                if u["Name"].casefold() == utilisateur_jellyfin.casefold()
            ),
            None,
        )
        if match is None:
            await interaction.followup.send(
                f"Aucun utilisateur Jellyfin `{utilisateur_jellyfin}`.", ephemeral=True
            )
            return
        await db.add_member(
            membre.id,
            match["Id"],
            match["Name"],
            display_name=membre.display_name,
            note=f"lié manuellement par {interaction.user}",
        )
        await interaction.followup.send(
            f"{membre.mention} ↔ `{match['Name']}` lié.", ephemeral=True
        )

    @tree.command(
        name="desactiver",
        description="[admin] Désactive le compte Jellyfin d'un membre",
    )
    @admin_only
    async def desactiver(interaction: discord.Interaction, membre: discord.Member):
        entry = await db.get_member(membre.id)
        if entry is None:
            await interaction.response.send_message(
                "Ce membre n'a pas de compte lié.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        try:
            await jellyfin.set_disabled(entry["jf_user_id"], True)
        except jellyfin.JellyfinError as exc:
            await interaction.followup.send(f"Échec : {exc}", ephemeral=True)
            return
        await db.append_note(membre.id, f"désactivé par {interaction.user}")
        await interaction.followup.send(
            f"Compte `{entry['jf_username']}` désactivé.", ephemeral=True
        )
        await admin_alert(
            f"🔒 Compte `{entry['jf_username']}` ({membre.mention}) désactivé "
            f"par {interaction.user.mention}."
        )

    for cmd in (creer_compte, lier, desactiver):
        cmd.on_error = _admin_error


async def _admin_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.CheckFailure):
        msg = f"Réservé au rôle {ADMIN_ROLE_NAME}."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    else:
        logger.exception("erreur commande admin", exc_info=error)
