# ADR 008 — Discord communautaire : structure native, pas de bot pour l'instant

**Statut :** Accepté
**Date :** 2026-08-28

## Contexte

La communauté (~10 personnes, famille/amis) a besoin d'un point d'entrée
unique : comprendre les règles d'usage (matériel perso, best-effort), savoir
comment se connecter à Jellyfin, savoir comment demander du contenu, et un
canal pour signaler les problèmes. Discord sert ce rôle, en plus de son usage
social existant pour le groupe.

Décision structurante : construire d'abord tout ce que les fonctionnalités
natives de Discord permettent de faire, sans écrire une seule ligne de bot.
Le bot Discord reste au roadmap (voir README) mais est traité comme un projet
séparé, à documenter et construire à part.

## Comptes invités : abandonnés

Piste initialement envisagée (Wizarr, liens d'invitation à durée limitée)
puis abandonnée : la communauté est un noyau fixe de ~10 personnes connues,
pas un flux de visiteurs ponctuels. Un compte Jellyfin créé/supprimé à la
main pour un cas rare suffit ; pas besoin d'un outil dédié pour un cas qui
n'arrive quasiment jamais.

## Mode Communauté + Safety Setup pour l'acceptation des règles

Le serveur est passé en mode **Communauté** (Server Settings → Community),
strictement pour débloquer les fonctionnalités natives suivantes — **la
Découverte des serveurs reste désactivée**, le serveur n'est pas et ne sera
pas listé publiquement, invitation uniquement.

- **Acceptation des règles** : la fonctionnalité s'appelle désormais
  **Rules Screening**, configurée dans **Safety Setup** (Server Settings →
  Modération → Safety Setup → section *DM and Spam Protection* → *"Members
  must accept rules before they can talk or DM"*) — pas dans un onglet dédié
  comme dans les anciennes versions de l'interface Discord.
- **Prérequis rencontrés en pratique** : au moins 5 membres sur le serveur, 2FA
  activée sur le compte propriétaire, Verification Level ≥ Low, Explicit
  Content Filter sur "Scan media from all members", au moins 2 salons
  textuels + 2 salons vocaux. Ces prérequis expliquent pourquoi l'option peut
  rester invisible tant que le serveur est encore en cours de construction
  avec peu de monde dessus.
- Le salon `#règles` créé automatiquement par l'assistant Communauté est
  rendu manuellement en lecture seule (permissions de salon → `@everyone` →
  refuser *Envoyer des messages*) — ce n'est pas automatique.

## Rôles : Admin / Membre seulement

Un rôle **Nouveau** (accès restreint temporaire, retiré après premier
visionnage confirmé) avait été envisagé, puis abandonné : sans bot pour
l'attribuer/le retirer automatiquement, ça demande une gestion manuelle sans
réel bénéfice. L'attribution automatique d'un rôle par défaut via
l'Onboarding natif de Discord a aussi été écartée : elle exige au minimum 7
salons par défaut dont 5 ouverts en lecture/écriture à `@everyone` — un
modèle pensé pour de gros serveurs publics, disproportionné pour 10
personnes. Résultat : accès égal pour tout le monde dès l'arrivée (une fois
les règles acceptées), le rôle Membre reste un simple repère visuel attribué
à la main.

## Deux salons "système" distincts, volontairement séparés

- **`#accueil`** : statique, en lecture seule (même traitement que
  `#règles`), contient uniquement le message d'accueil épinglé (connexion
  Jellyfin, comment demander du contenu, lien vers `#règles` et
  `#bugs-et-problèmes`).
