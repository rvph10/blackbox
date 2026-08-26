# Audit Homelab — Serveur de Streaming Communautaire

*Audit réalisé sur base du projet en phase de conception (Woluwe-Saint-Lambert, Bruxelles). Périmètre : 10 utilisateurs max, double vocation usage réel + portfolio technique.*

---

## 1. Vérification de la modernité de la stack

| Techno | État actuel | Verdict |
|---|---|---|
| Jellyfin | Actif, développement soutenu, alternative libre à Plex sans télémétrie | ✅ Pertinent |
| Suite *arr* (Prowlarr/Sonarr/Radarr/Bazarr) | Standard de facto homelab média, très mature | ✅ Pertinent |
| Jellyseerr | Fork actif de Overseerr (abandonné), maintenu par la communauté Jellyfin | ✅ Pertinent, bon choix vs Overseerr |
| Jellystat | Outil de stats tiers, plus jeune, moins mature que le reste de la stack | 🟠 À surveiller — dépendance à un projet plus petit pour une fonction critique (watcher de seuil) |
| Maintainerr | Actif, complète bien le vide laissé par les *arr* sur la rétention | ✅ Pertinent |
| qBittorrent + Gluetun | Standard robuste et éprouvé pour torrent-derrière-VPN | ✅ Pertinent |
| Cloudflare Tunnel | Solution moderne standard pour exposer un service sans port forwarding | ✅ Pertinent |
| Tailscale | Mature, largement adopté, bon choix pour l'admin | ✅ Pertinent |
| CrowdSec | Alternative moderne à Fail2ban, base de réputation communautaire | ✅ Pertinent, plus utile que Fail2ban seul |
| Docker Compose + Ansible | Standard IaC homelab, aucune raison de s'en écarter | ✅ Pertinent |
| Terraform (scope Cloudflare) | Usage raisonnable et limité, pas de sur-utilisation | ✅ Pertinent |
| HEVC comme cible d'encodage | Bon compromis en 2026 (support client large), AV1 encore trop tôt pour du direct play universel | ✅ Bon choix, pas premature |

**Constat global** : stack cohérente et à jour, aucune techno obsolète. Le seul point de vigilance est **Jellystat**, projet plus jeune sur lequel repose une fonction opérationnelle importante (watcher de seuil). Ce n'est pas rédhibitoire, mais prévoir un plan B (lecture directe des sessions actives via l'API native Jellyfin) au cas où Jellystat serait abandonné.

---

## 2. Architecture globale (bout en bout)

```
Internet
   │
   ▼
ONT fibre Proximus (VLAN 20)
   │
   ▼
[À AJOUTER] Routeur/Firewall dédié (recommandé — cf §6)
   │
   ├── Cloudflare Tunnel ──► Jellyfin / Jellyseerr (public)
   ├── Tailscale ──► Admin only (SSH, *arr dashboards, Grafana futur)
   │
   ▼
Switch managé (24/7)
   │
   ├──────────────────────────────┐
   ▼                               ▼
NucBox M6 (Ryzen 5 7640HS)     Ugreen DXP2800 (NAS, RAID1 recommandé)
Docker Compose (prod/staging)   SMB/NFS via 2.5GbE
- Jellyfin (+ VAAPI transcoding)
- Prowlarr/Sonarr/Radarr/Bazarr
- qBittorrent + Gluetun
- Jellyseerr, Jellystat, Maintainerr
- Postgres (base par service)
- CrowdSec
   │
   ▼
RPi5 (sentinelle, 24/7)
- Bot Discord (comptes, WoL, réveil)
- Watcher de seuil (poll Jellystat)
- Extinction programmée intelligente
   │
   ▼
RPi Zero/2W (watchdog)
- Ping RPi5 + alerte Discord si down
```

**Séparation des responsabilités** : globalement saine. Le NucBox concentre le compute applicatif, le NAS le stockage pur, le RPi5 l'orchestration légère. Pas de dépendance circulaire identifiée.

