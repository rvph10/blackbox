"""Bot Discord Blackbox — Layer 2 : commandes de statut en lecture seule.

Ne modifie jamais l'infra (pas de création de compte, pas d'action sur les
conteneurs) — voir docs/adr/008-discord-community.md pour le modèle en
couches. Deux commandes :
  /status  — Jellyfin en ligne ou hors ligne, rien de plus (volontairement
             simplifié, le dashboard reste l'outil de détail)
  /streams — liste des sessions de lecture en cours (utilisateur + titre)
"""

import logging
import os

import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
JELLYFIN_URL = os.environ.get("JELLYFIN_URL", "http://jellyfin:8096")
JELLYFIN_API_KEY = os.environ["JELLYFIN_API_KEY"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blackbox-bot")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    await tree.sync()
    logger.info("Connecté en tant que %s", client.user)


@tree.command(name="status", description="Jellyfin est-il en ligne ?")
async def status(interaction: discord.Interaction):
    online = await _jellyfin_online()
    message = "En ligne" if online else "Hors ligne"
    await interaction.response.send_message(message)


@tree.command(name="streams", description="Qui regarde quoi en ce moment")
async def streams(interaction: discord.Interaction):
    sessions = await _active_sessions()
    if sessions is None:
        await interaction.response.send_message(
            "Jellyfin est injoignable pour le moment."
        )
        return
    if not sessions:
        await interaction.response.send_message("Personne ne regarde rien en ce moment.")
        return

    lines = [_format_session(s) for s in sessions]
    await interaction.response.send_message("\n".join(lines))


async def _jellyfin_online() -> bool:
    url = f"{JELLYFIN_URL}/System/Info/Public"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
    except (aiohttp.ClientError, TimeoutError):
        return False


async def _active_sessions() -> list[dict] | None:
    url = f"{JELLYFIN_URL}/Sessions"
    headers = {"X-Emby-Token": JELLYFIN_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    return None
                sessions = await resp.json()
    except (aiohttp.ClientError, TimeoutError):
        return None

    return [s for s in sessions if s.get("NowPlayingItem")]


def _format_session(session: dict) -> str:
    user = session.get("UserName", "Quelqu'un")
    item = session["NowPlayingItem"]
    title = item.get("Name", "un contenu")
    series = item.get("SeriesName")
    label = f"{series} — {title}" if series else title
    return f"{user} regarde {label}"


client.run(DISCORD_BOT_TOKEN, log_handler=None)
