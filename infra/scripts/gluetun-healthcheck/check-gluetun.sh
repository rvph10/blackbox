#!/usr/bin/env bash
# Vérifie l'état de santé du conteneur gluetun (healthcheck Docker natif) et
# poste une alerte sur le webhook Discord admin uniquement si l'état change
# (pas à chaque exécution) — voir docs/adr/008-discord-community.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
[ -f "$ENV_FILE" ] && source "$ENV_FILE"

if [ -z "${ADMIN_ALERT_WEBHOOK_URL:-}" ]; then
  echo "ADMIN_ALERT_WEBHOOK_URL non défini (voir .env.example)" >&2
  exit 1
fi

STATE_FILE="${STATE_FILE:-$SCRIPT_DIR/.last_state}"
mkdir -p "$(dirname "$STATE_FILE")"

CURRENT="$(docker inspect --format='{{.State.Health.Status}}' gluetun 2>/dev/null || echo "unreachable")"
PREVIOUS="$(cat "$STATE_FILE" 2>/dev/null || echo "")"

if [ "$CURRENT" = "$PREVIOUS" ]; then
  exit 0
fi

case "$CURRENT" in
  healthy)
    MESSAGE="[OK] Gluetun (VPN) est de nouveau opérationnel."
    ;;
  unhealthy)
    MESSAGE="[ALERTE] Gluetun (VPN) est en échec — qBittorrent n'a plus de connectivité (kill switch actif, pas de fuite possible mais téléchargements à l'arrêt)."
    ;;
  unreachable)
    MESSAGE="[ALERTE] Conteneur gluetun injoignable (arrêté ou absent)."
    ;;
  *)
    MESSAGE="[INFO] Gluetun (VPN) : état \`$CURRENT\`."
    ;;
esac

curl -fsS -H "Content-Type: application/json" \
  -d "$(printf '{"content": "%s"}' "$MESSAGE")" \
  "$ADMIN_ALERT_WEBHOOK_URL" > /dev/null

echo "$CURRENT" > "$STATE_FILE"
