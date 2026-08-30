#!/usr/bin/env bash
# Sauvegarde restic des configs applicatives (pas la médiathèque, protégée
# par le RAID1 du NAS et re-téléchargeable via la suite *arr*) vers deux
# dépôts indépendants : NAS local + Backblaze B2 (natif restic, plus de
# rclone). Voir docs/adr/011-backup-restic-rclone.md et
# docs/adr/017-backup-b2.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
[ -f "$ENV_FILE" ] && source "$ENV_FILE"

: "${RESTIC_PASSWORD:?RESTIC_PASSWORD manquant (voir .env.example)}"
: "${ADMIN_ALERT_WEBHOOK_URL:?ADMIN_ALERT_WEBHOOK_URL manquant}"
: "${B2_ACCOUNT_ID:?B2_ACCOUNT_ID manquant (voir .env.example)}"
: "${B2_ACCOUNT_KEY:?B2_ACCOUNT_KEY manquant (voir .env.example)}"
export RESTIC_PASSWORD B2_ACCOUNT_ID B2_ACCOUNT_KEY

REPO_LOCAL="${REPO_LOCAL:-/mnt/nas-media/backups/restic}"
REPO_REMOTE="${REPO_REMOTE:?REPO_REMOTE manquant (ex: b2:blackbox-backups:restic)}"
LOG_FILE="${LOG_FILE:-$SCRIPT_DIR/last_run.log}"
: > "$LOG_FILE"

SOURCES=(
  "$HOME/blackbox/prod/data/jellyfin/config"
  "$HOME/blackbox/prod/data/gluetun"
  "$HOME/blackbox/prod/data/qbittorrent/config"
  "$HOME/blackbox/prod/data/prowlarr/config"
  "$HOME/blackbox/prod/data/sonarr/config"
  "$HOME/blackbox/prod/data/radarr/config"
  "$HOME/blackbox/prod/data/bazarr/config"
  "$HOME/blackbox/prod/data/jellyseerr/config"
  # Bot Discord Layer 3 : mapping Discord <-> Jellyfin + état du cycle
  # (SQLite), pas trivialement régénérable. Voir ADR-021.
  "$HOME/blackbox/prod/data/bot"
  # CrowdSec et Traefik ne sont volontairement pas sauvegardés : le conteneur
  # CrowdSec tourne en root (fichiers illisibles par kong) et tout son état
  # est régénérable — collections retéléchargées via COLLECTIONS, credentials
  # recréés par cscli au boot, bouncer via `cscli bouncers add`. Voir
  # docs/adr/017-backup-b2.md et docs/runbooks/setup-crowdsec.md.
  "$HOME/blackbox/prod/.env"
  "$HOME/blackbox/bot/.env"
  "$HOME/blackbox/scripts/gluetun-healthcheck/.env"
)

alert() {
  curl -fsS -H "Content-Type: application/json" \
    -d "$(printf '{"content": "%s"}' "$1")" \
    "$ADMIN_ALERT_WEBHOOK_URL" > /dev/null || true
}

# Ne garder que les sources qui existent : restic renvoie un code non nul si
# un chemin listé est absent (déjà rencontré avec jellyfin/config/temp,
# ADR-011). Une source attendue mais manquante est signalée sans faire
# échouer toute la sauvegarde.
PRESENT=()
for src in "${SOURCES[@]}"; do
  if [ -e "$src" ]; then
    PRESENT+=("$src")
  else
    alert "[INFO] Backup restic : source absente, ignorée — $src"
  fi
done
SOURCES=("${PRESENT[@]}")

run_backup() {
  local repo="$1" label="$2"

  if ! restic -r "$repo" snapshots >> "$LOG_FILE" 2>&1; then
    if ! restic -r "$repo" init >> "$LOG_FILE" 2>&1; then
      alert "[ALERTE] Backup restic ($label) : échec d'initialisation du dépôt."
      return 1
    fi
  fi

  local rc=0
  restic -r "$repo" backup "${SOURCES[@]}" --tag blackbox \
    --exclude "$HOME/blackbox/prod/data/jellyfin/config/temp" \
    >> "$LOG_FILE" 2>&1 || rc=$?
  # restic : 0 = OK, 3 = snapshot créé mais des fichiers étaient illisibles
  # (partiel, non bloquant — on alerte pour investiguer), autre = échec réel.
  if [ "$rc" -eq 3 ]; then
    alert "[ALERTE] Backup restic ($label) : snapshot créé, fichiers illisibles ignorés (code 3), voir $LOG_FILE."
  elif [ "$rc" -ne 0 ]; then
    alert "[ALERTE] Backup restic ($label) a échoué (code $rc), voir $LOG_FILE."
    return 1
  fi

  restic -r "$repo" forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune >> "$LOG_FILE" 2>&1 || \
    alert "[ALERTE] Backup restic ($label) : l'élagage (forget/prune) a échoué, les snapshots restent valides."
}

FAILED=0
run_backup "$REPO_LOCAL" "NAS local" || FAILED=1
run_backup "$REPO_REMOTE" "Backblaze B2" || FAILED=1

exit $FAILED
