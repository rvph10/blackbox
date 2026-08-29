# Blackbox — homelab streaming communautaire

Jellyfin partagé avec une dizaine de personnes (famille/amis), autorégulé en
capacité et bande passante, piloté via un bot Discord. Double objectif : usage
réel pour la communauté, et vitrine technique pour mon portfolio.

- Brief complet : [docs/homelab_projet.md](docs/homelab_projet.md)
- Audit externe (risques, priorités, scoring) : [docs/audit_projet.md](docs/audit_projet.md)

Woluwe-Saint-Lambert, Bruxelles. Fibre prévue le 15 septembre 2026.
Domaine : `blackbox.homes` (enregistré chez Porkbun, DNS géré par Cloudflare) —
exposition publique active via Cloudflare Tunnel.

## Où on en est

Phase 0 : valider les inconnues bloquantes avant de commencer à déployer quoi
que ce soit (voir §12 du brief et §17 de l'audit).

- [x] Squelette du repo
- [x] OS du NucBox tranché — Ubuntu Server LTS + HWE ([ADR-002](docs/adr/002-os-nucbox.md))
- [x] OS installé sur le NucBox
- [x] Décision extinction programmée — abandonnée, NucBox allumé 24/7, WoL abandonné ([ADR-005](docs/adr/005-nucbox-always-on.md))
- [x] Test transcodage matériel VAAPI — validé sur Radeon 760M ([ADR-006](docs/adr/006-vaapi-validated.md))
- [ ] Débit montant fibre réel — bloqué jusqu'au 15/09
- [x] RAID tranché — RAID1 ([ADR-003](docs/adr/003-raid-nas.md))
- [x] RAID1 configuré sur le NAS — NAS branché (`dxp`), RAID1 sain,
  partage NFS `media` monté sur le NucBox et utilisé par Jellyfin
- [ ] Routeur/firewall dédié + VLAN — bloqué jusqu'à la fibre
- [x] Stack applicative — Jellyfin + suite *arr* déployés sur le NucBox
  (Prowlarr, Sonarr, Radarr, Bazarr, Seerr, qBittorrent derrière un VPN
  Mullvad/Gluetun), voir [ADR-007](docs/adr/007-arr-stack.md). Postgres pas
  encore nécessaire (pas de service qui le requiert pour l'instant)
- [x] Serveur Discord communautaire — structure native (rôles, Rules
  Screening, Welcome Screen, accueil, intégration Seerr/Jellyfin), voir
  [ADR-008](docs/adr/008-discord-community.md). Le bot Discord lui-même
  reste à construire
- [x] Backup restic — configs applicatives (pas la médiathèque), deux dépôts
  indépendants : NAS local + Backblaze B2 (backend natif restic ; Google
  Drive abandonné, quota OAuth partagé de rclone), quotidien via systemd
  timer. Voir [ADR-011](docs/adr/011-backup-restic-rclone.md) +
  [ADR-017](docs/adr/017-backup-b2.md). **Restauration à blanc validée le
  2026-08-29** sur les deux dépôts (intégrité `--read-data`, bases SQLite,
  secrets)
- [ ] Bot Discord — notifications passives (Layer 1) en place sans code de
  bot : contenu ajouté (Jellyfin → webhook Discord natif) et santé VPN
  (Gluetun → script + timer systemd), voir [ADR-009](docs/adr/009-notifications-layer1.md).
  Layer 2 (`/status`, `/streams`, lecture seule) déployé et vérifié, voir
  [ADR-010](docs/adr/010-bot-layer2.md). Layer 3 (création de compte,
  gamification) pas commencé
- [x] CI/CD du bot — GitHub Actions : lint (ruff) + tests (pytest) sur PR,
  build image `ghcr.io/rvph10/blackbox-bot` + push GHCR + déploiement via
  runner self-hosted sur le NucBox à chaque push `main`, voir
  [ADR-013](docs/adr/013-cicd-github-actions.md). Runner self-hosted à
  installer sur le NucBox ([setup-cicd.md](docs/runbooks/setup-cicd.md))
- [x] Exposition publique — Cloudflare Tunnel géré par Terraform (tunnel à
  config distante, ingress, DNS), conteneur `cloudflared` sur le NucBox.
  `stream.blackbox.homes` (Jellyfin) et `requests.blackbox.homes` (Seerr)
  en ligne, flux distant validé. Zone `blackbox.homes` passée sur Cloudflare
  (NS chez Porkbun). Voir [ADR-014](docs/adr/014-cloudflare-tunnel.md) et
  [setup-cloudflare-tunnel.md](docs/runbooks/setup-cloudflare-tunnel.md)
- [x] Accès admin distant — Tailscale sur le NucBox (rôle Ansible `tailscale`,
  Tailscale SSH activé). `ssh kong@nucbox` et les dashboards *arr* joignables
  depuis le tailnet sans port ouvert. Voir [ADR-015](docs/adr/015-tailscale.md)
  et [setup-tailscale.md](docs/runbooks/setup-tailscale.md)
- [x] Protection de l'exposition publique — CrowdSec derrière Traefik
  (reverse proxy interne, file provider, aucun port publié). Le trafic public
  passe par `cloudflared → traefik → jellyfin/seerr` avec middleware CrowdSec
  sur chaque route ; détection sur les logs Traefik + Jellyfin, blocklist
  communautaire. Accès LAN/Tailscale inchangé (direct). Voir
  [ADR-016](docs/adr/016-crowdsec-traefik.md) et
  [setup-crowdsec.md](docs/runbooks/setup-crowdsec.md)

## Architecture cible

```mermaid
flowchart TD
    Internet((Internet))
    ONT[ONT fibre Proximus]
    RTR[Routeur/Firewall dédié\nVLAN mgmt/services/users]
    SW[Switch managé 24/7]
    NUC[NucBox M6 — Ryzen 5 7640HS — allumé 24/7\nDocker: Traefik + CrowdSec, Jellyfin,\nProwlarr, Sonarr, Radarr, Bazarr, Seerr,\nqBittorrent+VPN, cloudflared, Bot Discord]
    NAS[Ugreen DXP2800 — dxp\nRAID1 — NFS]
    ESP8266[ESP8266 NodeMCU — watchdog externe\nESPHome, ping + alerte, Wi-Fi]

    Internet --> ONT --> RTR
    RTR -- Cloudflare Tunnel --> NUC
    RTR -- Tailscale, admin only --> NUC
    RTR --> SW
    SW --> NUC
    SW --> NAS
    ESP8266 -. Wi-Fi .-> NUC
    NUC <-- 2.5GbE SMB/NFS --> NAS
    ESP8266 -- ping + alerte Discord --> NUC
```

Rien de tout ça n'est encore physiquement en place, c'est la cible.

Le NucBox reste allumé en permanence (pas d'extinction/veille programmée,
uniquement des redémarrages ponctuels nécessaires, WoL abandonné) — voir
[ADR-005](docs/adr/005-nucbox-always-on.md). Le bot Discord tourne dessus.
Pas de RPi dans l'archi cible : le seul rôle externe restant (watchdog) est
couvert par un microcontrôleur ESP8266 (AZ-Delivery NodeMCU, déjà en stock)
en Wi-Fi.

## Structure du repo

```
blackbox/
├── .github/workflows/       # CI (lint/tests) + release (build GHCR + deploy)
├── docs/
│   ├── homelab_projet.md   # brief, source de vérité vision/archi
│   ├── audit_projet.md     # audit externe
│   ├── adr/                # décisions d'architecture
│   └── runbooks/           # procédures opérationnelles
├── infra/
│   ├── ansible/             # provisioning NucBox
│   ├── terraform/           # ressources Cloudflare (tunnel, DNS)
│   └── docker/
│       ├── prod/
│       ├── staging/
│       └── dev/
└── bot/                      # bot Discord Python (+ tests, config ruff/pytest)
```

## ADR

| # | Titre |
|---|---|
| [001](docs/adr/001-monorepo-structure.md) | Structure monorepo |
| [002](docs/adr/002-os-nucbox.md) | OS du NucBox M6 — Ubuntu Server LTS + HWE |
| [003](docs/adr/003-raid-nas.md) | RAID1 sur le NAS |
| [004](docs/adr/004-wol-s3-not-s5.md) | Réveil réseau : veille S3 plutôt qu'extinction S5 (superseded) |
| [005](docs/adr/005-nucbox-always-on.md) | NucBox allumé en permanence, watchdog externe par microcontrôleur |
| [006](docs/adr/006-vaapi-validated.md) | Transcodage matériel VAAPI validé sur le NucBox M6 |
| [007](docs/adr/007-arr-stack.md) | Suite *arr* : Prowlarr, Sonarr, Radarr, Bazarr, Seerr, VPN Mullvad/Gluetun |
| [008](docs/adr/008-discord-community.md) | Discord communautaire : structure native, pas de bot pour l'instant |
| [009](docs/adr/009-notifications-layer1.md) | Notifications passives (Layer 1) : contenu ajouté + santé VPN, sans code de bot |
| [010](docs/adr/010-bot-layer2.md) | Bot Discord Layer 2 : commandes de statut en lecture seule (`/status`, `/streams`) |
| [011](docs/adr/011-backup-restic-rclone.md) | Backup restic : NAS local + hors site |
| [012](docs/adr/012-ansible-retrofit.md) | Rattrapage Ansible : provisioning + déploiement du NucBox |
| [013](docs/adr/013-cicd-github-actions.md) | CI/CD GitHub Actions pour le bot : lint/tests → image GHCR → runner self-hosted |
| [014](docs/adr/014-cloudflare-tunnel.md) | Exposition publique : Cloudflare Tunnel (config distante) + Terraform scopé Cloudflare |
| [015](docs/adr/015-tailscale.md) | Tailscale pour l'accès admin distant (SSH + dashboards *arr*), installé par Ansible |
| [016](docs/adr/016-crowdsec-traefik.md) | CrowdSec derrière Traefik (reverse proxy interne) pour protéger l'exposition publique |
| [017](docs/adr/017-backup-b2.md) | Backup hors site : Backblaze B2 remplace Google Drive |

## Runbooks

| Runbook | Description |
|---|---|
| [install-os-nucbox.md](docs/runbooks/install-os-nucbox.md) | Install/réinstall Ubuntu Server LTS sur le NucBox |
| [setup-jellyfin.md](docs/runbooks/setup-jellyfin.md) | Config Jellyfin post-install : VAAPI, plugins/repos, réglages |
| [setup-nas.md](docs/runbooks/setup-nas.md) | Config NAS (`dxp`) : RAID1, nettoyage, partage NFS, montage NucBox |
| [setup-arr-stack.md](docs/runbooks/setup-arr-stack.md) | Suite *arr* : VPN, indexeurs, clés API, config par service |
| [setup-discord.md](docs/runbooks/setup-discord.md) | Serveur Discord : rôles, salons, Rules Screening, accueil, intégration Seerr |
| [setup-notifications.md](docs/runbooks/setup-notifications.md) | Notifications Layer 1 : webhook Jellyfin, script santé Gluetun |
| [setup-bot.md](docs/runbooks/setup-bot.md) | Bot Discord Layer 2 : application Discord, clé API Jellyfin, déploiement |
| [setup-cicd.md](docs/runbooks/setup-cicd.md) | CI/CD : runner self-hosted NucBox, package GHCR, rollback |
| [setup-cloudflare-tunnel.md](docs/runbooks/setup-cloudflare-tunnel.md) | Cloudflare Tunnel : onboarding zone, jeton API, `terraform apply`, token, config proxy |
| [setup-tailscale.md](docs/runbooks/setup-tailscale.md) | Tailscale : compte, clé d'auth, install via Ansible, Tailscale SSH, subnet router |
| [setup-crowdsec.md](docs/runbooks/setup-crowdsec.md) | CrowdSec + Traefik : ingress Terraform, bootstrap de la clé bouncer, vérif, Console |
| [setup-backup.md](docs/runbooks/setup-backup.md) | Backup restic : bucket/clé Backblaze B2, NAS local, planification, restauration à blanc |

Le runbook WoL est archivé (obsolète, [ADR-005](docs/adr/005-nucbox-always-on.md)) : [setup-wol-nucbox.md](docs/runbooks/setup-wol-nucbox.md).

## Points ouverts

- Rétention Maintainerr (durée avant suppression auto)
- Politique d'approbation Jellyseerr par type de contenu
- Choix du routeur/firewall dédié (voir audit §15)
- Modèle d'UPS (compatibilité NUT à vérifier)
- Choix d'une prise connectée pour un power-cycle physique du NucBox à
  distance (voir [ADR-005](docs/adr/005-nucbox-always-on.md))
- IP codées en dur (NAS, NucBox, montage NFS, alias SSH) — à reconfigurer
  à l'installation du routeur dédié pour la fibre (voir [setup-nas.md](docs/runbooks/setup-nas.md#5-limite-connue--ip-en-dur))
- Pas de port forwarding côté VPN (Mullvad l'a retiré en 2023) — vitesses
  torrent en tant que seeder réduites sur du contenu peu populaire, pas
  bloquant pour l'usage prévu (voir [ADR-007](docs/adr/007-arr-stack.md))
- Indexeurs limités à YTS + The Pirate Bay (EZTV/1337x écartés, bloqués par
  Cloudflare) — à revisiter si le catalogue s'avère insuffisant
- Création de compte Jellyfin/Seerr automatisée à l'arrivée sur le Discord,
  et gamification par temps de visionnage — jugées faisables, reportées au
  bot Discord (voir [ADR-008](docs/adr/008-discord-community.md))
- Watchdog ESP8266 pas encore branché sur les notifications Discord
  (voir [ADR-009](docs/adr/009-notifications-layer1.md))
- État Terraform (`infra/terraform/terraform.tfstate`) : backend local
  gitignoré, sauvegarde hors machine à mettre en place (voir
  [ADR-014](docs/adr/014-cloudflare-tunnel.md))
- Conformité CGU Cloudflare sur le streaming proxifié : risque assumé,
  repli documenté (voir [ADR-014](docs/adr/014-cloudflare-tunnel.md))
