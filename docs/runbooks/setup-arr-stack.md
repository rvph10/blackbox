# Runbook — suite *arr* (Prowlarr, Sonarr, Radarr, Bazarr, Seerr)

Contexte et choix d'architecture : [ADR-007](../adr/007-arr-stack.md).

## 1. VPN (Gluetun) + qBittorrent

- Fournisseur : Mullvad, WireGuard, serveur Pays-Bas
- Clé privée + adresse récupérées sur
  `mullvad.net/en/account/wireguard-config`, stockées dans `.env`
  (`MULLVAD_PRIVATE_KEY`, `MULLVAD_ADDRESSES`, `MULLVAD_COUNTRY`) — jamais
  commitées
- `qbittorrent` tourne en `network_mode: service:gluetun` — tout son trafic
  passe par le tunnel, kill switch natif de Gluetun si le VPN tombe
- Vérification de la connexion :
  ```
  docker exec gluetun wget -qO- https://am.i.mullvad.net/connected
  ```

### Réglages qBittorrent appliqués

- **Downloads → Default Save Path** : `/data/downloads`
- **Downloads → Torrent Content Layout** : `Original`
- **Downloads → Automatic Torrent Management** : activé
- Catégories créées : `tv-sonarr` → `/data/downloads/tv-sonarr`,
  `movies-radarr` → `/data/downloads/movies-radarr`
- **Web UI → Host Header Validation** : désactivé (nécessaire, qBittorrent
  répond depuis le netns de Gluetun, pas `localhost`)
- **Advanced → Network Interface** : `tun0` (sécurité additionnelle,
  indépendante du kill switch iptables de Gluetun)
- **Connection → Encryption** : `Allow encryption`

**Bug trouvé et corrigé** : `Downloads\SavePath` et `Downloads\TempPath`/
`Session\TempPath` dans `qBittorrent.conf` pointaient encore vers
`/downloads/` (chemin absent du conteneur, seul `/data` est monté), alors
que `Session\DefaultSavePath` avait bien été mis à jour vers
`/data/downloads`. Corrigé directement dans le fichier de config puis
conteneur redémarré pour recharger proprement.

## 2. Prowlarr

- Authentification : Forms Login
- Download Client : qBittorrent — Host `gluetun`, Port `8080` (nom du
  conteneur Gluetun, pas `qbittorrent`, puisque qBittorrent partage son
  namespace réseau)
- Indexeurs actifs : **YTS**, **The Pirate Bay**. EZTV et 1337x écartés
  (bloqués par Cloudflare, y compris avec FlareSolverr — voir ADR-007)
- Apps connectées (Settings → Apps), sync `fullSync` : Sonarr
  (`http://sonarr:8989`), Radarr (`http://radarr:7878`)

## 3. Sonarr / Radarr

| | Sonarr | Radarr |
|---|---|---|
| URL | `http://192.168.129.175:8989` | `http://192.168.129.175:7878` |
| Root folder | `/data/tvshows` | `/data/movies` |
| Download client | qBittorrent, `gluetun:8080`, catégorie `tv-sonarr` | qBittorrent, `gluetun:8080`, catégorie `movies-radarr` |
| Indexeurs | The Pirate Bay (sync Prowlarr) | The Pirate Bay + YTS (sync Prowlarr) |
| Quality Profile | `[French MULTi.VO] HD Bluray + WEB (1080p)` (Recyclarr, §7) | `[French MULTi.VO] HD Bluray + WEB` (Recyclarr, §7) |
| Minimum Availability | — | `Released` |

Clés API (Settings → General de chaque app, à utiliser pour Bazarr/Seerr) :
- Sonarr : `836e05333a32436394a73375b01d7ea1`
- Radarr : `cab7b0384dca4214939d159081851558`

### Profil de qualité — pas de Remux (2026-08-31)

Le profil `HD - 720p/1080p` a **Remux-1080p, Remux-2160p et BR-DISK
désactivés**, et `Bluray-1080p` **plafonné** (Settings → Quality :
preferred ~18 Mbit/s, max ~25 Mbit/s).

Raison : tout le streaming sort par le VDSL montant (~20 Mbit/s jusqu'à la
fibre). Un remux à 30-40 Mbit/s est **toujours** transcodé par Jellyfin
avant de sortir → on regarde une version ré-encodée à 12 Mbit/s de toute
façon, pour 3-4× le poids disque et la bande passante. Un bon encode
1080p (~15 Mbit/s) est visuellement équivalent et souvent lisible en
direct.

13 remux déjà présents ont été supprimés (fichier + torrent) et re-cherchés
en version légère (~445 Go libérés). À revoir après la fibre : un profil
« Archive » séparé pourrait réautoriser le remux pour la lecture directe.

