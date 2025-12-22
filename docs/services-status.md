# 📊 Statut des Services Homelab

Ce document est la **source de vérité** pour connaître l'état de déploiement de chaque service dans le homelab Blackbox.

## Légende

| Symbole | Signification | Description                                 |
| ------- | ------------- | ------------------------------------------- |
| ✅      | **DÉPLOYÉ**   | Service actif et configuré via Ansible      |
| 🔄      | **EN COURS**  | Déploiement partiel ou en test              |
| 📋      | **PLANIFIÉ**  | Documentation existe, implémentation future |
| ❌      | **NON PRÉVU** | Abandonné ou non pertinent actuellement     |

---

## 🍓 Raspberry Pi 5 (Control Tower)

**IP** : `192.168.10.2`
**RAM** : 8 GB
**Stockage** : NVMe boot
**OS** : Raspberry Pi OS (Docker)

### Services Déployés

| Service               | Statut     | Playbook/Config         | Port(s)      | URL Accès                  | Notes                                          |
| --------------------- | ---------- | ----------------------- | ------------ | -------------------------- | ---------------------------------------------- |
| **AdGuard Home**      | ✅ DÉPLOYÉ | `deploy_rpi_stack.yml`  | 53, 80, 3000 | `http://192.168.10.2`      | DNS master avec blocage pubs                   |
| **Home Assistant**    | ✅ DÉPLOYÉ | `deploy_rpi_stack.yml`  | 8123         | `http://192.168.10.2:8123` | Domotique (Z-Wave, Zigbee, WiFi)               |
| **Homepage**          | ✅ DÉPLOYÉ | `deploy_rpi_stack.yml`  | 8082         | `http://192.168.10.2:8082` | Dashboard web centralisé                       |
| **Tailscale**         | ✅ DÉPLOYÉ | `install_tailscale.yml` | -            | -                          | VPN mesh, subnet router pour `192.168.10.0/24` |
| **Dashboard Tactile** | ✅ DÉPLOYÉ | `deploy_kiosk.yml`      | -            | Écran physique             | Application Python, écran 3.5" capacitif       |

| **Grafana** | ✅ DÉPLOYÉ | `deploy_observability_stack.yml` | 3001 | `http://192.168.10.2:3001` | Visualisation métriques et logs - Dashboard 1860 importé |
| **Prometheus** | ✅ DÉPLOYÉ | `deploy_observability_stack.yml` | 9090 | `http://192.168.10.2:9090` | Collecte métriques (CPU, RAM, I/O) |
| **Loki** | ✅ DÉPLOYÉ | `deploy_observability_stack.yml` | 3100 | `http://192.168.10.2:3100` | Agrégation logs centralisée |
| **Promtail** | ✅ DÉPLOYÉ | `deploy_observability_stack.yml` | - | - | Agent collecte logs pour Loki (actif sur RPi) |
| **Node Exporter** | ✅ DÉPLOYÉ | `install_node_exporter.yml` | 9100 | - | Exporteur métriques système (RPi, Proxmox, NAS) |

**Ressources actuelles** : ~3.8 GB RAM utilisés / 8 GB (stack observabilité complète + services critiques)
**Config Docker** : `/opt/blackbox/docker-compose.yml`
**Données** : `/mnt/appdata/` (NFS depuis NAS Cargo)

### Services Planifiés (Non Déployés)

| Service            | Statut      | Port Prévu | Objectif                                 | Priorité |
| ------------------ | ----------- | ---------- | ---------------------------------------- | -------- |
| **Uptime Kuma**    | 📋 PLANIFIÉ | 3002       | Monitoring disponibilité services        | Élevée   |
| **Scrutiny (Web)** | 📋 PLANIFIÉ | 8080       | Dashboard santé disques (S.M.A.R.T)      | Moyenne  |
| **Dozzle**         | 📋 PLANIFIÉ | 9999       | Visualiseur logs Docker temps réel       | Moyenne  |
| **Diun**           | 📋 PLANIFIÉ | -          | Notifications mises à jour images Docker | Moyenne  |
| **Paperless-ngx**  | 📋 PLANIFIÉ | 8000       | GED avec OCR                             | Moyenne  |
| **Stirling-PDF**   | 📋 PLANIFIÉ | 8080       | Manipulation PDF                         | Basse    |

