# ADR 006 — Transcodage matériel VAAPI validé sur le NucBox M6

**Statut :** Accepté
**Date :** 2026-08-27

## Contexte

Le brief (§4, §12) et l'audit (§3, §17) identifiaient le transcodage
matériel comme un risque non résolu : l'iGPU Radeon 760M du Ryzen 5 7640HS
(RDNA3, Phoenix/gfx1103) est concerné par des bugs VAAPI connus sur des
puces similaires. Sans transcodage matériel fonctionnel, la capacité réelle
du serveur tombe à ~3-4 flux transcodés en logiciel au lieu des 10 flux
visés.

## Test réalisé

Sur Ubuntu Server 26.04 LTS (kernel 7.0.0-30-generic, Mesa 26.0.8) :

1. Installation de `mesa-va-drivers`, `vainfo` et `ffmpeg`.
2. Ajout de l'utilisateur au groupe `video`/`render` — nécessaire, l'accès à
   `/dev/dri/renderD128` (device render, groupe `render`) est refusé par
   défaut.
3. `vainfo --display drm --device /dev/dri/renderD128` : driver `radeonsi`
   chargé sans erreur, profils supportés incluant H264 (decode + encode),
   HEVC Main/Main10 (decode + encode), VP9 (decode), AV1 (decode + encode).
4. Test de transcodage réel avec `ffmpeg` (pas seulement l'énumération de
   capacités de `vainfo`, qui peut passer même si le transcodage réel
   échoue) : decode H264 → encode HEVC via VAAPI sur une vidéo synthétique
   1280x720. Résultat : succès, ~23x la vitesse temps réel, fichier de
   sortie valide (vérifié via `ffprobe`).
5. Confirmation en conditions réelles via Jellyfin (conteneur Docker,
   `/dev/dri` passé avec les GID `video`/`render` de l'hôte via
   `group_add`) : lecture d'un fichier 1080p avec qualité forcée à la
   baisse dans le lecteur web — session marquée `Transcoding`, process
   `ffmpeg` du conteneur confirmé via `docker top` (`-hwaccel vaapi
   -codec:v:0 h264_vaapi -vf scale_vaapi=...`).
6. Test de charge (capacité concurrente) : plusieurs transcodages VAAPI
   identiques (1080p → 540p, downscale) lancés en parallèle en CLI, pour
   mesurer où le débit total passe sous le temps réel (1x — seuil où le
   streaming commencerait à ramer).

   | Flux simultanés | H264 (par flux) | HEVC (par flux) |
   |---|---|---|
   | 1 | 22.5x | 25.8x |
   | 8 | 2.89x | 3.33x |
   | 16 | 1.45x | 1.66x |
   | 20 | 1.16x | 1.33x |
   | 24 | 0.96x (sous le temps réel) | — |

   Le débit total plafonne à ~22.5x temps réel en H264, ~26x en HEVC,
   réparti équitablement entre les flux (pas d'effet de falaise, juste une
   dégradation linéaire). Le seuil de 1x tombe entre 20 et 24 flux
   simultanés selon le codec. Résultat pessimiste par construction (tous
   les flux transcodent en même temps sur le même fichier, alors que la
   stratégie retenue — §4 du brief — privilégie le direct play).

## Décision

Le transcodage matériel VAAPI est **validé** sur ce matériel avec cette
combinaison kernel/Mesa. Jellyfin sera configuré pour l'utiliser
(accélération matérielle AMD AMF/VAAPI dans les paramètres de lecture).

## Conséquences

- Le risque n°2 du projet (après le WoL) est levé : la capacité visée de
  10 flux simultanés avec transcodage à la volée reste réaliste, avec une
  marge confortable (seuil mesuré à 20+ flux transcodés simultanément avant
  de repasser sous le temps réel).
- Pour le déploiement Docker de Jellyfin : monter `/dev/dri/renderD128`
  dans le conteneur, et faire correspondre le GID du groupe `render` de
  l'hôte à l'intérieur du conteneur (ou lancer le conteneur avec ce groupe)
  pour que le process Jellyfin ait les mêmes droits d'accès que testé ici.
- ADR-002 (choix d'Ubuntu Server LTS + HWE) est confirmé a posteriori :
  l'objectif annoncé (garder un kernel/Mesa à jour avant le test VAAPI)
  s'est avéré payant, ce test aurait pu échouer sur une distribution avec
  un Mesa plus ancien.
- Le risque reste dépendant de la version de Mesa : une future mise à jour
  du kernel/Mesa via le canal HWE pourrait théoriquement réintroduire une
  régression. Pas d'action préventive nécessaire, mais à garder en tête si
  le transcodage matériel se met à échouer après une mise à jour système.
