# Services - Catalogue des Services

Tous les services du homelab organisés par catégorie. Pour connaître le statut de déploiement actuel, voir [reference/status.md](../reference/status.md).

## Organisation des Services

Les services sont répartis sur 3 machines selon leur criticité et leurs besoins en ressources :

- **Raspberry Pi** : Services critiques + Observabilité
- **Proxmox (VMs/LXCs)** : Services gourmands en ressources
- **NAS Cargo** : Stockage + Services légers

---

## Services par Catégorie

### Infrastructure & Réseau

| Service                 | Déployé sur     | Rôle                 | RAM    | Pourquoi là                              |
| ----------------------- | --------------- | -------------------- | ------ | ---------------------------------------- |
| **OPNsense**            | Proxmox VM 100  | Router/Firewall/DHCP | 2 GB   | Isolation réseau, contrôle total WAN/LAN |
| **AdGuard Home**        | Raspberry Pi    | DNS + Ad Blocking    | 200 MB | Doit rester UP même si Proxmox down      |
| **Tailscale**           | Raspberry Pi    | VPN Mesh             | 50 MB  | Accès distant zero-config                |
| **Nginx Proxy Manager** | Proxmox LXC 200 | Reverse Proxy + SSL  | 500 MB | Certificats SSL Let's Encrypt            |

**Architecture DNS** :

```
Client → AdGuard Home (192.168.10.2)
         ├─ Blocage ads/trackers
         ├─ Résolution locale (*.blackbox.homes)
         └─ Upstream → 1.1.1.1 (Cloudflare)
```

### Domotique

| Service            | Déployé sur  | Rôle                 | RAM    | Intégrations                 |
| ------------------ | ------------ | -------------------- | ------ | ---------------------------- |
| **Home Assistant** | Raspberry Pi | Hub domotique        | 500 MB | Z-Wave, Zigbee, WiFi, MQTT   |
| **Homepage**       | Raspberry Pi | Dashboard centralisé | 100 MB | Liens vers tous les services |

**Pourquoi sur Raspberry** :

- Doit rester UP 24/7 (contrôle lumières, capteurs, etc.)
- Si Proxmox en maintenance, domotique continue
- Connexion USB pour dongles Z-Wave/Zigbee

### Observabilité & Monitoring

| Service           | Déployé sur  | Rôle                       | RAM        | Rétention |
| ----------------- | ------------ | -------------------------- | ---------- | --------- |
| **Grafana**       | Raspberry Pi | Dashboards métriques/logs  | 300 MB     | -         |
| **Prometheus**    | Raspberry Pi | Time-series DB (métriques) | 1.5 GB     | 15 jours  |
| **Loki**          | Raspberry Pi | Agrégation logs            | 500 MB     | 30 jours  |
| **Promtail**      | Raspberry Pi | Agent collecte logs        | 50 MB      | -         |
| **Node Exporter** | Partout      | Export métriques système   | 50 MB/hôte | -         |

**Services planifiés** :

- **Uptime Kuma** : Monitoring disponibilité (HTTP, ping, DNS)
- **Scrutiny** : Monitoring santé disques (S.M.A.R.T)
- **Dozzle** : Logs Docker temps réel
- **Diun** : Notif updates images Docker

**Architecture Monitoring** :

```
Hosts (Proxmox, RPi, NAS)
  └─ Node Exporter → Prometheus
                      └─ Grafana (viz)

Docker Containers
  └─ Promtail → Loki → Grafana (logs)
```

### Media & Streaming

| Service       | Déployé sur    | Rôle           | RAM    | GPU      | Stockage   |
| ------------- | -------------- | -------------- | ------ | -------- | ---------- |
| **Jellyfin**  | Proxmox VM 110 | Media server   | 4-6 GB | AMD 760M | NFS /media |
| **Overseerr** | Proxmox VM 110 | Requêtes média | 500 MB | -        | -          |

**Hardware Acceleration (Jellyfin)** :

- GPU passthrough AMD Radeon 760M
- VA-API support (H.264, HEVC, AV1 decode)
- Transcoding 4K → 1080p sans charge CPU

**Bibliothèque Media** :

```
/mnt/media (NFS depuis NAS)
├── movies/
├── tv/
├── music/
└── audiobooks/
```

### Photos & Vidéos

| Service    | Déployé sur          | Rôle              | RAM  | GPU              | Notes                     |
| ---------- | -------------------- | ----------------- | ---- | ---------------- | ------------------------- |
| **Immich** | NAS Cargo (planifié) | Gestion photos ML | 6 GB | Intel UHD Gen 12 | Alternative Google Photos |

**Features Immich** :

- Reconnaissance faciale (ML)
- Classification objets (ML)
- Recherche sémantique
- Timeline automatique
- Backup mobile apps

