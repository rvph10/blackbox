# Runbook — bot Discord

Contexte : [ADR-010](../adr/010-bot-layer2.md) (Layer 2, lecture seule) puis
[ADR-021](../adr/021-bot-layer3.md) (Layer 3 : provisioning de comptes,
gamification, classement).

## 1. Application Discord

- https://discord.com/developers/applications → l'app **BlackBox Bot**
- Onglet **Bot** :
  - **Reset Token** si besoin (affiché une fois)
  - **activer « Server Members Intent »** (obligatoire pour `on_member_join`)
- Ré-inviter le bot avec la permission **Manage Roles** en plus :

```
https://discord.com/api/oauth2/authorize?client_id=1542994856333283378&scope=bot+applications.commands&permissions=268454912
```

`268454912` = Manage Roles + Voir les salons + Envoyer des messages +
Intégrer des liens.

- Serveur → Paramètres → Rôles : le rôle **BlackBox Bot** ne doit pas être
  tout en bas (il crée et attribue les rôles de palier, positionnés sous
  lui).
- Créer le rôle **`SysAdmin`** (ou vérifier qu'il existe) — seul rôle
  autorisé pour les commandes admin (repli : permission Administrator).
- Créer le salon **`#salle-de-projection`** (ADR-022) : `@everyone` →
  *Envoyer des messages* refusé, le bot y poste et édite un message unique.

## 2. Clés API

| Clé | Où | Usage |
|---|---|---|
| Jellyfin | Dashboard → Advanced → API Keys | lecture **et écriture** (création de comptes, policy, mot de passe, désactivation) — les clés Jellyfin ne sont pas scopables |
| Jellystat | Jellystat → Settings → API Keys | stats de visionnage (paliers, classement) |

## 3. Jellyseerr

Settings → Users → **cocher « Enable new Jellyfin Sign-In »**. Les comptes
créés par le bot s'y connecteront avec leurs identifiants Jellyfin, le
compte Seerr se crée alors automatiquement (quota illimité configuré).

## 4. Secrets

```bash
ssh nucbox "cat > ~/blackbox/bot/.env <<'EOF'
DISCORD_BOT_TOKEN=<token>
DISCORD_GUILD_ID=<id du serveur (mode dev → clic droit → Copier l'identifiant)>
JELLYFIN_URL=http://jellyfin:8096
JELLYFIN_API_KEY=<clé Jellyfin>
JELLYSTAT_URL=http://jellystat:3000
JELLYSTAT_API_KEY=<clé Jellystat>
ADMIN_ALERT_WEBHOOK_URL=<même webhook admin que gluetun-healthcheck / backup>
PUBLIC_STREAM_URL=https://stream.blackbox.homes
PUBLIC_REQUESTS_URL=https://requests.blackbox.homes
SCOREBOARD_CHANNEL_ID=1543646643629461628
NOW_PLAYING_CHANNEL_ID=1543666526400422089
WELCOME_CHANNEL_ID=1542926415484166194
CONTENT_CHANNEL_ID=1542926415484166194
SEERR_WEBHOOK_SECRET=<openssl rand -hex 24>
SEERR_URL=http://seerr:5055
SEERR_API_KEY=<Jellyseerr → Settings → General → API Key>
EOF
chmod 600 ~/blackbox/bot/.env"
```

## 5. Déploiement

Automatisé (GitHub Actions, [ADR-013](../adr/013-cicd-github-actions.md)) :
push sur `main` touchant `bot/` → lint + tests → image
`ghcr.io/rvph10/blackbox-bot` → GHCR → le runner NucBox fait
`docker compose pull bot && docker compose up -d bot`.

Le compose monte `./data/bot:/data` (SQLite du mapping, créé au premier
run). Ce dossier est **dans le périmètre backup restic**.

Déploiement manuel de secours :
```bash
ssh nucbox "cd ~/blackbox/prod && docker compose pull bot && docker compose up -d bot"
```

## 6. Vérification

```bash
ssh nucbox "docker logs bot --tail 40"
```

- `Connecté en tant que BlackBox Bot#xxxx` + alerte `🟢 Bot Blackbox démarré`
  dans le salon admin
- Rôles créés automatiquement : `Figurant`, `Second rôle`, `Premier rôle`,
  `Réalisateur`, `Tête d'affiche`
- Tester `/status`, `/streams`, `/messtats`, `/roulette`
- Faire rejoindre un compte de test → compte Jellyfin créé + MP reçu +
  alerte admin

## 7. Amorçage (comptes existants)

Le trigger est `on_member_join` : les membres déjà présents ne sont pas
provisionnés automatiquement.

- `/creer-compte @membre` — crée le compte (MP + alerte)
- `/lier @membre <user_jellyfin>` — mappe un compte Jellyfin **déjà
  existant** sans en recréer un

## 8. Commandes

| Commande | Accès | Comportement |
|---|---|---|
| `/status` | tous | Jellyfin en ligne / hors ligne + nb de lectures en cours |
| `/moncompte` | tous | rappel de l'identifiant ; `reinitialiser:True` → nouveau mot de passe en MP |
| `/messtats` | tous | heures cumulées, palier, prochain palier, genre préféré, rang |
| `/roulette` | tous | un film non vu au hasard |
| `/creer-compte @m` | SysAdmin | provisioning manuel |
| `/lier @m <user>` | SysAdmin | mappe un compte Jellyfin existant |
| `/desactiver <identifiant>` | SysAdmin | `IsDisabled: true` côté Jellyfin + note. `identifiant` = nom d'utilisateur Jellyfin **ou** ID Discord (marche même si le membre a quitté le serveur) |
| `/reactiver <identifiant>` | SysAdmin | `IsDisabled: false` (miroir de `/desactiver`) |
| `/supprimer <identifiant> <confirmation>` | SysAdmin | **suppression définitive** du compte Jellyfin (`DELETE /Users`) + du mapping en base. `confirmation` doit être le nom d'utilisateur Jellyfin exact. Le compte Jellyseerr éventuel reste à retirer à la main. |

## 9. Tâches de fond

- **Panneau « en direct »** — toutes les 45 s : `GET /Sessions`, édition
  d'un message unique dans `#salle-de-projection` (qui regarde quoi,
  progression, transcodage) + statut du bot (« Regarde : N flux »). ADR-022.
