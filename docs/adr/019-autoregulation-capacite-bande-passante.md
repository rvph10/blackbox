# ADR 019 — Autorégulation capacité et bande passante

**Statut :** Accepté — en production depuis le 2026-08-29

## Contexte

La première ligne du brief : Jellyfin « autorégulé en capacité et bande
passante ». Deux ressources se saturent silencieusement sur cette infra :

1. **Le disque du NAS** (`/mnt/nas-media`, RAID1) — la suite *arr* télécharge
   en continu (Seerr auto-approuve), rien ne freine quand l'espace se
   raréfie. Un NAS plein = imports *arr* en échec, qBittorrent bloqué,
   Jellyfin qui n'écrit plus ses métadonnées.
2. **Le débit montant** — mesuré à ~20 Mbit/s aujourd'hui (Proximus VDSL,
   fibre prévue le 15/09). Le streaming sortant vers ~10 personnes **et** le
   seeding qBittorrent se partagent ce lien. Deux lectures 1080p en
   *direct play* suffisent à le saturer : buffering pour tout le monde.

Il manquait une boucle de rétroaction : observer ces deux ressources et
agir avant la saturation.

## Décision

### Observation : Jellystat

Conteneur [Jellystat](https://github.com/CyferShepard/Jellystat) +
PostgreSQL dédié. Se branche sur l'API Jellyfin (clé API), fournit
l'historique de lecture, les stats par utilisateur, les sessions
concurrentes et la bande passante. C'est la brique de visibilité (dashboard
via Tailscale, port `3000`, **non exposé** sur le tunnel public).

Écarté : Streamystats (plus léger, SQLite embarqué) — Jellystat est plus
mûr, mieux maintenu, et le Postgres séparé sert de base à d'éventuels
services futurs (le brief anticipait « Postgres pas encore nécessaire »).

### Action : watcher de seuil

Script `infra/scripts/capacity-watcher/check-capacity.sh` + timer systemd
(toutes les 2 min, même schéma que `gluetun-healthcheck` — voir ADR-009).
Aucun code de bot, aucune dépendance à un service tiers en plus.

À chaque passage il mesure :

- **disque** : `df` sur `MEDIA_MOUNT`, pourcentage utilisé ;
- **débit montant streaming** : somme des bitrates des sessions Jellyfin
  actives via `/Sessions` (`TranscodingInfo.Bitrate` si transcodage, sinon
  `NowPlayingItem.Bitrate`). On ne compte que le trafic Jellyfin, pas le
  débit interface (qui inclut le seeding, le backup, etc.).

Trois niveaux, avec hystérésis (on n'agit qu'au **changement** de niveau,
via un fichier d'état — pas d'alerte répétée) :

| Niveau | Condition (l'un ou l'autre) | Action |
|---|---|---|
| **OK** | disque < `DISK_WARN_PCT`, montant < `UPLOAD_WARN_MBPS` | désactive les limites alternatives qBittorrent si actives ; alerte « retour à la normale » |
| **WARN** | disque ≥ 85 % **ou** montant ≥ `UPLOAD_WARN_MBPS` (14) | alerte Discord admin uniquement |
| **CRIT** | disque ≥ 92 % **ou** montant ≥ `UPLOAD_CRIT_MBPS` (17) | active les **limites alternatives** qBittorrent (bride le seeding) + alerte admin + message dans le salon communautaire (webhook, Layer 1, cf. ADR-009) |

### Pourquoi les limites alternatives qBittorrent plutôt qu'une pause

qBittorrent a un mode « limites alternatives » (upload plafonné bas,
configuré une fois dans ses réglages). Le watcher fait juste
`toggleSpeedLimitsMode` via l'API Web. Non destructif, réversible
instantanément, ne touche pas aux torrents individuels ni aux imports *arr*
en cours. Le seeding continue, ralenti, et rend la bande au streaming.

Écarté : mettre les *arr* en pause (API par app, état à restaurer, risque
de laisser un import à moitié fait) ; couper qBittorrent (casse le kill
switch gluetun au redémarrage).

### Seuils

Valeurs **absolues dans le `.env`**, pas en dur :

- disque : `DISK_WARN_PCT=85`, `DISK_CRIT_PCT=92`
- montant : `UPLOAD_WARN_MBPS=14`, `UPLOAD_CRIT_MBPS=17` — soit ~70 % / ~85 %
  des 20 Mbit/s mesurés (3 speedtests le 2026-08-29 : 6,2 / 24,0 / 21,6 —
  le premier écarté, serveur saturé).

Après la fibre (15/09) : refaire `speedtest`, remonter les deux valeurs
`UPLOAD_*`, `systemctl restart capacity-watcher.timer`. Rien d'autre.

## Conséquences

- `infra/docker/prod/docker-compose.yml` : services `jellystat` +
  `jellystat-db`. `.env.example` : `JELLYSTAT_DB_PASSWORD`,
  `JELLYSTAT_JWT_SECRET`.
- `infra/scripts/capacity-watcher/` : script + `.service` + `.timer` +
  `.env.example`.
- Rôle Ansible `base` : ajout de `jq` (parsing de l'API Jellyfin dans le
  script). Rôle `deploy` : déploiement du script + contrôle du `.env`. Rôle
  `systemd_timers` : unité `capacity-watcher`.
- Runbook `docs/runbooks/setup-capacity-watcher.md`.
- Point ouvert du README « débit montant fibre réel » : reste ouvert
  (bloqué au 15/09), mais l'infra est prête à l'absorber sans changement de
  code.
- Jellystat n'est **pas** ajouté au périmètre de backup restic : base
  Postgres reconstructible depuis l'historique Jellyfin, aucune donnée
  unique.
