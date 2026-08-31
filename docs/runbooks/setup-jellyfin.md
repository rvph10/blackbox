# Runbook — configuration Jellyfin (post-installation)

Réglages et plugins appliqués sur le premier déploiement Jellyfin
(`infra/docker/prod/`), au-delà du wizard d'installation standard. À
rejouer après une réinstallation ou pour vérifier l'état attendu.

## Identité du serveur

- **Nom du serveur** : `BlackBox`
- **Langue des métadonnées** : français (`fr`)
- **Pays des métadonnées** : Belgique (`BE`)
- **Thème** : JellyFlix (via Skin Manager, voir plugins ci-dessous)
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

## Repositories de plugins

**Dashboard → Plugins → Repositories → Add**

| Nom | URL |
|---|---|
| Skin Manager | `https://raw.githubusercontent.com/danieladov/JellyfinPluginManifest/master/manifest.json` |
| File Transformation | `https://www.iamparadox.dev/jellyfin/plugins/manifest.json` |
| Jellyfin Enhanced | `https://raw.githubusercontent.com/n00bcodr/jellyfin-plugins/main/10.11/manifest.json` (URL spécifique à la version 10.11.x du serveur) |
| Intro Skipper | `https://intro-skipper.org/manifest.json` |
| Logo Swap | `https://raw.githubusercontent.com/NewsGuyTor/LogoSwap/main/manifest.json` |

(Webhook et Playback Reporting sont officiels, déjà dans le repository
`Jellyfin Stable` par défaut — pas de repo à ajouter.)

## Plugins installés

| Plugin | Version | Rôle | Action après install |
|---|---|---|---|
| File Transformation | 2.5.11.0 | Dépendance technique — permet aux autres plugins d'injecter du JS/CSS dans jellyfin-web sans patcher les fichiers | Aucune, doit juste rester actif |
| Skin Manager | 2.0.2.0 | Gestionnaire de thèmes | Thème **Jellyfish** sélectionné — voir « Thème / apparence » ci-dessous |
| Jellyfin Tweaks | 4.0.0.0 | Force des réglages d'affichage client (localStorage) pour tous les appareils | `EnableBackdropsByDefault` + `EnableDetailsBannerByDefault` = **on** (requis par le thème Jellyfish) |
| Intro Skipper | 1.10.11.23 | Détecte et skip les intros/génériques de séries | Nécessite une analyse (`Analyze episodes`) une fois du contenu série présent — rien à faire tant que la bibliothèque est vide |
| Jellyfin Enhanced | 12.5.0.0 | Raccourcis clavier, styles sous-titres, intégration Jellyseerr (auto-request), etc. | Voir réglages détaillés ci-dessous |
| Playback Reporting | 17.0.0.0 | Statistiques de lecture | Passif, rien à configurer. Piste : remplacer/compléter Jellystat pour le watcher de seuil (§4 du brief) une fois assez de données |
| LogoSwap | 1.5.0.0 | Remplacement du logo Jellyfin par un logo perso | Pas encore utilisé (pas de logo Blackbox prêt) |
| Webhook | 21.0.0.0 | Envoie des notifications (nouveau contenu, lecture démarrée...) vers une URL externe | Pas encore configuré — cible prévue : le futur bot Discord (§8 du brief) |

### Réglages Jellyfin Enhanced appliqués

Activés : `AutoPause`, `AutoResume`, `RandomButton`, `PauseScreen`,
`AutoSkipIntro`/`AutoSkipOutro`.

Désactivés : `QualityTagsEnabled` **et** `RatingTagsEnabled` — les badges
sur les affiches chargeaient l'interface (choix esthétique, 2026-08-31).
Pour les réactiver : Dashboard → Plugins → Jellyfin Enhanced → Tags. Après
un changement de ces réglages, bumper `ClearLocalStorageTimestamp` (bouton
« clear localStorage on all clients » du plugin) sinon les anciens badges
restent en cache navigateur. `AutoPip` désactivé (optionnel selon usage).

Police de sous-titres : Noto Sans (meilleure couverture des caractères
accentués/non-latins que la police par défaut).

## Thème / apparence

Thème **Jellyfish** ([n00bcodr/Jellyfish](https://github.com/n00bcodr/Jellyfish)),
appliqué en CSS personnalisé (Dashboard → Général → CSS personnalisé, =
`branding.xml`). **Épinglé sur un commit** pour éviter qu'une mise à jour
amont casse l'UI :

```css
@import url(https://cdn.jsdelivr.net/gh/n00bcodr/Jellyfish@9735998467cb492e14b6404114e08eca638a90cc/theme.css);
@import url(https://cdn.jsdelivr.net/gh/n00bcodr/Jellyfish@9735998467cb492e14b6404114e08eca638a90cc/10.11_fixes.css);
```

Le second import corrige des soucis d'alignement propres à Jellyfin 10.11.
Skin Manager pointe sur le même contenu (cohérence, pas de clobber).

Le thème a besoin de **Backdrops** + **Details Banner** activés côté
affichage — forcés pour tous les appareils par le plugin **Jellyfin
Tweaks** (pas un réglage serveur, c'est du localStorage client).

Pour changer de version : mettre à jour le hash de commit dans les deux
`@import` (via l'API : `POST /System/Configuration/branding` avec
`X-Emby-Token`), puis purger le cache Cloudflare de `stream.blackbox.homes`
et vider les données de site du navigateur une fois (service worker).

Ancien thème : Ultrachromic / Monochromic (CTalvio) — retiré le
2026-08-31, jugé trop plat.

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
