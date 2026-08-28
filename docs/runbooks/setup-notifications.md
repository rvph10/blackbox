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

- Dashboard → Plugins → **Webhook** → ajouter une destination de type
  **Discord** (pas "Generic" — Generic exige un template JSON manuel ;
  Discord génère l'embed automatiquement, aucun template à écrire)
- URL : webhook `#annonces`
- Notification type : **Item Added** uniquement
- Movies + Episodes activés (Series/Seasons/Albums/Songs/Videos laissés
  tels quels par défaut, pas de filtrage supplémentaire nécessaire pour 10
  personnes)

**Erreur rencontrée** : la destination avait d'abord été créée en type
"Generic" avec un `Template` vide — Discord rejette un webhook sans
`content`/`embeds`, la notification échoue silencieusement. Vérifié
directement dans `Jellyfin.Plugin.Webhook.xml` (config sous `GenericOptions`
au lieu de `DiscordOptions`) et corrigé en recréant la destination avec le
bon type.

**Vérification** :
```bash
ssh nucbox "cat ~/blackbox/prod/data/jellyfin/config/plugins/configurations/Jellyfin.Plugin.Webhook.xml"
```
Confirmer `EnableWebhook: true` et la présence de l'entrée sous
`<DiscordOptions>`, pas `<GenericOptions>`.

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