---

## 💾 NAS Cargo (UGREEN DXP2800)

**IP** : `192.168.10.5`
**CPU** : Intel N100 (4C/4T, 12th gen Alder Lake-N, 0.8-3.4 GHz)
**RAM** : 8 GB DDR5
**Stockage** : 3.6 TB utilisable (RAID 1 Btrfs) + 500 GB NVMe cache
**OS** : UGOS (firmware UGREEN)

### Services Déployés

| Service           | Statut     | Playbook/Config             | Description                                                                  | Notes                        |
| ----------------- | ---------- | --------------------------- | ---------------------------------------------------------------------------- | ---------------------------- |
| **Partages NFS**  | ✅ DÉPLOYÉ | Configuration manuelle UGOS | Exports : `appdata`, `media`, `photos`, `proxmox-backups`, `backups-configs` | Montés par tous les hôtes    |
| **Partages SMB**  | ✅ DÉPLOYÉ | Configuration manuelle UGOS | Accès depuis PC Windows/Mac                                                  | Pour gestion manuelle        |
| **Rclone Backup** | ✅ DÉPLOYÉ | `deploy_nas_backup.yml`     | Sync quotidien vers Backblaze B2 (03:00 AM)                                  | 3-2-1 backup strategy        |
| **LED Control**   | ✅ DÉPLOYÉ | `deploy_nas_leds.yml`       | Extinction 23:00, allumage 09:00                                             | Script cron + module i2c-dev |

### Services Planifiés (Non Déployés)

| Service                | Statut      | Objectif                                        | Priorité | Notes                                  |
| ---------------------- | ----------- | ----------------------------------------------- | -------- | -------------------------------------- |
| **Scrutiny Collector** | 📋 PLANIFIÉ | Agent local pour S.M.A.R.T monitoring           | Moyenne  | Envoie données vers Scrutiny Web (RPi) |
| **Immich**             | 📋 PLANIFIÉ | Gestion photos/vidéos (migration depuis VM 110) | Moyenne  | Nécessite validation performance N100  |

**Notes importantes** :

- NAS utilisé principalement pour **stockage**, pas compute intensif actuellement
- Migration Immich possible grâce à Intel N100 (CPU moderne) + 8 GB DDR5
- Performance ML Immich sera 3-5x plus lente que sur Ryzen 5 (acceptable si usage ponctuel)

---

## 💻 GMKtec NucBox M6 (Proxmox VE 9.1)

**IP Management** : `192.168.10.10`
**CPU** : AMD Ryzen 5 7640HS (6C/12T @ 5.0 GHz)
**RAM** : 32 GB DDR5
**Stockage** : 1 TB NVMe PCIe 4.0
**GPU** : AMD Radeon 760M (iGPU, passthrough activé)

### VM 100 - OPNsense (Routeur/Firewall)

| Paramètre         | Valeur                                 | Notes                              |
| ----------------- | -------------------------------------- | ---------------------------------- |
| **Statut**        | ✅ DÉPLOYÉ                             | Configuration manuelle Proxmox     |
| **Type**          | VM                                     | FreeBSD                            |
| **vCPU**          | 2                                      |                                    |
| **RAM**           | 2 GB                                   | Réduit de 4 GB après analyse `top` |
| **Stockage**      | 16 GB                                  |                                    |
| **IP**            | 192.168.10.1                           | Statique (Gateway LAN)             |
| **Interfaces**    | net0: vmbr0 (LAN)<br>net1: vmbr1 (WAN) | Double NIC pour isolation WAN/LAN  |
| **Autostart**     | Oui                                    | Ordre 100, délai 60s               |
| **Documentation** | `docs/bootstrap/opnsense.md`           |                                    |

