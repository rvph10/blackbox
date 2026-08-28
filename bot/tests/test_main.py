"""Tests unitaires du bot — logique pure et appels HTTP mockés.

Le bot ne se connecte jamais à Discord ici : `main.py` ne lance `client.run`
que sous `if __name__ == "__main__"`, et les variables d'environnement sont
lues de façon tolérante au niveau module.
"""

import aiohttp
import pytest
from aioresponses import aioresponses

import main


def _session(user="Alice", name="Blade Runner", series=None):
    item = {"Name": name}
    if series:
        item["SeriesName"] = series
    return {"UserName": user, "NowPlayingItem": item}


def test_format_session_film():
    assert main._format_session(_session()) == "Alice regarde Blade Runner"


def test_format_session_serie():
    line = main._format_session(_session(name="Pilot", series="Severance"))
    assert line == "Alice regarde Severance — Pilot"


def test_format_session_valeurs_par_defaut():
    line = main._format_session({"NowPlayingItem": {}})
    assert line == "Quelqu'un regarde un contenu"


@pytest.mark.asyncio
async def test_jellyfin_online_vrai():
    with aioresponses() as m:
        m.get(f"{main.JELLYFIN_URL}/System/Info/Public", status=200)
        assert await main._jellyfin_online() is True


@pytest.mark.asyncio
async def test_jellyfin_online_injoignable():
    with aioresponses() as m:
        m.get(
            f"{main.JELLYFIN_URL}/System/Info/Public",
            exception=aiohttp.ClientError(),
        )
        assert await main._jellyfin_online() is False


@pytest.mark.asyncio
async def test_active_sessions_filtre_les_sessions_inactives():
    payload = [_session(), {"UserName": "Bob"}]
    with aioresponses() as m:
        m.get(f"{main.JELLYFIN_URL}/Sessions", status=200, payload=payload)
        sessions = await main._active_sessions()
    assert sessions is not None
    assert len(sessions) == 1
    assert sessions[0]["UserName"] == "Alice"


@pytest.mark.asyncio
async def test_active_sessions_erreur_http():
    with aioresponses() as m:
        m.get(f"{main.JELLYFIN_URL}/Sessions", status=401)
        assert await main._active_sessions() is None
