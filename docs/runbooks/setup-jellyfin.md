# Runbook — configuration Jellyfin (post-installation)

Réglages et plugins appliqués sur le premier déploiement Jellyfin
(`infra/docker/prod/`), au-delà du wizard d'installation standard. À
rejouer après une réinstallation ou pour vérifier l'état attendu.

## Identité du serveur

- **Nom du serveur** : `BlackBox`
- **Langue des métadonnées** : français (`fr`)
- **Pays des métadonnées** : Belgique (`BE`)
- **Thème** : JellyTheme (via Skin Manager, voir plugins ci-dessous) —
  choix esthétique non tranché, peut changer
- **Écran d'accueil** : réorganisé façon Netflix via le plugin Home Screen
  Sections, voir [ADR-023](../adr/023-home-accueil-netflix.md) et section
  dédiée ci-dessous
- **Logo** : personnalisable via LogoSwap (voir plugins ci-dessous), pas
  encore appliqué — logo Blackbox à uploader quand disponible

## Transcodage / VAAPI

Voir [ADR-006](../adr/006-vaapi-validated.md) pour la validation complète.
Réglages appliqués dans **Dashboard → Playback → Transcoding** :

| Réglage | Valeur | Pourquoi |
|---|---|---|
| Hardware acceleration | Video Acceleration API (VAAPI) | GPU Radeon 760M |
| VA-API Device | `/dev/dri/renderD128` | device passé au conteneur |
| Enable hardware decoding | H264, HEVC, VP9, AV1 | tout ce que le driver supporte |
| Enable hardware encoding | activé | |
| Allow encoding in HEVC format | **activé** | par défaut désactivé dans Jellyfin — sans ça, sortie toujours en H264 même avec VAAPI actif, alors que le brief (§4) vise HEVC comme cible |
| Transcoding temporary path | `/transcodes` | tmpfs (RAM), voir `infra/docker/prod/docker-compose.yml` |
| Delete previous transcoded segments | **activé** (`SegmentKeepSeconds=720`) | nécessaire avec le tmpfs plafonné à 4 Go — sans ça, les segments HLS d'un film long peuvent saturer la RAM allouée |
| Low-Power mode | désactivé | parfois instable sur AMD, pas testé nécessaire ici |

**Dashboard → Playback → Trickplay** :

| Réglage | Valeur | Pourquoi |
|---|---|---|
| Hardware acceleration / encoding | **activé** | décharge la génération de miniatures de scrubbing sur le GPU plutôt que le CPU pendant les scans |
| Extract during library scan | désactivé | tâche lourde, préférée en planifié plutôt que pendant le scan |

**Dashboard → Libraries → [bibliothèque]** :

- Extract chapter images : désactivé (tâche coûteuse, gain visuel mineur)

## Réseau / accès distant

**Dashboard → Networking** :

| Réglage | Valeur | Pourquoi |
|---|---|---|
| Known proxies | `traefik` | La chaîne publique est `cloudflared → traefik → jellyfin` (ADR-016). Sans ça, Jellyfin voit toutes les connexions venir du conteneur Traefik (`172.18.x`) → croit tout le monde en local → n'applique aucune limite distante, et les logs n'ont pas les vraies IP. **Ne pas** mettre `cloudflared` (il ne parle plus à Jellyfin directement). |
| LAN networks | `192.168.129.0/24`, `100.64.0.0/10` | LAN + Tailscale = lecture directe pleine qualité. Tout le reste (via `stream.blackbox.homes`) est traité comme distant. |

**Dashboard → Users → [chaque compte] → Maximum streaming bitrate (internet)** :
`12 Mbps`. Le VDSL montant est à ~20 Mbit/s jusqu'à la fibre ; au-delà de
12, Jellyfin transcode la vidéo (VAAPI, ~27× temps réel) pour que le flux
rentre. Le bot applique déjà cette valeur aux nouveaux comptes
(`NEW_USER_POLICY` → `RemoteClientBitrateLimit`). À relever après la fibre.

Un changement dans Networking demande un **redémarrage** de Jellyfin.

## Repositories de plugins

**Dashboard → Plugins → Repositories → Add**

| Nom | URL |
|---|---|
| Skin Manager | `https://raw.githubusercontent.com/danieladov/JellyfinPluginManifest/master/manifest.json` |
| File Transformation / Home Screen Sections / Plugin Pages | `https://www.iamparadox.dev/jellyfin/plugins/manifest.json` (un seul repo pour les trois) |
| Jellyfin Enhanced | `https://raw.githubusercontent.com/n00bcodr/jellyfin-plugins/main/10.11/manifest.json` (URL spécifique à la version 10.11.x du serveur) |
| Intro Skipper | `https://intro-skipper.org/manifest.json` |
| Logo Swap | `https://raw.githubusercontent.com/NewsGuyTor/LogoSwap/main/manifest.json` |

(Webhook et Playback Reporting sont officiels, déjà dans le repository
`Jellyfin Stable` par défaut — pas de repo à ajouter.)

