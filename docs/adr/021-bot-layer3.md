# ADR 021 — Bot Discord Layer 3 : provisioning de comptes + gamification

**Statut :** Accepté — 2026-08-30

**Suit :** [ADR-010](010-bot-layer2.md) (Layer 2, lecture seule). Le bot
cesse d'être sans état et sans action : il crée des comptes Jellyfin,
attribue des rôles Discord, tient un classement. Toujours **aucun accès**
à Gluetun, aux conteneurs, au NAS, aux backups.

## Contexte

ADR-008 avait acté le principe : création de compte automatisée à
l'arrivée sur le Discord + gamification par temps de visionnage, reportées
au bot. Layer 2 (`/status`, `/streams`) est en prod depuis ADR-010. Layer 3
est le dernier gros morceau fonctionnel.

Le serveur est familial (famille + amis, ~10 personnes). Le propriétaire
assume un modèle « confiance par défaut » : compte créé dès l'arrivée sur
le Discord, les règles ne sont qu'un garde-fou.

## Décisions

### Provisioning

| Sujet | Décision |
|---|---|
| Déclencheur | `on_member_join` — compte créé dès l'arrivée (intent privilégié **Server Members**) |
| Compte Jellyfin | créé par API (`POST /Users/New`), policy appliquée (pas admin, 2 bibliothèques, téléchargement + accès distant ON, **3 flux simultanés**, pas de suppression de contenu) |
| Nom d'utilisateur | pseudo Discord nettoyé (`[a-z0-9]`), suffixe numérique si collision ; nom affiché stocké en `note` |
| Mot de passe | 20 caractères aléatoires (`secrets`), **jamais stocké**, envoyé une seule fois en MP |
| Livraison | MP au membre (identifiants + `stream.` / `requests.blackbox.homes` + apps). Si le MP échoue (privacy Discord) → message dans le salon admin, remise en main propre |
| Seerr | **rien** — auto-import au premier login sur `requests.blackbox.homes` (Jellyseerr « Enable new Jellyfin Sign-In », quota illimité) |
| Départ Discord (`on_member_remove`) | **alerte admin uniquement**, jamais de désactivation auto |
| Retour d'un membre | mapping conservé en base → on ne recrée pas, on notifie l'admin |

### Commandes

Publiques : `/status`, `/streams` (inchangées), `/moncompte` (rappel du
nom d'utilisateur + réinitialisation du mot de passe en MP), `/messtats`
(heures, palier, prochain palier, genre préféré, rang), `/roulette` (un
film de la bibliothèque non vu par l'appelant).

Admin (rôle **`SysAdmin`**, repli sur la permission Administrator) :
`/creer-compte @membre` (provisioning manuel — MP échoué, membre arrivé
pendant une coupure), `/lier @membre <user_jellyfin>` (mapping d'un compte
préexistant sans en recréer), `/desactiver @membre` (`IsDisabled: true`
côté Jellyfin + note en base).

### Gamification — cosmétique

4 rôles Discord cumulatifs, **sans emoji**, créés par le bot au démarrage
s'ils manquent (positionnés juste sous son propre rôle) :

| Rôle | Seuil (heures cumulées, tout l'historique) |
|---|---|
| `Figurant` | 0 |
| `Second rôle` | 15 |
| `Premier rôle` | 60 |
| `Réalisateur` | 180 |

Recalcul quotidien (05h00 Europe/Brussels) : lecture de
`getAllUserActivity` (Jellystat, `TotalWatchTime`), calcul du palier,
`add_roles` / `remove_roles`, `tier` mis à jour en base.

### Classement — tous les 15 jours

Posté dans `#classement` (`1543646643629461628`), toutes les 15 jours à
19h00 (ancré à la première exécution, état en base). Embed :

- **Top 3** de la quinzaine (heures via `getGlobalUserStats {hours: 360}`),
  membres **pingés**, avec leur titre le plus regardé
- **Film / série de la quinzaine** côté serveur (`getMostViewedByType`)
- **Nouveaux membres** de la période
- **Total serveur** : heures cumulées, nombre de lectures
- **Tête d'affiche de la quinzaine** : le n°1, rôle `Tête d'affiche`
  transféré (retiré à l'ancien, donné au nouveau)
- rendu sous forme de **carte-image** (Pillow, `bot/cards.py`) : podium 3
  places, photos de profil Discord en rond, couronne dorée dessinée sur le
  n°1 ; une courte légende texte pingue le top 3. Le MP de bienvenue
  embarque aussi une carte (avatar + « Bienvenue sur Blackbox »). Police
  `fonts-dejavu-core` dans l'image.

**IPTV** : le calcul compte toute lecture enregistrée par Jellystat. Le
Live TV crée des sessions mais avec des métadonnées pauvres — inclus
best-effort, à revalider quand Threadfin sera déployé (ADR-018).

### Persistance

**SQLite** (`aiosqlite`), fichier `/data/bot.db` dans le volume
`./data/bot`. Table `members(discord_id, jf_user_id, jf_username,
display_name, created_at, tier, note)` + table `meta` (date du dernier
classement, ancre du cycle). Ajouté aux sources restic (le mapping
Discord ↔ Jellyfin n'est pas trivialement régénérable).

Écarté : une base sur le Postgres de Jellystat — coupler le cycle de vie
du bot à `jellystat-db` pour quelques centaines de lignes est
disproportionné.

### Accès aux données

- **Jellyfin** : la clé API du bot (déjà existante, `X-Emby-Token`) sert
  maintenant aussi en écriture (création d'utilisateur, policy, mot de
  passe, `IsDisabled`). Les clés API Jellyfin ne sont pas *scopables* —
  une clé = accès complet. Clé dédiée possible plus tard pour la
  révocabilité.
- **Jellystat** : API REST, header `x-api-token`, clé générée dans son UI.
  Couplage assumé à quelques endpoints (`getAllUserActivity`,
  `getGlobalUserStats`, `getMostViewedByType`, `getGenreUserStats`,
  `sync/beginSync`).

## Conséquences

- `bot/` refondu en modules : `main.py`, `config.py`, `db.py`,
  `jellyfin.py`, `jellystat.py`, `provisioning.py`, `gamification.py`,
  `scoreboard.py`, `commands.py`. `discord.ext.commands.Bot` +
  `discord.ext.tasks`.
- `bot/requirements.txt` : `aiosqlite`. `bot/Dockerfile` : copie tous les
  modules + `mkdir /data`.
- `bot/.env.example` : `DISCORD_GUILD_ID` (sync rapide des commandes),
  `JELLYSTAT_URL`, `JELLYSTAT_API_KEY`, `ADMIN_ALERT_WEBHOOK_URL`,
  `PUBLIC_STREAM_URL`, `PUBLIC_REQUESTS_URL`, `BOT_DB_PATH`.
- `docker-compose.yml` : volume `./data/bot:/data` sur le service `bot`.
- `infra/scripts/backup/backup.sh` : `~/blackbox/prod/data/bot` ajouté aux
  sources.
- Intent **Server Members** à activer dans le Dev Portal ; bot ré-invité
  avec **Manage Roles** ; rôle du bot pas en bas de la hiérarchie.
- Jellyseerr : « Enable new Jellyfin Sign-In » coché.
- Runbook `setup-bot.md` étendu ; permissions élargies documentées.
- La position d'ADR-010 « aucune restriction de permission par rôle »
  tombe pour les commandes admin.