**Single points of failure identifiés** :
- **RPi5** : concentre bot Discord + WoL + watcher de seuil. S'il tombe, tu perds la gestion des comptes ET la capacité de réveiller le NucBox ET le enforcement des seuils. Acceptable pour un homelab (pas de SLA), mais à documenter clairement comme risque assumé.
- **Absence de routeur dédié** (au moment de l'audit) : la box opérateur reste le seul point de contrôle réseau. Résolu si tu suis la recommandation §6.
- **Postgres unique** : si l'instance tombe, Sonarr/Radarr/Jellyseerr sont down simultanément. Acceptable à cette échelle (cf §5).

---

## 3. Hardware et capacité

| Composant | Évaluation |
|---|---|
| NucBox M6 (Ryzen 5 7640HS, 32 Go, 1 To) | Bien dimensionné pour la charge applicative. Le CPU 7640HS a un iGPU RDNA3 (Radeon 760M) — **le point de capacité le plus incertain du projet** (voir Risques). 32 Go RAM est confortable, pas de sous-dimensionnement. |
| Ugreen DXP2800 (2×4 To) | Correct pour la volumétrie visée. Limite : 2 baies seulement → pas d'évolution de RAID possible sans tout remplacer. Futur goulot d'étranglement si la bibliothèque grossit vite. |
| RPi5 8 Go | Largement suffisant pour son rôle réduit (bot + watcher, sans HA). |
| Switch managé | Adapté, permet VLAN si un routeur dédié est ajouté. |

**Verdict dimensionnement** : ni sur- ni sous-dimensionné dans l'ensemble. Le vrai risque n'est pas la capacité brute mais une **fonctionnalité non confirmée** (transcodage matériel) qui conditionne la capacité réelle en flux simultanés. Le NAS 2 baies est le composant le plus susceptible de devenir un goulot d'étranglement à moyen terme (pas d'évolutivité RAID).

---

## 4. Virtualisation et compute

Docker directement sur l'hôte, sans couche de virtualisation (Proxmox). **Bon choix.**

Justification : le projet n'a pas besoin d'isoler plusieurs OS ou plusieurs tenants — les conteneurs Docker offrent une isolation suffisante pour ce niveau de confiance (toi + 10 personnes connues, pas de multi-tenant hostile). Ajouter Proxmox introduirait : overhead ressources, complexité de sauvegarde des VM, une couche de restauration supplémentaire — sans bénéfice réel.

Kubernetes n'est pas envisagé dans le projet — c'est la bonne décision. K8s n'a de sens qu'à partir d'un besoin réel d'orchestration multi-nœuds avec haute dispo, ce qui n'est pas le cas ici (un seul hôte compute). L'utiliser serait de l'overengineering pur, même à visée pédagogique — le ratio complexité/valeur d'apprentissage serait mauvais comparé à investir ce temps dans du IaC/CI/CD bien fait, ce que fait déjà le projet.

---

## 5. Réseau

### Situation actuelle → cible

Aujourd'hui : box Proximus non-fibre, réseau à plat, pas de routeur dédié.
Dans 20 jours : fibre Proximus, 500 Mbps symétrique, **possibilité confirmée de brancher un routeur personnel directement sur l'ONT** (VLAN 20 taggé sur le WAN), contournant l'Internet Box.

**Recommandation forte** : profiter de l'installation de la fibre pour introduire un routeur/firewall dédié dès le départ, plutôt que de le rajouter après coup sur un réseau déjà en production. C'est le moment le moins coûteux pour le faire.

### Segmentation recommandée (Option B — voir §16)

| VLAN | Contenu | Règle |
|---|---|---|
| Management | RPi5, RPi Zero, interface admin NAS, switch | Accessible uniquement via Tailscale, jamais exposé |
| Services | NucBox (Docker) | Cloudflare Tunnel sortant uniquement pour Jellyfin/Jellyseerr ; pas d'entrée directe |
| Utilisateurs/IoT | Reste du réseau domestique | Pas d'accès direct au VLAN management |

### Flux à autoriser / interdire

- ✅ NucBox → Internet (sortant, pour *arr* + Cloudflare Tunnel + Gluetun VPN)
- ✅ NucBox ↔ NAS (SMB/NFS, interne)
- ✅ RPi5 → NucBox (API Jellyfin/Jellystat, WoL)
- ❌ Accès admin (Portainer, dashboards *arr*, Grafana futur) exposé publiquement — doit rester strictement Tailscale
- ❌ VLAN utilisateurs/invités → VLAN management (pas de confiance implicite)

