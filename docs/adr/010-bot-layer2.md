# ADR 010 — Bot Discord Layer 2 : commandes de statut en lecture seule

**Statut :** Accepté
**Date :** 2026-08-28

## Contexte

Suite à [ADR-008](008-discord-community.md) et [ADR-009](009-notifications-layer1.md),
premier vrai code de bot du projet (le dossier `bot/` était vide jusqu'ici,
Layer 1 n'en avait pas eu besoin). Objectif : des commandes de statut à la
demande, strictement en lecture, aucune action sur l'infra.

## Scope volontairement réduit

Deux commandes seulement, décidées après une première proposition plus
large (vue d'ensemble avec espace disque, VPN, etc.) explicitement
simplifiée par choix : le dashboard admin reste l'outil de détail, le bot
n'a pas besoin de le dupliquer.

- **`/status`** : "En ligne" ou "Hors ligne" sur Jellyfin, rien de plus
  (`GET /System/Info/Public`, endpoint public, pas d'authentification
  nécessaire)
- **`/streams`** : liste des sessions de lecture en cours (utilisateur +
  titre), via `GET /Sessions` avec une clé API Jellyfin dédiée ("Bot",
  lecture seule dans l'usage qu'on en fait, générée depuis Dashboard →
  Advanced → API Keys)

**Décision explicite sur `/streams`** : accessible à tout le monde, avec
identités visibles ("Untel regarde Film X"). Ça revient en partie sur la
position prise pour les notifications passives (Layer 1, ADR-009) où
Playback Start/Stop avait été écarté pour raison de vie privée — la
différence assumée : `/streams` est **interrogé à la demande** par un
membre qui veut savoir, jamais poussé automatiquement à tout le monde.
Décision du propriétaire du serveur, actée telle quelle.

## Aucun état, aucune action

- Pas de tâche de fond, pas de polling permanent — chaque commande relit
  l'état actuel de Jellyfin au moment où elle est appelée
- Pas de mémoire entre deux appels
- Aucun accès à Gluetun, à l'ESP8266, aux comptes Jellyfin/Seerr, au NAS ou
  aux futurs backups — strictement scope Layer 2 (voir modèle en couches,
  ADR-008)
- Aucune restriction de permission par rôle sur les commandes

## Implémentation

- Python + `discord.py` (App Commands / slash commands), dans `bot/`
  (jusqu'ici vide)
- Conteneur Docker séparé (`bot/Dockerfile`), nouveau service dans
  `docker-compose.yml`, sur le réseau Docker interne pour joindre Jellyfin
  via `http://jellyfin:8096`
- Secrets (`DISCORD_BOT_TOKEN`, `JELLYFIN_API_KEY`) dans `bot/.env`
  (jamais commité), même traitement que le reste des secrets du projet
- Application Discord créée sur le Developer Portal, invitée avec les
  scopes `bot` + `applications.commands` et les permissions minimales
  (Voir salons, Envoyer des messages, Intégrer des liens — `19456`), pas
  d'accès administrateur

## Piège de déploiement rencontré : chemins relatifs

Le repo Git structure `bot/` à la racine et le compose de prod sous
`infra/docker/prod/`, alors que sur le NucBox le déploiement réel place
`~/blackbox/{bot,prod,scripts}` en frères directs (`prod/` ne contient pas
la même profondeur que `infra/docker/prod/` dans le repo). Un premier
`build: ../../../bot` (correct *dans le repo*) cassait donc le déploiement
réel. Corrigé en `build: ../bot`, qui correspond à la structure serveur —
commenté directement dans le compose pour ne pas reproduire l'erreur.

## Conséquences

- `bot/` contient maintenant du vrai code (`main.py`, `Dockerfile`,
  `requirements.txt`, `.env.example`)
- Nouveau service `bot` dans `docker-compose.yml`, déployé et vérifié en
  conditions réelles (connexion Discord confirmée dans les logs, commandes
  testées sur le serveur)
- Layer 3 (création de compte à l'arrivée, gamification par temps de
  visionnage — voir ADR-008) reste à faire, pas commencé
- Détail de déploiement dans
  [docs/runbooks/setup-bot.md](../runbooks/setup-bot.md)
