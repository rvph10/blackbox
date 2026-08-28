# Runbook — serveur Discord communautaire

Contexte et choix : [ADR-008](../adr/008-discord-community.md).

## 1. Création du serveur

- Discord → `+` → **Créer un serveur** → **Créer le mien** → **Pour un club
  ou une communauté**
- Nom : `Blackbox`
- Pas de lien d'invitation public tant que la structure n'est pas finalisée

## 2. Mode Communauté

- Server Settings → **Communauté** → **Commencer**, suivre l'assistant
  (Verification Level, Explicit Content Filter, salon Rules + Community
  Updates créés automatiquement)
- Vérifier que **Découverte des serveurs** reste désactivée (Server Settings
  → Découverte) — le serveur ne doit pas être listé publiquement

## 3. Rôles

Server Settings → **Rôles** → `+` :
- **Admin** — permissions administrateur
- **Membre** — accès normal, attribué à la main (pas d'auto-attribution,
  voir ADR-008 pour le pourquoi)

## 4. Salons

| Salon | Catégorie | Permissions |
|---|---|---|
| `#règles` | Infos | Lecture seule (`@everyone` → refuser *Envoyer des messages*) |
| `#accueil` | Infos | Lecture seule, contient le message épinglé (§7) |
| `#annonces` | Infos | *System Messages Channel* (§6), futures notifs auto |
| `#discussion` | Général | Normal |
| `#demandes` | Général | Normal (discussion libre autour des demandes, pas le canal de demande lui-même — ça passe par Jellyfin/Seerr, §8) |
| `#bugs-et-problèmes` | Support | Normal |

## 5. Rules Screening (acceptation des règles)

L'interface a changé : ce n'est plus un onglet "Filtrage par règles" séparé.

1. Server Settings → **Modération** → **Safety Setup**
2. Section **DM and Spam Protection** → cocher **"Members must accept rules
   before they can talk or DM"**
3. Rédiger les règles (réutilise le salon `#règles`)
4. **Save**

Si l'option reste invisible/grisée, vérifier dans l'ordre :
- Au moins 5 membres sur le serveur
- 2FA activée sur le compte propriétaire (Server Settings → mon compte →
  Sécurité)
- Verification Level ≥ Low et Explicit Content Filter sur "Scan media from
  all members" (les deux dans Safety Setup)
- Au moins 2 salons textuels et 2 salons vocaux créés

### Règles retenues

```
# Règles du serveur

### 1. C'est du fait maison
Blackbox tourne sur du matériel personnel, pas sur un service pro. Ça peut planter, ralentir ou être hors ligne de temps en temps — c'est normal, pas la peine de paniquer.

### 2. Ton compte est à toi, pas à partager
Ne partage ni ton compte, ni l'invitation du serveur avec quelqu'un d'extérieur. Le serveur est dimensionné **pour nous**, pas pour s'agrandir — un compte de plus, c'est moins de place pour tout le monde.

### 3. Le contenu reste ici
Ce qui est regardé ou téléchargé via Blackbox *ne se redistribue pas* en dehors du groupe.

### 4. Tu arrêtes d'utiliser ton compte ? Préviens-moi
Ça libère de la place si quelqu'un d'autre en a besoin plus tard.

### 5. Un souci, tu le remontes
Bug, contenu manquant, souci de lecture — direction `#bugs-et-problèmes`, ça aide à améliorer le truc.
```

## 6. Welcome Screen, description, message système

- **Description du serveur** (Server Settings → Overview → Description,
  visible sur l'écran d'invitation) :
  > Blackbox, c'est notre propre plateforme de streaming, rien qu'à nous.
  > Films, séries, tout ce que t'as envie de voir, accessible à tout
  > moment. Tu proposes, on ajoute. Un espace simple et sans prise de tête,
  > pensé pour le groupe.

- **Welcome Screen** (Server Settings → Welcome Screen, affiché une seule
  fois avant l'entrée sur le serveur) :
  - Description (< 300 caractères) :
    > Bienvenue sur Blackbox, un serveur de streaming perso hébergé à la
    > maison. Films et séries disponibles pour le groupe, demandes de
    > contenu possibles. Projet fait sur mon temps libre, best-effort —
    > lis les règles avant de commencer.
  - Salons recommandés : `#règles`, `#accueil`, `#annonces`,
    `#discussion`, `#demandes`

