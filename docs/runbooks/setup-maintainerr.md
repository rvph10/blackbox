# Runbook — Maintainerr (rétention de bibliothèque)

Contexte et politique : [ADR-020](../adr/020-retention-maintainerr.md).
Maintainerr tourne en **revue manuelle** : les collections se remplissent,
rien n'est supprimé sans validation humaine.

## 1. Déploiement

Le service `maintainerr` est dans le `docker-compose.yml` (déployé par
Ansible, rôle `deploy`). À la main :

```bash
ssh nucbox 'cd ~/blackbox/prod && docker compose up -d maintainerr && docker logs maintainerr --tail 20'
```

Attendre `Nest application successfully started`. Dashboard :
`http://nucbox:6246` **via Tailscale** (jamais exposé publiquement).

Pré-requis CPU : `x86-64-v2` pour les overlays/posters (`sharp`). Le Ryzen
5 7640HS le supporte, rien à faire.

## 2. Connexion des services (UI Maintainerr → Settings)

| Service | URL interne | Clé API |
|---|---|---|
| **Jellyfin** | `http://jellyfin:8096` | Dashboard → Advanced → API Keys → « Maintainerr » |
| **Seerr** | `http://seerr:5055` | Seerr → Settings → General → API Key |
| **Radarr** | `http://radarr:7878` | Radarr → Settings → General → API Key |
| **Sonarr** | `http://sonarr:8989` | Sonarr → Settings → General → API Key |

Tester chaque connexion (bouton *Test*) avant de continuer. Laisser
Tautulli / Streamystats / Plex vides.

## 3. Convention : le tag `keep`

Dans **Radarr** et **Sonarr** : Settings → Tags → créer le tag `keep`.
Poser ce tag sur un film / une série le sort définitivement du champ de
Maintainerr (voir les règles ci-dessous). C'est l'échappatoire manuelle.

## 4. Réglages généraux (Settings → Main)

- **Collection handling** : créer la collection sur le serveur média
  (pour l'étagère « Bientôt retiré » visible dans Jellyfin)
- **Rule handler / Collection handler** : quotidien

## 5. Les trois collections (créées via l'API le 2026-08-29)

Les 3 rule groups sont **déjà créés** (script `infra/scripts/` non versionné,
POST `/api/rules`). Chacun est en **mode observation** : `arrAction = Do
Nothing` → les collections se remplissent, l'étagère « Bientôt retiré »
s'affiche dans Jellyfin, mais **rien n'est jamais supprimé**, ni
automatiquement ni manuellement, tant que l'action reste sur « Do Nothing ».

Cron d'exécution : quotidien à 3 h (`0 3 * * *`).

### Contenu des règles (référence — pour les recréer à la main si besoin)

Toutes les sections sont combinées en **ET**. `> Nj` = date **before**
`N jours en secondes` (Maintainerr stocke les dates relatives en secondes).

**Collection 1 — Films dormants** (library Films, `movie`, grâce 14 j) :
- `(` Jellyfin *Times viewed* `= 0` **OU** Jellyfin *Last view date* `before` 180 j `)`
- **ET** Jellyfin *Date added* `before` 90 j
- **ET** Radarr *Tags* `not contains` `keep`
- **ET** Jellyfin *Present in amount of other collections* `smaller` 1
- **ET** `(` Seerr *Requested in Seerr* `= false` **OU** Seerr *Request date* `before` 90 j `)`

**Collection 2 — Séries terminées inactives** (library Séries, `show`, grâce 21 j) :
- Sonarr *Status* `= ended`
- **ET** Jellyfin *Last episode added at* `before` 120 j
- **ET** Sonarr *Tags (show)* `not contains` `keep`
- **ET** `(` Jellyfin *Amount of watched episodes* `= 0` **OU** Jellyfin *Newest episode view date* `before` 180 j `)`
- **ET** `(` Seerr *Requested in Seerr* `= false` **OU** Seerr *Request date* `before` 120 j `)`

**Collection 3 — Demandé puis jamais lancé** (library Films, `movie`, grâce 7 j) :
- Seerr *Requested in Seerr* `= true`
- **ET** Jellyfin *Times viewed* `= 0`
- **ET** Jellyfin *Date added* `before` 45 j
- **ET** Radarr *Tags* `not contains` `keep`

## 6. Vérification

```bash
ssh nucbox 'K=<api-key>; curl -sS -H "x-api-key: $K" http://localhost:6246/api/rules | python3 -m json.tool | grep -E "\"name\"|\"id\""'
```

1. Exécution : `curl -sS -X POST -H "x-api-key: $K" http://localhost:6246/api/rules/execute`
   (ou bouton *Run* dans l'UI). Résultat attendu aujourd'hui : **0 média**
   (rien n'a encore 90 j de dormance).
2. Dans quelques semaines : Collections → vérifier que le contenu attrapé
   est bien du dormant légitime. Faux positif → l'exclure de la collection
   (bouton par item) ou poser le tag `keep` dans Radarr/Sonarr.
3. Jellyfin : l'étagère « Bientôt retiré » apparaît quand une collection
   se remplit.

## 7. Passage en mode actif (plus tard)

Rien ne supprime tant que `arrAction = Do Nothing`. Pour activer une
collection, dans l'UI : éditer le rule group → **Action** →

- Films / séries : **Delete** avec *unmonitor + delete files*
  (`UNMONITOR_DELETE_ALL`), ne PAS cocher « add to arr exclusion list »
- la grâce (14 / 21 / 7 j) est déjà réglée

Ordre conseillé : **Collection 1 d'abord**, seulement quand le NAS
dépasse ~70 % (le capacity-watcher d'ADR-019 alerte bien avant).
Collections 2 et 3 : à activer au cas par cas, la 3 reste la plus agressive.

## 8. Ce qui n'est pas couvert

- La config Maintainerr (`data/maintainerr/`) n'est **pas** dans le backup
  restic : les règles sont re-saisissables depuis ce runbook.
- Maintainerr ne déclenche pas sur l'espace disque — c'est du temporel
  pur. Le volet « seuil disque » reste le capacity-watcher (alerte + bride
  qBittorrent), pas une purge.
