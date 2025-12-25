# Architecture - Vue d'Ensemble

Documentation de l'architecture du homelab Blackbox. Ce qui existe, comment c'est organisé, et pourquoi.

## Lecture Rapide

**En 30 secondes** :

- Homelab composé de 3 machines (Proxmox, Raspberry Pi, NAS)
- Réseau isolé avec OPNsense comme gateway
- Services critiques sur Raspberry Pi (DNS, domotique)
- Services gourmands sur Proxmox (media, downloads)
- Stockage centralisé sur NAS
- Accès distant via Tailscale (zero-trust)

**Déploiement complet** : ~1h30 avec playbooks Ansible

## Documents Architecture

### [Philosophie](./philosophy.md)

Pourquoi j'ai fait ces choix d'architecture. Les principes qui guident les décisions.

**À lire si** :

- Tu veux comprendre le "pourquoi" avant le "comment"
- Tu te demandes pourquoi j'ai pas fait autrement
- Tu veux voir les trade-offs acceptés

**Points clés** :

- Isolation réseau (subnet dédié)
- Services critiques externalisés (Raspberry Pi)
- Accès distant zero-trust (Tailscale)
- Stratégie backup 3-2-1
- Mindset "Nuke & Pave"
- Simplicité > Fonctionnalités

### [Hardware](./hardware.md)

Toutes les specs matérielles détaillées. Processeurs, RAM, stockage, réseau.

**À lire si** :

- Tu veux connaître le matériel exact
- Tu compares des choix hardware
- Tu upgrade du hardware

**Contenu** :

- GMKtec NucBox M6 (Proxmox) : Ryzen 5 7640HS, 32GB DDR5
- Raspberry Pi 5 (Control Tower) : 8GB RAM
- UGREEN DXP2800 (NAS Cargo) : Intel N100, 8GB DDR5, 4TB RAID 1
- Switch PoE+ manageable
- Consommation électrique (~33-71W)

### [Réseau](./network.md)

Configuration réseau complète. IPs, VLANs, DNS, firewall, NFS.

**À lire si** :

- Un service ne ping pas
- Tu dois changer une IP
- Tu ajoutes un nouvel équipement

**Contenu** :

- Subnet 192.168.10.0/24
- IPs statiques (OPNsense, Proxmox, NAS, Raspberry Pi)
- Configuration OPNsense (WAN PPPoE, LAN, DHCP, firewall)
- Stratégie DNS (AdGuard Home)
- Accès distant (Tailscale)
- Montages NFS
- Troubleshooting réseau

### [Services](./services.md)

Catalogue complet de tous les services. Qui tourne où, pourquoi, combien de RAM.

**À lire si** :

- Tu veux ajouter un service
- Tu veux connaître l'allocation RAM
- Tu cherches un service spécifique

**Contenu** :

- Services par catégorie (infra, domotique, media, etc.)
- Allocation RAM par machine
- Ports & accès
- Dépendances entre services
- Ordre de démarrage

## Architecture Visuelle

### Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                      INTERNET (Box FAI)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │ WAN (PPPoE)
                      v
          ┌───────────────────────┐
          │  OPNsense (VM 100)    │ 192.168.10.1
          │  Router/Firewall/DHCP │
          └───────────┬───────────┘
                      │ LAN (vmbr0)
                      v
              ┌───────────────┐
              │ Switch PoE+   │ 192.168.10.3
              └───┬───────────┘
                  │
    ┌─────────────┼─────────────┬──────────────┐
    v             v             v              v
┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│Proxmox │  │Raspberry │  │   NAS    │  │  VMs/LXCs    │
│  Host  │  │   Pi 5   │  │  Cargo   │  │   (DHCP)     │
│ .2     │  │   .10    │  │   .5     │  │ .100-.250    │
└────────┘  └──────────┘  └──────────┘  └──────────────┘
```

### Distribution des Services

```
┌─────────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI 5 (8 GB)                       │
├─────────────────────────────────────────────────────────────────┤
│ CRITIQUES          │ OBSERVABILITÉ     │ MONITORING             │
│ - AdGuard Home     │ - Grafana         │ - Uptime Kuma          │
│ - Home Assistant   │ - Prometheus      │ - Scrutiny             │
│ - Homepage         │ - Loki            │ - Dozzle               │
│ - Tailscale        │ - Promtail        │ - Diun                 │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                   PROXMOX GMKtec M6 (32 GB)                      │
├──────────────────────────────────────────────────────────────────┤
│ VM 100           │ VM 110 (planifié)  │ VM 120 (planifié)        │
│ - OPNsense (2GB) │ - Jellyfin (14GB)  │ - Gluetun (6GB)          │
│                  │ - Immich           │ - qBittorrent            │
│                  │ - Overseerr        │ - *arr stack             │
├──────────────────────────────────────────────────────────────────┤
│ LXC 200 (planifié)        │ LXC 210 (planifié)                   │
│ - NPM (4GB)               │ Paperless + Stirling-PDF             │
│ - Authentik               │                                      │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    NAS CARGO Intel N100 (8 GB)                   │
├──────────────────────────────────────────────────────────────────┤
│ STOCKAGE (4TB)   │ BACKUP            │ SERVICES (planifié)       │
│ - NFS exports    │ - Rclone → B2     │ - Immich (6GB)            │
│ - Btrfs RAID 1   │ - Snapshots       │ - Scrutiny Collector      │
│ - NVMe cache     │ - LED Control     │                           │
└──────────────────────────────────────────────────────────────────┘
```

## Flux de Données

### DNS Resolution

```
Client Device
  ↓ (DNS query)
