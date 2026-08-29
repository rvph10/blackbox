# Changelog

## [Non publié]

### 2026-08-29

- ADR-014 : exposition publique de Jellyfin et Seerr via **Cloudflare
  Tunnel**, préparé avant la fibre (le tunnel est sortant, il n'attend pas
  le routeur/VLAN). Tunnel à configuration distante (`config_src =
  "cloudflare"`) : règles d'ingress dans Terraform, le conteneur
  `cloudflared` ne reçoit qu'un token
- `infra/terraform/` : premier code Terraform du projet, scopé strictement
  Cloudflare (tunnel, config d'ingress, 2 CNAME). Backend `local` gitignoré
  (l'état contient le token), lock file versionné. Sous-domaines
  thématiques : `stream.blackbox.homes` (Jellyfin),
  `requests.blackbox.homes` (Seerr)
- `infra/docker/prod/docker-compose.yml` : service `cloudflared` (connexion
  sortante, aucun port publié), `.env.example` : `TUNNEL_TOKEN`
- Pas de Cloudflare Access devant les services : casserait les clients
  natifs (appli mobile Jellyfin, Infuse). Jellyfin a sa propre auth, Seerr
  le SSO Jellyfin. Exposition = tunnel + DNS uniquement
- Runbook `setup-cloudflare-tunnel.md` : bascule de la zone `blackbox.homes`
  sur Cloudflare (NS chez Porkbun), jeton d'API scopé, `terraform apply`,
  déploiement du token, config Jellyfin/Seerr derrière le proxy, rollback
- Appliqué et en production : zone `blackbox.homes` basculée sur Cloudflare
  (NS chez Porkbun), `terraform apply` (4 ressources), token déployé,
  `cloudflared` up (Healthy, 4 connexions). `stream.blackbox.homes` et
  `requests.blackbox.homes` accessibles hors LAN, validé en 4G. Jellyfin
  configuré avec `cloudflared` en known proxy, Seerr Application URL publique
- Idempotence du playbook Ansible confirmée (2ᵉ run réel :
  `ok=12 changed=0`) — point ouvert d'ADR-012 clos

- ADR-013 : chaîne CI/CD GitHub Actions pour le bot Discord (seul code
  applicatif maison du projet). `ci.yml` : `ruff check`, `ruff format
  --check`, `pytest` sur PR et push `main` touchant `bot/`. `release.yml` :
  build de l'image `ghcr.io/rvph10/blackbox-bot` (linux/amd64 seul — plus
  aucune machine ARM dans l'archi depuis ADR-005), push GHCR, puis job
  `deploy` sur un runner self-hosted du NucBox (`docker compose pull bot &&
  up -d bot`)
- Runner self-hosted plutôt que SSH depuis le cloud : pas de clé d'accès au
  NucBox dans un secret de repo, connexion sortante uniquement, cohérent
  avec l'absence de port entrant. Aucun secret de repo ajouté (`GITHUB_TOKEN`
  + `packages: write` suffisent pour GHCR)
- `bot/` : `pyproject.toml` (config ruff + pytest), `requirements-dev.txt`,
  `tests/test_main.py` (7 tests — logique de formatage pure + appels
  Jellyfin mockés via `aioresponses`, le bot ne se connecte jamais à
  Discord en test). `main.py` : `client.run` déplacé sous `if __name__ ==
  "__main__"` avec vérification des variables d'env au démarrage, lecture
  tolérante au niveau module pour permettre l'import en test
- `infra/docker/prod/docker-compose.yml` : service `bot` passe de
  `build: ../bot` à `image: ghcr.io/rvph10/blackbox-bot:latest` — le code du
  bot n'est plus déployé sur le NucBox (rôle Ansible `deploy` allégé), seul
  `~/blackbox/bot/.env` y reste. Handler Ansible `docker compose up` fait
  désormais `pull` avant `up -d`
- Runbook `setup-cicd.md` : installation du runner self-hosted, passage du
  package GHCR en public, procédure de rollback. `setup-bot.md` §4 mis à
  jour (déploiement automatisé, commande manuelle de secours conservée)

### 2026-08-28

- ADR-008 : serveur Discord communautaire construit sur les fonctionnalités
  natives uniquement, aucun bot pour l'instant. Mode Communauté activé
  (Découverte désactivée, invitation uniquement), rôles Admin/Membre, salons
  `#règles` (lecture seule), `#accueil` (lecture seule, message épinglé),
  `#annonces` (System Messages Channel + futures notifs), `#discussion`,
  `#demandes`, `#bugs-et-problèmes`
- Rules Screening configuré via Safety Setup (l'interface Discord a changé,
  ce n'est plus un onglet séparé) — règles rédigées, `#règles` verrouillé en
  écriture
- Welcome Screen et description du serveur rédigés
- Décisions actées et documentées : comptes invités (Wizarr) abandonnés
  (communauté fixe, pas de flux de visiteurs), rôle "Nouveau" et onboarding
  natif à rôle par défaut écartés (exigences disproportionnées pour 10
  personnes), création de compte et gamification par temps de visionnage
  jugées faisables mais reportées au futur bot Discord
- Intégration Seerr du plugin Jellyfin-Enhanced vérifiée directement dans sa
  config (déjà active : recherche/demande depuis Jellyfin, 4K désactivé de
  façon cohérente avec le profil qualité Radarr, import auto des comptes
  Seerr via Sign-in with Jellyfin) — `DownloadsPageEnabled` et
  `CalendarPageEnabled` activés en plus (suivi des téléchargements et
  calendrier des sorties directement dans Jellyfin)
- Runbook `setup-discord.md` : procédure complète (rôles, salons, Rules
  Screening, Welcome Screen, message d'accueil, config Jellyfin-Enhanced)
- ADR-009 : premières notifications Discord (Layer 1) mises en place sans
  code de bot. Liste volontairement courte pour éviter le spam : contenu
  ajouté (Jellyfin, événement *Item Added*) vers `#annonces`, santé du VPN
  Gluetun vers le salon admin. Écartés explicitement : doublon Seerr/
  Jellyfin sur "média disponible", notifs de nouvelle demande (auto-approve
  déjà actif, aucune action requise), Playback Start/Stop (vie privée),
  User Created
- Bug trouvé et corrigé sur le webhook Jellyfin : la destination Discord
  avait été créée en type "Generic" avec un template JSON vide, ce qui
  aurait fait échouer silencieusement les notifications côté Discord (API
  Discord rejette un webhook sans `content`/`embeds`) — corrigé en
  recréant la destination avec le type "Discord" natif du plugin, qui
  génère l'embed automatiquement
- Script `infra/scripts/gluetun-healthcheck/check-gluetun.sh` : vérifie
  l'état de santé du conteneur gluetun, poste sur le webhook Discord admin
  uniquement quand l'état change (pas à chaque exécution). Déployé sur le
  NucBox, exécuté toutes les 2 minutes via `gluetun-healthcheck.timer`
  (systemd), testé en conditions réelles (premier message reçu avec
  succès)
- Rich Presence Discord façon Spotify ("voir ce que les autres regardent")
  : identifié comme non réalisable côté serveur (fonctionne par IPC locale
  sur la machine de chaque utilisateur), solutions existantes
  (`jellyfin-rpc`) notées comme option client opt-in à documenter plus
  tard, pas un chantier serveur
- ESP8266 (watchdog) volontairement mis en pause pour cette itération, même
  principe que Gluetun à appliquer plus tard côté ESPHome
- ADR-010 : premier vrai code du bot Discord (`bot/`, jusqu'ici vide) —
  Layer 2, deux commandes slash en lecture seule : `/status` (Jellyfin en
  ligne/hors ligne, volontairement simplifié) et `/streams` (qui regarde
  quoi, accessible à tout le monde avec identités visibles — décision
  assumée, revient en partie sur la prudence vie privée de Layer 1 car
  interrogé à la demande plutôt que poussé automatiquement)
- Bot en Python (`discord.py`), conteneur Docker dédié, connecté à Jellyfin
  via le réseau Docker interne et une clé API dédiée. Déployé et vérifié en
  conditions réelles (connexion Discord confirmée dans les logs, commandes
  testées sur le serveur)
- Piège de déploiement trouvé et corrigé : le chemin relatif du build
  Docker (`../../../bot`, correct dans la structure du repo Git) ne
  correspondait pas à la structure réelle du NucBox où `bot/` et `prod/`
  sont frères directs — corrigé en `../bot`, commenté dans le compose pour
  éviter de reproduire l'erreur
- Runbook `setup-bot.md` : création de l'application Discord, clé API
  Jellyfin dédiée, déploiement, invitation du bot, vérification
- ADR-011 : premier backup du projet — restic vers deux dépôts
  indépendants, NAS local (`dxp`, partage NFS déjà monté) et Google Drive
  (via `rclone`, compte déjà possédé par l'utilisateur). Périmètre : configs
  applicatives uniquement (bases Sonarr/Radarr/Prowlarr/Bazarr/Seerr, config
  Jellyfin, `.env`), pas la médiathèque (déjà protégée par le RAID1 du NAS,
  re-téléchargeable via la suite *arr*)
- Passphrase restic générée (`openssl rand -base64 32`), remise à
  l'utilisateur avec consigne explicite de la conserver hors du NucBox
  (gestionnaire de mots de passe) — sans quoi les deux dépôts deviennent
  irrécupérables si le NucBox meurt
- Bug trouvé et corrigé au premier test réel : `restic backup` échouait
  (code 3) sur des fichiers temporaires root-only créés par Jellyfin
  (`config/temp/mm-exhelper.so.*`, extraction de bibliothèques natives),
  malgré un snapshot valide créé — corrigé en excluant ce dossier
  (sans intérêt à restaurer, recréé au démarrage)
- Backup quotidien planifié à 4h via `blackbox-backup.timer` (systemd),
  rétention `--keep-daily 7 --keep-weekly 4 --keep-monthly 6`, alerte
  Discord sur le webhook admin uniquement en cas d'échec (silence sinon)
- Runbook `setup-backup.md` : configuration rclone/Google Drive, restic,
  déploiement, vérification, procédure de restauration (non testée en
  conditions réelles, point ouvert noté)
- ADR-012 : rattrapage du choix Ansible du brief initial, resté non
  appliqué (dossier `infra/ansible/` vide) tout au long du déploiement
  manuel documenté dans les runbooks précédents. Playbook `site.yml` + 4
  rôles (base, docker, deploy, systemd_timers) couvrant tout ce qui avait
  été construit à la main jusqu'ici — secrets toujours volontairement hors
  scope (vérifiés, jamais générés/modifiés par Ansible)
- Bug bloquant trouvé et corrigé : le NucBox utilise `sudo-rs` (réécriture
  Rust de sudo, devenue le défaut sur Ubuntu récent) au lieu du `sudo` GNU
  historique — incompatibilité connue et non résolue avec le plugin
  `become` d'Ansible (`[sudo: authenticate]` au lieu du prompt standard,
  timeout systématique). Corrigé en réinstallant `sudo` classique et en
  basculant l'alternative système (`update-alternatives --set sudo`)
- Playbook testé en mode simulation (`--check --diff`, aucune surprise)
  puis en conditions réelles (`changed=1`, uniquement une correction de
  permissions mineure sur deux dossiers) — deuxième run de confirmation
  d'idempotence pas encore fait, noté en point ouvert

### 2026-08-26

- Squelette du repo (docs/infra/bot), import du brief et de l'audit dans `docs/`
- ADR-001 : structure monorepo
- ADR-002 : OS du NucBox → Ubuntu Server LTS + HWE, surtout pour garder un
  kernel/Mesa à jour avant le test VAAPI
- ADR-003 : RAID1 sur le NAS plutôt que RAID0
- Runbook d'installation OS pour le NucBox (BIOS, HWE, snap Docker à éviter)

### 2026-08-27

- OS Ubuntu Server 26.04 LTS installé sur le NucBox, hostname `nucbox`
- Clé SSH dédiée générée et déployée (`id_nucbox`), alias `ssh nucbox` ajouté
- Wake-on-LAN testé de bout en bout : ne fonctionne pas depuis S5 malgré BIOS
  correct et driver `r8125-dkms` avec tous les paramètres recommandés
  (`s5wol`, `aspm=0`, `eee_enable=0`) — fonctionne de façon fiable depuis S3.
  ADR-004 : on utilisera S3 plutôt que S5 pour l'extinction programmée.
- Runbook WoL complet (BIOS, driver, netplan par MAC, paramètres module)
- Netplan corrigé : `eno1` marqué optionnel (supprime un délai de boot de 2min
  dû à `systemd-networkd-wait-online`), `dhcp4` activé sur l'interface filaire
- ADR-005 (supersède ADR-004) : abandon de l'extinction/veille programmée —
  le NucBox reste allumé 24/7 (redémarrages ponctuels uniquement). WoL
  abandonné entièrement (plus nécessaire), runbook associé archivé. Bot
  Discord hébergé sur le NucBox plutôt que sur un RPi séparé. Plus de RPi
  dans l'archi cible : le seul rôle externe restant (watchdog ping + alerte,
  domaine de panne indépendant du NucBox) sera couvert par un microcontrôleur
  ESP8266 (AZ-Delivery NodeMCU, déjà en stock) en Wi-Fi via ESPHome ; archi
  cible du README mise à jour
- Choix microcontrôleur watchdog ajusté : ESP8266 (AZ-Delivery NodeMCU/D1
  mini déjà possédés) plutôt qu'un ESP32+Ethernet à acheter — compromis
  Wi-Fi documenté dans l'ADR-005. RPi Zero 2 W disponible mais gardé en
  réserve, pas utilisé pour ce rôle
- Brief (`docs/homelab_projet.md`) et audit (`docs/audit_projet.md`)
  réécrits pour un ton documentaire neutre (suppression des emojis de
  sévérité, des tournures trop orales/IA), contenu et conclusions inchangés
- ADR-006 : transcodage matériel VAAPI validé sur le Radeon 760M
  (`mesa-va-drivers` + `vainfo`, utilisateur ajouté aux groupes
  `video`/`render` pour accéder à `/dev/dri/renderD128`). Test réel via
  `ffmpeg` (decode H264 → encode HEVC en VAAPI, ~23x temps réel), pas
  seulement l'énumération de capacités `vainfo`. Risque n°2 du projet levé
- Docker Engine installé sur le NucBox (dépôt officiel apt, pas le snap ;
  utilisateur ajouté au groupe `docker`)
- Premier déploiement applicatif : Jellyfin seul (`infra/docker/prod/`),
  stockage média temporaire en local (SSD) en attendant le NAS,
  `/dev/dri` passé au conteneur avec les GID `video`/`render` de l'hôte via
  `group_add` — accès GPU confirmé à l'intérieur du conteneur, `ffmpeg`
  embarqué détecte les encodeurs/décodeurs VAAPI. Postgres et la suite
  *arr* pas encore ajoutés (périmètre volontairement réduit pour ce
  premier déploiement)
- Charge de travail VAAPI mesurée : ~22.5x temps réel en H264, ~26x en
  HEVC au total, réparti équitablement entre flux concurrents. Seuil de
  1x (temps réel) entre 20 et 24 flux transcodés simultanément — marge
  confortable au-dessus de la cible de 10 flux (détail dans ADR-006)
- Transcodage en RAM : `/transcodes` monté en tmpfs (4 Go) dans le
  conteneur Jellyfin plutôt que sur le SSD
- Configuration Jellyfin post-install : nom du serveur `BlackBox`,
  thème JellyFlix, bibliothèques Films/Séries (stockage local temporaire),
  7 plugins installés (File Transformation, Skin Manager, Intro Skipper,
  Jellyfin Enhanced, Playback Reporting, LogoSwap, Webhook) et leurs
  repositories. Corrections de config par rapport aux défauts Jellyfin :
  `AllowHevcEncoding` activé (sinon toujours H264 malgré VAAPI actif),
  suppression des segments HLS activée (nécessaire avec le tmpfs
  plafonné), accélération matérielle activée pour la génération
  trickplay. Détail complet dans le runbook `setup-jellyfin.md`
- NAS branché et configuré : nommé `dxp`, RAID1 déjà en place d'une
  installation précédente (sain, `[UU]`) + cache SSD NVMe en bonus.
  Nettoyage des restes d'un autre projet homelab (Grafana, Loki,
  Prometheus, Home Assistant, Proxmox...), rien de ce projet-ci n'était
  encore dessus. Partage NFS `media` exposé au NucBox, monté en
  `_netdev,noauto,x-systemd.automount,nofail` (ne bloque pas le boot si
  le NAS est injoignable). Bibliothèque Jellyfin basculée du stockage
  local vers le NAS (`MEDIA_PATH` dans `.env`, chemins internes au
  conteneur inchangés). Runbook `setup-nas.md` ; limite connue : IP
  codées en dur, à reconfigurer à la migration fibre (15/09)
- ADR-007 : suite *arr* déployée (Prowlarr, Sonarr, Radarr, Bazarr, Seerr,
  qBittorrent). Téléchargement torrent routé exclusivement via un VPN
  Mullvad (WireGuard, Pays-Bas) dans un conteneur Gluetun dédié
  (`network_mode: service:gluetun`, kill switch natif). Racine de stockage
  commune (`${MEDIA_PATH}` → `/data`) entre qBittorrent et les *arr* apps
  pour permettre le hardlink. Indexeurs : YTS + The Pirate Bay (EZTV et
  1337x écartés, bloqués par Cloudflare même avec FlareSolverr). Bazarr
  connecté à Sonarr/Radarr, provider OpenSubtitles.com, profil Français
  par défaut. Jellyseerr déployé puis migré le jour même vers **Seerr**
  (`ghcr.io/seerr-team/seerr`) suite à l'abandon du projet Jellyseerr
  (fusionné dans Seerr en février 2026) — migration automatique sans
  perte de données, vérifiée après coup
- Vérification post-déploiement de toute la stack *arr* directement dans
  les fichiers de config / API de chaque service plutôt que de se fier à
  l'UI seule. Un bug trouvé et corrigé : `qBittorrent.conf` pointait
  encore vers `/downloads/` (chemin absent du conteneur) pour le save
  path et le dossier temporaire par défaut, malgré un réglage de
  catégorie correct vers `/data/downloads`. Un problème de config Bazarr
  également trouvé (connexion Sonarr/Radarr et providers non sauvegardés
  malgré un premier passage dans l'UI) et corrigé après une première
  correction trop large (clés API d'autres providers touchées par erreur,
  revert immédiat puis correctif ciblé). Détail complet dans
  `setup-arr-stack.md`