**Services actifs** :

- Routage (PPPoE vers Proximus)
- Pare-feu (pf)
- DHCP (plage 192.168.10.100-200)
- DNS Forwarder (vers AdGuard 192.168.10.2)

### VM 110 - Media Stack

| Paramètre         | Valeur                           | Notes                                  |
| ----------------- | -------------------------------- | -------------------------------------- |
| **Statut**        | 📋 PLANIFIÉ                      | Non déployé actuellement               |
| **Type**          | VM                               | Ubuntu Server + Docker (prévu)         |
| **vCPU**          | 6                                | Parallélisation transcodage + ML       |
| **RAM**           | 14 GB                            | Jellyfin (4-6 GB) + Immich (6-8 GB)    |
| **Stockage**      | 100 GB                           |                                        |
| **IP**            | DHCP                             | Via OPNsense                           |
| **GPU**           | Passthrough iGPU AMD Radeon 760M | Transcodage Jellyfin + accélération ML |
| **Autostart**     | Oui                              | Ordre 90, délai 30s                    |
| **Documentation** | `docs/homelab.md:86-90`          |                                        |

**Services planifiés** :

- **Jellyfin** : Streaming vidéo avec transcodage GPU
- **Immich** : Gestion photos/vidéos avec ML (reconnaissance faciale, objets)
- **Overseerr** : Interface de requêtes médias

**Note** :

- ⚠️ VM non créée - Infrastructure à déployer

### VM 120 - Download Stack

| Paramètre         | Valeur                  | Notes                          |
| ----------------- | ----------------------- | ------------------------------ |
| **Statut**        | 📋 PLANIFIÉ             | Non déployé actuellement       |
| **Type**          | VM                      | Ubuntu Server + Docker (prévu) |
| **vCPU**          | 2                       |                                |
| **RAM**           | 6 GB                    |                                |
| **Stockage**      | 50 GB                   |                                |
| **IP**            | DHCP                    | Via OPNsense                   |
| **Isolation**     | VPN Killswitch          | Via Gluetun                    |
| **Autostart**     | Oui                     | Ordre 90, délai 30s            |
| **Documentation** | `docs/homelab.md:92-97` |                                |

**Services planifiés** :

- **Gluetun** : VPN Gateway avec killswitch (isolation réseau)
- **qBittorrent** : Client torrent
- **Radarr** : Automatisation films
- **Sonarr** : Automatisation séries
- **Prowlarr** : Gestionnaire indexeurs
- **Bazarr** : Gestion sous-titres

**Note** :

- ⚠️ VM non créée - Infrastructure à déployer

### LXC 200 - Infrastructure

| Paramètre         | Valeur                   | Notes                          |
| ----------------- | ------------------------ | ------------------------------ |
| **Statut**        | 📋 PLANIFIÉ              | Non déployé actuellement       |
| **Type**          | LXC                      | Debian 12 unprivileged (prévu) |
| **vCPU**          | 2                        |                                |
| **RAM**           | 4 GB                     |                                |
| **Stockage**      | 20 GB                    |                                |
| **IP**            | DHCP                     | Via OPNsense                   |
| **Features**      | nesting=1                | Pour Docker dans LXC           |
| **Autostart**     | Oui                      | Ordre 80, délai 15s            |
| **Documentation** | `docs/homelab.md:99-103` |                                |

**Services planifiés** :

