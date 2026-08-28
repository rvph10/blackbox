# ADR 007 — Suite *arr* : Prowlarr, Sonarr, Radarr, Bazarr, Seerr

**Statut :** Accepté
**Date :** 2026-08-28

## Contexte

Jellyfin seul (ADR-006) ne permet que de lire du contenu déjà présent sur le
NAS — rien n'automatise la recherche, le téléchargement, le rangement ou les
sous-titres. Pour que le service serve réellement la communauté (~10
personnes) sans que l'ajout de contenu repose entièrement sur une
intervention manuelle, il faut la suite *arr* : indexation (Prowlarr),
gestion automatique séries/films (Sonarr/Radarr), sous-titres (Bazarr) et
requêtes utilisateurs (Seerr).

## Téléchargement : qBittorrent derrière un VPN (Gluetun)

Le trafic torrent expose l'IP réelle aux autres pairs et au tracker. Décision
: qBittorrent tourne dans le namespace réseau d'un conteneur Gluetun dédié
(`network_mode: service:gluetun`) plutôt qu'en direct.

- **Kill switch natif** : si le tunnel VPN tombe, Gluetun coupe le réseau du
  conteneur entier — qBittorrent perd toute connectivité, aucune fuite
  possible sur l'IP réelle du NucBox.
- **Fournisseur : Mullvad** (WireGuard, clé privée + adresse récupérées sur
  `mullvad.net/en/account/wireguard-config`), choisi plutôt que NordVPN
  (déjà possédé) car le support Gluetun est natif et direct (juste une clé
  WireGuard à coller), alors que NordVPN demande une extraction bricolée de
  la clé.
- **Serveur : Pays-Bas** (bonne infra Mullvad, faible latence depuis la
  Belgique, juridiction plutôt neutre pour du P2P).
- **Limite connue** : Mullvad a retiré le port forwarding pour tous les
  utilisateurs depuis 2023. Conséquence : les téléchargements fonctionnent
  normalement (connexions sortantes), mais moins de vitesse en tant que
  seeder sur des torrents peu populaires. Pas bloquant pour l'usage prévu.
- **Sécurité additionnelle** : `Network Interface: tun0` forcé dans
  qBittorrent (ceinture et bretelles en plus du kill switch iptables de
  Gluetun), `Host Header Validation` désactivée (nécessaire car qBittorrent
  répond depuis le netns de Gluetun, pas `localhost`).

## Structure de stockage : racine commune pour le hardlink

Jellyfin monte `${MEDIA_PATH}` sur `/media`. Les *arr* apps et qBittorrent
montent la **même racine** `${MEDIA_PATH}` sur `/data` (au lieu de volumes
séparés par service). Sans ça, Sonarr/Radarr ne peuvent pas faire de
hardlink/déplacement atomique entre le dossier de téléchargement et la
bibliothèque finale (Docker traite des points de montage différents comme
des systèmes de fichiers différents) — ils recopient les fichiers en entier
à chaque import à la place, plus lent, plus d'usure disque.

Structure sous `${MEDIA_PATH}` :
```
movies/
tvshows/
downloads/
  tv-sonarr/
  movies-radarr/
```

Catégories qBittorrent (`tv-sonarr`, `movies-radarr`) alignées avec les
catégories configurées côté Sonarr/Radarr dans leur download client.

## Indexeurs : liste courte plutôt que tout activer

Recommandation TRaSH Guides suivie : peu d'indexeurs fiables plutôt que des
dizaines qui ralentissent chaque recherche et multiplient les échecs.
Retenus : **YTS** (films) et **The Pirate Bay** (généraliste, films + séries,
filet de sécurité). **EZTV écarté** : protégé par Cloudflare, bloqué même
avec FlareSolverr configuré (problème connu et non résolu côté Prowlarr/
Cloudflare). **1337x écarté** pour la même raison — nécessiterait un
conteneur FlareSolverr additionnel dont la fiabilité se dégrade. Ces choix
pourront être revisités si le catalogue s'avère trop pauvre à l'usage.

## Sous-titres : Bazarr + OpenSubtitles.com

Bazarr connecté à Sonarr et Radarr (sync automatique des séries/films
suivis). Provider **OpenSubtitles.com** (compte VIP payant pris par
l'utilisateur — l'accès anonyme a été fermé par le service, un compte est
obligatoire). Profil de langue par défaut : **Français**, appliqué aux
séries et films par défaut.

## Requêtes utilisateurs : Seerr (pas Jellyseerr)

Déployé initialement avec Jellyseerr (`fallenbagel/jellyseerr:latest`), puis
migré vers **Seerr** (`ghcr.io/seerr-team/seerr:latest`) le jour même : le
projet Jellyseerr a été abandonné en février 2026, fusionné avec Overseerr
dans un projet unique maintenu par la même équipe. Migration automatique
depuis les données existantes (même fichier `settings.json`), zéro perte —
confirmé après coup (`serverId` Jellyfin conservé, connexions Sonarr/Radarr
intactes, `initialized: true`).

## Qualité Radarr

Profil qualité **`HD - 720p/1080p`** plutôt que `Ultra-HD` : plafonner à
1080p évite de faire exploser le stockage NAS et la bande passante interne
pour un gain perceptible marginal en usage de streaming partagé — cohérent
avec la stratégie de transcodage VAAPI validée en 1080p (ADR-006).
Disponibilité minimale : **`Released`** (évite les captures cam/TS en
attendant la sortie officielle).

## Conséquences

- 7 nouveaux conteneurs dans `infra/docker/prod/docker-compose.yml` :
  gluetun, qbittorrent, prowlarr, sonarr, radarr, bazarr, seerr.
- Secrets (clé Mullvad, PUID/PGID) ajoutés à `.env` (non commité) —
  `.env.example` documente les clés attendues.
- Un vrai bug de configuration a été trouvé et corrigé en vérifiant les
  fichiers de config directement plutôt que de se fier à l'UI : le save
  path par défaut de qBittorrent pointait vers `/downloads/` (chemin
  inexistant dans le conteneur, seul `/data` est monté) malgré un réglage
  de catégorie correct. Détail dans le runbook.
- Détail complet de la configuration (repos, catégories, clés API par
  service) dans `docs/runbooks/setup-arr-stack.md`.
