# ADR 018 — Live TV / IPTV : Threadfin devant le module natif Jellyfin

**Statut :** Proposé — en attente de la réponse du fournisseur IPTV (nombre
de connexions, specs de flux, support proxy). À passer en « Accepté » une
fois ces points tranchés.
**Date :** 2026-08-29

## Contexte

Le brief (§1) annonce « films, séries, **chaînes TV à la demande** » et le
runbook `setup-jellyfin.md` laisse le Live TV explicitement « pas
configuré, prévu nativement ». Il faut décider comment on ingère un flux
IPTV pour la communauté (~10 personnes) sans faire exploser la capacité du
NucBox ni improviser au moment de l'installation.

Deux questions distinctes : **quel logiciel** pour brancher l'IPTV sur
Jellyfin, et **quel coût ressources** réel.

## Contrainte structurante : une connexion = un flux

Les abonnements M3U du marché autorisent en général **1 à 3 flux
simultanés par compte**, et le fournisseur visé (type « Strong 8K »)
interdit explicitement le streaming simultané sur un compte unique et
recommande **l'achat de plusieurs comptes**.

Conséquence directe : pour ~10 personnes regardant des chaînes
différentes, il faut ~10 comptes (moins si on tolère de la contention).
Le buffer d'un proxy ne mutualise une connexion que pour les viewers sur
**la même chaîne**. C'est le vrai facteur limitant du projet, pas le
matériel. Le dimensionnement (nombre de comptes, prix en volume, comptes à
line-up identique pour load-balancing, usage concurrent depuis une seule
IP) fait l'objet du message au fournisseur — voir Points ouverts.

## Décision logicielle : Threadfin → module Live TV natif Jellyfin

| Option | Retenue ? |
|---|---|
| **Jellyfin Live TV seul** (M3U + XMLTV en direct) | Non. Fonctionne mais gestion des chaînes pénible sur un gros bouquet : pas de filtrage propre, mapping EPG manuel, renumérotation à la main, ré-scan lourd à chaque màj du M3U. |
| **Threadfin** (fork maintenu de xTeVe) en proxy | **Oui.** Ingère le M3U complet, on sélectionne les chaînes utiles, il mappe l'EPG XMLTV et expose un tuner **HDHomeRun** virtuel que Jellyfin détecte nativement. Buffering intégré (mutualisation des viewers sur une même chaîne), peut porter plusieurs jeux d'identifiants et répartir la charge entre comptes. Conteneur Go, s'aligne avec le style de la stack *arr*. |
| **TVHeadend** | Non. Backend DVR complet conçu pour de vrais tuners DVB, trop lourd pour l'usage. |
| dispatcharr / m3u-proxy | Non. Mêmes idées que Threadfin, moins éprouvés. |

## Coût ressources sur le NucBox

**Conteneur Threadfin :** négligeable. RAM idle ~30–60 Mo, ~150–300 Mo
sous charge avec buffers ; CPU quasi nul (remux MPEG-TS, aucun transcode
côté Threadfin) ; disque = EPG XMLTV (quelques Mo) + buffer ffmpeg par
flux actif (quelques centaines de Mo). `mem_limit: 512m` posé sur le
conteneur — c'est le seul service à bufferiser du réseau non maîtrisé.

**Coût réel = transcodage Jellyfin**, fonction du direct play vs transcode :

| Cas | Coût / flux | Note |
|---|---|---|
| Direct play (client compatible codec + conteneur) | ~1–2 % CPU (remux TS→HLS) | Fréquent sur apps natives (Android TV, Kodi) |
| Transcode vidéo VAAPI | ≈ 1 flux « ADR-006 » | Marge mesurée : 20+ flux avant de repasser sous le temps réel |
| Transcode + **désentrelacement** (chaînes 1080i, courant en IPTV) | ≈ **1,5 flux ADR-006** | Le deinterlace VAAPI coûte plus qu'un transcode simple |
| Transcode audio seul (AC3/EAC3 → AAC navigateur) | ~3–5 % CPU | Peu coûteux |

Estimation pessimiste : 10 flux 1080i tous transcodés+désentrelacés en
simultané ≈ **12–14 flux équivalents ADR-006** sur une capacité mesurée à
20+. Passe confortablement. Pic RAM +1–2 Go dans le tmpfs `/transcodes`
(plafonné à 4 Go, ADR-006) — **à surveiller, éventuellement porter à 6 Go**
si le Live TV s'ajoute à une charge VOD déjà élevée.

**Bande passante WAN :** chaque flux source IPTV ~5–12 Mbit/s en continu
tant que quelqu'un regarde. 10 flux ≈ 50–120 Mbit/s **entrants
permanents**, à additionner à l'upload des flux distants Jellyfin
(cible ≥ 100–120 Mbit/s upload, §4 du brief). Le débit fibre réel reste un
risque à valider (§12.3 du brief).

## Intégration dans l'archi existante

- **Pas d'exposition publique.** Le Live TV ne passe **pas** par le
  Cloudflare Tunnel (bande passante + CGU Cloudflare sur le streaming).
  Admin Threadfin accessible via Tailscale uniquement, comme les dashboards
  *arr* (ADR-015).
- Nouveau conteneur dans `infra/docker/prod/docker-compose.yml` (port
  34400, volume `./data/threadfin/conf`, `mem_limit: 512m`). Identifiants
  IPTV dans `.env` (jamais commités), `.env.example` documente les clés.
- EPG : URL XMLTV du fournisseur, complétée par une source type EPGShare si
  le guide fourni est trop pauvre.
- CrowdSec : rien à faire, trafic interne.
- DVR Jellyfin (enregistrements) : hors périmètre pour l'instant, à
  rouvrir plus tard avec une règle de rétention (cf. Maintainerr).

## Point légal

Même cadre que la suite *arr* (§3 du brief) : la rediffusion de flux IPTV
de chaînes protégées via un abonnement M3U tiers reste dans une zone grise
/ illégale en Belgique-UE selon les chaînes concernées. Choix assumé par
l'admin, restreint à la communauté fermée, aucune rediffusion publique.

## Points ouverts (bloquants pour le passage en « Accepté »)

1. Nombre de comptes à acheter pour ~10 flux concurrents — réponse
   fournisseur.
2. Possibilité de comptes à **line-up + EPG identiques** pour que Threadfin
   répartisse les viewers de façon transparente.
3. Usage concurrent de N comptes **depuis une seule IP résidentielle** :
   autorisé, ou risque de blocage ?
4. Specs de flux : codec (H.264/H.265), 1080p progressif ou 1080i
   entrelacé, bitrate moyen — détermine le budget transcodage et WAN
   ci-dessus.
5. Proxy Threadfin/xTeVe officiellement supporté par le fournisseur ?
6. Prix en volume et alignement des dates d'expiration des comptes.
7. Essai possible avant achat en volume.

## Conséquences (à l'acceptation)

- +1 conteneur (`threadfin`) dans le compose prod, entrées `.env` /
  `.env.example`, `mem_limit` posé.
- Section Live TV à écrire dans `docs/runbooks/setup-jellyfin.md`
  (sélection des chaînes, mapping EPG, ajout du tuner HDHomeRun virtuel
  côté Jellyfin, réglages de désentrelacement VAAPI).
- Éventuel passage du tmpfs `/transcodes` de 4 à 6 Go (à trancher après
  mesure).
- README : ligne ADR-018 + entrée « points ouverts » tant que le
  fournisseur n'a pas répondu.
- `docs/homelab_projet.md` §13 : point ouvert IPTV ajouté.