Ce profil `HD - 720p/1080p` a depuis été **remplacé par le profil Recyclarr
`[French MULTi.VO] HD Bluray + WEB`** (§7), qui exclut le Remux par
construction et ajoute les Custom Formats TRaSH. Il est conservé mais
inutilisé.

## 4. Bazarr

- URL : `http://192.168.129.175:6767`
- Connecté à Sonarr (`sonarr:8989`) et Radarr (`radarr:7878`) via leurs
  clés API respectives
- Provider : **OpenSubtitles.com** (compte requis, l'accès anonyme a été
  fermé par le service — VIP payant pris par choix personnel, un compte
  gratuit suffit pour l'usage prévu)
- Profil de langue par défaut : **Français**, appliqué aux séries et films

## 5. Seerr (anciennement Jellyseerr)

Déployé initialement sous `fallenbagel/jellyseerr:latest`, **migré vers
`ghcr.io/seerr-team/seerr:latest`** le jour même du déploiement — Jellyseerr
a été abandonné en février 2026 (fusion avec Overseerr dans le projet
Seerr). Migration automatique au premier démarrage à partir des données
existantes, aucune reconfiguration nécessaire.

- URL : `http://192.168.129.175:5055`
- Connexion : "Sign in with Jellyfin" (`http://jellyfin:8096` en interne)
- Services connectés : Sonarr (`sonarr:8989`, root folder `/data/tvshows`),
  Radarr (`radarr:7878`, root folder `/data/movies`)
- Settings → External URL / Forgot Password URL : laissés vides (pas de
  domaine public tant que le Cloudflare Tunnel — Phase 2 — n'est pas en
  place)

## 6. Vérification post-déploiement

Les réglages "confirmés" côté UI ne veulent pas toujours dire "sauvegardés"
(cas vécu avec Bazarr : la connexion Sonarr/Radarr et les providers de
sous-titres n'avaient pas persisté malgré un premier passage dans l'UI).
Pour vérifier réellement l'état d'une app, lire son fichier de config ou
interroger son API plutôt que de se fier à l'affichage :

```bash
# Sonarr / Radarr / Prowlarr : clé API dans config.xml, puis appel API
grep -A1 ApiKey ~/blackbox/prod/data/<app>/config/config.xml
curl -s -H "X-Api-Key: <clé>" http://localhost:<port>/api/v3/rootfolder

# Bazarr : clé API dans config.yaml (auth.apikey)
curl -s -H "X-API-KEY: <clé>" http://localhost:6767/api/system/settings
curl -s -H "X-API-KEY: <clé>" http://localhost:6767/api/providers

# Seerr : settings.json directement
cat ~/blackbox/prod/data/jellyseerr/config/settings.json
```

## 7. Recyclarr — profils de qualité TRaSH Guides

Conteneur `recyclarr` (`ghcr.io/recyclarr/recyclarr:8`), cron `@daily`.
Synchronise les Custom Formats + profils de qualité des
[TRaSH Guides](https://trash-guides.info/) vers Radarr et Sonarr.

**Config** : `infra/docker/prod/recyclarr/configs/{radarr,sonarr}.yml`
(versionnés). Profil retenu : **`[French MULTi.VO] HD Bluray + WEB`**
(Radarr) / `… (1080p)` (Sonarr) :

- **MULTi** : releases avec piste VF *et* VO. Chaque membre choisit sa
  langue audio par défaut dans son profil Jellyfin.
- **VO de référence** : meilleure qualité de source, dispo plus vite pour
  les nouveautés. Bascule possible vers `french-multi-vf` si trop de films
  démarrent en anglais (une ligne `trash_id` à changer + re-sync).
- **Pas de Remux** (Bluray + WEB seulement) — cf. §3.

**Secrets** : `infra/docker/prod/recyclarr/secrets.yml` (gitignoré,
`chmod 600` sur le NucBox) contient `radarr_url` / `radarr_api_key` /
`sonarr_url` / `sonarr_api_key`, référencés par `!secret` dans la config.
Modèle : `secrets.yml.example`.

**Sync manuel** (le cron le fait chaque jour) :
```bash
ssh nucbox "cd ~/blackbox/prod && docker compose exec -T recyclarr recyclarr sync"
```

Après le premier sync : basculer les films/séries existants sur le nouveau
profil (`PUT /api/v3/movie/editor` + `/series/editor`). Les anciens profils
(`HD - 720p/1080p` etc.) sont conservés mais inutilisés.

**Pièges** :
- Les noms d'instance (`movies:`, `series:`) doivent être **uniques sur
  tout le fichier**, pas seulement par app — deux `main:` → sync silencieux
  qui ne fait rien (`Duplicate instances` en debug).
- `minFormatScore` du profil est à `0` : une release au score CF négatif
  n'est pas récupérée. Si un contenu ne se télécharge jamais, vérifier son
  score dans Radarr (Activity → onglet du film) et au besoin baisser
  `minFormatScore` via l'UI.
