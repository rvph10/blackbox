"""Tests unitaires — logique pure, HTTP mocké, base SQLite temporaire.

Le bot ne se connecte jamais à Discord ici : `main.py` ne lance `run()` que
sous `if __name__ == "__main__"`, et `config.py` lit l'env avec des valeurs
par défaut.
"""

import aiohttp
import pytest
from aioresponses import aioresponses

import cards
import config
import db
import jellyfin
import now_playing
import provisioning
import seerr_hook


# --- config : paliers -----------------------------------------------------
def test_tier_for_seconds():
    assert config.tier_for_seconds(0) == "Figurant"
    assert config.tier_for_seconds(14 * 3600) == "Figurant"
    assert config.tier_for_seconds(15 * 3600) == "Second rôle"
    assert config.tier_for_seconds(60 * 3600) == "Premier rôle"
    assert config.tier_for_seconds(500 * 3600) == "Réalisateur"


def test_next_tier():
    name, remaining = config.next_tier(10 * 3600)
    assert name == "Second rôle"
    assert remaining == 5 * 3600
    assert config.next_tier(200 * 3600) is None


# --- provisioning : helpers -------------------------------------------------
def test_clean_username():
    assert provisioning.clean_username("Jean-Michel_92") == "jeanmichel92"
    assert provisioning.clean_username("Éléonore") == "lonore"
    assert provisioning.clean_username("???") == "membre"


def test_generate_password_longueur_et_charset():
    pw = provisioning.generate_password()
    assert len(pw) == 20
    assert pw.isalnum()
    assert provisioning.generate_password() != provisioning.generate_password()


def test_welcome_lines_pick():
    import welcome_lines

    assert welcome_lines.LINES
    line = welcome_lines.pick("<@123>")
    assert "<@123>" in line
    assert "{mention}" not in line


# --- jellyfin : rendu + HTTP mocké --------------------------------------
def test_describe_session_film():
    s = {"UserName": "Alice", "NowPlayingItem": {"Name": "Blade Runner"}}
    assert jellyfin.describe_session(s) == "Alice regarde Blade Runner"


def test_describe_session_serie():
    s = {
        "UserName": "Alice",
        "NowPlayingItem": {"Name": "Pilot", "SeriesName": "Severance"},
    }
    assert jellyfin.describe_session(s) == "Alice regarde Severance — Pilot"


def test_describe_session_defauts():
    assert jellyfin.describe_session({}) == "Quelqu'un regarde un contenu"


@pytest.mark.asyncio
async def test_is_online_vrai():
    with aioresponses() as m:
        m.get(f"{jellyfin.JELLYFIN_URL}/System/Info/Public", status=200)
        assert await jellyfin.is_online() is True


@pytest.mark.asyncio
async def test_is_online_injoignable():
    with aioresponses() as m:
        m.get(
            f"{jellyfin.JELLYFIN_URL}/System/Info/Public",
            exception=aiohttp.ClientError(),
        )
        assert await jellyfin.is_online() is False


@pytest.mark.asyncio
async def test_active_sessions_filtre_inactifs():
    payload = [
        {"UserName": "Alice", "NowPlayingItem": {"Name": "X"}},
        {"UserName": "Bob"},
    ]
    with aioresponses() as m:
        m.get(f"{jellyfin.JELLYFIN_URL}/Sessions", status=200, payload=payload)
        sessions = await jellyfin.active_sessions()
    assert sessions is not None
    assert [s["UserName"] for s in sessions] == ["Alice"]


@pytest.mark.asyncio
async def test_active_sessions_erreur_http():
    with aioresponses() as m:
        m.get(f"{jellyfin.JELLYFIN_URL}/Sessions", status=401)
        assert await jellyfin.active_sessions() is None


@pytest.mark.asyncio
async def test_delete_user_ok_et_erreur():
    with aioresponses() as m:
        m.delete(f"{jellyfin.JELLYFIN_URL}/Users/abc", status=204)
        await jellyfin.delete_user("abc")
    with aioresponses() as m:
        m.delete(f"{jellyfin.JELLYFIN_URL}/Users/abc", status=404)
        with pytest.raises(jellyfin.JellyfinError):
            await jellyfin.delete_user("abc")


@pytest.mark.asyncio
async def test_resolve_entry_par_nom_ou_id_discord(tmp_path, monkeypatch):
    import bot_commands

    monkeypatch.setattr(db, "BOT_DB_PATH", str(tmp_path / "t.db"))
    await db.init()
    await db.add_member(688703615770296331, "jf-1", "kong", display_name="rvph")

    assert (await bot_commands._resolve_entry("kong"))["jf_user_id"] == "jf-1"
    assert (await bot_commands._resolve_entry("KONG"))["jf_user_id"] == "jf-1"
    assert (await bot_commands._resolve_entry("688703615770296331"))[
        "jf_username"
    ] == "kong"
    assert await bot_commands._resolve_entry("inconnu") is None


def test_account_rows():
    import bot_commands

    members = [
        {"jf_user_id": "a", "jf_username": "zoe", "discord_id": 1},
        {"jf_user_id": "b", "jf_username": "amy", "discord_id": 2},
        {"jf_user_id": "gone", "jf_username": "bob", "discord_id": 3},
    ]
    jf_users = [
        {"Id": "a", "Policy": {"IsDisabled": False}},
        {"Id": "b", "Policy": {"IsDisabled": True}},
    ]
    lines, counts = bot_commands._account_rows(members, jf_users)
    assert lines[0].startswith("`amy`") and "désactivé" in lines[0]  # trié par nom JF
    assert lines[1].startswith("`bob`") and "introuvable" in lines[1]
    assert lines[2].startswith("`zoe`") and "actif" in lines[2]
    assert counts == {"actif": 1, "désactivé": 1, "orphelin": 1}


