# Philosophie d'Architecture

Pourquoi j'ai construit le homelab comme ça. Les principes qui guident mes choix.

## Principes Fondamentaux

### 1. Isolation Réseau

**Principe** : Création d'un réseau homelab dédié (192.168.10.0/24) isolé de la Box FAI via OPNsense en mode PPPoE.

**Pourquoi** :

- Contrôle total du réseau (DNS, DHCP, firewall)
- Évite les conflits avec le réseau de la Box
- Permet de redémarrer/reconfigurer sans casser le WiFi de la maison
- Sécurité : filtrage du trafic entrant/sortant

**Trade-off accepté** :

- Si OPNsense crash, plus d'Internet sur le homelab
- Mais le WiFi de la Box continue pour les devices critiques (phone, etc.)

### 2. Cœur Virtualisé (Proxmox)

**Principe** : Le GMKtec centralise le routage (OPNsense VM) et la puissance de calcul (VMs/LXCs).

**Pourquoi** :

- VMs = Isolation forte pour services lourds (Jellyfin, Downloads)
- LXCs = Léger pour services simples (Vaultwarden, etc.)
- Snapshots = Restore rapide si je casse quelque chose
- Hardware moderne = Transcode GPU + basses consos

**Alternatives rejetées** :

- Bare metal Docker : Moins flexible, pas de snapshots
- Kubernetes : Overkill pour usage perso, complexité inutile
- Serveur dédié sans virtualisation : Impossible de tester sans tout casser

### 3. Services Critiques Externalisés (Raspberry Pi)

**Principe** : DNS (AdGuard) et Domotique (Home Assistant) tournent sur un Raspberry Pi indépendant.

**Pourquoi** :

- Résilience : Si Proxmox crash ou en maintenance, DNS + Domotique continuent
- DNS sur Raspberry = résolution locale même si GMKtec est éteint
- Raspberry Pi boot vite et consomme peu (3-8W)
- Séparation des responsabilités : Control Tower vs Compute

**Services critiques** :

- AdGuard Home (DNS + blocage ads)
- Home Assistant (domotique doit être toujours UP)
- Homepage (dashboard local)
- Tailscale (accès distant)

**Services non-critiques** (peuvent tolérer downtime) :

- Jellyfin, Immich, Nextcloud, etc. → Sur Proxmox

### 4. Accès Distant "Zero Trust" (Tailscale)

**Principe** : Stratégie "DNS Public / IP Privée"

**Comment ça marche** :