- **`#annonces`** : défini comme *System Messages Channel* (Server Settings
  → Overview), reçoit les messages système d'arrivée (`{user} a rejoint le
  serveur`) et accueillera plus tard les notifications automatiques (Seerr,
  Jellyfin) une fois le bot construit.

Les deux ont été volontairement séparés : sans ça, les arrivées successives
auraient fini par noyer le message d'accueil statique dans le flux, obligeant
à défiler pour le retrouver.

Le **Welcome Screen** (écran affiché une seule fois avant l'entrée sur le
serveur) reste distinct des deux : description courte + salons recommandés
(`#règles`, `#accueil`, `#annonces`, `#discussion`, `#demandes`).

## Demande de contenu : Jellyfin ou Seerr, pas de salon Discord dédié

Les demandes de contenu passent par l'intégration native Seerr du plugin
**Jellyfin-Enhanced** (déjà installé, voir
[runbook setup-jellyfin.md](../runbooks/setup-jellyfin.md)) plutôt que par un
salon Discord ou un plugin Jellyfin tiers dédié
(`jellyfin-plugin-seerr-bridge`, `JellyBridge`) — l'intégration native
suffit et évite une dépendance supplémentaire :

- `JellyseerrEnabled: true`, connecté en interne via `http://seerr:5055`
  (nom du conteneur Docker, pas d'IP LAN codée en dur pour cet appel
  serveur-à-serveur)
- `JellyseerrEnable4KRequests` / `JellyseerrEnable4KTvRequests` : `false` —
  cohérent avec le profil qualité Radarr plafonné à 1080p (ADR-007)
- `JellyseerrAutoImportUsers: true` — un compte Seerr est créé/lié
  automatiquement à la première connexion "Sign in with Jellyfin", aucune
  action manuelle
- Activé en supplément : `DownloadsPageEnabled` (suivi des téléchargements
  en cours via Sonarr/Radarr) et `CalendarPageEnabled` (calendrier des
  sorties à venir), tous deux en mode `UsePluginPages` (intégré nativement,
  pas de plugin Jellyfin additionnel requis)

Résultat : un utilisateur peut demander un film ou une série indifféremment
depuis la recherche Jellyfin ou depuis Seerr directement, un seul lien
(Jellyfin) à distribuer aux membres.

## Création de compte automatisée à l'arrivée : jugée faisable, pas construite

Techniquement possible (API Jellyfin `POST /Users/New` pour créer le compte,
mot de passe temporaire généré et envoyé en DM Discord, changement du mot de
passe encouragé à la première connexion ; le compte Seerr suit
automatiquement via `JellyseerrAutoImportUsers`). Explicitement classée comme
fonctionnalité candidate pour le futur bot Discord, pas construite
maintenant — la création de compte reste manuelle (faite par l'admin) tant
que le bot n'existe pas.

## Gamification (niveaux liés au temps de visionnage) : reportée

Idée jugée faisable (webhook Jellyfin `PlaybackStart` par utilisateur +
lecture des données Playback Reporting/Jellystat), mais représente un vrai
projet de bot à part entière (liaison de comptes Discord↔Jellyfin, calcul de
niveaux). Explicitement reportée à la discussion bot future, pas traitée
dans cette phase de construction du serveur.

## Conséquences

- Serveur Discord "Blackbox" créé, mode Communauté actif, non listé en
  Découverte.
- Structure : rôles Admin/Membre, salons `#règles` (lecture seule),
  `#accueil` (lecture seule, statique), `#annonces` (messages système +
  futures notifs), `#discussion`, `#demandes`, `#bugs-et-problèmes`.
- Rules Screening actif via Safety Setup.
- Description du serveur et Welcome Screen rédigés et publiés.
- Config Jellyfin-Enhanced étendue (Downloads/Calendar pages) sur le
  NucBox, en plus de l'intégration Seerr déjà active.
- Comptes invités (Wizarr), rôle Nouveau, création de compte automatisée et
  gamification : explicitement écartés ou reportés — voir sections
  ci-dessus pour le raisonnement, à ne pas reproposer sans relire cet ADR.
- Détail pas-à-pas dans
  [docs/runbooks/setup-discord.md](../runbooks/setup-discord.md).
