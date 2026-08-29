# ADR 011 — Backup restic : NAS local + Google Drive

**Statut :** Accepté — destination hors site remplacée par Backblaze B2
([ADR-017](017-backup-b2.md), 2026-08-29). Le reste (deux dépôts
indépendants, périmètre, passphrase, rétention, planification) tient.
**Date :** 2026-08-28

## Contexte

Aucune sauvegarde n'existait pour les configs des services applicatifs
(bases SQLite Sonarr/Radarr/Prowlarr/Bazarr/Seerr, config Jellyfin,
historique de visionnage, secrets `.env`) — un disque NucBox mort aurait
signifié tout reconfigurer de zéro. La médiathèque elle-même n'entre pas
dans ce périmètre : déjà protégée par le RAID1 du NAS et re-téléchargeable
via la suite *arr* (ADR-007) si besoin, pas économique à dupliquer.

## Deux dépôts restic indépendants, pas un seul répliqué

- **Local** : `/mnt/nas-media/backups/restic`, sur le NAS `dxp` via le
  partage NFS déjà monté (voir `setup-nas.md`)
- **Hors site** : Google Drive, via `rclone` (`rclone:gdrive:blackbox-backups`)

Deux dépôts séparés plutôt qu'un seul avec réplication : si l'un se
corrompt, l'autre reste intact et restaurable indépendamment. Respecte la
logique 3-2-1 (2 copies en plus des données live, 1 hors site).

## Google Drive comme destination hors site

Compte déjà possédé par l'utilisateur, aucun coût. Passé en revue avant
adoption : le point de friction connu de la communauté restic avec Google
Drive est le rate-limiting de l'API sur beaucoup de petits fichiers — non
bloquant ici car restic empaquette ses données en blocs (~65 Mio par
sauvegarde dans ce cas, configs uniquement, largement sous le quota gratuit
de 15 Go). À réévaluer vers Backblaze B2 si ça devient un problème en
pratique — changement possible sans perdre l'historique du dépôt local.

Authentification `rclone` faite via OAuth interactif (`rclone config`,
remote `gdrive`, type `drive`, scope `drive` complet) — étape qui devait
être faite par l'utilisateur lui-même (connexion à son propre compte
Google), pas automatisable.

## Passphrase restic : responsabilité explicite de l'utilisateur

Générée une fois (`openssl rand -base64 32`), stockée dans
`infra/scripts/backup/.env` sur le NucBox. **Point critique documenté
explicitement** : cette passphrase doit être conservée par l'utilisateur en
dehors du NucBox (gestionnaire de mots de passe) — si le NucBox meurt et
que la passphrase n'existe que dedans, les deux dépôts deviennent
illisibles, annulant tout l'intérêt du backup.

## Ce qui est sauvegardé

Configs applicatives uniquement, pas la médiathèque :
```
prod/data/{jellyfin,gluetun,qbittorrent,prowlarr,sonarr,radarr,bazarr,jellyseerr}/config (ou dossier service)
prod/.env, bot/.env, scripts/gluetun-healthcheck/.env
```

**Exclusion** : `jellyfin/config/temp/` — fichiers temporaires
d'extraction de bibliothèques natives (`mm-exhelper.so.*`), créés par
Jellyfin avec des permissions root, illisibles par l'utilisateur `kong` et
sans valeur à restaurer (recréés automatiquement au démarrage). Découvert
au premier test réel : `restic backup` retournait un code de sortie 3
("some source files could not be read") malgré un snapshot valide créé —
corrigé en excluant ce dossier plutôt qu'en ignorant l'erreur.

## Planification et rétention

- **Timer systemd** quotidien, 4h du matin (`blackbox-backup.timer`)
- **Rétention** : `--keep-daily 7 --keep-weekly 4 --keep-monthly 6`,
  élagage automatique après chaque sauvegarde réussie (`forget --prune`)
- **Alertes** : webhook Discord admin déjà utilisé pour Gluetun
  (ADR-009), mais **uniquement en cas d'échec** — silence sinon, cohérent
  avec la volonté de ne pas noyer le salon admin sous des messages de
  routine
- Journal détaillé de chaque exécution dans
  `infra/scripts/backup/last_run.log` (écrasé à chaque run) pour
  diagnostiquer sans devoir relancer en mode debug

## Conséquences

- `infra/scripts/backup/` ajouté au repo (script, `.env.example`, unités
  systemd), déployé sur le NucBox
  (`~/blackbox/scripts/backup/`)
- Testé en conditions réelles : premier run en échec (permissions sur les
  fichiers temp Jellyfin) diagnostiqué et corrigé, deuxième run propre sur
  les deux dépôts (snapshots confirmés via `restic snapshots`), timer
  vérifié actif (`systemctl list-timers`)
- Détail de déploiement dans
  [docs/runbooks/setup-backup.md](../runbooks/setup-backup.md)
