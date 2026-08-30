# ADR 022 — Panneau « en direct » des lectures en cours

**Statut :** Accepté — 2026-08-30

**Complète :** [ADR-021](021-bot-layer3.md). Remplace la slash command
`/streams` par un affichage permanent.

## Contexte

`/streams` (ADR-010) répond à la demande mais il faut la lancer. Le
propriétaire veut un affichage **permanent et en direct** de « qui regarde
quoi », dans un salon dédié.

## Décision

Un **unique message-embed** maintenu par le bot dans **`#salle-de-projection`**
(`1543666526400422089`), salon en lecture seule pour `@everyone`.

- Rafraîchi toutes les **45 s** par une `tasks.loop` : `GET /Sessions`,
  reconstruction de l'embed, édition en place (pas de repost → pas de
  notification, message stable).
- ID du message stocké en base (`meta.now_playing_message_id`) → survit
  aux redémarrages ; si le message a été supprimé, le bot en repost un.
- Contenu :
  - rien en cours → « Personne ne regarde en ce moment. » + horodatage
  - sinon, une ligne par lecture : `pseudo Discord — Titre (SxxEyy) ·
    barre de progression · lecture directe / transcodage · (en pause)`
  - le pseudo affiché est celui du **membre Discord** (via le mapping
    ADR-021), repli sur le nom d'utilisateur Jellyfin
  - pas d'appareil ni de débit affichés (jugés inutiles)
  - pied : « mis à jour » + horodatage
- En parallèle : `change_presence` (ligne « Regarde : N flux » sous le nom
  du bot dans la sidebar).
- **`/streams` est supprimée.**

### Pourquoi pas les autres options

- **Webhook Jellyfin → messages Playback Start/Stop** : crée un flux de
  messages (début + fin par session) au lieu d'un panneau unique, et
  impose un listener HTTP entrant dans le bot (surface d'attaque, routage).
  45 s de latence sur ce panneau sont sans conséquence.
- **Renommer un salon** : Discord limite à 2 renommages / 10 min.
- **Statut du bot seul** : une ligne tronquée, gardée en complément.

### Vie privée

Cette décision revient (à nouveau) sur la position d'ADR-009 (Playback
Start/Stop écarté pour la vie privée), déjà dépassée par ADR-010
(`/streams` avec identités visibles). Assumé : serveur familial, décision
du propriétaire, affichage réservé aux membres du Discord.

## Conséquences

- `bot/now_playing.py` (nouveau module) : construction de l'embed +
  maintien du message. `bot/main.py` : `tasks.loop(seconds=45)` +
  `change_presence`. `bot/bot_commands.py` : retrait de `/streams`.
- `bot/config.py` / `.env.example` : `NOW_PLAYING_CHANNEL_ID`.
- Salon `#salle-de-projection` à créer en lecture seule (le bot poste).
- Aucune nouvelle clé ni permission Discord (le bot a déjà
  `View Channels` + `Send Messages` + la clé Jellyfin).
- Runbook `setup-bot.md` mis à jour.
