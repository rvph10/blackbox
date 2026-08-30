# Changelog

## [Non publié]

### 2026-08-30

- Bot : **annonces « nouveau contenu » via Jellyseerr → écouteur HTTP du
  bot** (révise ADR-009). Le plugin Webhook de Jellyfin est retiré ;
  l'agent Webhook de Jellyseerr POST l'event « Media Available » sur
  `http://bot:8000/jellyseerr` (jamais exposé, header secret vérifié). Le
  bot poste dans `#annonces` (affiche TMDB, titre, résumé, lien « Regarder »
  vers la fiche Jellyfin) **en pinguant le demandeur** (ID Discord de son
  profil Jellyseerr, repli sur le mapping `jf_username`). Dédup sur l'ID de
  demande. `bot/seerr_hook.py`, `aiohttp.web` (déjà présent), `.env` :
  `SEERR_WEBHOOK_SECRET`, `CONTENT_CHANNEL_ID`.
- Bot : **message d'accueil public** à `on_member_join` dans `#annonces`
  (`WELCOME_CHANNEL_ID`) — pingue le nouvel arrivant, texte **aléatoire**
  (pool éditable `bot/welcome_lines.py`) + carte de bienvenue sans
  identifiants. `/creer-compte` ne poste rien de public.
- Bot : **cartes-images** (Pillow, `bot/cards.py`) pour le classement
  (podium 3 places, photos de profil Discord rondes, couronne dorée
  dessinée sur le n°1) et le MP de bienvenue (avatar + « Bienvenue sur
  Blackbox »). `Pillow` + `fonts-dejavu-core` ajoutés à l'image. Le
  classement poste l'image + une courte légende qui pingue le top 3
  (fini l'embed compact).
- Bot : panneau live — le pseudo affiché est celui du membre **Discord**
  (repli Jellyfin), appareil et débit retirés.

- ADR-022 : **panneau « en direct » des lectures**. Un message-embed unique
  maintenu par le bot dans `#salle-de-projection` (lecture seule),
  rafraîchi toutes les 45 s : qui regarde quoi (pseudo Discord), barre de
  progression, transcodage / lecture directe. Statut du bot mis à jour en
  parallèle (« Regarde : N flux »).
  **La slash command `/streams` est supprimée.** Nouveau module
  `bot/now_playing.py`, `tasks.loop(seconds=45)`, `NOW_PLAYING_CHANNEL_ID`
  dans le `.env`. Salon `#salle-de-projection` à créer en lecture seule.
- ADR-021 : **bot Discord Layer 3**. Le bot passe de lecteur passif à
  acteur avec état.
  - **Provisioning** : `on_member_join` → compte Jellyfin créé par API
    (nom dérivé du pseudo, mot de passe aléatoire jamais stocké, policy :
    2 bibliothèques, 3 flux simultanés, pas admin) → mapping en base →
    identifiants envoyés en MP (repli alerte admin si MP fermés). Seerr :
    rien, auto-import au premier login.
  - **Gamification** cosmétique : 4 rôles cumulatifs (`Figurant` /
    `Second rôle` / `Premier rôle` / `Réalisateur`, seuils 0/15/60/180 h),
    recalcul quotidien 05h00 depuis Jellystat.
  - **Classement** tous les 15 j dans `#classement` : top 3 pingé, film /
    série de la quinzaine, nouveaux membres, total serveur, rôle
    `Tête d'affiche` transféré au n°1.
  - **Commandes** : `/moncompte` (rappel identifiant + reset mdp en MP),
    `/messtats`, `/roulette` (film non vu au hasard) ; admin (rôle
    `SysAdmin`) `/creer-compte`, `/lier`, `/desactiver`.
  - `bot/` refondu en modules (`config`, `db`, `jellyfin`, `jellystat`,
    `provisioning`, `gamification`, `scoreboard`, `bot_commands`, `main`),
    `discord.ext.commands.Bot` + `tasks`. SQLite (`aiosqlite`) dans le
    volume `./data/bot`, ajouté aux sources restic.
  - `docker-compose.yml` : volume `./data/bot`, `JELLYSTAT_URL`,
    `depends_on: jellystat`. `.env.example` : `DISCORD_GUILD_ID`,
    `JELLYSTAT_URL/API_KEY`, `ADMIN_ALERT_WEBHOOK_URL`, URLs publiques.
  - Intent privilégié **Server Members**, bot ré-invité avec
    **Manage Roles**. Jellyseerr : « Enable new Jellyfin Sign-In ».
  - Runbook `setup-bot.md` réécrit.

### 2026-08-29

- Notifications `#annonces` (ADR-009) : les nouveaux ajouts Jellyfin
  n'arrivaient jamais — la **destination "Discord" native du plugin Webhook
  est buggée** (Discord rejette son corps, `400 / code 50109 invalid JSON`,
  [bug amont #369](https://github.com/jellyfin/jellyfin-plugin-webhook/issues/369)).
  Basculé sur une destination **Generic** + template Handlebars maison
  (accroche « 🎬 Nouveau film disponible ! » / « 📺 Nouvel épisode », titre,
  résumé, affiche, lien fiche Jellyfin). Pièges corrigés : `json_encode`
  n'ajoute pas les guillemets (`"{{json_encode X}}"`) et lève sur valeur
  nulle (champs optionnels sous `{{#if_exist}}`) ; `Server URL` du plugin à
  renseigner ; header `Content-Type: application/json`. Validé de bout en
  bout (film de test → embed dans `#annonces`). Runbook `setup-notifications.md`
  mis à jour avec le template et la procédure de test.
- ADR-020 : **rétention de la bibliothèque avec Maintainerr** (complète
  ADR-019 — le capacity-watcher alerte/bride, Maintainerr libère l'espace).
  Support Jellyfin natif + Seerr + Radarr/Sonarr. Déployé en **revue
  manuelle** : aucune suppression automatique tant que le NAS n'est pas
  sous pression (2 % aujourd'hui). Trois collections de règles temporelles
  (films dormants 90/180 j grâce 14 j ; séries terminées inactives 120 j
  grâce 21 j ; « demandé puis jamais lancé » 45 j grâce 7 j, toujours
  manuelle) + protections globales (vu < 180 j, demandé < 90 j, ajouté
  < 90 j, tag `keep`). Étagère « Bientôt retiré » visible dans Jellyfin.
  `docker-compose.yml` : service `maintainerr` (`user: ${PUID}:${PGID}`,
  volume `data/maintainerr` + `${MEDIA_PATH}:/data`, port `6246`, dashboard
  Tailscale). Aucun secret (clés API saisies dans l'UI). Runbook
  `setup-maintainerr.md`. Bascule auto de la Collection 1 à décider quand
  le NAS dépassera ~70 %.

- ADR-019 (**accepté, en production**) : autorégulation capacité + bande
  passante. **Jellystat** (+ Postgres dédié) pour l'observation des usages
  Jellyfin (dashboard Tailscale `:3000`, jamais exposé publiquement) et un
  watcher `infra/scripts/capacity-watcher/check-capacity.sh` + timer systemd
  (2 min, schéma ADR-009). À chaque passage : `df` sur `MEDIA_MOUNT` +
  somme des bitrates des sessions Jellyfin actives (`/Sessions`). Trois
  niveaux avec hystérésis (fichier d'état) : WARN → alerte Discord admin ;
  CRIT → bascule des **limites alternatives qBittorrent** (bride le seeding,
  non destructif, réversible) + alerte admin + message communautaire ;
  retour OK → limites désactivées. Seuils absolus dans le `.env`
  (`DISK_WARN/CRIT_PCT`, `UPLOAD_WARN/CRIT_MBPS` calés sur ~20 Mbit/s VDSL,
  à remonter après la fibre). Ansible : `jq` dans le rôle `base`,
  déploiement du script + unité `capacity-watcher`. Runbook
  `setup-capacity-watcher.md`. Jellystat hors périmètre backup restic
  (Postgres reconstructible via Full Sync).
- ADR-018 (**proposé**) : Live TV / IPTV. Choix logiciel = **Threadfin**
  (proxy M3U/EPG, tuner HDHomeRun virtuel) devant le module Live TV natif de
  Jellyfin — préféré à Jellyfin-seul (gestion des chaînes pénible sur un gros
  bouquet) et à TVHeadend (trop lourd). Coût ressources : conteneur
  négligeable (~150–300 Mo RAM, CPU nul) ; le vrai coût est le transcodage
  Jellyfin (1080i désentrelacé ≈ 1,5 flux ADR-006), ~12–14 flux équivalents
  au pire pour 10 viewers, dans la marge des 20+ mesurés. WAN : ~50–120
  Mbit/s entrants permanents. Contrainte structurante = **1 flux/compte
  fournisseur, streaming simultané interdit** → ~10 comptes nécessaires.
  Passage en « Accepté » bloqué sur la réponse du fournisseur (nb de comptes,
  specs de flux, support proxy, multi-comptes depuis une seule IP). Pas
  d'exposition publique (hors Cloudflare Tunnel), admin via Tailscale.
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
- Test de restauration à blanc restic (point ouvert d'ADR-011) : **clos** —
  dépôt NAS local (restauration + `check --read-data` + bases SQLite
  `integrity_check = ok` + secrets) et dépôt B2 (`init` + snapshot +
  `check --read-data` sans erreur). Timer quotidien : `EXIT=0` sur les deux
- ADR-017 : le test a révélé que le **dépôt Google Drive était figé depuis
  2 jours** — `rclone config` sans `client_id` tape dans le client OAuth
  partagé de rclone (`project_number 202264815644`), régulièrement saturé
  → `403 RATE_LIMIT_EXCEEDED`. Bascule vers **Backblaze B2, backend natif
  restic** (plus de rclone dans le chemin hors site) : offre gratuite 10 Go,
  clé d'application restreinte au bucket. Le dépôt NAS local garde tout
  l'historique (dépôts indépendants)
- `backup.sh` : `b2:` au lieu de `rclone:`, `B2_ACCOUNT_ID`/`B2_ACCOUNT_KEY`,
  filtre des sources inexistantes, code 3 de restic (snapshot partiel)
  traité comme non bloquant + alerte. CrowdSec/Traefik **exclus**
  volontairement (conteneur root illisible par `kong`, état 100 %
  régénérable). Dépôt B2 `restic init` + premier snapshot + `check
  --read-data` OK (clé restreinte au bucket, backend natif restic)
- Rôle Ansible `base` : `rclone` retiré. Runbook `setup-backup.md` §1
  réécrit (bucket + clé B2), §8 mis à jour avec la procédure de test à blanc
- Étendu la LV racine du NucBox : l'installeur Ubuntu plafonne à ~100 Go,
  `/` passée de 98 Go à 936 Go (Docker, bases *arr, cache Jellyfin sur `/`) —
  noté dans `install-os-nucbox.md`
- Import Radarr bloqué diagnostiqué (film étranger *La Captura* / *Facing El
  Chapo* : titre local ≠ titre TMDB → `Manual Import required`, sécurité pas
  bug)
- ADR-015 : rôle Ansible `tailscale` pour l'accès admin distant (SSH +
  dashboards *arr*) sans port ouvert. Installation idempotente via le dépôt
  apt officiel ; `tailscale up --ssh --hostname=nucbox` conditionné à une
  clé d'auth passée en extra-var (`-e tailscale_authkey=…`, jamais dans Git,
  `no_log`), sautée si le nœud est déjà connecté. Tailscale SSH activé,
  `sshd` classique inchangé (durcissement reporté au chantier routeur/VLAN).
  Pas de subnet router par défaut (les dashboards *arr* sont sur le NucBox) —
  option `tailscale_advertise_routes` pour joindre le NAS. Runbook
  `setup-tailscale.md`. Appliqué : NucBox sur le tailnet, Tailscale SSH et
  dashboards *arr* joignables à distance, expiration de clé désactivée
- ADR-016 : CrowdSec pour protéger l'exposition publique (brute-force
  Jellyfin). Vu l'absence de reverse proxy avec Cloudflare Tunnel, ajout de
  **Traefik** en proxy interne (file provider, pas de socket Docker, aucun
  port publié) — l'ingress Cloudflare pointe désormais vers `traefik:80`,
  qui route par `Host` derrière un middleware CrowdSec
  (`crowdsec-bouncer-traefik-plugin` v1.7.1, très actif — le bouncer
  Cloudflare classique n'est plus maintenu, le Worker Bouncer jugé
  disproportionné). Moteur CrowdSec en détection sur les logs Traefik +
  Jellyfin, blocklist communautaire consommée. LAPI sur le réseau Docker,
  aucune dépendance SaaS. Accès LAN/Tailscale inchangé (direct, hors proxy).
  Runbook `setup-crowdsec.md`. Appliqué : `terraform apply` (ingress →
  traefik:80), Traefik + CrowdSec up, bouncer validé, `stream.` / `requests.`
  toujours servis (via cloudflared → traefik → app). Piège rencontré :
  `traefik/lapi-key` auto-créé en dossier root par un `docker compose up`
  prématuré — runbook corrigé (créer le fichier vide d'abord)

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