**Pourquoi sur NAS** :

- Photos stockées localement (pas de transfert réseau)
- Intel N100 + QuickSync suffisant pour ML inference
- DDR5 haute bande passante pour matrices ML

### Downloads & Automation

| Service         | Déployé sur    | Rôle              | RAM    | Notes             |
| --------------- | -------------- | ----------------- | ------ | ----------------- |
| **Gluetun**     | Proxmox VM 120 | VPN Gateway       | 100 MB | Killswitch réseau |
| **qBittorrent** | Proxmox VM 120 | Client torrent    | 500 MB | Via Gluetun       |
| **Radarr**      | Proxmox VM 120 | Automation films  | 500 MB | -                 |
| **Sonarr**      | Proxmox VM 120 | Automation séries | 500 MB | -                 |
| **Prowlarr**    | Proxmox VM 120 | Indexeurs         | 200 MB | -                 |
| **Bazarr**      | Proxmox VM 120 | Sous-titres       | 200 MB | -                 |

**Isolation Réseau** :

```
VM 120 (Download Stack)
├─ Gluetun (VPN container)
│  └─ qBittorrent, *arr (via Gluetun network)
└─ Killswitch: Si VPN down → Pas d'Internet
```

**Flux Automation** :

```
Prowlarr (indexeurs)
  ├─ Radarr (films) → qBittorrent → /media/movies
  └─ Sonarr (séries) → qBittorrent → /media/tv
                                    └─ Jellyfin détecte nouveaux fichiers
```

### Productivity & Documents

| Service           | Déployé sur             | Rôle             | RAM    | Features                       |
| ----------------- | ----------------------- | ---------------- | ------ | ------------------------------ |
| **Nextcloud**     | Proxmox LXC 210         | Cloud personnel  | 2 GB   | Files, Calendar, Contacts      |
| **Paperless-ngx** | Raspberry Pi (planifié) | GED avec OCR     | 2.5 GB | Scan docs, recherche full-text |
| **Stirling-PDF**  | Raspberry Pi (planifié) | Manipulation PDF | 500 MB | Merge, split, compress         |

**Nextcloud Apps** :

- Files (stockage)
- Calendar (sync CalDAV)
- Contacts (sync CardDAV)
- Tasks
- Notes

### Sécurité & Authentification

| Service         | Déployé sur     | Rôle             | RAM    | Notes                             |
| --------------- | --------------- | ---------------- | ------ | --------------------------------- |
| **Vaultwarden** | Proxmox LXC 200 | Password manager | 512 MB | Compatible Bitwarden              |
| **Authentik**   | Proxmox LXC 200 | SSO              | 1 GB   | Single Sign-On pour tous services |

**SSO avec Authentik** :

- Login unique pour Jellyfin, Nextcloud, etc.
- OIDC/SAML support
- 2FA (TOTP, WebAuthn)

### Backup & Stockage

| Service             | Déployé sur | Rôle                 | Fréquence       | Destination          |
| ------------------- | ----------- | -------------------- | --------------- | -------------------- |
| **Rclone**          | NAS Cargo   | Sync cloud           | Quotidien 03:00 | Backblaze B2         |
| **Proxmox Backup**  | Proxmox     | VM snapshots         | Hebdo dimanche  | NAS /proxmox-backups |
| **Btrfs Snapshots** | NAS Cargo   | Snapshots filesystem | Quotidien       | Local                |

**Stratégie 3-2-1** :

```
3 copies:
  1. Données live (NAS RAID 1)
  2. Snapshots Btrfs (NAS local)
  3. Backblaze B2 (cloud)

2 supports:
  1. RAID 1 miroir (protection hardware)
  2. Snapshots (protection logique)

1 hors-site:
  - Backblaze B2 chiffré (client-side)
```

---

## Allocation RAM Totale

### Raspberry Pi (8 GB)

| Catégorie       | Services                            | RAM      |
| --------------- | ----------------------------------- | -------- |
| Critiques       | AdGuard, HA, Homepage, Tailscale    | 800 MB   |
| Observabilité   | Grafana, Prometheus, Loki, Promtail | 2.3 GB   |
| Monitoring      | Uptime Kuma, Scrutiny, Dozzle, Diun | 500 MB   |
| Productivity    | Paperless, Stirling-PDF             | 3 GB     |
| System + Buffer | OS + marge                          | 1.4 GB   |
| **TOTAL**       |                                     | **8 GB** |

### NAS Cargo (8 GB)

