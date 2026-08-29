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
- Ne PAS activer la suppression automatique pour l'instant (chaque
  collection reste en « manual action » — cf. §5)

## 5. Les trois collections

Rules → Add. Pour chacune : **Library = Movies ou Shows**, **Schedule =
quotidien**, **Action = supprimer** (voir détail), **Automatic = OFF**
(validation manuelle), période de grâce = « Days » indiqué.

### 5.1 Protections communes (à remettre dans CHAQUE collection)

Ajouter ces conditions en **AND**, en plus des conditions propres :

| Condition | Opérateur | Valeur |
|---|---|---|
| Jellyfin – last view date | not in last | 180 days |
| Seerr – request date | not in last | 90 days |
| *arr – date added | before | 90 days ago |
| Radarr/Sonarr – tags | not contains | `keep` |

> « ajouté il y a plus de 90 j » = `date added` **before** `90 days ago`.
> Certaines versions exposent ça comme `added` + `not in last 90 days`.

### 5.2 Collection 1 — Films dormants

Library **Movies**. En plus des protections communes (AND) :

| Condition | Opérateur | Valeur |
|---|---|---|
| Jellyfin – view count | equals | 0 *(OU)* Jellyfin – last view date : not in last 180 days |
| Plex/Jellyfin – collection | is not present | — |
| Radarr – part of a collection | false | — |

- **Grâce : 14 jours**
- **Action** : *Delete* → cocher « delete file », « unmonitor in Radarr »,
  « clear Seerr request ». **Ne pas** cocher « add to Radarr exclusion
  list ».

### 5.3 Collection 2 — Séries terminées inactives

Library **Shows**. En plus des protections communes (AND) :

| Condition | Opérateur | Valeur |
|---|---|---|
| Sonarr – series status | in | `ended`, `deleted` (PAS `continuing`) |
| Sonarr – last episode added | before | 120 days ago |
| Jellyfin – last view date | not in last | 180 days |

- **Grâce : 21 jours**
- **Action** : *Delete* → « delete files », « unmonitor series in Sonarr »,
  « clear Seerr request ».

### 5.4 Collection 3 — Demandé puis jamais lancé

Library **Movies** (et une variante identique pour **Shows** si tu veux).
En plus des protections communes **sauf** le « date added before 90 days »
qu'on remplace par **45 days** :

| Condition | Opérateur | Valeur |
|---|---|---|
| Seerr – is requested | true | — |
| *arr – date added | before | 45 days ago |
| Jellyfin – view count | equals | 0 |

- **Grâce : 7 jours**
- **Action** : *Delete* (mêmes cases que Collection 1)
- **Automatic : OFF en permanence** — cette règle ne s'automatise jamais.

## 6. Vérification

1. Laisser tourner un cycle (ou *Run rule* manuellement).
2. Collections → vérifier que le contenu attrapé est bien du « dormant »
   légitime. Faux positif → l'exclure de la collection (bouton par item) ou
   poser le tag `keep`.
3. Jellyfin : l'étagère « Bientôt retiré » doit apparaître avec le contenu
   en période de grâce.
4. Ne **rien** supprimer avant d'avoir observé 1–2 semaines et ajusté.

## 7. Bascule en automatique (plus tard)

Quand le NAS dépasse ~70 % (le capacity-watcher d'ADR-019 alertera bien
avant) : passer **uniquement la Collection 1** en *Automatic = ON*, grâce
14 j inchangée. Collections 2 et 3 restent manuelles.

## 8. Ce qui n'est pas couvert

- La config Maintainerr (`data/maintainerr/`) n'est **pas** dans le backup
  restic : les règles sont re-saisissables depuis ce runbook.
- Maintainerr ne déclenche pas sur l'espace disque — c'est du temporel
  pur. Le volet « seuil disque » reste le capacity-watcher (alerte + bride
  qBittorrent), pas une purge.
