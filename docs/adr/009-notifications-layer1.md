# ADR 009 — Notifications passives (Layer 1) sans code de bot

**Statut :** Accepté
**Date :** 2026-08-28

> **Révision 2026-08-30** — l'annonce « nouveau contenu » ne passe plus par
> le plugin Webhook de Jellyfin (destination Generic + template Handlebars)
> mais par un **écouteur HTTP dans le bot** alimenté par l'agent Webhook de
> **Jellyseerr** (event « Media Available »). Ça permet de **pinguer le
> membre Discord qui a fait la demande**. Voir
> [ADR-021](021-bot-layer3.md) et `bot/seerr_hook.py`. Le reste d'ADR-009
> (santé Gluetun via script + timer) est inchangé.

## Contexte

Suite à [ADR-008](008-discord-community.md), premier chantier du bot Discord
envisagé selon le modèle en 3 couches (Layer 1 notifications passives, Layer
2 commandes de statut en lecture seule, Layer 3 actions actives sur
l'infra). Décision : démarrer uniquement par Layer 1.

## Peu de notifications, choisies pour éviter le spam

Point de départ explicite : ne pas noyer le serveur sous des notifications
au point que tout le monde finisse par mute le salon et rate les infos
utiles. Liste volontairement courte, deux salons aux audiences différentes :

| Notification | Salon | Pourquoi |
|---|---|---|
| Nouveau contenu ajouté (Jellyfin, *Item Added*) | `#annonces` | La seule information qui a une vraie valeur pour les membres : "c'est regardable maintenant" |
| Santé VPN Gluetun (up/down) | salon admin | Signale un vrai problème (téléchargements à l'arrêt) |

**Écarté explicitement :**
- **Media Available côté Seerr** : doublon quasi simultané avec l'événement
  Jellyfin *Item Added* pour le même ajout (Radarr/Sonarr importe → Jellyfin
  scanne) — un seul des deux suffit, Jellyfin choisi car il correspond au
  moment où le contenu est réellement lisible, pas juste importé.
- **Nouvelle demande / demande approuvée (Seerr)** : aucune action requise
  côté admin (auto-approve déjà configuré) ni côté membres — pas de valeur
  à notifier.
- **Playback Start/Stop (Jellyfin)** : jamais envisagé comme notification de
  salon — problème de vie privée (qui regarde quoi, quand) en plus du bruit.
  L'envie sous-jacente ("voir ce que les autres regardent, façon Spotify")
  est couverte autrement, voir plus bas.
- **User Created** : les comptes sont créés à la main par l'admin, qui le
  sait déjà au moment de le faire.
- **Media Failed** (échec de téléchargement) : pas de valeur ajoutée tant
  que le catalogue actuel (YTS + The Pirate Bay, ADR-007) n'a pas montré de
  limite concrète — à réévaluer si ce point ouvert se confirme.
- **ESP8266 (watchdog NucBox injoignable)** : mis en pause pour l'instant,
  à reprendre plus tard (câblage HTTP identique au principe Gluetun,
  `http_request` ESPHome vers le webhook admin).

## Aucune ligne de code de bot nécessaire pour ce qui est fait

- **Jellyfin → Discord** : géré par le plugin **Webhook** déjà installé,
  destination de type **Generic** avec un template Handlebars maison (voir
  runbook). La destination **Discord native est buggée** : elle produit un
  corps que Discord rejette (`400`, `code 50109 – invalid JSON`), bug connu
  et non corrigé du plugin
  ([jellyfin-plugin-webhook#369](https://github.com/jellyfin/jellyfin-plugin-webhook/issues/369)).
  Le contournement standard est Generic + template. Pièges du template
  (tous rencontrés) : le helper `json_encode` **échappe** le texte mais
  n'ajoute **pas** les guillemets — il faut écrire `"{{json_encode X}}"` ;
  et `json_encode` **lève une exception sur une valeur nulle**, donc tout
  champ optionnel (`Overview`, `Year`) doit être sous `{{#if_exist}}`.
  Validé le 2026-08-29 (film de test → embed « Nouveau film disponible »
  dans `#annonces`, aucun `BadRequest` dans les logs du plugin).
- **Gluetun → Discord** : aucune intégration native n'existe pour ça, seul
  point nécessitant un script (voir ci-dessous), mais toujours pas un
  "bot" — un script ponctuel déclenché par un timer.

## Script de santé Gluetun

`infra/scripts/gluetun-healthcheck/check-gluetun.sh` — lit
`docker inspect --format='{{.State.Health.Status}}' gluetun`, compare à un
fichier d'état local (`.last_state` à côté du script, pas dans `/var/lib` —
évite d'avoir besoin de sudo pour l'exécution normale), ne poste sur le
webhook Discord admin que si l'état a changé depuis la dernière exécution.

- Webhook admin stocké dans `.env` à côté du script sur le NucBox (jamais
  commité, `.env.example` documente la clé attendue), pas dans le
  `docker-compose.yml` de la stack principale — ce script est indépendant
  des conteneurs
- Exécuté toutes les 2 minutes via `gluetun-healthcheck.timer`
  (systemd, installé dans `/etc/systemd/system/`, nécessite sudo pour
  l'installation initiale uniquement)
- Testé en conditions réelles : premier lancement a bien posté le message
  "opérationnel" (aucun état précédent enregistré = changement détecté),
  timer actif et enabled confirmé via `systemctl status`

## Rich Presence "façon Spotify" : hors de portée d'un bot serveur

Envie exprimée : voir ce que les autres regardent, dans l'esprit du statut
Spotify sur Discord. Ce n'est **pas réalisable côté serveur** : le Rich
Presence Discord fonctionne par IPC locale entre un petit programme et le
client Discord de chaque utilisateur, lisant sa propre session Jellyfin —
aucun bot ou service central ne peut l'activer à la place des gens. Solution
existante et pertinente : des outils communautaires
(`jellyfin-rpc`, `jellyfin-discord-presence`) que chaque membre intéressé
installe lui-même, opt-in. À documenter comme option recommandée dans
`#accueil` plus tard, pas un chantier serveur.

## Conséquences

- `#annonces` reçoit uniquement les nouveaux ajouts de contenu (Jellyfin) —
  Films + Épisodes (pas les Saisons, pour éviter saison + N épisodes)
- Le salon admin reçoit les changements d'état du VPN (Gluetun) — ESP8266 à
  ajouter plus tard sur le même principe
- `infra/scripts/gluetun-healthcheck/` ajouté au repo (script + unités
  systemd + `.env.example`), déployé sur le NucBox
  (`~/blackbox/scripts/gluetun-healthcheck/`)
- Le dossier `bot/` du repo reste vide — Layer 1 n'a nécessité aucun bot,
  Layer 2/3 (commandes de statut, création de compte, gamification) pas
  commencé
- Détail de déploiement dans
  [docs/runbooks/setup-notifications.md](../runbooks/setup-notifications.md)
