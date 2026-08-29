#!/usr/bin/env bash
# Autorégulation capacité (disque NAS) et bande passante (débit montant
# streaming Jellyfin) — voir docs/adr/019-autoregulation-capacite-bande-passante.md.
#
# Évalue un niveau OK / WARN / CRIT à chaque passage et n'agit qu'au
# changement de niveau (fichier d'état, comme gluetun-healthcheck / ADR-009) :
#   WARN -> alerte Discord admin
#   CRIT -> + limites alternatives qBittorrent (bride le seeding) + message communautaire
#   retour OK -> désactive les limites alternatives + alerte "retour à la normale"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
[ -f "$ENV_FILE" ] && source "$ENV_FILE"

: "${ADMIN_ALERT_WEBHOOK_URL:?ADMIN_ALERT_WEBHOOK_URL manquant (voir .env.example)}"
: "${JELLYFIN_API_KEY:?JELLYFIN_API_KEY manquant (voir .env.example)}"

JELLYFIN_URL="${JELLYFIN_URL:-http://localhost:8096}"
MEDIA_MOUNT="${MEDIA_MOUNT:-/mnt/nas-media}"
DISK_WARN_PCT="${DISK_WARN_PCT:-85}"
DISK_CRIT_PCT="${DISK_CRIT_PCT:-92}"
UPLOAD_WARN_MBPS="${UPLOAD_WARN_MBPS:-14}"
UPLOAD_CRIT_MBPS="${UPLOAD_CRIT_MBPS:-17}"
QBT_URL="${QBT_URL:-http://localhost:8080}"
QBT_USER="${QBT_USER:-}"
QBT_PASS="${QBT_PASS:-}"
COMMUNITY_WEBHOOK_URL="${COMMUNITY_WEBHOOK_URL:-}"
STATE_FILE="${STATE_FILE:-$SCRIPT_DIR/.last_state}"

alert() {
  curl -fsS -H "Content-Type: application/json" \
    -d "$(printf '{"content": "%s"}' "$1")" "$ADMIN_ALERT_WEBHOOK_URL" > /dev/null || true
}

community() {
  [ -n "$COMMUNITY_WEBHOOK_URL" ] || return 0
  curl -fsS -H "Content-Type: application/json" \
    -d "$(printf '{"content": "%s"}' "$1")" "$COMMUNITY_WEBHOOK_URL" > /dev/null || true
}

# --- Mesure disque ---------------------------------------------------------
DISK_PCT="$(df --output=pcent "$MEDIA_MOUNT" 2>/dev/null | tail -1 | tr -dc '0-9')"
DISK_PCT="${DISK_PCT:-0}"

# --- Mesure débit montant streaming (somme des bitrates Jellyfin actifs) ---
UPLOAD_MBPS=0
SESSIONS_JSON="$(curl -fsS -H "X-Emby-Token: $JELLYFIN_API_KEY" \
  "$JELLYFIN_URL/Sessions" 2>/dev/null || echo '[]')"
UPLOAD_BPS="$(printf '%s' "$SESSIONS_JSON" | jq '[.[]
  | select(.NowPlayingItem != null and .PlayState.IsPaused != true)
  | (.TranscodingInfo.Bitrate // .NowPlayingItem.Bitrate // 0)] | add // 0' 2>/dev/null || echo 0)"
if [ "${UPLOAD_BPS:-0}" -gt 0 ] 2>/dev/null; then
  UPLOAD_MBPS=$(( UPLOAD_BPS / 1000000 ))
fi

# --- Niveau --------------------------------------------------------------
LEVEL=OK
if [ "$DISK_PCT" -ge "$DISK_WARN_PCT" ] || [ "$UPLOAD_MBPS" -ge "$UPLOAD_WARN_MBPS" ]; then
  LEVEL=WARN
fi
if [ "$DISK_PCT" -ge "$DISK_CRIT_PCT" ] || [ "$UPLOAD_MBPS" -ge "$UPLOAD_CRIT_MBPS" ]; then
  LEVEL=CRIT
fi

PREVIOUS="$(cat "$STATE_FILE" 2>/dev/null || echo "OK")"
[ "$LEVEL" = "$PREVIOUS" ] && exit 0

DETAIL="disque ${DISK_PCT}% (seuils ${DISK_WARN_PCT}/${DISK_CRIT_PCT}), montant streaming ~${UPLOAD_MBPS} Mbit/s (seuils ${UPLOAD_WARN_MBPS}/${UPLOAD_CRIT_MBPS})"

# --- Bascule des limites alternatives qBittorrent ------------------------
# Nécessite que la limite alternative d'upload soit configurée dans
# qBittorrent (Options -> Vitesse -> Débits alternatifs). $1 = on|off
qbt_alt_limits() {
  local want="$1" jar
  [ -n "$QBT_USER" ] && [ -n "$QBT_PASS" ] || { alert "[INFO] capacity-watcher : QBT_USER/QBT_PASS non renseignés, bascule qBittorrent ignorée."; return 0; }
  jar="$(mktemp)"
  curl -fsS -c "$jar" --data-urlencode "username=$QBT_USER" --data-urlencode "password=$QBT_PASS" \
    "$QBT_URL/api/v2/auth/login" > /dev/null 2>&1 || true
  # Le corps de /auth/login est vide sur certaines versions : on valide la
  # session en interrogeant un endpoint authentifié plutôt que le corps.
  local mode
  mode="$(curl -fsS -b "$jar" "$QBT_URL/api/v2/transfer/speedLimitsMode" 2>/dev/null || echo "")"
  if [ "$mode" != "0" ] && [ "$mode" != "1" ]; then
    rm -f "$jar"; alert "[ALERTE] capacity-watcher : authentification qBittorrent échouée."; return 1
  fi
  if { [ "$want" = "on" ] && [ "$mode" != "1" ]; } || { [ "$want" = "off" ] && [ "$mode" = "1" ]; }; then
    curl -fsS -b "$jar" -X POST "$QBT_URL/api/v2/transfer/toggleSpeedLimitsMode" > /dev/null || true
  fi
  rm -f "$jar"
}

case "$LEVEL" in
  WARN)
    alert "[WARN] Capacité/bande passante — $DETAIL. Surveillance renforcée, pas d'action automatique."
    ;;
  CRIT)
    qbt_alt_limits on || true
    alert "[ALERTE] Capacité/bande passante CRITIQUE — $DETAIL. Limites alternatives qBittorrent activées (seeding bridé)."
    community "Le serveur est très sollicité en ce moment, la lecture peut être un peu plus lente que d'habitude. Ça se régule tout seul, merci de votre patience."
    ;;
  OK)
    qbt_alt_limits off || true
    alert "[OK] Capacité/bande passante revenue à la normale — $DETAIL. Limites alternatives qBittorrent désactivées."
    ;;
esac

echo "$LEVEL" > "$STATE_FILE"
