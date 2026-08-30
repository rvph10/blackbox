"""Alerte admin sur le webhook Discord (même canal que gluetun/backup)."""

import logging

import aiohttp

from config import ADMIN_ALERT_WEBHOOK_URL

logger = logging.getLogger("blackbox-bot.notify")


async def admin_alert(message: str) -> None:
    if not ADMIN_ALERT_WEBHOOK_URL:
        logger.warning("ADMIN_ALERT_WEBHOOK_URL absent — alerte perdue : %s", message)
        return
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            await s.post(ADMIN_ALERT_WEBHOOK_URL, json={"content": message})
    except aiohttp.ClientError as exc:
        logger.warning("échec envoi alerte admin : %s", exc)