### Erreurs classiques déjà évitées par le projet
Bon point : pas de port forwarding prévu, admin déjà cantonnée à Tailscale, exposition publique limitée à Jellyfin/Jellyseerr via Cloudflare Tunnel. C'est l'essentiel des bonnes pratiques déjà en place *pour les services*, il manque la couche réseau physique (segmentation) pour compléter.

---

## 6. Stockage

- **RAID1 vs RAID0 → RAID1**, sans ambiguïté pour ce cas.
  - RAID0 (8 To) : zéro tolérance de panne. Un disque qui lâche = perte totale de la médiathèque, plusieurs semaines/mois de re-téléchargement.
  - RAID1 (4 To utiles) : survit à une panne disque unique.
  - Rappel du principe central de ton propre brief : **RAID ≠ sauvegarde**. RAID1 protège contre une panne matérielle, pas contre une suppression accidentelle ou une corruption. Il ne remplace pas la stratégie de backup du §8.
  - Si 4 To s'avèrent trop justes à terme, la bonne réponse est un NAS 4 baies en RAID5/6, pas du RAID0.

- **Filesystem** : UGOS Pro (OS propriétaire Ugreen) — pas de ZFS natif ni de snapshots avancés. C'est une limite acceptée du choix de ce NAS grand public plutôt qu'un TrueNAS/Proxmox+ZFS. Pas rédhibitoire pour ce cas d'usage, mais à savoir : pas de snapshot natif ni de checksumming avancé type ZFS, donc surveillance SMART manuelle/scriptée recommandée.

- **Monitoring SMART** : rien de prévu actuellement — à ajouter (script simple type `smartctl` planifié, alerte Discord si erreurs SMART détectées). Coût quasi nul, valeur de détection précoce élevée.

---

## 7. Sauvegardes et Disaster Recovery

**Situation actuelle : aucune sauvegarde. C'est le point le plus faible du projet dans son état actuel.**

### Ce qui est réellement critique (à sauvegarder)
- Dumps Postgres (toutes les bases)
- Configs des conteneurs (`.env`, `docker-compose.yml`, volumes de config *arr*/Jellyfin)
- Code du bot Discord (déjà couvert par Git, si le repo est bien poussé)

### Ce qui n'a pas besoin de backup
- La médiathèque elle-même : volumineuse, redondante avec la source (ré-téléchargeable via la suite *arr*), coût de reconstruction élevé mais pas une perte de données irréversible.

### Recommandation
**rclone (remote `crypt`) → Google Drive (4.5 To déjà disponibles)**, idéalement via **restic** en backend rclone pour bénéficier du versioning et de la déduplication plutôt qu'un simple mirror écrasé.
- Chiffrement côté client **obligatoire** avant upload — Google Drive n'est pas zero-knowledge, et tu y stockeras des dumps de base de données et potentiellement des secrets.
- Coût : nul (espace déjà payé), volume concerné : quelques Go, largement sous le plafond de 750 Go/jour de Google Drive grand public.
- Planification via systemd timer, fréquence quotidienne suffisante pour ce périmètre.

### Logique RPO/RTO
- **RPO cible réaliste** : 24h (backup quotidien des configs/DB) — acceptable pour un homelab non critique.
- **RTO** : dépend directement du niveau d'automatisation. Avec Ansible complet (provisioning) + Git (code) + backup restic/rclone (configs/DB) + médiathèque redownloadable, une reconstruction complète du NucBox est réaliste en quelques heures à un jour, hors temps de re-téléchargement média.

### La question fondamentale
*« Si ton Homelab disparaît complètement ce soir, combien de temps pour reconstruire un environnement fonctionnel ? »*

Aujourd'hui : **indéterminé, car aucune sauvegarde n'existe** — même avec Ansible/Git, tu perdrais l'historique Sonarr/Radarr (ce qui est déjà indexé/suivi), la config Jellyfin (bibliothèques, utilisateurs), les watchlists Jellyseerr. Ce n'est pas la fin du monde (pas de perte de données utilisateur irremplaçable), mais plusieurs jours de reconfiguration manuelle seraient nécessaires. C'est le premier chantier à traiter avant tout développement supplémentaire.

---

## 8. Sécurité — Threat model