AdGuard Home (192.168.10.2)
  ├─ *.blackbox.homes → IP locale
  ├─ Ads/Trackers → Bloqué
  └─ Autres → Upstream (1.1.1.1)
```

### Media Flow

```
qBittorrent (VM 120)
  ↓ (download)
NAS /media (via NFS)
  ↓ (mount)
Jellyfin (VM 110)
  ↓ (stream + transcode GPU)
Client (browser/app)
```

### Backup Flow

```
Services (appdata)
  ↓ (Docker volumes)
NAS /appdata (NFS)
  ├─ Btrfs Snapshot (quotidien)
  └─ Rclone Sync (quotidien 03:00)
      ↓
  Backblaze B2 (chiffré, 30j retention)
```

## Décisions Architecturales Importantes

### Pourquoi Proxmox et pas Docker sur bare metal ?

**Avantages Proxmox** :

- Snapshots VMs/LXCs (rollback facile)
- Isolation forte (VM pour services gourmands)
- GPU passthrough (Jellyfin transcoding)
- Mix VMs + LXCs selon besoins
- OPNsense nécessite une VM

**Trade-off** :

- Overhead virtualisation (~2GB RAM pour host)
- Légèrement plus complexe que Docker direct

### Pourquoi Raspberry Pi séparé ?

**Avantages** :

- DNS reste UP même si Proxmox down
- Domotique 24/7 critique (lumières, capteurs)
- Boot rapide, faible conso (3-8W)
- Pas de dépendance à Proxmox

**Trade-off** :

- Un équipement de plus à gérer
- RAM limitée (8GB) vs Proxmox

### Pourquoi Tailscale et pas VPN classique ?

**Avantages Tailscale** :

- Zero-config mesh VPN
- NAT traversal automatique
- Apps mobiles simples
- Pas de port forwarding
- Subnet routing facile

**Trade-off** :

- Dépendance à service externe (control plane)
- Moins de contrôle qu'OpenVPN/WireGuard self-hosted

### Pourquoi NAS externe et pas stockage Proxmox ?

**Avantages NAS séparé** :

- Stockage accessible même si Proxmox down
- RAID 1 + Btrfs snapshots + rclone backup
- Intel N100 peut faire du compute léger (Immich)
- Évite saturer stockage Proxmox

**Trade-off** :

- Latence NFS (~0.5-2ms)
- Dépendance réseau (si switch down, pas d'appdata)

## Chemins Rapides

**Je veux comprendre** :

- Pourquoi ces choix ? → [philosophy.md](./philosophy.md)
- Quel matériel ? → [hardware.md](./hardware.md)
- Comment réseau configuré ? → [network.md](./network.md)
- Quels services tournent ? → [services.md](./services.md)

**Je veux déployer** :

- Premier déploiement → [../quickstart.md](../quickstart.md)
- Déploiement détaillé → [../deployment/README.md](../deployment/README.md)

**Je veux maintenir** :

- Opérations quotidiennes → [../operations/maintenance.md](../operations/maintenance.md)
- Troubleshooting → [../operations/troubleshooting.md](../operations/troubleshooting.md)

## Évolution Prévue

**Court terme** (à déployer maintenant) :

- VMs 110/120 (Media + Downloads)
- LXCs 200/210 (Infra + Productivity)
- Monitoring complet (Uptime Kuma, Scrutiny)

**Moyen terme** (6 mois) :

- Migration Immich sur NAS
- SSO avec Authentik
- Paperless-ngx

**Long terme** (nice to have) :

- Paperless-ngx + Stirling-PDF
- Dashboards Grafana custom
- Tests automatisés restore backup

Pour connaître l'état actuel des déploiements, voir [../reference/status.md](../reference/status.md)
