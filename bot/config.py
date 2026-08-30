"""Configuration centrale du bot — lecture tolérante des variables d'env.

Les valeurs sont lues au niveau module pour permettre l'import en test/lint
sans secrets. La présence réelle est vérifiée dans `main.require_env()` au
démarrage.
"""

import os

# --- Discord ---------------------------------------------------------------
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_GUILD_ID = int(os.environ.get("DISCORD_GUILD_ID", "0") or "0")

# --- Jellyfin ------------------------------------------------------------
JELLYFIN_URL = os.environ.get("JELLYFIN_URL", "http://jellyfin:8096")
JELLYFIN_API_KEY = os.environ.get("JELLYFIN_API_KEY", "")

# --- Jellystat ----------------------------------------------------------
JELLYSTAT_URL = os.environ.get("JELLYSTAT_URL", "http://jellystat:3000")
JELLYSTAT_API_KEY = os.environ.get("JELLYSTAT_API_KEY", "")

# --- Divers -----------------------------------------------------------------
ADMIN_ALERT_WEBHOOK_URL = os.environ.get("ADMIN_ALERT_WEBHOOK_URL", "")
PUBLIC_STREAM_URL = os.environ.get("PUBLIC_STREAM_URL", "https://stream.blackbox.homes")
PUBLIC_REQUESTS_URL = os.environ.get(
    "PUBLIC_REQUESTS_URL", "https://requests.blackbox.homes"
)
BOT_DB_PATH = os.environ.get("BOT_DB_PATH", "/data/bot.db")

# --- Gamification -------------------------------------------------------
# (nom du rôle, seuil en secondes de visionnage cumulé, tout l'historique)
TIERS: list[tuple[str, int]] = [
    ("Figurant", 0),
    ("Second rôle", 15 * 3600),
    ("Premier rôle", 60 * 3600),
    ("Réalisateur", 180 * 3600),
]
TIER_ROLE_NAMES = [name for name, _ in TIERS]
HEADLINER_ROLE_NAME = "Tête d'affiche"
ADMIN_ROLE_NAME = "SysAdmin"

# --- Classement --------------------------------------------------------
SCOREBOARD_CHANNEL_ID = int(
    os.environ.get("SCOREBOARD_CHANNEL_ID", "1543646643629461628") or "0"
)
SCOREBOARD_INTERVAL_DAYS = 15

# --- Panneau « en direct » (ADR-022) -----------------------------------
NOW_PLAYING_CHANNEL_ID = int(
    os.environ.get("NOW_PLAYING_CHANNEL_ID", "1543666526400422089") or "0"
)
NOW_PLAYING_REFRESH_SECONDS = 45

# --- Politique Jellyfin des nouveaux comptes -------------------------------
NEW_USER_POLICY = {
    "IsAdministrator": False,
    "IsDisabled": False,
    "EnableAllFolders": True,
    "EnabledFolders": [],
    "EnableRemoteAccess": True,
    "EnableContentDownloading": True,
    "EnableContentDeletion": False,
    "EnableMediaPlayback": True,
    "EnableAudioPlaybackTranscoding": True,
    "EnableVideoPlaybackTranscoding": True,
    "EnablePlaybackRemuxing": True,
    "EnableUserPreferenceAccess": True,
    "EnableAllDevices": True,
    "MaxActiveSessions": 3,
}


def tier_for_seconds(seconds: float) -> str:
    """Nom du palier atteint pour un temps de visionnage cumulé (secondes)."""
    current = TIERS[0][0]
    for name, threshold in TIERS:
        if seconds >= threshold:
            current = name
    return current


def next_tier(seconds: float) -> tuple[str, int] | None:
    """(nom, secondes restantes) du palier suivant, ou None si au sommet."""
    for name, threshold in TIERS:
        if seconds < threshold:
            return name, threshold - int(seconds)
    return None