| Risque | Niveau | Détail |
|---|---|---|
| Pas de sauvegarde | 🔴 Élevé | Cf §7 — perte de configuration en cas de panne matérielle |
| Réseau à plat (avant fibre) | 🟠 Moyen | Résolu si routeur dédié + VLAN mis en place à l'installation de la fibre |
| Postgres unique, pas de secrets management avancé | 🟡 Faible-Moyen | `.env` en `.gitignore` est le minimum correct ; SOPS+age en option avancée, pas indispensable à ce stade |
| Torrenting via qBittorrent+Gluetun | 🟠 Moyen (légal, pas technique) | Le VPN réduit le risque de détection mais ne rend rien légal — point déjà noté et assumé par l'admin |
| Exposition Jellyfin/Jellyseerr via Cloudflare Tunnel | 🟡 Faible | Bonne pratique (pas de port forwarding), CrowdSec en protection additionnelle — cohérent |
| Accès admin exclusivement Tailscale | 🟢 Faible | Bonne pratique, rien à changer |
| Support Wake-on-LAN non confirmé | 🟡 Faible (opérationnel, pas sécurité) | Bloquant fonctionnel plutôt que risque sécurité, mais à tester en premier |
| Transcodage matériel VAAPI non confirmé | 🟡 Faible (capacité, pas sécurité) | Idem — impacte la capacité réelle, pas la sécurité |
| Pas de MFA mentionné sur les comptes Jellyfin | 🟡 Faible | Jellyfin supporte le MFA nativement — à activer au minimum pour le compte admin |
| Images Docker | 🟢 Faible | Stack standard, images officielles/maintenues (linuxserver.io généralement), pas de risque particulier identifié |

**Risque le plus critique à traiter en premier : l'absence de sauvegarde (§7).** Le reste est globalement bien géré pour un homelab de ce périmètre.

---

## 9. Observabilité

Actuellement prévu : Jellystat (stats streaming), watcher de seuil custom, alertes Discord (soft/hard threshold, watchdog RPi).

**Ce qui manque** :
- Aucune vue d'ensemble système (CPU/RAM/disque NucBox, santé NAS, température) — un léger Uptime Kuma ou Netdata sur le NucBox donnerait beaucoup de valeur pour un coût de configuration très faible.
- Pas de conservation de logs centralisée — en cas de problème, il faudra fouiller `docker logs` service par service.