- **Recalcul des paliers** — tous les jours à 05h00 (Europe/Brussels) :
  lit Jellystat (`getAllUserActivity`), attribue le rôle de palier.
- **Classement** — vérifié tous les jours à 19h00, posté dans `#classement`
  si ≥ 15 jours depuis le dernier (état en base `meta`).

## 9bis. Annonces « nouveau contenu » (Jellyseerr → bot)

Le bot ouvre un écouteur HTTP interne sur `:8000` (jamais publié — joignable
seulement par `seerr → bot:8000` sur le réseau Docker).

Config Jellyseerr (Settings → Notifications → **Webhook**) :
- **Webhook URL** : `http://bot:8000/jellyseerr`
- **Authorization Header** : la valeur de `SEERR_WEBHOOK_SECRET`
- **Notification Types** : cocher **Media Available** uniquement
- **JSON Payload** : template minimal (`notification_type`, `subject`,
  `message`, `image`, `media_type`, `tmdbId`, `requestedBy_username`,
  `requestedBy_settings_discordId`)

Peut se faire via l'API : `POST /api/v1/settings/notifications/webhook`
puis `POST /api/v1/settings/notifications/webhook/test` (le bot répond en
postant `[OK] test reçu` dans le salon admin).

Le plugin Webhook de **Jellyfin** doit être **désactivé** (l'annonce ne
passe plus par lui).

## 10. Accueil des nouveaux (à l'arrivée)

À `on_member_join`, en plus du provisioning : message d'accueil **public**
dans le salon `WELCOME_CHANNEL_ID` (`#annonces`), qui pingue le nouvel
arrivant, avec un texte **aléatoire** (pool éditable dans
`bot/welcome_lines.py`) + la carte de bienvenue (avatar, **sans**
identifiants — ceux-là restent en MP). `/creer-compte` ne poste **pas** de
message public (le membre est déjà là depuis un moment).

## 11. Départ d'un membre

`on_member_remove` → alerte admin uniquement. Jamais de désactivation
automatique (ADR-021 : famille/amis, peut revenir). L'alerte contient le
nom d'utilisateur Jellyfin + l'ID Discord + les commandes prêtes à
copier : `/desactiver identifiant:<nom>` (le membre a déjà quitté, donc
`/desactiver` prend un identifiant texte, pas une mention) ou `/supprimer`
pour une suppression définitive.

## 12. Ce que le bot ne touche pas

Gluetun, les conteneurs, le NAS, les backups, Terraform, Tailscale,
CrowdSec. Périmètre : Discord + Jellyfin (comptes) + Jellystat (lecture).
