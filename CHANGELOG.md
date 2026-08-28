# Changelog

## [Non publié]

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