@pytest.mark.asyncio
async def test_delete_member(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "BOT_DB_PATH", str(tmp_path / "t.db"))
    await db.init()
    await db.add_member(1, "jf-1", "alice")
    await db.delete_member(1)
    assert await db.get_member(1) is None


# --- now_playing : panneau live -------------------------------------------
def test_progress_bar():
    assert now_playing._progress_bar(0, 0) == ""
    assert now_playing._progress_bar(0, 100).endswith("0%")
    assert now_playing._progress_bar(50, 100).endswith("50%")
    assert now_playing._progress_bar(200, 100).endswith("100%")  # clampé


def test_episode_label():
    assert now_playing._episode_label({"Name": "Dune", "ProductionYear": 2021}) == (
        "Dune (2021)"
    )
    ep = {
        "Name": "The Pod",
        "SeriesName": "Severance",
        "ParentIndexNumber": 2,
        "IndexNumber": 4,
    }
    assert now_playing._episode_label(ep) == "Severance — S02E04 · The Pod"


def test_build_embed_vide():
    embed = now_playing.build_embed([])
    assert "Personne" in embed.description


def test_build_embed_actif_utilise_le_nom_discord():
    sessions = [
        {
            "UserId": "jf-alice",
            "UserName": "alice_jf",
            "PlayMethod": "DirectPlay",
            "NowPlayingItem": {"Name": "Dune", "RunTimeTicks": 10},
            "PlayState": {"PositionTicks": 5},
        },
        {
            "UserId": "jf-bob",
            "UserName": "bob_jf",
            "PlayMethod": "Transcode",
            "NowPlayingItem": {"Name": "Heat"},
            "PlayState": {},
        },
    ]
    embed = now_playing.build_embed(sessions, {"jf-alice": "Alice"})
    assert len(embed.fields) == 2
    assert embed.fields[0].name.startswith("Alice — Dune")  # nom Discord
    assert embed.fields[1].name.startswith("bob_jf — Heat")  # repli Jellyfin
    assert "transcodage" in embed.fields[1].value
    assert "Mbit" not in (embed.footer.text or "")


def test_presence_text():
    assert now_playing.presence_text(None) == "personne ne regarde"
    assert now_playing.presence_text([{"NowPlayingItem": {"Name": "Dune"}}]) == (
        "1 flux · Dune"
    )


# --- cards : rendu PNG (smoke) -------------------------------------------
def _is_png(buf) -> bool:
    return buf.getvalue()[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_welcome_png():
    assert _is_png(cards.render_welcome("s3g3n", None))


def test_render_scoreboard_png_complet_et_partiel():
    full = cards.render_scoreboard(
        [
            {"name": "rvph", "avatar": None, "seconds": 14 * 3600},
            {"name": "Bob", "avatar": None, "seconds": 9 * 3600},
            {"name": "Cléo", "avatar": None, "seconds": 4 * 3600},
        ],
        period_days=15,
        movie="Dune",
        total_seconds=40 * 3600,
        total_plays=20,
    )
    assert _is_png(full)
    # moins de 3 personnes classées : ne doit pas planter
    partial = cards.render_scoreboard(
        [{"name": "rvph", "avatar": None, "seconds": 3600}],
        period_days=15,
        movie=None,
        total_seconds=3600,
        total_plays=1,
    )
    assert _is_png(partial)


# --- seerr_hook : webhook Jellyseerr ------------------------------------
def test_make_app_route():
    app = seerr_hook.make_app(object())
    paths = {r.resource.canonical for r in app.router.routes()}
    assert "/jellyseerr" in paths


@pytest.mark.asyncio
async def test_requester_label(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "BOT_DB_PATH", str(tmp_path / "t.db"))
    await db.init()
    await db.add_member(42, "jf-x", "bob")

    # ID Discord présent dans le profil Jellyseerr → priorité
    assert (
        await seerr_hook._requester_label({"requestedBy_discordId": "999"}) == "<@999>"
    )
    # sinon match par nom d'utilisateur Jellyfin
    assert await seerr_hook._requester_label({"requestedBy_username": "Bob"}) == "<@42>"
    # inconnu → nom brut
    assert await seerr_hook._requester_label({"requestedBy_username": "Zoe"}) == "Zoe"


@pytest.mark.asyncio
async def test_dedup(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "BOT_DB_PATH", str(tmp_path / "t.db"))
    await db.init()
    assert not await seerr_hook._already_announced("r1")
    await seerr_hook._remember("r1")
    assert await seerr_hook._already_announced("r1")


# --- db : aller-retour SQLite -------------------------------------------
@pytest.mark.asyncio
async def test_db_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "BOT_DB_PATH", str(tmp_path / "t.db"))
    await db.init()

    await db.add_member(1, "jf-1", "alice", display_name="Alice")
    entry = await db.get_member(1)
    assert entry["jf_username"] == "alice"
    assert (await db.get_by_jf_user_id("jf-1"))["discord_id"] == 1

    await db.set_tier(1, "Second rôle")
    assert (await db.get_member(1))["tier"] == "Second rôle"

    await db.append_note(1, "test")
    assert "test" in (await db.get_member(1))["note"]

    await db.set_meta("k", "v")
    assert await db.get_meta("k") == "v"

    # add_member est idempotent (upsert)
    await db.add_member(1, "jf-1b", "alice2")
    assert (await db.get_member(1))["jf_username"] == "alice2"
    assert len(await db.all_members()) == 1
