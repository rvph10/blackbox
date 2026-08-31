# ADR 023 — Home d'accueil façon Netflix (Home Screen Sections)

**Statut :** Accepté — 2026-08-31

**Complète :** la configuration Jellyfin ([runbook](../runbooks/setup-jellyfin.md)).

## Contexte

La home Jellyfin par défaut : sections figées (« Continuer », « Ajouts
récents » par bibliothèque), une entrée par bibliothèque, recommandations
quasi inexistantes (onglet « Suggestions » par bibliothèque seulement).

Le propriétaire veut une home **façon Netflix / Disney+ / HBO** : films et
séries **mélangés**, rangées par catégorie / genre, « Parce que vous avez
regardé… ».

Première tentative : changer le **thème CSS** (Jellyfish). Rejetée — un
thème ne fait que restyler, il ne réorganise pas la home. Le sujet n'est
pas cosmétique.

## Décision

Plugin **Home Screen Sections** ([IAmParadox27](https://github.com/IAmParadox27/jellyfin-plugin-home-sections)),
côté serveur, qui s'injecte dans jellyfin-web via **File Transformation**
(déjà installé pour d'autres plugins).

- **Liste de sections curée** : 12 actives, 18 désactivées (musique,
  livres, Live TV, doublons). Ordre défini par l'admin, `AllowUserOverride`
  laissé actif → chaque membre peut réordonner sa propre home, le défaut
  admin s'applique sinon.
- **Jellyseerr** branché (URL interne + externe + clé API) → rangées
  *Discover* et *My Requests* + bouton « demander » sur les cartes.
- **Radarr / Sonarr** branchés → rangées *Upcoming* (sorties à venir).
- Le **thème** reste indépendant (le propriétaire utilise JellyTheme via
  Skin Manager — choix orthogonal, non tranché ici).

### Sections actives

| # | Section | Source |
|---|---|---|
| 1 | Continue Watching / Next Up (combiné) | Jellyfin |
| 2 | Because You Watched (max 3) | historique |
| 3 | My List | Jellyfin |
| 4 | Latest Movies | biblio Films |
| 5 | Latest Shows | biblio Séries |
| 6 | Genre (max 3, pondéré par l'historique) | historique |
| 7 | Watch Again | collections + séries finies |
| 8 | Discover | Jellyseerr |
| 9 | My Requests | Jellyseerr |
| 10 | Upcoming Movies | Radarr |
| 11 | Upcoming Shows | Sonarr |
| 99 | My Media | Jellyfin (tout en bas) |

### Pourquoi pas les autres options

- **Un thème CSS seul** (Jellyfish, JellyFlix…) : restyle sans réorganiser.
  Testé, rejeté.
- **Streamyfin ou un client custom** : application séparée, alors que tout
  le monde passe par l'UI web.
- **Onglet « Suggestions » natif** : par bibliothèque, pas mélangé, pas sur
  la home.
- **Le coder dans le bot** : le bot en fait déjà beaucoup ; un plugin
  Jellyfin est la bonne couche.

## Conséquences

- Plugins ajoutés : **Home Screen Sections** `2.5.11.0`, **Plugin Pages**
  `2.4.11.0` (dépendance, sert la page de réglages « Modular Home »).
- **Jellyfin Tweaks** a été installé puis retiré (il ne servait qu'à
  forcer les backdrops pour la tentative Jellyfish).
- Config dans `/config/plugins/configurations/Jellyfin.Plugin.HomeScreenSections.xml` —
  contient les clés API Seerr / Radarr / Sonarr **en clair** (dans le
  périmètre backup restic, jamais dans git).
- Les rangées de reco (*Because You Watched*, *Genre*, *Watch Again*)
  dépendent de l'historique de visionnage → maigres tant que l'usage n'a
  pas construit de données.
- **Chaque client doit vider son service worker / « Clear site data » une
  fois** après l'installation (File Transformation modifie le bundle web),
  et à chaque grosse MàJ du plugin. Vrai pour `192.168.x` comme pour
  `stream.blackbox.homes` (origines séparées) + purge Cloudflare pour le
  domaine public.
- Les nouveaux membres héritent de la home par défaut automatiquement —
  aucune modification du bot.
- Runbook `setup-jellyfin.md` mis à jour.

## Vie privée

Sans objet : aucune nouvelle exposition de données. Les recommandations
sont calculées par Jellyfin, par utilisateur, et restent locales au
serveur.
