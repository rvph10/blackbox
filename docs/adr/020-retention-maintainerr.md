# ADR 020 — Rétention de la bibliothèque : Maintainerr

**Statut :** Accepté — déployé le 2026-08-29, **en mode observation**
(`arrAction = Do Nothing` : les collections se remplissent et l'étagère
« Bientôt retiré » s'affiche, mais aucune suppression, ni auto ni manuelle,
tant que l'action reste sur « Do Nothing »). Les 3 rule groups ont été
créés via l'API Maintainerr (`POST /api/rules`).

**Complète :** [ADR-019](019-autoregulation-capacite-bande-passante.md). Le
capacity-watcher *alerte* et *bride* quand le disque se remplit ; il ne
libère rien. Maintainerr est le maillon qui récupère de l'espace.

## Contexte

La suite *arr* télécharge en continu (Seerr auto-approuve), rien ne sort
jamais de la bibliothèque. Aujourd'hui le NAS est à **2 %** (73 Go / 3,7 To)
— aucune urgence. Mais :

- le premier gaspilleur d'un serveur communautaire est le « demandé puis
  jamais lancé » : quelqu'un demande un film, ne le regarde pas, il reste
  là pour toujours ;
- sans outil, le ménage devient un travail manuel pénible quand la
  bibliothèque grossit ;
- une gestion de cycle de vie automatisée est une brique attendue d'un
  serveur bien tenu (et une pièce de portfolio).

## Décision : Maintainerr

Conteneur [Maintainerr](https://github.com/Maintainerr/Maintainerr)
(support Jellyfin natif depuis 2026, + Seerr + Radarr + Sonarr). Dashboard
`:6246` via Tailscale uniquement, **jamais** sur le tunnel public.

Écarté : Janitorr (orienté seuil disque pur, moins de finesse sur les
règles, pas de collection « Bientôt retiré » visible côté Jellyfin) ;
scripts maison (réinventer le matching multi-sources par IMDB/TMDB/TVDB).

### Déploiement prudent

**Mode revue manuelle d'abord.** Les collections se remplissent, la
période de grâce tourne, mais la suppression n'est **pas** automatique : on
regarde les collections une fois par semaine et on valide. On bascule une
règle en automatique seulement quand le disque le justifie (voir
« Bascule auto » plus bas). Vu les 2 % actuels, la valeur immédiate est
surtout l'étagère « Bientôt retiré » visible dans Jellyfin et la
discipline de revue.

### Protections globales (jamais éligible, quelle que soit la règle)

- vu par quelqu'un dans les **180 derniers jours**
- demandé via Seerr dans les **90 derniers jours**
- ajouté il y a **moins de 90 jours** (fenêtre de visionnage équitable)
- tag `keep` posé à la main dans Radarr / Sonarr

### Collection 1 — Films dormants

`ajouté > 90 j` **ET** (`jamais vu` **OU** `dernière lecture > 180 j`)
**ET** `hors collection/saga` (protège LOTR, MCU…) **ET** `pas de demande
Seerr < 90 j`.

- Grâce : **14 jours**
- Action : supprimer le fichier + *unmonitor* dans Radarr + purger la
  demande Seerr. **Pas** d'exclusion d'import : le film peut être
  re-demandé plus tard.

### Collection 2 — Séries terminées inactives

`statut = Ended / Canceled` (**jamais** une série *Continuing*) **ET**
`dernier épisode ajouté > 120 j` **ET** `aucun épisode vu < 180 j` **ET**
`pas de demande Seerr < 120 j`.

- Grâce : **21 jours**
- Action : supprimer les fichiers + *unmonitor* la série dans Sonarr +
  purger la demande Seerr.

### Collection 3 — Demandé puis jamais lancé

`une demande Seerr existe` **ET** `ajouté > 45 j` **ET** `jamais lu par
personne` (même pas le demandeur).

- Grâce : **7 jours**
- **Reste en validation manuelle en permanence** — règle la plus agressive,
  on ne l'automatise pas.

### Cadence

Exécution quotidienne de Maintainerr. Revue humaine hebdomadaire des
collections.

### Bascule auto (plus tard)

Quand le NAS dépassera **70 %**, passer la **Collection 1** en automatique
(grâce 14 j inchangée). Collections 2 et 3 restent manuelles. Ce seuil est
un rappel, pas une automatisation : Maintainerr ne déclenche pas sur
l'espace disque, c'est une décision à prendre à la main le moment venu (le
capacity-watcher alertera bien avant, cf. ADR-019).

## Conséquences

- `infra/docker/prod/docker-compose.yml` : service `maintainerr`
  (`user: ${PUID}:${PGID}`, volume `data/maintainerr` + `${MEDIA_PATH}:/data`
  pour le nettoyage des dossiers résiduels, port `6246`).
- Aucun secret : les clés d'API (Jellyfin, Seerr, Radarr, Sonarr) se
  saisissent dans l'UI de Maintainerr, stockées dans son volume.
- Pas de rôle Ansible dédié : le compose est déjà déployé par le rôle
  `deploy`, le dossier `data/maintainerr` est créé par Docker.
- Runbook `docs/runbooks/setup-maintainerr.md` (connexion des services +
  saisie des 3 collections règle par règle).
- Hors périmètre backup restic : la config Maintainerr (règles) est
  re-saisissable depuis le runbook ; pas de donnée unique à sauvegarder.
- Le tag `keep` devient une convention Radarr/Sonarr à documenter.
