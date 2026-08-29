# ADR 017 — Backup hors site : Backblaze B2 remplace Google Drive

**Statut :** Accepté — en production depuis le 2026-08-29
**Remplace :** la destination hors site de [ADR-011](011-backup-restic-rclone.md)
(le reste d'ADR-011 tient : deux dépôts indépendants, périmètre, passphrase,
rétention, planification).

## Contexte

Le premier test de restauration à blanc (2026-08-29) a montré deux choses :

1. **Le dépôt NAS local fonctionne parfaitement** — `restic check --read-data`
   sans erreur, restauration complète, toutes les bases SQLite restaurées
   passent `PRAGMA integrity_check`, secrets intègres. La moitié locale du
   point ouvert d'ADR-011 est levée.
2. **Le dépôt Google Drive était figé depuis 2 jours.** Le run quotidien du
   29/08 04:00 a écrit sur le NAS puis a bouclé 16 minutes sur des erreurs
   `403 RATE_LIMIT_EXCEEDED` de l'API Drive avant `Fatal: unable to save
   snapshot`.

Cause : `rclone config` avec `client_id`/`client_secret` vides (ce que le
runbook indiquait) fait utiliser **le client OAuth intégré de rclone,
partagé par tous ses utilisateurs dans le monde** (`project_number
202264815644` dans les logs d'erreur). Ce quota commun est régulièrement
saturé — indépendant du volume qu'on pousse (130 Mio ici). Pas contournable
par du tuning : c'est une ressource partagée globale.

ADR-011 avait anticipé le principe (« rate-limiting connu... à réévaluer
vers Backblaze B2 si ça devient un problème en pratique »). C'est le cas.

## Décision : Backblaze B2, backend natif restic

- restic parle B2 **directement** (`b2:<bucket>:<chemin>`), **plus de
  rclone** dans le chemin hors site. Une couche en moins, et le backend B2
  est l'un des plus éprouvés de restic.
- Offre gratuite B2 : 10 Go de stockage, 1 Go/jour de download — le dépôt
  fait ~130 Mio, marge énorme et durable.
- Clé d'application **restreinte au seul bucket de backup** (`keyID` →
  `B2_ACCOUNT_ID`, `applicationKey` → `B2_ACCOUNT_KEY` dans le `.env` du
  script, jamais dans Git).
- Le bucket doit être créé à la main (restic ne le crée pas, et une clé
  restreinte ne peut pas lister les buckets).

Écarté : créer son propre projet Google Cloud + client OAuth. Ça résout le
quota partagé mais ajoute l'écran de consentement Google en mode « test »
qui fait expirer le refresh token tous les 7 jours — friction permanente
pour un cron.

## Migration

Nouveau dépôt B2 initialisé de zéro (`restic init` au premier run). Aucun
historique à migrer : le dépôt Google Drive n'avait que 2 snapshots de test
et le dépôt **NAS local garde tout l'historique** (dépôts indépendants,
c'est le principe d'ADR-011). L'ancien remote `gdrive` peut être purgé
(`rclone purge gdrive:blackbox-backups`) et `rclone` désinstallé — il ne
sert plus à rien (retiré du rôle Ansible `base`).

## Périmètre : CrowdSec et Traefik volontairement exclus

Tentative initiale d'ajouter `prod/data/crowdsec/config` et
`prod/traefik/lapi-key` aux sources, abandonnée au premier run réel : le
conteneur CrowdSec tourne en **root**, son arborescence `config/hub/` et
ses `*_credentials.yaml` sont illisibles par `kong` → `restic backup` en
code 3 à chaque passage. Or ce contenu est **entièrement régénérable** :
- `hub/` = les collections déclarées dans `COLLECTIONS`, retéléchargées au
  démarrage
- `local_api_credentials.yaml` / `online_api_credentials.yaml` = recréés par
  `cscli` au boot
- la clé du bouncer Traefik = inutile sans la DB CrowdSec (non sauvegardée),
  refaite via `cscli bouncers add` à la restauration (runbook `setup-crowdsec.md`)

Rien d'unique à sauvegarder. Le `acquis.yaml` et la config Traefik sont
déjà dans Git et déployés par Ansible.

## Robustesse du script

- Filtre des sources inexistantes (alerte `[INFO]`, pas d'échec) — évite le
  code non nul de restic sur un chemin absent, même classe de bug que le
  `jellyfin/config/temp` d'ADR-011.
- `restic backup` code 3 (« snapshot créé mais fichiers illisibles »)
  traité comme **non bloquant + alerte Discord** plutôt que comme un échec :
  mieux vaut un snapshot amputé de 2 fichiers qu'aucun snapshot, et l'alerte
  quotidienne pousse à investiguer.

## Conséquences

- `infra/scripts/backup/backup.sh` : `b2:` au lieu de `rclone:`, export
  `B2_ACCOUNT_ID`/`B2_ACCOUNT_KEY`, filtre des sources présentes, code 3
  de restic non bloquant, `.env` vérifie les nouvelles variables
- `infra/scripts/backup/.env.example` : `B2_ACCOUNT_ID`, `B2_ACCOUNT_KEY`,
  `REPO_REMOTE=b2:...`
- Rôle Ansible `base` : `rclone` retiré (plus utilisé)
- Runbook `setup-backup.md` §1 réécrit (bucket + clé B2 au lieu de rclone)
- Restauration à blanc **validée** (2026-08-29) : dépôt local (intégrité
  `--read-data`, bases SQLite, secrets) ET dépôt B2 (`restic init`, premier
  snapshot 145 Mio, `check --read-data` sans erreur). Clé restreinte au
  bucket : aucun souci `b2_list_buckets` avec le backend natif restic.
  Point ouvert d'ADR-011 clos.