## Plugins installés

| Plugin | Version | Rôle | Action après install |
|---|---|---|---|
| File Transformation | 2.5.11.0 | Dépendance technique — permet aux autres plugins d'injecter du JS/CSS dans jellyfin-web sans patcher les fichiers | Aucune, doit juste rester actif |
| Home Screen Sections | 2.5.11.0 | Home façon Netflix (films + séries mélangés, rangées par genre, reco) | [ADR-023](../adr/023-home-accueil-netflix.md) — voir section « Écran d'accueil » ci-dessous |
| Plugin Pages | 2.4.11.0 | Dépendance de Home Screen Sections (page de réglages « Modular Home ») | Aucune |
| Skin Manager | 2.0.2.0 | Gestionnaire de thèmes | Thème **JellyTheme** sélectionné (esthétique, peut changer) |
| Intro Skipper | 1.10.11.23 | Détecte et skip les intros/génériques de séries | Nécessite une analyse (`Analyze episodes`) une fois du contenu série présent — rien à faire tant que la bibliothèque est vide |
| Jellyfin Enhanced | 12.5.0.0 | Raccourcis clavier, styles sous-titres, intégration Jellyseerr (auto-request), etc. | Voir réglages détaillés ci-dessous |
| Playback Reporting | 17.0.0.0 | Statistiques de lecture | Passif, rien à configurer. Piste : remplacer/compléter Jellystat pour le watcher de seuil (§4 du brief) une fois assez de données |
| LogoSwap | 1.5.0.0 | Remplacement du logo Jellyfin par un logo perso | Pas encore utilisé (pas de logo Blackbox prêt) |
| Webhook | 21.0.0.0 | Envoie des notifications (nouveau contenu, lecture démarrée...) vers une URL externe | Pas encore configuré — cible prévue : le futur bot Discord (§8 du brief) |

### Réglages Jellyfin Enhanced appliqués

Activés : `AutoPause`, `AutoResume`, `RandomButton`, `PauseScreen`,
`AutoSkipIntro`/`AutoSkipOutro`, `RatingTags` (badges de notes sur les
affiches).

Désactivés : `QualityTags` (badges résolution/codec — chargeait
l'interface), `AutoPip` (optionnel selon usage). Après un changement des
réglages de tags, bumper `ClearLocalStorageTimestamp` (bouton du plugin)
sinon les anciens badges restent en cache navigateur.

Police de sous-titres : Noto Sans (meilleure couverture des caractères
accentués/non-latins que la police par défaut).

## Écran d'accueil (Home Screen Sections)

Voir [ADR-023](../adr/023-home-accueil-netflix.md) pour le raisonnement.

**Config serveur** — Dashboard → Plugins → Home Screen Sections :

| Champ | Valeur |
|---|---|
| Enable | ✅ |
| Default Movies Library | `Films` (`db4c1708cbb5dd1676284a40f2950aba`) |
| Default TV Shows Library | `Séries` (`d565273fd114d77bdf349a2896867069`) |
| Cache timeout | 86400 (baisser à ~600 pendant un réglage, remonter ensuite) |
| Jellyseerr URL / External URL | `http://seerr:5055` / `https://requests.blackbox.homes` |
| Jellyseerr API Key | clé Seerr |
| Radarr / Sonarr URL + clé | `http://radarr:7878` / `http://sonarr:8989` |

12 sections actives (ordre) : Continue Watching/Next Up · Because You
Watched (max 3) · My List · Latest Movies · Latest Shows · Genre (max 3) ·
Watch Again · Discover · My Requests · Upcoming Movies · Upcoming Shows ·
My Media (999). Tout le reste désactivé (musique, livres, Live TV,
doublons `ContinueWatching`/`NextUp` séparés, `RecentlyAdded*`,
`Discover{Movies,TV}`).

**Config client** — la liste/l'ordre par défaut est posé par l'admin via
menu ☰ → « Modular Home ». `AllowUserOverride` actif : chaque membre peut
réordonner sa propre home.

**Piège** : File Transformation modifie le bundle web → après
install/MàJ du plugin, **chaque navigateur** doit vider son service worker
une fois (F12 → Application → Service Workers → Unregister, puis Clear site
data). Idem sur `stream.blackbox.homes` (origine séparée) + purge du cache
Cloudflare.

## Bibliothèques

- **Films** → `/media/movies`
- **Séries** → `/media/tvshows`
- Chemins locaux temporaires (`infra/docker/prod/data/media/`) en
  attendant le NAS — à rebasculer sur le point de montage NFS/SMB une fois
  disponible (voir [ADR-003](../adr/003-raid-nas.md)).
- Live TV / IPTV : pas configuré. Approche retenue = **Threadfin** (proxy
  M3U/EPG, tuner HDHomeRun virtuel) devant le module Live TV natif de
  Jellyfin, voir [ADR-018](../adr/018-iptv-live-tv.md). En attente de la
  réponse du fournisseur (nombre de comptes, specs de flux) avant
  déploiement et rédaction de la section dédiée ici.
