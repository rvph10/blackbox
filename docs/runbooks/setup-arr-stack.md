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
| Quality Profile | — | `HD - 720p/1080p` (pas Ultra-HD, cohérent avec la stratégie VAAPI 1080p — ADR-006) |
| Minimum Availability | — | `Released` |

Clés API (Settings → General de chaque app, à utiliser pour Bazarr/Seerr) :
- Sonarr : `836e05333a32436394a73375b01d7ea1`
- Radarr : `cab7b0384dca4214939d159081851558`

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
