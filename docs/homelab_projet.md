# Projet Homelab — Serveur de streaming communautaire

**Localisation :** Woluwe-Saint-Lambert, Bruxelles
**Statut :** Phase de conception — installation prévue à l'arrivée de la fibre

> Ce document fixe la vision et l'architecture initiales du projet. Les
> décisions prises depuis sont tracées dans les [ADR](adr/) et l'état
> d'avancement dans le [README](../README.md) ; en cas de divergence, ces
> derniers font foi.

---

## 1. Vision du projet

Serveur de streaming personnel (films, séries, chaînes TV à la demande)
partagé avec une communauté restreinte de dix personnes (famille et amis
proches, sélectionnés par l'admin, aucun mineur). Chaque membre dispose d'un
accès individuel, peut demander du contenu, et le système s'autorégule pour
rester dans les limites de capacité du serveur et de la connexion internet.

Le projet a une double vocation : usage réel pour la communauté et vitrine
technique (repo structuré comme un environnement de production, à usage
portfolio/entretien d'embauche).

---

## 2. Communauté et gestion des accès

| Rôle | Qui | Droits |
|---|---|---|
| Admin/Dev | Le porteur du projet (seul) | Accès total : gestion serveur, comptes, config |
| Membre | Famille/amis, jusqu'à 10 | Visionnage + demande de contenu illimitée (tant qu'il y a de l'espace) |
| Invité | Temporaire | Accès limité dans le temps, expiration automatique |

- **Login unique** : les membres n'ont besoin que d'un compte Jellyfin —
  Jellyseerr (demande de contenu) s'authentifie nativement via ce même
  compte. Pas de SSO externe (Authentik/Authelia) : complexité inutile pour
  ce périmètre.
- **Gestion via Discord** : création de compte, suppression, reset password
  pilotés par un bot Discord qui appelle l'API Jellyfin.
- **Modération du contenu** : pas de téléchargement de saisons complètes en
  un coup, qualité plafonnée (voir §4).
- **Rétention** : contenu non consulté depuis un certain temps supprimé
  automatiquement (via Maintainerr).

---

## 3. Contenu et modération

- Suite *arr* pour l'automatisation : Prowlarr (indexeurs) → Sonarr
  (séries) / Radarr (films) → Bazarr (sous-titres) → qBittorrent
  (téléchargement, derrière VPN).
- Jellyseerr comme interface de demande utilisateur : approbation
  automatique ou manuelle selon le type de contenu (ex. auto pour les
  films, manuel pour les séries complètes).
- Maintainerr : suppression automatique du contenu non regardé après X
  jours (règle à définir).

**Point légal.** Le torrenting de contenu protégé par le droit d'auteur
reste illégal en Belgique/UE, avec ou sans VPN. Le VPN réduit le risque de
détection, il ne rend pas l'acte légal. Ce choix reste celui de l'admin.

---

## 4. Qualité vidéo et gestion de bande passante

- **Cible qualité** : 1080p, encodage HEVC recommandé plutôt que H.264 — le
  parc d'appareils prévu (PC, smartphone, iPad, AirPlay) décode nativement
  le HEVC, ce qui permet environ 5-6 Mbps par flux pour une qualité
  équivalente à ~8 Mbps en H.264.
- Le **4K** est réservé à l'usage local (réseau maison), pas au streaming
  distant.
- **Priorité au direct play** (pas de transcodage) : c'est le levier le
  plus important pour la capacité du serveur — une bibliothèque bien
  encodée en amont réduit fortement le besoin de transcodage à la volée.
- **Seuil critique** géré via un watcher qui interroge l'API Jellystat,
  avec deux niveaux :
  - seuil *soft* → alerte Discord ;
  - seuil *hard* → blocage des nouvelles connexions ou réduction de qualité
    forcée.
  - L'admin reste toujours prioritaire et n'est jamais bloqué.

### Estimation de capacité — 10 flux simultanés

| Facteur | Statut |
|---|---|
| Réseau interne (NucBox ↔ NAS) | Non limitant (2.5GbE largement suffisant) |
| Bande passante montante (upload fibre) | À confirmer — cible recommandée ≥ 100-120 Mbps pour tenir 10 flux confortablement |
| Transcodage matériel (Radeon 760M / VAAPI) | Risque non résolu au moment de la rédaction — bug connu sur des puces RDNA3 similaires (gfx1103) côté Jellyfin/VAAPI, à tester en priorité. Si le transcodage matériel est indisponible, la capacité réelle tombe à ~3-4 flux transcodés en logiciel |

---

## 5. Architecture matérielle

| Machine | Rôle | Composants hébergés |
|---|---|---|
| GMKtec NucBox M6 (Ryzen 5 7640HS, 32 Go RAM, 1 To SSD) | Serveur applicatif principal | Jellyfin, suite *arr*, Jellyseerr, qBittorrent+Gluetun, Jellystat, Maintainerr, Postgres partagé, reverse proxy/Cloudflare Tunnel |
| Ugreen DXP2800 (2×4 To) | Stockage pur | RAID (RAID1 4 To utiles protégés, ou RAID0 8 To sans redondance — arbitrage à trancher), partage réseau SMB/NFS. Reste sur UGOS Pro d'origine |
| Raspberry Pi 5 (8 Go) | Sentinelle, toujours allumé | Bot Discord, émetteur Wake-on-LAN, Home Assistant (monitoring conso via prise Shelly), watcher de seuil de streaming (surveillance externe) |
| Raspberry Pi Zero / 2W | Watchdog secondaire | Ping du RPi5 et alerte Discord (webhook) si la sentinelle ne répond plus. Non affecté pour l'instant (option : Pi-hole) |
| Switch managé | Réseau | Toujours allumé, indispensable au fonctionnement de la sentinelle |

**Note réseau.** Pas de routeur/pare-feu dédié dans l'inventaire au moment
de la rédaction (box fibre opérateur probable) : la segmentation VLAN
prévue initialement n'est pas réaliste dans l'immédiat, réseau à plat par
défaut en attendant.

**À ajouter :** onduleur (UPS + NUT), prise connectée avec mesure de
consommation (Shelly Plug S), éventuellement un second SSD en miroir pour
le NucBox (2ᵉ slot M.2 libre).

---

## 6. Accès distant et sécurité

- **Cloudflare Tunnel** pour l'accès public (Jellyfin/Jellyseerr) — pas de
  port forwarding, pas de dépendance à la config NAT de la box fibre. Usage
  conforme aux CGU actuelles de Cloudflare (le Tunnel/Zero Trust est une
  couche réseau distincte du CDN concerné par la restriction historique sur
  le streaming vidéo).
- **Tailscale** réservé à l'administration (SSH, dashboards admin,
  Sonarr/Radarr/Grafana), jamais exposé publiquement.
- **CrowdSec** sur les services exposés publiquement (protection
  brute-force).

---

## 7. Extinction programmée / réveil à la demande

- Plage de sommeil visée : 3h-11h, extinction complète (S5) si aucun flux
  actif.
- Avertissement Discord automatique avant extinction si une inactivité est
  détectée.
- Réveil : commande Discord `/reveiller` → paquet Wake-on-LAN envoyé par le
  RPi5 → boot du NucBox → services Docker démarrent (`restart:
  unless-stopped`) → confirmation Discord une fois l'API Jellyfin
  disponible.
- Les commandes admin (créer un compte, reset password) doivent déclencher
  un réveil automatique si le serveur dort au moment de la demande.

**Risque non confirmé au moment de la rédaction :** le support
Wake-on-LAN du NucBox M6 n'est pas vérifié — à tester en tout premier
(BIOS et comportement S5 réel), toute la logique d'extinction en dépend.

---

## 8. Ce qui nécessite du développement (vs déploiement pur)

La majorité du stack est du logiciel existant à déployer/configurer. Le
développement sur mesure se concentre sur un service Python (bot Discord +
tâches de fond) tournant sur le RPi5 :

1. **Bot Discord** : commandes admin (créer/supprimer/reset compte), réveil
   manuel et auto-réveil sur commande admin, mapping rôles Discord → droits.
2. **Watcher de seuil de streaming** : polling Jellystat, logique soft/hard,
   action d'enforcement (pas nativement disponible).
3. **Extinction automatique intelligente** : vérification d'activité +
   plage horaire + avertissement préalable.
4. **Gestion des comptes invités temporaires** : expiration automatique
   après durée définie.
5. **Watchdog (Pi Zero)** : script minimal de surveillance de la sentinelle.
6. *(Optionnel)* Rapport de consommation agrégé posté sur Discord.

**Ordre de développement recommandé :** WoL/extinction (risque le plus
élevé) → bot basique (réveil + statut) → gestion de comptes → watcher de
seuil → watchdog/rapport conso.

---

## 9. Organisation du repo et DevOps

**Structure monorepo :** infrastructure (Docker Compose multi-environnements
+ Ansible), bot Discord (code + tests), documentation (architecture, ADR,
runbooks).

**Environnements :**
- *Dev local* : stack complète avec données factices, serveur Discord de
  test séparé.
- *Staging* : même NucBox, projet Docker Compose distinct (`-p staging`),
  ports/volumes séparés, validation avant bascule prod.
- *Prod* : bascule après validation staging.

**CI/CD (GitHub Actions) :** lint/tests (pytest, mocks API) → build
d'images Docker multi-arch (x86_64 + arm64, `buildx`) → push GHCR →
déploiement via runner self-hosted sur le NucBox.

**Provisioning :** Ansible pour les deux machines (reproductibilité,
réinstallation rapide en cas de panne SD/disque).

**Ressources cloud :** Terraform, mais scopé uniquement aux ressources
Cloudflare (Tunnel, DNS, règles Access) — les machines physiques déjà
existantes relèvent d'Ansible.

**Secrets :** `.env` en `.gitignore` + `.env.example` documenté ; option
avancée SOPS + age pour secrets chiffrés versionnés.

**Documentation portfolio :** README avec schéma d'architecture, ADR
(Architecture Decision Records) expliquant les choix (Jellyfin vs Plex,
Cloudflare Tunnel vs port forwarding, etc.), CHANGELOG, badges CI.

---

## 10. Consommation électrique estimée

**Prix retenu :** environ 0,30 €/kWh TTC (moyenne Bruxelles, à ajuster
selon facture réelle — fourchette 0,28-0,35 €/kWh).

| Scénario | Conso/jour | Conso/an | Coût/an |
|---|---|---|---|
| Veille respectée (extinction 3h-11h) | ~0,91 kWh | ~333 kWh | ≈ 100 €/an |
| 24/7 sans extinction | ~1,08 kWh | ~394 kWh | ≈ 118 €/an |

**Constat.** L'écart entre les deux scénarios n'est que d'environ 18 €/an.
Les composants devant rester allumés en permanence (sentinelle RPi5,
watchdog, switch — ~336 Wh/jour, ~37 €/an à eux seuls) forment un socle fixe
qui limite mécaniquement le gain de la veille programmée. À valider avec
des mesures réelles une fois la prise connectée Shelly en place.

---

## 11. Estimation de temps

| Version | Durée estimée (temps partiel, ~10-15h/semaine) |
|---|---|
| MVP (streaming + demandes + bot basique) | 4 à 6 semaines |
| Version complète (watcher, CI/CD, doc soignée) | 2 à 3 mois |

**Recommandation :** lancement en deux temps — Jellyfin + Jellyseerr +
réveil manuel d'abord (communauté opérationnelle rapidement), puis
automatisation complète (bot, watcher, extinction) en tâche de fond.

---

## 12. Risques à valider en priorité (avant tout développement)

1. Wake-on-LAN sur le NucBox M6 — support non confirmé, bloquant pour toute
   la logique d'extinction/réveil.
2. Transcodage matériel VAAPI sur Radeon 760M — bug connu sur puces
   similaires, à vérifier via `vainfo` et un test de session réelle dans le
   dashboard Jellyfin.
3. Débit montant réel de la fibre — détermine la capacité réelle en flux
   distants simultanés.
4. Choix RAID1 vs RAID0 sur le NAS — arbitrage capacité vs sécurité des
   données, à trancher.

---

## 13. Points encore ouverts

- Règle précise de rétention Maintainerr (durée avant suppression
  automatique).
- Politique exacte d'approbation Jellyseerr par type de contenu.
- Durée par défaut des comptes invités temporaires.
- Arbitrage RAID1/RAID0 sur le DXP2800.
