# Audit Homelab — Serveur de streaming communautaire

*Audit réalisé sur base du projet en phase de conception (Woluwe-Saint-Lambert,
Bruxelles). Périmètre : 10 utilisateurs maximum, double vocation usage réel
et portfolio technique.*

> Cet audit porte sur l'état du projet décrit dans [homelab_projet.md](homelab_projet.md)
> au moment de sa rédaction. Les décisions prises depuis sont tracées dans les
> [ADR](adr/) ; en cas de divergence, ces derniers font foi.

---

## 1. Modernité de la stack

| Techno | État au moment de l'audit | Verdict |
|---|---|---|
| Jellyfin | Actif, développement soutenu, alternative libre à Plex sans télémétrie | Pertinent |
| Suite *arr* (Prowlarr/Sonarr/Radarr/Bazarr) | Standard de facto homelab média, très mature | Pertinent |
| Jellyseerr | Fork actif d'Overseerr (abandonné), maintenu par la communauté Jellyfin | Pertinent, bon choix face à Overseerr |
| Jellystat | Outil de stats tiers, plus jeune, moins mature que le reste de la stack | À surveiller — dépendance à un projet plus petit pour une fonction critique (watcher de seuil) |
| Maintainerr | Actif, comble le vide laissé par les *arr* sur la rétention | Pertinent |
| qBittorrent + Gluetun | Standard robuste et éprouvé pour torrent derrière VPN | Pertinent |
| Cloudflare Tunnel | Solution moderne standard pour exposer un service sans port forwarding | Pertinent |
| Tailscale | Mature, largement adopté, bon choix pour l'admin | Pertinent |
| CrowdSec | Alternative moderne à Fail2ban, base de réputation communautaire | Pertinent, plus utile que Fail2ban seul |
| Docker Compose + Ansible | Standard IaC homelab, aucune raison de s'en écarter | Pertinent |
| Terraform (scope Cloudflare) | Usage raisonnable et limité, pas de sur-utilisation | Pertinent |
| HEVC comme cible d'encodage | Bon compromis à ce stade (support client large), AV1 encore trop tôt pour du direct play universel | Bon choix |

