# 📊 Statut des Services Homelab

**Dernière mise à jour** : 2024-12-22

Ce document est la **source de vérité** pour connaître l'état de déploiement de chaque service dans le homelab Blackbox.

## Légende

| Symbole | Signification | Description |
|---------|---------------|-------------|
| ✅ | **DÉPLOYÉ** | Service actif et configuré via Ansible |
| 🔄 | **EN COURS** | Déploiement partiel ou en test |
| 📋 | **PLANIFIÉ** | Documentation existe, implémentation future |
| ❌ | **NON PRÉVU** | Abandonné ou non pertinent actuellement |

---

## 🍓 Raspberry Pi 5 (Control Tower)

**IP** : `192.168.10.2`
**RAM** : 8 GB
**Stockage** : NVMe boot
**OS** : Raspberry Pi OS (Docker)

### Services Déployés

| Service | Statut | Playbook/Config | Port(s) | URL Accès | Notes |
|---------|--------|-----------------|---------|-----------|-------|
| **AdGuard Home** | ✅ DÉPLOYÉ | `deploy_rpi_stack.yml` | 53, 80, 3000 | `http://192.168.10.2` | DNS master avec blocage pubs |
| **Home Assistant** | ✅ DÉPLOYÉ | `deploy_rpi_stack.yml` | 8123 | `http://192.168.10.2:8123` | Domotique (Z-Wave, Zigbee, WiFi) |
| **Homepage** | ✅ DÉPLOYÉ | `deploy_rpi_stack.yml` | 8082 | `http://192.168.10.2:8082` | Dashboard web centralisé |
| **Tailscale** | ✅ DÉPLOYÉ | `install_tailscale.yml` | - | - | VPN mesh, subnet router pour `192.168.10.0/24` |
| **Dashboard Tactile** | ✅ DÉPLOYÉ | `deploy_kiosk.yml` | - | Écran physique | Application Python, écran 3.5" capacitif |

**Ressources actuelles** : ~800 MB RAM utilisés / 8 GB
**Config Docker** : `/opt/blackbox/docker-compose.yml`
**Données** : `/mnt/appdata/` (NFS depuis NAS Cargo)

### Services Planifiés (Non Déployés)

| Service | Statut | Port Prévu | Objectif | Priorité |
|---------|--------|------------|----------|----------|
| **Uptime Kuma** | 📋 PLANIFIÉ | 3001 | Monitoring disponibilité services | Élevée |
| **Scrutiny (Web)** | 📋 PLANIFIÉ | 8080 | Dashboard santé disques (S.M.A.R.T) | Moyenne |
| **Dozzle** | 📋 PLANIFIÉ | 9999 | Visualiseur logs Docker temps réel | Moyenne |
| **Diun** | 📋 PLANIFIÉ | - | Notifications mises à jour images Docker | Moyenne |
| **Grafana** | 📋 PLANIFIÉ | 3000 | Visualisation métriques et logs | Élevée |
| **Prometheus** | 📋 PLANIFIÉ | 9090 | Collecte métriques (CPU, RAM, I/O) | Élevée |
| **Loki** | 📋 PLANIFIÉ | 3100 | Agrégation logs centralisée | Élevée |
| **Promtail** | 📋 PLANIFIÉ | - | Agent collecte logs pour Loki | Élevée |
| **Paperless-ngx** | 📋 PLANIFIÉ | 8000 | GED avec OCR (migration depuis LXC 210) | Moyenne |
| **Stirling-PDF** | 📋 PLANIFIÉ | 8080 | Manipulation PDF (migration depuis LXC 210) | Basse |

---

## 💾 NAS Cargo (UGREEN DXP2800)

**IP** : `192.168.10.5`
**CPU** : Intel N100 (4C/4T, 12th gen Alder Lake-N, 0.8-3.4 GHz)
**RAM** : 8 GB DDR5
**Stockage** : 3.6 TB utilisable (RAID 1 Btrfs) + 500 GB NVMe cache
**OS** : UGOS (firmware UGREEN)

### Services Déployés

| Service | Statut | Playbook/Config | Description | Notes |
|---------|--------|-----------------|-------------|-------|
| **Partages NFS** | ✅ DÉPLOYÉ | Configuration manuelle UGOS | Exports : `appdata`, `media`, `photos`, `proxmox-backups`, `backups-configs` | Montés par tous les hôtes |
| **Partages SMB** | ✅ DÉPLOYÉ | Configuration manuelle UGOS | Accès depuis PC Windows/Mac | Pour gestion manuelle |
| **Rclone Backup** | ✅ DÉPLOYÉ | `deploy_nas_backup.yml` | Sync quotidien vers Backblaze B2 (03:00 AM) | 3-2-1 backup strategy |
| **LED Control** | ✅ DÉPLOYÉ | `deploy_nas_leds.yml` | Extinction 23:00, allumage 09:00 | Script cron + module i2c-dev |