| Catégorie | Services                   | RAM      |
| --------- | -------------------------- | -------- |
| System    | UGOS + NFS                 | 700 MB   |
| Backup    | Rclone, Scrutiny Collector | 300 MB   |
| Media     | Immich (futur)             | 6 GB     |
| Buffer    | Marge sécurité             | 1 GB     |
| **TOTAL** |                            | **8 GB** |

### Proxmox GMKtec (32 GB)

| Machine   | Services                    | RAM       |
| --------- | --------------------------- | --------- |
| Host      | Proxmox VE                  | 2 GB      |
| VM 100    | OPNsense                    | 2 GB      |
| VM 110    | Jellyfin, Immich, Overseerr | 14 GB     |
| VM 120    | Gluetun, qBit, \*arr stack  | 6 GB      |
| LXC 200   | NPM, Authentik, Vaultwarden | 4 GB      |
| LXC 210   | Nextcloud                   | 2 GB      |
| Buffer    | Marge                       | 2 GB      |
| **TOTAL** |                             | **32 GB** |

---

## Ports & Accès

### Ports Raspberry Pi

| Port     | Service               | Accès           |
| -------- | --------------------- | --------------- |
| 53       | AdGuard Home (DNS)    | LAN uniquement  |
| 80, 3000 | AdGuard Home (Web UI) | LAN uniquement  |
| 8123     | Home Assistant        | LAN + Tailscale |
| 8082     | Homepage              | LAN uniquement  |
| 3001     | Grafana               | LAN + Tailscale |
| 9090     | Prometheus            | LAN uniquement  |
| 3100     | Loki                  | LAN uniquement  |

### Ports VMs/LXCs (via NPM)

Tous les services accessibles via Nginx Proxy Manager avec certificats SSL :

| Service     | URL                     | IP Interne  | Accès     |
| ----------- | ----------------------- | ----------- | --------- |
| Jellyfin    | jellyfin.blackbox.homes | VM 110:8096 | Tailscale |
| Overseerr   | overseer.blackbox.homes | VM 110:5055 | Tailscale |
| Nextcloud   | cloud.blackbox.homes    | LXC 210:80  | Tailscale |
| Vaultwarden | vault.blackbox.homes    | LXC 200:80  | Tailscale |

**Principe** :

- Certificats Let's Encrypt via DNS Challenge (Cloudflare)
- DNS public pointe vers IP Tailscale
- Aucun port ouvert sur WAN OPNsense

---

## Dépendances entre Services

### Ordre de Démarrage

```
1. NAS Cargo
   └─ Exports NFS disponibles
      |
2. OPNsense (VM 100)
   └─ Gateway + DHCP
      |
3. Raspberry Pi
   ├─ AdGuard Home (DNS)
   ├─ Home Assistant
   └─ Monitoring stack
      |
4. VMs/LXCs Proxmox
   ├─ VM 110 (Media)
   ├─ VM 120 (Downloads)
   ├─ LXC 200 (Infra)
   └─ LXC 210 (Productivity)
```

### Dépendances NFS

Services dépendant de montages NFS :

| Service             | NFS Mount                 | Dépendance critique    |
| ------------------- | ------------------------- | ---------------------- |
| Raspberry Pi (tous) | /mnt/appdata              | OUI (ne boot pas sans) |
| Jellyfin            | /mnt/media, /mnt/appdata  | OUI                    |
| Immich              | /mnt/photos, /mnt/appdata | OUI                    |
| Downloads           | /mnt/media, /mnt/appdata  | OUI                    |
| Nextcloud           | /mnt/appdata              | OUI                    |

**Bootstrap** :

- `/etc/fstab` avec option `_netdev` (attend réseau)
- Systemd wait-for-network
- Docker Compose `depends_on` custom scripts si besoin

---

## Évolution Future

### Court Terme (déployer maintenant)

- VM 110 (Media Stack) : Jellyfin + Overseerr
- VM 120 (Downloads) : Gluetun + \*arr stack
- LXC 200 (Infra) : NPM + Vaultwarden
- Uptime Kuma, Scrutiny (sur Raspberry Pi)

### Moyen Terme (next 6 mois)

- Migration Immich sur NAS Cargo
- Authentik SSO
- Paperless-ngx + Stirling-PDF

### Long Terme (nice to have)

- LXC 210 Nextcloud
- Automation backups avec tests restore
- Dashboards Grafana custom

---

## Notes

**Qu'est-ce qu'on NE déploie PAS** :

- Kubernetes : Overkill pour usage perso
- Plex : Jellyfin open-source suffit
- GitLab : GitHub suffit
- Elasticsearch : Trop gourmand, Loki suffit
- Multiple instances pour HA : Pas nécessaire usage perso

**Services abandonnés** :

- Screen (legacy) : Remplacé par dashboard Python

Pour status actuel de déploiement : voir [reference/status.md](../reference/status.md)