**Recommandation proportionnée** : ne pas viser une stack Prometheus/Grafana/Loki complète tout de suite (overkill pour 10 utilisateurs), mais ajouter un **Uptime Kuma** (monitoring de disponibilité simple, alertes Discord) en complément du watcher existant. Ça comble le vrai manque (« est-ce qu'un service est up ? ») sans complexité disproportionnée. Grafana/Prometheus peuvent venir plus tard comme brique pédagogique volontaire (portfolio), pas comme nécessité opérationnelle immédiate.

---

## 10. Automatisation et Infrastructure as Code

Ansible (provisioning machines) + Docker Compose (déploiement) + Terraform scopé Cloudflare + CI/CD GitHub Actions : **c'est une combinaison cohérente et bien scopée**, chaque outil a un périmètre clair sans chevauchement inutile.

**Question du brief : « Si je dois reconstruire ce Homelab à partir de zéro avec uniquement mon dépôt Git et mes sauvegardes, est-ce possible ? »**

Réponse actuelle : **non**, car il manque la brique sauvegarde (§7). Une fois celle-ci en place, la réponse devient oui — Ansible reconstruit l'OS et les dépendances, Git contient le code/configs versionnés, Terraform recrée les ressources Cloudflare, restic/rclone restaure les données Postgres et configs. C'est un objectif atteignable et cohérent avec l'ambition portfolio du projet.

---

## 11. Gestion opérationnelle

- Monorepo avec structure infra/bot/doc : bon choix pour un projet solo de cette taille (pas besoin de repos séparés).
- ADR prévus dans la doc portfolio : excellente pratique, rare en homelab, forte valeur pour l'objectif entretien d'embauche.
- Environnements dev/staging/prod sur la même machine physique via projets Compose séparés : pragmatique et suffisant à cette échelle — pas besoin de machines séparées.

**Manque identifié** : aucun runbook de restauration mentionné à ce stade (logique, tout est en conception). À prévoir dès que la stratégie de backup (§7) est implémentée : un document court « comment restaurer depuis zéro » a une valeur pédagogique et opérationnelle disproportionnée par rapport à son coût de rédaction.

---

## 12. Complexité et overengineering

| Composant | Valeur | Complexité | Verdict |
|---|---|---|---|
| Suite *arr* + Jellyseerr | Élevée | Faible-moyenne | Indispensable |
| Cloudflare Tunnel | Élevée | Faible | Indispensable |
| Tailscale (admin) | Élevée | Faible | Indispensable |
| Bot Discord custom | Élevée (UX communauté) | Moyenne | Utile, cœur du projet |
| Watcher de seuil custom | Moyenne-élevée | Moyenne | Utile, pas nativement disponible ailleurs |
| Extinction/réveil programmé | Moyenne (économie ~18€/an) | Moyenne-élevée (dev + risque WoL) | **Discutable** — voir ci-dessous |
| CrowdSec | Moyenne | Faible | Utile, complément raisonnable |
| Staging séparé | Moyenne (portfolio) | Faible | Optionnel, ajouté pour l'apprentissage/portfolio — assumé |
| Terraform (Cloudflare only) | Faible-moyenne | Faible | Optionnel mais bien scopé, pas de sur-utilisation |
| Home Assistant | — | — | Retiré (bon appel) |

**Point à challenger frontalement : l'extinction programmée (3h-11h).**

Le calcul même du projet montre que le gain réel n'est que d'environ **18 €/an**, car le socle fixe (RPi5, watchdog, switch, toujours allumés) limite mécaniquement l'économie. En face de ce gain financier marginal, il y a : du développement sur-mesure (bot, logique WoL, avertissement Discord), un risque non confirmé (support WoL du NucBox), et un point de friction utilisateur (délai de réveil pour la communauté).

Deux lectures possibles :
- **Lecture "produire"** : ce n'est pas rentable économiquement — le rapport effort/gain est mauvais, 18€/an ne justifie pas le risque et le développement.
- **Lecture "apprendre" (portfolio)** : la logique WoL + veille programmée + réveil orchestré est un morceau d'automatisation intéressant à montrer en entretien — c'est un choix pédagogique assumé, pas de l'overengineering aveugle, **à condition** que tu le documentes explicitement comme tel dans le README/ADR plutôt que de le présenter comme une optimisation de coût (ce qui ne résisterait pas à un chiffrage).

Je ne le retirerais pas, mais je le repositionnerais : ce n'est pas une optimisation financière, c'est une démonstration technique. Formule-le ainsi dans ta doc portfolio, ce sera plus honnête et plus convaincant en entretien qu'un argument ROI qui ne tient pas.

---

## 13. Architecture pédagogique

Compétences réellement développées par ce projet :
- **Linux/Docker** : gestion de conteneurs, réseaux Docker, volumes
- **Réseau** : VLAN (une fois le routeur ajouté), reverse proxy/tunnel, DNS
- **Sécurité** : threat modeling léger, VPN, tunnel zero-trust, CrowdSec
- **DevOps** : CI/CD multi-arch, GitOps-like workflow, Ansible provisioning
- **Développement backend** : bot Discord Python, API polling (Jellystat), gestion d'état (comptes, seuils)
- **SRE** : logique de watcher/alerting, disponibilité, gestion d'incidents (watchdog)

C'est un projet avec une **vraie densité pédagogique**, bien au-delà d'un simple "j'installe Jellyfin". Le bot Discord custom et le watcher de seuil sont les pièces qui démarquent vraiment ce projet d'un tutoriel homelab standard — à mettre en avant dans le portfolio.

**Suggestion à valeur ajoutée sans complexité disproportionnée** : ajouter un test d'intégration simple dans la CI (ex: valider que le docker-compose se lève correctement, healthchecks) plutôt que juste lint/unit tests sur le bot — ça complète la démonstration DevOps à faible coût.

---

## 14. Dette technique — sources identifiées

| Source | Cause | Impact | Probabilité | Difficulté correction | Moment recommandé |
|---|---|---|---|---|---|
| Absence de backup | Pas encore implémenté | Élevé (perte config en cas de panne) | Certaine à terme | Faible (rclone+restic à mettre en place) | **Avant tout développement** |
| RAID0 si choisi | Arbitrage capacité vs sécurité mal tranché | Élevé (perte totale médiathèque) | Moyenne | Faible si tranché maintenant, élevée après migration des données | **Avant remplissage du NAS** |
| Dépendance à Jellystat | Projet plus jeune que le reste de la stack | Moyen (watcher cassé si abandon) | Faible-moyenne | Moyenne (réécrire watcher sur API Jellyfin native) | À surveiller, pas urgent |
| Pas de MFA sur comptes Jellyfin | Non activé par défaut | Faible-moyen | Faible | Très faible (activation native) | Rapide, à faire tôt |
| NAS 2 baies sans évolutivité RAID | Choix hardware initial | Moyen (goulot d'étranglement futur) | Moyenne à long terme | Élevée (remplacement matériel) | À anticiper, pas urgent |
| Réseau à plat si routeur dédié non ajouté | Dépendance à la box opérateur | Moyen | Faible si fibre+routeur suit le plan | Faible si fait maintenant | **À l'installation de la fibre** |

---

## 15. Alternatives sur les choix clés

### Sauvegarde
- **Option A — Simple** : rclone seul (sync/copy chiffré vers Drive), sans versioning.
- **Option B — Recommandée** : restic + backend rclone vers Google Drive chiffré, planifié en systemd timer. Meilleur compromis simplicité/robustesse.
- **Option C — Avancée** : Kopia avec interface web + politiques de rétention fines + repository multi-cible (Drive + NAS local). Plus riche mais plus de configuration à maintenir pour un gain marginal à cette échelle.

### Réseau
- **Option A — Simple** : routeur consumer avec support VLAN basique (ex: TP-Link Omada, UniFi Express).
- **Option B — Recommandée** : UniFi Cloud Gateway ou équivalent — bon compromis interface/fonctionnalités/coût, intégration VLAN + firewall simple, communauté large.
- **Option C — Avancée** : OPNsense/pfSense sur mini PC dédié — plus de contrôle et de valeur pédagogique (règles firewall fines, IDS/IPS), mais plus de temps d'administration et une machine supplémentaire à maintenir/sauvegarder.

### Observabilité
- **Option A — Simple** : Uptime Kuma seul (dispo services + alertes Discord).
- **Option B — Recommandée** : Uptime Kuma + Netdata léger sur le NucBox (vue système en plus de la dispo).
- **Option C — Avancée** : stack Prometheus + Grafana + Loki — forte valeur portfolio si tu veux démontrer des compétences observabilité, mais complexité et charge de maintenance disproportionnées pour le besoin opérationnel réel à 10 utilisateurs.

---

## 16. Scoring

| Domaine | Score | Commentaire |
|---|---|---|
| Architecture | 8/10 | Séparation claire des responsabilités, cohérente une fois le routeur ajouté |
| Cohérence | 8/10 | Choix technos alignés entre eux, pas de couche contradictoire |
| Modernité | 9/10 | Stack à jour, rien d'obsolète |
| Sécurité | 6/10 | Bonne base (Tunnel, Tailscale, CrowdSec) mais absence de backup = risque réel |
| Fiabilité | 6/10 | Bonne conception mais risques non confirmés (WoL, VAAPI) et SPOF non documentés |
| Scalabilité | 6/10 | Suffisant pour 10 users, NAS 2 baies limite l'évolution à moyen terme |
| Maintenabilité | 8/10 | Ansible + Git + doc/ADR prévus, bonne trajectoire |
| Automatisation | 7/10 | Bon socle CI/CD/Ansible, incomplet tant que backup n'est pas automatisé |
| Observabilité | 5/10 | Watcher de seuil bien pensé, mais vue système globale manquante |
| Sauvegarde / DR | **3/10** | Le point faible du projet actuellement |
| Simplicité | 8/10 | Complexité globalement justifiée, pas de sur-ingénierie gratuite (hors extinction programmée à requalifier) |
| Valeur pédagogique | 9/10 | Densité d'apprentissage réelle et diversifiée, bien au-delà d'un déploiement standard |

**Note globale pondérée : 7/10** (et non une moyenne arithmétique). Le score global est tiré vers le bas principalement par la **sauvegarde (3/10)**, qui est un domaine que je considère critique — pas simplement "un domaine parmi d'autres" — car son absence peut annuler d'un coup toute la valeur de maintenabilité et d'automatisation construite par ailleurs. Une fois ce point corrigé (effort faible, cf §7), le projet remonterait naturellement autour de 8.5-9/10.

---

## 17. Verdict final

### 🟢 Ce qui est solide
- Le choix de Docker direct sans virtualisation — proportionné et bien justifié
- Retrait de Home Assistant — bonne discipline de scope
- Cloudflare Tunnel + Tailscale pour la séparation public/admin — exemplaire pour un homelab
- Stack média (*arr* + Jellyseerr + Maintainerr) — moderne, cohérente, complète
- CI/CD multi-arch + Ansible + Terraform scopé — bonne discipline DevOps pour un solo dev
- Absence de Kubernetes — bon jugement, pas de sur-ingénierie par mode

### 🟠 Ce qui mérite réflexion
- L'extinction programmée : à conserver mais à repositionner comme démonstration technique plutôt qu'optimisation de coût (le calcul ne tient pas)
- Le NAS 2 baies : suffisant maintenant, probable contrainte dans 1-2 ans si la bibliothèque grossit vite
- Dépendance à Jellystat pour une fonction opérationnelle importante

### 🔴 Ce que je changerais
- **Absence totale de sauvegarde** — à corriger avant tout développement supplémentaire
- **RAID0** si c'est l'option retenue — RAID1 est le bon choix ici
- **Réseau à plat sans routeur dédié** — à corriger dès l'installation de la fibre, pas après

### 🧨 Les risques cachés
- Le RPi5 concentre trois fonctions critiques (bot, WoL, watcher) — une panne unique coupe toute l'orchestration
- Le transcodage matériel VAAPI sur Radeon 760M est un bug connu et documenté sur les puces RDNA3 similaires (gfx1103/1150) — ne pas construire la logique de qualité vidéo en supposant qu'il fonctionnera
- Pas de MFA activé sur les comptes Jellyfin exposés publiquement

### 🧹 Ce que je supprimerais
- Rien de structurel — la stack est déjà raisonnablement épurée. Le seul candidat serait de repousser Prometheus/Grafana/Loki à plus tard (pas les supprimer, juste ne pas les ajouter maintenant) tant qu'Uptime Kuma seul couvre le besoin opérationnel réel

### 🚀 Ce que je moderniserais
- Ajouter un monitoring système léger (Uptime Kuma minimum) — actuellement le seul vrai manque d'observabilité
- Basculer vers restic+rclone dès que possible pour fermer le trou de sauvegarde
- Prévoir MFA sur les comptes Jellyfin admin au minimum

### 🎯 Mes 5 priorités (meilleur rapport impact/effort)
1. **Mettre en place le backup restic+rclone vers Google Drive** (configs + Postgres) — effort faible, risque éliminé le plus critique
2. **Trancher RAID1 sur le NAS** avant tout remplissage de données
3. **Tester le support Wake-on-LAN du NucBox** (BIOS + comportement S5) — bloque toute la logique d'extinction, à faire en tout premier comme déjà identifié dans ton propre plan
4. **Introduire un routeur/firewall dédié à l'installation de la fibre** avec segmentation VLAN de base (management / services / utilisateurs)
5. **Tester le transcodage matériel VAAPI réel** (`vainfo` + session Jellyfin) avant de dimensionner la capacité de flux simultanés sur cette hypothèse

### 🏗️ Architecture cible recommandée

L'architecture actuelle est déjà à ~85% de la cible. Les seuls ajouts recommandés :
1. Un routeur/firewall dédié avec 3 VLAN (management/services/utilisateurs) branché directement sur l'ONT fibre
2. Une routine de backup restic+rclone chiffrée vers Google Drive, automatisée en systemd timer, incluant Postgres + configs
3. RAID1 tranché sur le NAS avant migration des données
4. Un Uptime Kuma léger sur le NucBox pour la vue de disponibilité globale
5. Le reste de la stack (compute, Docker, *arr*, bot Discord, CI/CD, Ansible/Terraform) reste inchangé — c'est déjà une architecture cohérente, moderne et bien dimensionnée pour l'usage visé.

---

## ❓ Informations manquantes (pour affiner encore l'audit)

- Politique exacte d'approbation Jellyseerr par type de contenu (déjà noté comme point ouvert dans ton doc)
- Durée de rétention Maintainerr avant suppression automatique (idem)
- Durée par défaut des comptes invités temporaires (idem)
- OS exact prévu sur le NucBox (Debian/Ubuntu ?) — n'affecte pas l'audit mais utile pour les playbooks Ansible
- Marque/modèle envisagé pour l'UPS, si déjà en réflexion, pour vérifier la compatibilité NUT avant achat