### Services Planifiés (Non Déployés)

| Service | Statut | Objectif | Priorité | Notes |
|---------|--------|----------|----------|-------|
| **Scrutiny Collector** | 📋 PLANIFIÉ | Agent local pour S.M.A.R.T monitoring | Moyenne | Envoie données vers Scrutiny Web (RPi) |
| **Immich** | 📋 PLANIFIÉ | Gestion photos/vidéos (migration depuis VM 110) | Moyenne | Nécessite validation performance N100 |

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

| Paramètre | Valeur | Notes |
|-----------|--------|-------|
| **Statut** | ✅ DÉPLOYÉ | Configuration manuelle Proxmox |
| **Type** | VM | FreeBSD |
| **vCPU** | 2 | |
| **RAM** | 2 GB | Réduit de 4 GB après analyse `top` |
| **Stockage** | 16 GB | |
| **IP** | 192.168.10.1 | Statique (Gateway LAN) |
| **Interfaces** | net0: vmbr0 (LAN)<br>net1: vmbr1 (WAN) | Double NIC pour isolation WAN/LAN |
| **Autostart** | Oui | Ordre 100, délai 60s |
| **Documentation** | `docs/bootstrap/opnsense.md` | |

**Services actifs** :
- Routage (PPPoE vers Proximus)
- Pare-feu (pf)
- DHCP (plage 192.168.10.100-200)
- DNS Forwarder (vers AdGuard 192.168.10.2)

### VM 110 - Media Stack

| Paramètre | Valeur | Notes |
|-----------|--------|-------|
| **Statut** | ✅ DÉPLOYÉ | Configuration manuelle Proxmox |
| **Type** | VM | Ubuntu Server + Docker |
| **vCPU** | 6 | Parallélisation transcodage + ML |
| **RAM** | 14 GB | Jellyfin (4-6 GB) + Immich (6-8 GB) |
| **Stockage** | 100 GB | |
| **IP** | DHCP | Via OPNsense |
| **GPU** | Passthrough iGPU AMD Radeon 760M | Transcodage Jellyfin + accélération ML |
| **Autostart** | Oui | Ordre 90, délai 30s |
| **Documentation** | `docs/homelab.md:86-90` | |

**Services déployés** :
- **Jellyfin** : Streaming vidéo avec transcodage GPU
- **Immich** : Gestion photos/vidéos avec ML (reconnaissance faciale, objets)
- **Overseerr** : Interface de requêtes médias

**Migration planifiée** :
- 📋 Déplacer Immich vers NAS Cargo (libère ~6 GB RAM)

### VM 120 - Download Stack

| Paramètre | Valeur | Notes |
|-----------|--------|-------|
| **Statut** | ✅ DÉPLOYÉ | Configuration manuelle Proxmox |
| **Type** | VM | Ubuntu Server + Docker |
| **vCPU** | 2 | |
| **RAM** | 6 GB | |
| **Stockage** | 50 GB | |
| **IP** | DHCP | Via OPNsense |
| **Isolation** | VPN Killswitch | Via Gluetun |
| **Autostart** | Oui | Ordre 90, délai 30s |
| **Documentation** | `docs/homelab.md:92-97` | |

**Services déployés** :
- **Gluetun** : VPN Gateway avec killswitch (isolation réseau)
- **qBittorrent** : Client torrent
- **Radarr** : Automatisation films
- **Sonarr** : Automatisation séries
- **Prowlarr** : Gestionnaire indexeurs
- **Bazarr** : Gestion sous-titres

### LXC 200 - Infrastructure

| Paramètre | Valeur | Notes |
|-----------|--------|-------|
| **Statut** | ✅ DÉPLOYÉ | Configuration manuelle Proxmox |
| **Type** | LXC | Debian 12 unprivileged |
| **vCPU** | 2 | |
| **RAM** | 4 GB | |
| **Stockage** | 20 GB | |
| **IP** | DHCP | Via OPNsense |
| **Features** | nesting=1 | Pour Docker dans LXC |
| **Autostart** | Oui | Ordre 80, délai 15s |
| **Documentation** | `docs/homelab.md:99-103` | |