- **Message système d'arrivée** : Server Settings → Overview → **System
  Messages Channel** → `#annonces` (pas `#accueil`, pour ne pas noyer le
  message épinglé sous les arrivées successives — voir ADR-008)

## 7. Message d'accueil (`#accueil`)

À poster puis épingler dans `#accueil` :

```
# Bienvenue sur Blackbox

Blackbox, c'est notre propre plateforme de streaming, rien qu'à nous. Films, séries, tout ce que t'as envie de voir, accessible à tout moment.

### Se connecter
Ton compte Jellyfin t'a été créé et transmis directement. Va sur le lien fourni et connecte-toi avec les identifiants reçus.

### Demander un film ou une série
Deux façons de faire, au choix :
- **Depuis Jellyfin** : cherche le titre dans la barre de recherche, même s'il n'est pas encore dans la bibliothèque — une option pour le demander apparaît directement.
- **Depuis Seerr** : même chose, en te connectant avec ton compte Jellyfin.

### Une envie de voir ce qui arrive bientôt ?
Un calendrier des sorties à venir est maintenant disponible directement dans Jellyfin.

### Un souci ?
Bug, contenu manquant, souci de lecture — direction `#bugs-et-problèmes`.

### Les règles
Un rapide rappel : `#règles`, ça vaut le coup d'y jeter un œil si ce n'est pas encore fait.
```

## 8. Intégration Seerr dans Jellyfin (plugin Jellyfin-Enhanced)

Déjà installé (voir [setup-jellyfin.md](setup-jellyfin.md)). Config
vérifiée directement dans le fichier du plugin sur le NucBox :

```
~/blackbox/prod/data/jellyfin/config/plugins/configurations/Jellyfin.Plugin.JellyfinEnhanced.xml
```

Réglages clés déjà actifs :
- `JellyseerrEnabled: true`, `JellyseerrUrls: http://seerr:5055` (nom du
  conteneur Docker, appel serveur-à-serveur — pas d'IP LAN codée en dur)
- `JellyseerrApiKey` : clé API Seerr (Settings → General → API Key côté
  Seerr)
- `JellyseerrShowSearchResults` / `JellyseerrShowDetailPageLink` : `true` —
  demande possible directement depuis la recherche et les fiches détail
- `JellyseerrEnable4KRequests` / `JellyseerrEnable4KTvRequests` : `false`
  (cohérent avec le profil qualité 1080p de Radarr, ADR-007)
- `JellyseerrAutoImportUsers: true` — compte Seerr lié automatiquement à la
  première connexion "Sign in with Jellyfin", rien à faire côté admin

Activés en plus le 2026-08-28 :
- `DownloadsPageEnabled` + `DownloadsUsePluginPages` : suivi des
  téléchargements en cours (via Sonarr/Radarr) directement dans Jellyfin
- `CalendarPageEnabled` + `CalendarUsePluginPages` : calendrier des sorties
  à venir des séries suivies

Édition faite via `sudo sed -i` sur le fichier de config puis
`docker compose restart jellyfin` pour recharger.

**Vérification** : chercher dans Jellyfin un titre absent de la
bibliothèque — il doit apparaître dans les résultats avec une option de
demande.

## 9. Ce qui a été délibérément écarté ou reporté

Voir [ADR-008](../adr/008-discord-community.md) pour le raisonnement
complet :
- Comptes invités (Wizarr) — abandonné, communauté fixe
- Rôle "Nouveau" et son attribution auto — abandonné, demande un bot pour
  peu de bénéfice
- Onboarding natif avec rôles par défaut — écarté (exige 7 salons par
  défaut dont 5 ouverts à `@everyone`)
- Création de compte Jellyfin/Seerr automatisée à l'arrivée — jugée
  faisable, reportée au futur bot
- Gamification par temps de visionnage — jugée faisable, reportée au futur
  bot
- Bandeaux de bienvenue stylés avec avatar — nécessitent un bot tiers
  (Welcomer, VibeBot...), pas natif Discord, non fait pour l'instant