1. Les services ont des noms de domaine publics (`jellyfin.blackbox.homes`)
2. Certificats SSL valides (Let's Encrypt via DNS Challenge)
3. Mais les IPs pointent vers Tailscale (100.x.y.z) ou LAN (192.168.10.x)
4. Aucun port ouvert sur WAN

**Pourquoi** :

- Sécurité : Pas d'exposition publique
- HTTPS : Certificats valides pour tous les services
- Mobilité : Accès depuis n'importe où via Tailscale
- Pas de port forwarding = pas de scans/attaques

**Alternatives rejetées** :

- Port forwarding : Exposition publique = risque de sécurité
- Cloudflare Tunnel : Dépendance externe, latence, limitations
- VPN classique (OpenVPN/WireGuard self-hosted) : Plus complexe à maintenir que Tailscale

### 5. Stratégie de Backup 3-2-1

**Principe** : 3 copies, 2 supports, 1 hors-site

**Implémentation** :

- **3 copies** :

  1. Données live (NAS Cargo)
  2. Snapshots Btrfs locaux (NAS)
  3. Backup cloud (Backblaze B2)

- **2 supports** :

  1. RAID 1 miroir (protection hardware)
  2. Btrfs snapshots (protection logique - erreurs, suppressions)

- **1 hors-site** :
  - Rclone quotidien vers Backblaze B2
  - Chiffrement client-side
  - Retention 30 jours

**Pourquoi** :

- RAID ≠ backup (protège juste contre défaillance disque)
- Snapshots = rollback rapide en cas d'erreur
- Cloud = protection contre incendie/vol/catastrophe
- Backblaze B2 = moins cher que S3 pour cold storage

**Ce que je NE backup PAS** :

- Media (films/séries) : Re-téléchargeable
- Cache/logs : Éphémère
- OS des VMs : Reconstruit via Ansible

### 6. "Nuke & Pave" Mindset

**Principe** : Tout doit pouvoir être reconstruit depuis zéro rapidement.

**Comment** :

- Infrastructure as Code (Ansible playbooks)
- Secrets dans Vault (vault.yml chiffré)
- Documentation à jour (ce que tu lis là)
- Appdata sur NFS (données persistentes hors VMs)

**Scénario "J'ai tout cassé"** :

1. Réinstaller Proxmox (30 min)
2. Lancer `bootstrap_pve.yml` (15 min)
3. Créer VMs/LXCs (30 min)
4. Services redémarrent avec appdata NFS intact (5 min)
5. **Total : ~1h30** pour reconstruire tout

**Pourquoi** :

- Pas de peur de tester/casser
- Upgrades majeures = rebuild from scratch
- Évite "configuration drift" (config qui diverge de la doc)

### 7. Simplicité > Fonctionnalités

**Principe** : Éviter la complexité inutile.

**Exemples** :

- Pas de VLANs (single flat network suffit)
- Pas de Kubernetes (Docker Compose suffit)
- Pas de HA Proxmox cluster (1 nœud suffit pour usage perso)
- Pas de monitoring ultra-poussé (Grafana simple suffit)

**Pourquoi** :

- Moins de complexité = moins de points de défaillance
- Maintenance plus facile
- Je suis seul à gérer, donc simplicité = longévité

**Quand j'ajoute de la complexité** :

- Si ça résout un vrai problème que je rencontre
- Pas pour "apprendre" ou "faire comme les pros"
- Exemples : GPU passthrough (vraiment utile), Tailscale (vraiment pratique)

### 8. Performance vs Coût Électrique

**Principe** : Hardware moderne low-power pour tourner 24/7.

**Choix matériels** :

- GMKtec Ryzen 5 7640HS : Excellent perf/watt
- Intel N100 (NAS) : 6W TDP, parfait pour stockage
- Raspberry Pi 5 : 3-8W, idéal services légers

**Conso totale** : ~33W idle, ~71W charge moyenne

**Coût annuel** : ~72-156€/an (selon charge)

**Pourquoi** :

- Tourne 24/7 donc conso = coût récurrent
- Hardware moderne = moins de chaleur = moins de bruit
- Évite besoin de climatisation dans rack

**Alternatives rejetées** :

- Serveurs rack enterprise : Bruyants, consommation 200-400W
- Vieux hardware "gratuit" : Conso excessive, perfs médiocres

### 9. Acceptation du Risque

**Risques acceptés** :

1. **Single Point of Failure (Proxmox)** :

   - Si GMKtec crash → services Proxmox DOWN
   - Acceptable car usage perso, downtime pas critique
   - Services critiques (DNS, HA) sur Raspberry Pi

2. **Pas de redondance hardware** :

   - 1 seul hyperviseur, 1 seul NAS
   - Coût cluster HA > bénéfice pour usage perso
   - Backups suffisants pour restore

3. **Internet dépend d'OPNsense VM** :
   - Si VM crash → plus d'Internet sur homelab
   - Acceptable : WiFi Box FAI reste UP pour urgences
   - Restore OPNsense = 10 min max

**Pourquoi accepter ces risques** :

- Usage personnel, pas de SLA à respecter
- Coût redondance > bénéfice
- Temps de restore acceptable (~1h max)

## Anti-Patterns à Éviter

Choses que je refuse de faire :

1. **Complexité pour "apprendre"** :

   - Kubernetes homelab juste pour le CV
   - Multi-cluster sans vraie raison
   - Monitoring ultra-détaillé type APM

2. **Optimisation prématurée** :

   - Micro-optimiser avant d'avoir un problème
   - Caching complexe sans mesurer le besoin
   - Tuning kernel sans benchmark

3. **Configuration manuelle** :

   - Pas de doc des changements manuels
   - Configs qui dérivent de la doc
   - "Je m'en souviendrai" (spoiler : non)

4. **Technologie à la mode** :
   - Adopter chaque nouveau tool hype
   - Remplacer ce qui marche pour "moderniser"
   - Stack complexe pour impressionner

## Évolution Future

**Principes pour faire évoluer** :

1. **Ajouter uniquement si besoin réel** :

   - Je rencontre un problème que ça résout
   - Pas juste pour tester

2. **Maintenir la simplicité** :

   - Si j'ajoute X, est-ce que je peux retirer Y ?
   - La complexité totale doit rester gérable

3. **Documenter immédiatement** :

   - Nouveau service = update services.md
   - Changement réseau = update network.md
   - Pas de "je documenterai plus tard"

4. **Tester le restore** :
   - Nouveau service = vérifier backup fonctionne
   - Changement infra = tester rebuild

## Conclusion

Ce homelab est conçu pour :

- Être simple à maintenir
- Pouvoir être reconstruit rapidement
- Tourner 24/7 sans souci
- Me servir au quotidien

Pas pour :

- Reproduire une infra entreprise
- Apprendre tous les outils DevOps
- Impressionner sur Reddit/Discord

Si un choix ne sert pas ces objectifs, je ne le fais pas.
