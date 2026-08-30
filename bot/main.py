"""Bot Discord Blackbox — Layer 3.

Provisioning de comptes Jellyfin à l'arrivée, gamification par temps de
visionnage, classement bihebdomadaire. Voir docs/adr/021-bot-layer3.md.

Toujours aucun accès à Gluetun, aux conteneurs, au NAS ou aux backups.
"""

import datetime as dt
import logging
import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

import bot_commands
import db
import gamification
import now_playing
import provisioning
import scoreboard
from config import DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, NOW_PLAYING_REFRESH_SECONDS
from notify import admin_alert

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blackbox-bot")

_TZ = dt.timezone(dt.timedelta(hours=1))  # Europe/Brussels (approx., pas de DST)
_TIER_RECOMPUTE_AT = dt.time(hour=5, minute=0, tzinfo=_TZ)
_SCOREBOARD_CHECK_AT = dt.time(hour=19, minute=0, tzinfo=_TZ)

REQUIRED_ENV = (
    "DISCORD_BOT_TOKEN",
    "JELLYFIN_API_KEY",
    "JELLYSTAT_API_KEY",
    "ADMIN_ALERT_WEBHOOK_URL",
)


class BlackboxBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        await db.init()
        bot_commands.register(self.tree)
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=DISCORD_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        self.daily_tier_recompute.start()
        self.scoreboard_check.start()
        self.now_playing_panel.start()

    async def on_ready(self) -> None:
        logger.info("Connecté en tant que %s", self.user)
        await admin_alert(f"[OK] Bot Blackbox démarré (`{self.user}`).")

        guild = self._guild()
        if guild is None:
            return
        # Rôles de palier créés dès le démarrage (ADR-021).
        try:
            await gamification.ensure_tier_roles(guild)
        except discord.DiscordException:
            logger.exception("création des rôles de palier au démarrage")
        # Ne pas poster un classement vide juste après le tout premier
        # démarrage : on ancre le cycle à maintenant.
        if await db.get_meta(scoreboard.LAST_RUN_KEY) is None:
            await db.set_meta(
                scoreboard.LAST_RUN_KEY, dt.datetime.now(dt.UTC).isoformat()
            )

    async def on_member_join(self, member: discord.Member) -> None:
        logger.info("nouveau membre : %s", member)
        await provisioning.provision_member(member)

    async def on_member_remove(self, member: discord.Member) -> None:
        entry = await db.get_member(member.id)
        if entry is None:
            return
        await admin_alert(
            f"[INFO] {member} a quitté le Discord — compte Jellyfin "
            f"`{entry['jf_username']}` toujours actif. `/desactiver` si besoin."
        )

    def _guild(self) -> discord.Guild | None:
        if DISCORD_GUILD_ID:
            return self.get_guild(DISCORD_GUILD_ID)
        return self.guilds[0] if self.guilds else None

    @tasks.loop(time=_TIER_RECOMPUTE_AT)
    async def daily_tier_recompute(self) -> None:
        guild = self._guild()
        if guild is None:
            return
        try:
            await gamification.recompute_all(guild)
        except Exception:
            logger.exception("recompute des paliers a échoué")
            await admin_alert(
                "[ALERTE] Recalcul des paliers a échoué, voir les logs du bot."
            )

    @tasks.loop(time=_SCOREBOARD_CHECK_AT)
    async def scoreboard_check(self) -> None:
        guild = self._guild()
        if guild is None or not await scoreboard.due():
            return
        try:
            await scoreboard.post(guild)
        except Exception:
            logger.exception("post du classement a échoué")
            await admin_alert(
                "[ALERTE] Post du classement a échoué, voir les logs du bot."
            )

    @tasks.loop(seconds=NOW_PLAYING_REFRESH_SECONDS)
    async def now_playing_panel(self) -> None:
        try:
            await now_playing.update(self)
        except Exception:
            logger.exception("mise à jour du panneau live a échoué")

    @daily_tier_recompute.before_loop
    @scoreboard_check.before_loop
    @now_playing_panel.before_loop
    async def _wait_ready(self) -> None:
        await self.wait_until_ready()


def require_env() -> None:
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise SystemExit(f"Variables d'environnement manquantes : {', '.join(missing)}")


if __name__ == "__main__":
    require_env()
    BlackboxBot().run(DISCORD_BOT_TOKEN, log_handler=None)