- **Nginx Proxy Manager** : Reverse proxy + SSL (Let's Encrypt DNS Challenge)
- **Authentik** : SSO (Single Sign-On)
- **Bitwarden** : Gestionnaire mots de passe auto-hébergé

**Note** :

- ⚠️ LXC non créé - Infrastructure à déployer

### LXC 210 - Productivity

| Paramètre         | Valeur                    | Notes                          |
| ----------------- | ------------------------- | ------------------------------ |
| **Statut**        | 📋 PLANIFIÉ               | Non déployé actuellement       |
| **Type**          | LXC                       | Debian 12 unprivileged (prévu) |
| **vCPU**          | 2                         |                                |
| **RAM**           | 3 GB                      |                                |
| **Stockage**      | 30 GB                     |                                |
| **IP**            | DHCP                      | Via OPNsense                   |
| **Features**      | nesting=1                 | Pour Docker dans LXC           |
| **Autostart**     | Oui                       | Ordre 80, délai 15s            |
| **Documentation** | `docs/homelab.md:105-108` |                                |

**Services planifiés** :

- **Paperless-ngx** : GED avec OCR (Tesseract)
- **Stirling-PDF** : Manipulation PDF

**Note** :

- ⚠️ LXC non créé - Infrastructure à déployer
- Alternative : Déployer directement sur Raspberry Pi 5 au lieu de Proxmox

### Hôte Proxmox

| Paramètre          | Valeur                                           | Notes                |
| ------------------ | ------------------------------------------------ | -------------------- |
| **RAM réservée**   | 3 GB                                             | Cache système et ARC |
| **Version**        | Proxmox VE 9.1                                   |                      |
| **Bridges réseau** | vmbr0 (LAN via enp1s0)<br>vmbr1 (WAN via enp2s0) |                      |
| **IOMMU**          | Activé                                           | Pour GPU passthrough |
| **Documentation**  | `docs/bootstrap/proxmox.md`                      |                      |

**Amélioration planifiée** :

- 📋 Augmenter cache à 6-12 GB après migrations (meilleures performances I/O)

---

## 📊 Résumé Global des Ressources

### Allocation RAM Actuelle

| Machine             | RAM Totale | RAM Utilisée | RAM Libre | Taux   |
| ------------------- | ---------- | ------------ | --------- | ------ |
| **Raspberry Pi 5**  | 8 GB       | ~3.5 GB      | ~4.5 GB   | 44%    |
| **NAS Cargo**       | 8 GB       | ~500 MB      | ~7.5 GB   | 6%     |
| **Proxmox (total)** | 32 GB      | ~5 GB        | ~27 GB    | 16% ✅ |

**État actuel** : Proxmox a beaucoup de RAM libre (27 GB disponibles) car seule la VM 100 (OPNsense) est déployée.

### Allocation RAM par Instance Proxmox

| Instance               | RAM Allouée      | Usage Typique | Efficacité    | Statut      |
| ---------------------- | ---------------- | ------------- | ------------- | ----------- |
| VM 100 (OPNsense)      | 2 GB             | ~1.6 GB       | ✅ Optimisé   | ✅ Déployé  |
| VM 110 (Media)         | 14 GB (prévu)    | ~12-13 GB     | ⚠️ Tendu      | 📋 Planifié |
| VM 120 (Downloads)     | 6 GB (prévu)     | ~4-5 GB       | ✅ Correct    | 📋 Planifié |
| LXC 200 (Infra)        | 4 GB (prévu)     | ~3-3.5 GB     | ✅ Correct    | 📋 Planifié |
| LXC 210 (Productivity) | 3 GB (prévu)     | ~2.5 GB       | ✅ Correct    | 📋 Planifié |
| Host Proxmox           | 3 GB             | -             | ✅ Actuel     | ✅ Actif    |
| **TOTAL UTILISÉ**      | **5 GB / 32 GB** |               | **84% LIBRE** |             |

---

## 🎯 Services à Déployer (Priorités)

### ✅ Récemment Déployé

| Service                          | Destination    | RAM Requise | Statut                                           |
| -------------------------------- | -------------- | ----------- | ------------------------------------------------ |
| **Stack Observabilité Complète** | Raspberry Pi 5 | ~2.5 GB     | ✅ Grafana + Prometheus + Loki + Promtail actifs |
| **Node Exporter**                | Tous hôtes     | ~50 MB/hôte | ✅ Actif sur RPi, Proxmox, NAS Cargo             |
| **Dashboard Grafana 1860**       | Grafana        | -           | ✅ Node Exporter Full dashboard importé          |

### Priorité Élevée

| Service                      | Destination    | RAM Requise | Bénéfice                                    |
| ---------------------------- | -------------- | ----------- | ------------------------------------------- |
| **Uptime Kuma**              | Raspberry Pi 5 | ~200 MB     | Monitoring proactif des services            |
| **VM 110 (Media Stack)**     | Proxmox        | 14 GB       | Jellyfin + Immich + Overseerr               |
| **LXC 200 (Infrastructure)** | Proxmox        | 4 GB        | Nginx Proxy Manager + Authentik + Bitwarden |

### Priorité Moyenne

| Service                      | Destination    | RAM Requise | Bénéfice                            |
| ---------------------------- | -------------- | ----------- | ----------------------------------- |
| **Scrutiny Web + Collector** | RPi + NAS      | ~250 MB     | Surveillance santé disques          |
| **Dozzle + Diun**            | Raspberry Pi 5 | ~150 MB     | Logs Docker + notifications updates |
| **VM 120 (Download Stack)**  | Proxmox        | 6 GB        | Gluetun + \*Arr stack + qBittorrent |
| **LXC 210 (Productivity)**   | Proxmox ou RPi | 3 GB        | Paperless-ngx + Stirling-PDF        |

---

## 🔄 Plan de Déploiement

Voir `docs/architecture/migration-plan.md` pour détails complets.

### Phase 1 : Observabilité (En cours)

- ✅ Grafana/Prometheus/Loki/Promtail configurés dans docker-compose.yml
- 📋 Déployer Node Exporter sur tous les hôtes (playbook `install_node_exporter.yml` existant)
- 📋 Déployer Uptime Kuma, Scrutiny, Dozzle, Diun

**Impact** : +2.8 GB RAM sur RPi, monitoring complet actif

### Phase 2 : Infrastructure Proxmox (Priorité élevée)

- 📋 Créer VM 110 (Media Stack) - Jellyfin + Immich + Overseerr
- 📋 Créer LXC 200 (Infrastructure) - Nginx Proxy Manager + Authentik + Bitwarden
- 📋 Créer VM 120 (Download Stack) - \*Arr stack + Gluetun + qBittorrent

**Impact** : Utilisation de 24 GB RAM sur Proxmox (restent 8 GB libres)

### Phase 3 : Services Additionnels (Moyen terme)

- 📋 Déployer LXC 210 (Productivity) sur Proxmox OU Raspberry Pi 5
- 📋 Déployer services monitoring additionnels (Scrutiny, Dozzle, Diun)
- 📋 Évaluer migration Immich vers NAS Cargo si besoin de RAM

---

## 📝 Notes de Maintenance

### Commandes Utiles

```bash
# Vérifier statut services Raspberry Pi
ssh control-tower.blackbox.homes
docker ps
docker stats

# Vérifier allocation RAM Proxmox
ssh pve.blackbox.homes
qm list              # VMs
pct list             # LXCs
free -h              # RAM host

# Redéployer stack Raspberry Pi
cd /home/rvph/Projects/blackbox/ansible
ansible-playbook playbooks/deploy_rpi_stack.yml

# Vérifier backups Backblaze B2
ssh 192.168.10.5  # NAS
cat /volume1/appdata/rclone/backup_status.json
```

### Références Croisées

- Architecture détaillée : `docs/homelab.md`
- Allocation ressources compute : `docs/architecture/compute-allocation.md`
- Bootstrap Proxmox : `docs/bootstrap/proxmox.md`
- Bootstrap OPNsense : `docs/bootstrap/opnsense.md`
- Bootstrap Raspberry Pi : `docs/bootstrap/control-tower.md`
- Plan migrations : `docs/architecture/migration-plan.md`
- Opérations : `docs/operations.md`

---

**Maintenu par** : Automatisation Ansible + Documentation manuelle