**Services déployés** :
- **Nginx Proxy Manager** : Reverse proxy + SSL (Let's Encrypt DNS Challenge)
- **Authentik** : SSO (Single Sign-On)
- **Bitwarden** : Gestionnaire mots de passe auto-hébergé

**Migration discutée** :
- 🔄 Bitwarden pourrait rester ici (pas besoin migration vers RPi)

### LXC 210 - Productivity

| Paramètre | Valeur | Notes |
|-----------|--------|-------|
| **Statut** | ✅ DÉPLOYÉ | Configuration manuelle Proxmox |
| **Type** | LXC | Debian 12 unprivileged |
| **vCPU** | 2 | |
| **RAM** | 3 GB | |
| **Stockage** | 30 GB | |
| **IP** | DHCP | Via OPNsense |
| **Features** | nesting=1 | Pour Docker dans LXC |
| **Autostart** | Oui | Ordre 80, délai 15s |
| **Documentation** | `docs/homelab.md:105-108` | |

**Services déployés** :
- **Paperless-ngx** : GED avec OCR (Tesseract)
- **Stirling-PDF** : Manipulation PDF

**Migration planifiée** :
- 📋 Déplacer vers Raspberry Pi 5 (libère 3 GB RAM sur Proxmox)
- ⚠️ OCR sera 2x plus lent sur ARM (acceptable si usage occasionnel)

### Hôte Proxmox

| Paramètre | Valeur | Notes |
|-----------|--------|-------|
| **RAM réservée** | 3 GB | Cache système et ARC |
| **Version** | Proxmox VE 9.1 | |
| **Bridges réseau** | vmbr0 (LAN via enp1s0)<br>vmbr1 (WAN via enp2s0) | |
| **IOMMU** | Activé | Pour GPU passthrough |
| **Documentation** | `docs/bootstrap/proxmox.md` | |

**Amélioration planifiée** :
- 📋 Augmenter cache à 6-12 GB après migrations (meilleures performances I/O)

---

## 📊 Résumé Global des Ressources

### Allocation RAM Actuelle

| Machine | RAM Totale | RAM Utilisée | RAM Libre | Taux |
|---------|-----------|--------------|-----------|------|
| **Raspberry Pi 5** | 8 GB | ~800 MB | ~7.2 GB | 10% |
| **NAS Cargo** | 8 GB | ~500 MB | ~7.5 GB | 6% |
| **Proxmox (total)** | 32 GB | 32 GB | 0 GB | 100% ⚠️ |

**Problème identifié** : Proxmox est à **100% RAM allouée** sans marge.

### Allocation RAM par Instance Proxmox

| Instance | RAM Allouée | Usage Typique | Efficacité |
|----------|-------------|---------------|------------|
| VM 100 (OPNsense) | 2 GB | ~1.6 GB | ✅ Optimisé |
| VM 110 (Media) | 14 GB | ~12-13 GB | ⚠️ Tendu |
| VM 120 (Downloads) | 6 GB | ~4-5 GB | ✅ Correct |
| LXC 200 (Infra) | 4 GB | ~3-3.5 GB | ✅ Correct |
| LXC 210 (Productivity) | 3 GB | ~2.5 GB | ✅ Correct |
| Host Proxmox | 3 GB | - | ❌ Insuffisant |
| **TOTAL** | **32 GB** | | |

---

## 🎯 Services à Déployer (Priorités)

### Priorité Élevée

| Service | Destination | RAM Requise | Bénéfice |
|---------|-------------|-------------|----------|
| **Uptime Kuma** | Raspberry Pi 5 | ~200 MB | Monitoring proactif des services |
| **Grafana + Prometheus + Loki** | Raspberry Pi 5 | ~2.3 GB | Observabilité complète (métriques + logs) |

### Priorité Moyenne

| Service | Destination | RAM Requise | Bénéfice |
|---------|-------------|-------------|----------|
| **Scrutiny Web + Collector** | RPi + NAS | ~250 MB | Surveillance santé disques |
| **Dozzle + Diun** | Raspberry Pi 5 | ~150 MB | Logs Docker + notifications updates |
| **Immich migration** | NAS Cargo | ~6 GB | Libère RAM Proxmox pour cache |
| **Paperless migration** | Raspberry Pi 5 | ~3 GB | Libère RAM Proxmox |

---

## 🔄 Migrations Planifiées

Voir `docs/architecture/migration-plan.md` pour détails complets.

### Phase 1 : Observabilité (Immédiat)
- ✅ Déployer Grafana/Prometheus/Loki sur Raspberry Pi 5
- ✅ Déployer Uptime Kuma, Scrutiny, Dozzle, Diun

**Impact** : +2.8 GB RAM sur RPi, monitoring complet actif

### Phase 2 : Libération RAM Proxmox (Court terme)
- 📋 Migrer Paperless + Stirling vers Raspberry Pi 5
- 📋 Migrer Immich vers NAS Cargo

**Impact** : Libère 9 GB RAM sur Proxmox (3 GB LXC 210 + 6 GB VM 110)

### Phase 3 : Optimisation (Moyen terme)
- 📋 Augmenter cache Proxmox à 12 GB
- 📋 Augmenter RAM VM 110 (Jellyfin seul : 8 GB au lieu de 14 GB)
- 📋 Augmenter RAM VM 120 à 8 GB (téléchargements intensifs)

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
**Dernière vérification** : 2024-12-22