**Constat.** Stack cohérente et à jour, rien d'obsolète identifié. Le seul
point de vigilance est Jellystat, projet plus jeune sur lequel repose une
fonction opérationnelle importante (watcher de seuil). Ce n'est pas
rédhibitoire, mais un plan B (lecture directe des sessions actives via
l'API native Jellyfin) est à prévoir si Jellystat venait à être abandonné.

---

## 2. Architecture globale (bout en bout)

```
Internet
   │
   ▼
ONT fibre Proximus (VLAN 20)
   │
   ▼
Routeur/Firewall dédié [à ajouter — cf. §6]
   │
   ├── Cloudflare Tunnel ──► Jellyfin / Jellyseerr (public)
   ├── Tailscale ──► Admin uniquement (SSH, *arr* dashboards, Grafana futur)
   │
   ▼
Switch managé (24/7)
   │
   ├──────────────────────────────┐
   ▼                               ▼
NucBox M6 (Ryzen 5 7640HS)     Ugreen DXP2800 (NAS, RAID1 recommandé)
Docker Compose (prod/staging)   SMB/NFS via 2.5GbE
- Jellyfin (+ transcodage VAAPI)
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
- Ping du RPi5, alerte Discord si down
```

**Séparation des responsabilités.** Globalement saine : le NucBox
concentre le compute applicatif, le NAS le stockage pur, le RPi5
l'orchestration légère. Aucune dépendance circulaire identifiée.

**Points de défaillance uniques identifiés :**
- **RPi5** : concentre bot Discord, WoL et watcher de seuil. S'il tombe, la
  gestion des comptes, la capacité de réveiller le NucBox et l'enforcement
  des seuils sont perdus simultanément. Acceptable pour un homelab sans
  exigence de SLA, mais à documenter clairement comme risque assumé.
- **Absence de routeur dédié** au moment de l'audit : la box opérateur reste
  le seul point de contrôle réseau. Résolu si la recommandation du §6 est
  suivie.
- **Postgres unique** : si l'instance tombe, Sonarr, Radarr et Jellyseerr
  sont indisponibles simultanément. Acceptable à cette échelle (cf. §5).

---

## 3. Hardware et capacité

| Composant | Évaluation |
|---|---|
| NucBox M6 (Ryzen 5 7640HS, 32 Go, 1 To) | Bien dimensionné pour la charge applicative. Le CPU intègre un iGPU RDNA3 (Radeon 760M) — le point de capacité le plus incertain du projet (voir Risques). 32 Go de RAM est confortable, pas de sous-dimensionnement |
| Ugreen DXP2800 (2×4 To) | Correct pour la volumétrie visée. Limite : deux baies seulement, donc pas d'évolution de RAID possible sans tout remplacer — futur goulot d'étranglement si la bibliothèque grossit vite |
| RPi5 8 Go | Largement suffisant pour son rôle réduit (bot + watcher, sans haute disponibilité) |
| Switch managé | Adapté, permet le VLAN si un routeur dédié est ajouté |

**Dimensionnement.** Ni sur- ni sous-dimensionné dans l'ensemble. Le risque
principal n'est pas la capacité brute mais une fonctionnalité non confirmée
au moment de l'audit (transcodage matériel) qui conditionne la capacité
réelle en flux simultanés. Le NAS deux baies est le composant le plus
susceptible de devenir un goulot d'étranglement à moyen terme, faute
d'évolutivité RAID.

---

## 4. Virtualisation et compute

Docker directement sur l'hôte, sans couche de virtualisation (Proxmox).
Choix approprié.

Le projet n'a pas besoin d'isoler plusieurs OS ou plusieurs tenants : les
conteneurs Docker offrent une isolation suffisante pour ce niveau de
confiance (l'admin et dix personnes connues, pas de multi-tenant hostile).
Ajouter Proxmox introduirait un surcoût en ressources, une complexité de
sauvegarde des VM et une couche de restauration supplémentaire, sans
bénéfice réel ici.

Kubernetes n'est pas envisagé dans le projet, à raison. K8s n'a de sens qu'à
partir d'un besoin réel d'orchestration multi-nœuds à haute disponibilité,
ce qui n'est pas le cas ici (un seul hôte compute). L'utiliser serait de
l'overengineering, y compris à visée pédagogique : le ratio complexité/valeur
d'apprentissage serait moins bon que d'investir ce temps dans du IaC/CI-CD
soigné, ce que fait déjà le projet.

---

## 5. Réseau

### Situation au moment de l'audit → cible

Avant fibre : box Proximus non-fibre, réseau à plat, pas de routeur dédié.
À l'arrivée de la fibre : Proximus 500 Mbps symétrique, avec possibilité
confirmée de brancher un routeur personnel directement sur l'ONT (VLAN 20
taggé sur le WAN), en contournant l'Internet Box.

**Recommandation.** Profiter de l'installation de la fibre pour introduire
un routeur/firewall dédié dès le départ, plutôt que de le rajouter après
coup sur un réseau déjà en production — c'est le moment le moins coûteux
pour le faire.

### Segmentation recommandée (option B, voir §16)

| VLAN | Contenu | Règle |
|---|---|---|
| Management | RPi5, RPi Zero, interface admin NAS, switch | Accessible uniquement via Tailscale, jamais exposé |
| Services | NucBox (Docker) | Cloudflare Tunnel sortant uniquement pour Jellyfin/Jellyseerr ; pas d'entrée directe |
| Utilisateurs/IoT | Reste du réseau domestique | Pas d'accès direct au VLAN management |

### Flux à autoriser / interdire

- Autorisé : NucBox → Internet (sortant, pour *arr*, Cloudflare Tunnel,
  Gluetun VPN).
- Autorisé : NucBox ↔ NAS (SMB/NFS, interne).
- Autorisé : RPi5 → NucBox (API Jellyfin/Jellystat, WoL).
- Interdit : accès admin (Portainer, dashboards *arr*, Grafana futur)
  exposé publiquement — doit rester strictement Tailscale.
- Interdit : VLAN utilisateurs/invités → VLAN management (pas de confiance
  implicite).

**Bonnes pratiques déjà en place.** Pas de port forwarding prévu, admin
déjà cantonnée à Tailscale, exposition publique limitée à
Jellyfin/Jellyseerr via Cloudflare Tunnel. L'essentiel des bonnes pratiques
réseau est déjà couvert au niveau des services ; il manque la couche
physique (segmentation) pour compléter.

---

## 6. Stockage

- **RAID1 vs RAID0 : RAID1**, sans ambiguïté pour ce cas.
  - RAID0 (8 To) : zéro tolérance de panne. Un disque qui lâche entraîne la
    perte totale de la médiathèque, soit plusieurs semaines ou mois de
    re-téléchargement.
  - RAID1 (4 To utiles) : survit à une panne disque unique.
  - Rappel du principe central déjà posé dans le brief : le RAID n'est pas
    une sauvegarde. RAID1 protège contre une panne matérielle, pas contre
    une suppression accidentelle ou une corruption. Il ne remplace pas la
    stratégie de backup du §7.
  - Si 4 To s'avèrent trop justes à terme, la bonne réponse est un NAS
    quatre baies en RAID5/6, pas du RAID0.

- **Filesystem** : UGOS Pro (OS propriétaire Ugreen), pas de ZFS natif ni
  de snapshots avancés. C'est une limite acceptée du choix de ce NAS grand
  public plutôt qu'un TrueNAS ou Proxmox+ZFS. Pas rédhibitoire pour cet
  usage, mais à noter : sans snapshot natif ni checksumming avancé type
  ZFS, une surveillance SMART manuelle ou scriptée est recommandée.

- **Monitoring SMART** : rien de prévu au moment de l'audit — à ajouter
  (script `smartctl` planifié, alerte Discord en cas d'erreur SMART). Coût
  quasi nul, valeur de détection précoce élevée.

---

## 7. Sauvegardes et disaster recovery

**Situation au moment de l'audit : aucune sauvegarde.** C'est le point le
plus faible du projet à ce stade.

### Ce qui est réellement critique à sauvegarder

- Dumps Postgres (toutes les bases).
- Configs des conteneurs (`.env`, `docker-compose.yml`, volumes de config
  *arr*/Jellyfin).
- Code du bot Discord (déjà couvert par Git, sous réserve que le repo soit
  bien poussé).

### Ce qui n'a pas besoin de backup

- La médiathèque elle-même : volumineuse, redondante avec la source
  (ré-téléchargeable via la suite *arr*), coût de reconstruction élevé mais
  pas une perte de données irréversible.

### Recommandation

**rclone (remote `crypt`) → Google Drive (4,5 To déjà disponibles)**, si
possible via **restic** en backend rclone pour bénéficier du versioning et
de la déduplication plutôt qu'un simple mirror écrasé.

- Chiffrement côté client obligatoire avant upload : Google Drive n'est pas
  zero-knowledge, et les dumps de base de données et secrets potentiels y
  seraient stockés.
- Coût nul (espace déjà payé), volume concerné de l'ordre de quelques Go,
  largement sous le plafond de 750 Go/jour de Google Drive grand public.
- Planification via systemd timer, fréquence quotidienne suffisante pour ce
  périmètre.

### Logique RPO/RTO

- **RPO cible réaliste** : 24h (backup quotidien des configs/DB), acceptable
  pour un homelab non critique.
- **RTO** : dépend directement du niveau d'automatisation. Avec Ansible
  complet (provisioning), Git (code) et backup restic/rclone (configs/DB),
  plus une médiathèque re-téléchargeable, une reconstruction complète du
  NucBox est réaliste en quelques heures à une journée, hors temps de
  re-téléchargement média.

### Question de référence

*Si le homelab disparaît complètement ce soir, combien de temps pour
reconstruire un environnement fonctionnel ?*

Au moment de l'audit : indéterminé, faute de sauvegarde — même avec
Ansible/Git, l'historique Sonarr/Radarr (contenu déjà indexé/suivi), la
config Jellyfin (bibliothèques, utilisateurs) et les watchlists Jellyseerr
seraient perdus. Ce n'est pas une perte de données utilisateur
irremplaçable, mais plusieurs jours de reconfiguration manuelle seraient
nécessaires. C'est le premier chantier à traiter avant tout développement
supplémentaire.

---

## 8. Sécurité — modèle de menace

| Risque | Niveau | Détail |
|---|---|---|
| Pas de sauvegarde | Élevé | Cf. §7 — perte de configuration en cas de panne matérielle |
| Réseau à plat (avant fibre) | Moyen | Résolu si routeur dédié + VLAN mis en place à l'installation de la fibre |
| Postgres unique, pas de secrets management avancé | Faible-moyen | `.env` en `.gitignore` est le minimum correct ; SOPS+age en option avancée, pas indispensable à ce stade |
| Torrenting via qBittorrent+Gluetun | Moyen (légal, pas technique) | Le VPN réduit le risque de détection mais ne rend rien légal — point déjà noté et assumé par l'admin |
| Exposition Jellyfin/Jellyseerr via Cloudflare Tunnel | Faible | Bonne pratique (pas de port forwarding), CrowdSec en protection additionnelle |
| Accès admin exclusivement Tailscale | Faible | Bonne pratique, rien à changer |
| Support Wake-on-LAN non confirmé (au moment de l'audit) | Faible (opérationnel, pas sécurité) | Bloquant fonctionnel plutôt que risque sécurité, mais à tester en premier |
| Transcodage matériel VAAPI non confirmé (au moment de l'audit) | Faible (capacité, pas sécurité) | Impacte la capacité réelle, pas la sécurité |
| Pas de MFA mentionné sur les comptes Jellyfin | Faible | Jellyfin supporte le MFA nativement — à activer au minimum pour le compte admin |
| Images Docker | Faible | Stack standard, images généralement officielles/maintenues (linuxserver.io) |

**Priorité.** Le risque le plus critique à traiter en premier est
l'absence de sauvegarde (§7). Le reste est globalement bien géré pour un
homelab de ce périmètre.

---

## 9. Observabilité

Prévu au moment de l'audit : Jellystat (stats streaming), watcher de seuil
custom, alertes Discord (soft/hard threshold, watchdog RPi).

**Manques identifiés :**
- Aucune vue d'ensemble système (CPU/RAM/disque du NucBox, santé du NAS,
  température) — un Uptime Kuma ou Netdata léger sur le NucBox apporterait
  beaucoup de valeur pour un coût de configuration faible.
- Pas de conservation de logs centralisée — en cas de problème, il faudra
  fouiller `docker logs` service par service.

**Recommandation.** Ne pas viser une stack Prometheus/Grafana/Loki complète
dès le départ (surdimensionnée pour dix utilisateurs), mais ajouter Uptime
Kuma (monitoring de disponibilité simple, alertes Discord) en complément
du watcher existant — cela couvre le vrai manque (« un service est-il up »)
sans complexité disproportionnée. Grafana/Prometheus peuvent venir plus
tard comme brique pédagogique volontaire (portfolio), pas comme nécessité
opérationnelle immédiate.

---

## 10. Automatisation et Infrastructure as Code

Ansible (provisioning), Docker Compose (déploiement), Terraform scopé
Cloudflare et CI/CD GitHub Actions forment une combinaison cohérente et bien
scopée, chaque outil ayant un périmètre clair sans chevauchement inutile.

**Question de référence :** si le homelab doit être reconstruit à partir de
zéro avec uniquement le dépôt Git et les sauvegardes, est-ce possible ?

Au moment de l'audit : non, faute de sauvegarde (§7). Une fois cette brique
en place, la réponse devient oui — Ansible reconstruit l'OS et les
dépendances, Git contient le code et les configs versionnés, Terraform
recrée les ressources Cloudflare, restic/rclone restaure les données
Postgres et les configs. C'est un objectif atteignable, cohérent avec
l'ambition portfolio du projet.

---

## 11. Gestion opérationnelle

- Monorepo avec structure infra/bot/doc : choix approprié pour un projet
  solo de cette taille, pas besoin de dépôts séparés.
- ADR prévus dans la doc portfolio : bonne pratique, rare en homelab, forte
  valeur pour l'objectif entretien d'embauche.
- Environnements dev/staging/prod sur la même machine physique via des
  projets Compose séparés : pragmatique et suffisant à cette échelle, pas
  besoin de machines séparées.

**Manque identifié.** Aucun runbook de restauration au moment de l'audit
(cohérent, le projet est encore en conception). À prévoir dès que la
stratégie de backup (§7) est implémentée : un document court « comment
restaurer depuis zéro » a une valeur pédagogique et opérationnelle
disproportionnée par rapport à son coût de rédaction.

---

## 12. Complexité et overengineering

| Composant | Valeur | Complexité | Verdict |
|---|---|---|---|
| Suite *arr* + Jellyseerr | Élevée | Faible-moyenne | Indispensable |
| Cloudflare Tunnel | Élevée | Faible | Indispensable |
| Tailscale (admin) | Élevée | Faible | Indispensable |
| Bot Discord custom | Élevée (UX communauté) | Moyenne | Utile, cœur du projet |
| Watcher de seuil custom | Moyenne-élevée | Moyenne | Utile, pas nativement disponible ailleurs |
| Extinction/réveil programmé | Moyenne (économie ~18€/an) | Moyenne-élevée (dev + risque WoL) | Discutable, voir ci-dessous |
| CrowdSec | Moyenne | Faible | Utile, complément raisonnable |
| Staging séparé | Moyenne (portfolio) | Faible | Optionnel, ajouté pour l'apprentissage/portfolio, assumé |
| Terraform (Cloudflare only) | Faible-moyenne | Faible | Optionnel mais bien scopé, pas de sur-utilisation |
| Home Assistant | — | — | Retiré du périmètre |

**Extinction programmée (3h-11h) : point à challenger.** Le calcul même du
brief montre un gain réel d'environ 18 €/an seulement, le socle fixe
(RPi5, watchdog, switch, toujours allumés) limitant mécaniquement
l'économie possible. En face de ce gain marginal : du développement sur
mesure (bot, logique WoL, avertissement Discord), un risque non confirmé
(support WoL du NucBox) et un point de friction utilisateur (délai de
réveil pour la communauté).

Deux lectures possibles :
- **Lecture opérationnelle** : le rapport effort/gain est mauvais, 18 €/an
  ne justifie pas le risque ni le développement associé.
- **Lecture pédagogique (portfolio)** : la logique WoL, veille programmée
  et réveil orchestré constitue une démonstration d'automatisation
  intéressante à présenter en entretien — un choix assumé, à condition
  d'être documenté explicitement comme tel dans le README/ADR plutôt que
  présenté comme une optimisation de coût, ce qui ne résisterait pas à un
  chiffrage.

Recommandation : conserver la fonctionnalité mais la repositionner comme
démonstration technique plutôt qu'optimisation financière dans la doc
portfolio — c'est la présentation la plus honnête et la plus convaincante
en entretien.

---

## 13. Valeur pédagogique

Compétences réellement développées par ce projet :
- **Linux/Docker** : gestion de conteneurs, réseaux Docker, volumes.
- **Réseau** : VLAN (une fois le routeur ajouté), reverse proxy/tunnel, DNS.
- **Sécurité** : threat modeling léger, VPN, tunnel zero-trust, CrowdSec.
- **DevOps** : CI/CD multi-arch, workflow GitOps-like, provisioning Ansible.
- **Développement backend** : bot Discord Python, polling d'API (Jellystat),
  gestion d'état (comptes, seuils).
- **SRE** : logique de watcher/alerting, disponibilité, gestion d'incidents
  (watchdog).

Le projet présente une densité pédagogique réelle, bien au-delà d'une
simple installation de Jellyfin. Le bot Discord custom et le watcher de
seuil sont les éléments qui le distinguent le plus d'un tutoriel homelab
standard, à mettre en avant dans le portfolio.

**Suggestion.** Ajouter un test d'intégration simple dans la CI (par
exemple, valider que le `docker-compose` se lève correctement, healthchecks)
plutôt que du seul lint/unit test sur le bot — cela complète la
démonstration DevOps à faible coût.

---

## 14. Dette technique — sources identifiées

| Source | Cause | Impact | Probabilité | Difficulté de correction | Moment recommandé |
|---|---|---|---|---|---|
| Absence de backup | Pas encore implémenté | Élevé (perte de config en cas de panne) | Certaine à terme | Faible (rclone+restic à mettre en place) | Avant tout développement supplémentaire |
| RAID0 si retenu | Arbitrage capacité vs sécurité mal tranché | Élevé (perte totale de la médiathèque) | Moyenne | Faible si tranché maintenant, élevée après migration des données | Avant remplissage du NAS |
| Dépendance à Jellystat | Projet plus jeune que le reste de la stack | Moyen (watcher cassé en cas d'abandon) | Faible-moyenne | Moyenne (réécrire le watcher sur l'API Jellyfin native) | À surveiller, pas urgent |
| Pas de MFA sur les comptes Jellyfin | Non activé par défaut | Faible-moyen | Faible | Très faible (activation native) | Rapide, à faire tôt |
| NAS deux baies sans évolutivité RAID | Choix hardware initial | Moyen (goulot d'étranglement futur) | Moyenne à long terme | Élevée (remplacement matériel) | À anticiper, pas urgent |
| Réseau à plat si routeur dédié non ajouté | Dépendance à la box opérateur | Moyen | Faible si fibre + routeur suit le plan | Faible si fait maintenant | À l'installation de la fibre |

---

## 15. Alternatives sur les choix clés

### Sauvegarde
- **Option A — simple** : rclone seul (sync/copy chiffré vers Drive), sans
  versioning.
- **Option B — recommandée** : restic + backend rclone vers Google Drive
  chiffré, planifié en systemd timer. Meilleur compromis
  simplicité/robustesse.
- **Option C — avancée** : Kopia avec interface web, politiques de
  rétention fines et repository multi-cible (Drive + NAS local). Plus
  riche mais davantage de configuration à maintenir pour un gain marginal
  à cette échelle.

### Réseau
- **Option A — simple** : routeur consumer avec support VLAN basique (ex.
  TP-Link Omada, UniFi Express).
- **Option B — recommandée** : UniFi Cloud Gateway ou équivalent, bon
  compromis interface/fonctionnalités/coût, intégration VLAN + firewall
  simple, communauté large.
- **Option C — avancée** : OPNsense/pfSense sur mini PC dédié — plus de
  contrôle et de valeur pédagogique (règles firewall fines, IDS/IPS), mais
  davantage de temps d'administration et une machine supplémentaire à
  maintenir et sauvegarder.

### Observabilité
- **Option A — simple** : Uptime Kuma seul (disponibilité des services +
  alertes Discord).
- **Option B — recommandée** : Uptime Kuma + Netdata léger sur le NucBox
  (vue système en plus de la disponibilité).
- **Option C — avancée** : stack Prometheus + Grafana + Loki, forte valeur
  portfolio pour démontrer des compétences en observabilité, mais
  complexité et charge de maintenance disproportionnées pour le besoin
  opérationnel réel à dix utilisateurs.

---

## 16. Scoring

| Domaine | Score | Commentaire |
|---|---|---|
| Architecture | 8/10 | Séparation claire des responsabilités, cohérente une fois le routeur ajouté |
| Cohérence | 8/10 | Choix technos alignés entre eux, pas de couche contradictoire |
| Modernité | 9/10 | Stack à jour, rien d'obsolète |
| Sécurité | 6/10 | Bonne base (Tunnel, Tailscale, CrowdSec) mais absence de backup = risque réel |
| Fiabilité | 6/10 | Bonne conception mais risques non confirmés au moment de l'audit (WoL, VAAPI) et SPOF non documentés |
| Scalabilité | 6/10 | Suffisant pour dix utilisateurs, NAS deux baies limite l'évolution à moyen terme |
| Maintenabilité | 8/10 | Ansible + Git + doc/ADR prévus, bonne trajectoire |
| Automatisation | 7/10 | Bon socle CI/CD/Ansible, incomplet tant que le backup n'est pas automatisé |
| Observabilité | 5/10 | Watcher de seuil bien pensé, mais vue système globale manquante |
| Sauvegarde / DR | 3/10 | Le point faible du projet au moment de l'audit |
| Simplicité | 8/10 | Complexité globalement justifiée, pas de sur-ingénierie gratuite (hors extinction programmée à requalifier) |
| Valeur pédagogique | 9/10 | Densité d'apprentissage réelle et diversifiée, bien au-delà d'un déploiement standard |

**Note globale pondérée : 7/10** (pondérée, non une moyenne arithmétique).
Le score global est tiré vers le bas principalement par la sauvegarde
(3/10), considérée ici comme critique plutôt que comme un domaine parmi
d'autres, car son absence peut annuler d'un coup toute la valeur de
maintenabilité et d'automatisation construite par ailleurs. Une fois ce
point corrigé (effort faible, cf. §7), le projet remonterait naturellement
autour de 8,5-9/10.

---

## 17. Verdict

### Points solides
- Le choix de Docker direct sans virtualisation, proportionné et bien
  justifié.
- Le retrait de Home Assistant, bonne discipline de scope.
- Cloudflare Tunnel + Tailscale pour la séparation public/admin, exemplaire
  pour un homelab.
- La stack média (*arr* + Jellyseerr + Maintainerr), moderne, cohérente,
  complète.
- CI/CD multi-arch + Ansible + Terraform scopé, bonne discipline DevOps
  pour un développeur solo.
- L'absence de Kubernetes, bon jugement, pas de sur-ingénierie par effet
  de mode.

### Points qui méritent réflexion
- L'extinction programmée : à conserver mais à repositionner comme
  démonstration technique plutôt qu'optimisation de coût (le calcul ne
  tient pas).
- Le NAS deux baies : suffisant dans l'immédiat, contrainte probable dans
  un à deux ans si la bibliothèque grossit vite.
- La dépendance à Jellystat pour une fonction opérationnelle importante.

### Points à corriger

- Absence totale de sauvegarde, à corriger avant tout développement
  supplémentaire.
- RAID0 si c'est l'option retenue — RAID1 est le bon choix ici.
- Réseau à plat sans routeur dédié, à corriger dès l'installation de la
  fibre, pas après.

### Risques cachés

- Le RPi5 concentre trois fonctions critiques (bot, WoL, watcher) : une
  panne unique coupe toute l'orchestration.
- Le transcodage matériel VAAPI sur Radeon 760M est un bug connu et
  documenté sur des puces RDNA3 similaires (gfx1103/1150) : ne pas
  construire la logique de qualité vidéo en supposant qu'il fonctionnera.
- Pas de MFA activé sur les comptes Jellyfin exposés publiquement.

### Ce qui pourrait être retiré

Rien de structurel : la stack est déjà raisonnablement épurée. Le seul
candidat serait de repousser Prometheus/Grafana/Loki à plus tard (pas les
supprimer, juste ne pas les ajouter maintenant) tant qu'Uptime Kuma seul
couvre le besoin opérationnel réel.

### Pistes de modernisation

- Ajouter un monitoring système léger (Uptime Kuma au minimum), seul vrai
  manque d'observabilité au moment de l'audit.
- Basculer vers restic+rclone dès que possible pour combler le manque de
  sauvegarde.
- Prévoir le MFA sur les comptes Jellyfin admin au minimum.

### Priorités (meilleur rapport impact/effort)

1. Mettre en place le backup restic+rclone vers Google Drive (configs +
   Postgres) — effort faible, élimine le risque le plus critique.
2. Trancher RAID1 sur le NAS avant tout remplissage de données.
3. Tester le support Wake-on-LAN du NucBox (BIOS et comportement S5) —
   bloque toute la logique d'extinction, à faire en tout premier.
4. Introduire un routeur/firewall dédié à l'installation de la fibre, avec
   segmentation VLAN de base (management/services/utilisateurs).
5. Tester le transcodage matériel VAAPI réel (`vainfo` + session Jellyfin)
   avant de dimensionner la capacité de flux simultanés sur cette
   hypothèse.

### Architecture cible recommandée

L'architecture au moment de l'audit est déjà proche de la cible. Les seuls
ajouts recommandés :

1. Un routeur/firewall dédié avec trois VLAN (management/services/
   utilisateurs) branché directement sur l'ONT fibre.
2. Une routine de backup restic+rclone chiffrée vers Google Drive,
   automatisée en systemd timer, incluant Postgres et les configs.
3. RAID1 tranché sur le NAS avant migration des données.
4. Un Uptime Kuma léger sur le NucBox pour la vue de disponibilité globale.
5. Le reste de la stack (compute, Docker, *arr*, bot Discord, CI/CD,
   Ansible/Terraform) reste inchangé : c'est déjà une architecture
   cohérente, moderne et bien dimensionnée pour l'usage visé.

---

## Informations manquantes au moment de l'audit

- Politique exacte d'approbation Jellyseerr par type de contenu (déjà
  notée comme point ouvert dans le brief).
- Durée de rétention Maintainerr avant suppression automatique (idem).
- Durée par défaut des comptes invités temporaires (idem).
- OS exact prévu sur le NucBox — n'affecte pas l'audit mais utile pour les
  playbooks Ansible.
- Marque/modèle envisagé pour l'UPS, si déjà en réflexion, pour vérifier la
  compatibilité NUT avant achat.
