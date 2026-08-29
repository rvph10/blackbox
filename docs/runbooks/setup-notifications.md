# Runbook — notifications Discord (Layer 1)

Contexte et choix : [ADR-009](../adr/009-notifications-layer1.md).

## 1. Webhooks Discord

Server Settings → **Integrations** → **Webhooks** → **New Webhook**, un par
salon cible :
- Un webhook pour `#annonces` (contenu ajouté)
- Un webhook pour le salon admin (alertes techniques)

Copier l'URL de chaque webhook (`https://discord.com/api/webhooks/...`) —
ne jamais la committer dans le repo, traitée comme un secret.

## 2. Jellyfin → `#annonces` (nouveau contenu)

> **Ne pas utiliser la destination "Discord" native du plugin** : elle est
> buggée et Discord rejette son corps (`400`, `code 50109 – invalid JSON`),
> bug connu non corrigé
> ([jellyfin-plugin-webhook#369](https://github.com/jellyfin/jellyfin-plugin-webhook/issues/369)).
> On passe par une destination **Generic** + template Handlebars maison.

Dashboard → Plugins → **Webhook** :

1. Renseigner **Server URL** en haut de la page :
   `https://stream.blackbox.homes` (sinon pas d'affiche ni de lien dans
   l'embed).
2. **Add Generic Destination** :
   - **Webhook URL** : webhook `#annonces` (étape 1)
   - **Notification Type** : `Item Added` uniquement
   - **Item Types** : `Movies` + `Episodes` (décocher Seasons : sinon une
     saison entière = 1 notif « Saison » + N notifs « Épisode »)
   - **Add Request Header** : `Content-Type` = `application/json`
   - **Template** : coller le bloc ci-dessous
3. **Save.**

```handlebars
{
  {{#if_equals ItemType 'Episode'}}
  "content": "📺  **Nouvel épisode disponible !**",
  {{else}}
  "content": "🎬  **Nouveau film disponible !**",
  {{/if_equals}}
  "username": "BlackBox",
  "embeds": [
    {
      "color": 11164867,
      {{#if_equals ItemType 'Episode'}}
      "author": { "name": "{{json_encode SeriesName}}" },
      "title": "S{{SeasonNumber00}}E{{EpisodeNumber00}} · {{json_encode Name}}",
      {{else}}
      "title": "{{json_encode Name}}{{#if_exist Year}} ({{Year}}){{/if_exist}}",
      {{/if_equals}}
      "url": "{{ServerUrl}}/web/#/details?id={{ItemId}}&serverId={{ServerId}}",
      {{#if_exist Overview}}
      "description": "{{json_encode Overview}}",
      {{/if_exist}}
      "thumbnail": { "url": "{{ServerUrl}}/Items/{{#if_equals ItemType 'Episode'}}{{SeriesId}}{{else}}{{ItemId}}{{/if_equals}}/Images/Primary" },
      "footer": { "text": "Disponible maintenant sur BlackBox • stream.blackbox.homes" }
    }
  ]
}
```

**Règles du template (pièges rencontrés) :**
- `{{json_encode X}}` **échappe** le texte mais n'ajoute **pas** les
  guillemets → toujours écrire `"{{json_encode X}}"`.
- `json_encode` **plante sur une valeur nulle** → tout champ optionnel
  (`Overview`, `Year`) doit être sous `{{#if_exist}}`.
- `color` en **entier** (`11164867` = `#AA5CC3`), pas en chaîne hex.

**Vérification** :
```bash
ssh nucbox "cat ~/blackbox/prod/data/jellyfin/config/plugins/configurations/Jellyfin.Plugin.Webhook.xml"
```
Confirmer `EnableWebhook: true`, l'entrée sous `<GenericOptions>` (pas
`<DiscordOptions>`), le header `Content-Type`, et `<ServerUrl>` rempli.

**Test de bout en bout** (crée un faux film, déclenche un scan, nettoie) :
```bash
ssh nucbox
KEY=$(grep JELLYFIN_API_KEY ~/blackbox/bot/.env | cut -d= -f2)
mkdir -p "/mnt/nas-media/movies/Sintel (2010)"
docker exec jellyfin /usr/lib/jellyfin-ffmpeg/ffmpeg -loglevel error -f lavfi \
  -i color=c=teal:s=640x360:d=3 -y "/media/movies/Sintel (2010)/Sintel (2010).mp4"
curl -s -X POST "http://localhost:8096/Library/Refresh" -H "X-Emby-Token: $KEY" -w " %{http_code}\n"
# attendre ~2 min, surveiller :
docker logs --since 5m jellyfin 2>&1 | grep -i "Jellyfin.Plugin.Webhook"
#   → aucune ligne [WRN] BadRequest = OK, l'embed est parti dans #annonces
# nettoyage :
rm -rf "/mnt/nas-media/movies/Sintel (2010)"
curl -s -X POST "http://localhost:8096/Library/Refresh" -H "X-Emby-Token: $KEY" -w " %{http_code}\n"
```
`Sintel (2010)` est un court-métrage libre Blender (présent sur TMDb, donc
métadonnées résolues) — un faux titre sans correspondance TMDb serait
ignoré par le plugin (il attend des métadonnées qui n'arrivent jamais).

## 3. Gluetun → salon admin (santé VPN)

Pas d'intégration Discord native pour Gluetun — script dédié
(`infra/scripts/gluetun-healthcheck/`) :

- `check-gluetun.sh` : lit l'état de santé du conteneur
  (`docker inspect --format='{{.State.Health.Status}}' gluetun`), compare à
  un fichier d'état local, poste sur le webhook admin uniquement si l'état a
  changé depuis la dernière exécution (pas de spam à chaque exécution du
  timer)
- `.env` (à créer à partir de `.env.example`, jamais commité) : contient
  `ADMIN_ALERT_WEBHOOK_URL`
- `gluetun-healthcheck.service` + `gluetun-healthcheck.timer` : exécution
  toutes les 2 minutes via systemd

### Déploiement

```bash
# Script + config (utilisateur kong, pas de sudo nécessaire)
ssh nucbox "mkdir -p ~/blackbox/scripts/gluetun-healthcheck"
scp infra/scripts/gluetun-healthcheck/check-gluetun.sh nucbox:~/blackbox/scripts/gluetun-healthcheck/
ssh nucbox "chmod +x ~/blackbox/scripts/gluetun-healthcheck/check-gluetun.sh"

# .env avec le webhook admin — à créer manuellement sur le serveur, jamais
# depuis le repo (secret)

# Unités systemd (nécessite sudo, à lancer soi-même en interactif)
scp infra/scripts/gluetun-healthcheck/gluetun-healthcheck.service \
    infra/scripts/gluetun-healthcheck/gluetun-healthcheck.timer nucbox:~/
ssh nucbox '
sudo mv ~/gluetun-healthcheck.service ~/gluetun-healthcheck.timer /etc/systemd/system/ &&
sudo systemctl daemon-reload &&
sudo systemctl enable --now gluetun-healthcheck.timer &&
systemctl status gluetun-healthcheck.timer --no-pager
'
```

**Vérification** :
```bash
ssh nucbox "systemctl status gluetun-healthcheck.timer --no-pager"
ssh nucbox "cat ~/blackbox/scripts/gluetun-healthcheck/.last_state"
```
Le premier lancement poste toujours un message (aucun état précédent
enregistré = changement détecté) — normal, pas un bug.

## 4. Ce qui reste hors scope pour l'instant

- **ESP8266 (watchdog NucBox)** : même principe possible côté ESPHome
  (`http_request.post` vers le webhook admin), mis en pause volontairement,
  à reprendre plus tard.
- **Rich Presence "façon Spotify"** (voir ce que les autres regardent) :
  pas un chantier serveur, outils client à opt-in individuel
  (`jellyfin-rpc`, `jellyfin-discord-presence`) — à documenter dans
  `#accueil` quand on y reviendra.
- **Layer 2 (commandes de statut) et Layer 3 (bot actif : création de
  compte, gamification)** : pas commencés, voir
  [ADR-008](../adr/008-discord-community.md) et
  [ADR-009](../adr/009-notifications-layer1.md) pour le détail des
  fonctionnalités candidates déjà identifiées.
