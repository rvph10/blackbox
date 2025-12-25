# Deployment Status

**Single source of truth** for what's deployed, what's planned, and what's not happening.

---

## Status Legend

| Symbol | Status      | Meaning                           |
| ------ | ----------- | --------------------------------- |
| ✅     | DEPLOYED    | Active and configured via Ansible |
| 📋     | PLANNED     | Documented, not yet implemented   |
| ❌     | NOT PLANNED | Abandoned or not relevant         |

---

## Raspberry Pi 5 (Control Tower)

**IP**: 192.168.10.2
**RAM**: 8 GB (3.8 GB used / 4.2 GB free)
**OS**: Raspberry Pi OS + Docker

### Core Services

| Service               | Status      | Ports        | URL                      | Notes                                       |
| --------------------- | ----------- | ------------ | ------------------------ | ------------------------------------------- |
| AdGuard Home          | ✅ DEPLOYED | 53, 80, 3000 | http://192.168.10.2      | DNS master with ad blocking                 |
| Home Assistant        | ✅ DEPLOYED | 8123         | http://192.168.10.2:8123 | Home automation (Z-Wave, Zigbee, WiFi)      |
| Homepage              | ✅ DEPLOYED | 8082         | http://192.168.10.2:8082 | Web dashboard                               |
| Tailscale             | ✅ DEPLOYED | -            | -                        | VPN mesh, subnet router for 192.168.10.0/24 |
| Touchscreen Dashboard | ✅ DEPLOYED | -            | Physical screen          | Python app, 3.5" capacitive display         |

### Observability Stack

| Service       | Status      | Ports | URL                      | Notes                              |
| ------------- | ----------- | ----- | ------------------------ | ---------------------------------- |
| Grafana       | ✅ DEPLOYED | 3001  | http://192.168.10.2:3001 | Metrics and logs visualization     |
| Prometheus    | ✅ DEPLOYED | 9090  | http://192.168.10.2:9090 | Metrics collection (CPU, RAM, I/O) |
| Loki          | ✅ DEPLOYED | 3100  | http://192.168.10.2:3100 | Log aggregation                    |
| Promtail      | ✅ DEPLOYED | -     | -                        | Log collector agent for Loki       |
| Alertmanager  | ✅ DEPLOYED | 9093  | http://192.168.10.2:9093 | Alerting system (Discord)          |
| Node Exporter | ✅ DEPLOYED | 9100  | -                        | System metrics exporter            |

### Planned Services

| Service        | Status     | Port | Purpose                           | Priority |
| -------------- | ---------- | ---- | --------------------------------- | -------- |
| Uptime Kuma    | 📋 PLANNED | 3002 | Service availability monitoring   | High     |
| Scrutiny (Web) | 📋 PLANNED | 8080 | Disk health dashboard (S.M.A.R.T) | Medium   |
| Dozzle         | 📋 PLANNED | 9999 | Real-time Docker logs viewer      | Medium   |
| Diun           | 📋 PLANNED | -    | Docker image update notifications | Medium   |
| Paperless-ngx  | 📋 PLANNED | 8000 | Document management with OCR      | Medium   |
| Stirling-PDF   | 📋 PLANNED | 8080 | PDF manipulation                  | Low      |

**Config**: `/opt/blackbox/docker-compose.yml`
**Data**: `/mnt/appdata/` (NFS from NAS)

---

## NAS Cargo (UGREEN DXP2800)

**IP**: 192.168.10.5
**CPU**: Intel N100 (4C/4T)
**RAM**: 8 GB DDR5 (500 MB used / 7.5 GB free)
**Storage**: 3.6 TB usable (RAID 1 Btrfs) + 500 GB NVMe cache
**OS**: UGOS (UGREEN firmware)

### Services

| Service       | Status      | Description                                                       | Notes                     |
| ------------- | ----------- | ----------------------------------------------------------------- | ------------------------- |
| NFS Shares    | ✅ DEPLOYED | Exports: appdata, media, photos, proxmox-backups, backups-configs | Mounted by all hosts      |
| SMB Shares    | ✅ DEPLOYED | Windows/Mac access                                                | For manual management     |
| Rclone Backup | ✅ DEPLOYED | Daily sync to Backblaze B2 (03:00 AM)                             | 3-2-1 backup strategy     |
| LED Control   | ✅ DEPLOYED | Off at 23:00, on at 09:00                                         | Via cron + i2c-dev module |

### Planned Services

| Service            | Status     | Purpose                                      | Priority | Notes                                   |
| ------------------ | ---------- | -------------------------------------------- | -------- | --------------------------------------- |
| Scrutiny Collector | 📋 PLANNED | Local S.M.A.R.T monitoring agent             | Medium   | Sends data to Scrutiny Web on RPi       |
| Immich             | 📋 PLANNED | Photo/video management (migrate from VM 110) | Medium   | Requires performance validation on N100 |

**Note**: NAS primarily for storage. Immich migration possible due to modern Intel N100 + 8 GB DDR5, though ML will be 3-5x slower than Ryzen 5.

---

## Proxmox VE (GMKtec NucBox M6)

**IP**: 192.168.10.10
**CPU**: AMD Ryzen 5 7640HS (6C/12T @ 5.0 GHz)
**RAM**: 32 GB DDR5 (5 GB used / 27 GB free)
**Storage**: 1 TB NVMe PCIe 4.0
**GPU**: AMD Radeon 760M (iGPU, passthrough enabled)

### VM 100 - OPNsense (Router/Firewall)

| Parameter  | Value                                  | Notes                            |
| ---------- | -------------------------------------- | -------------------------------- |
| Status     | ✅ DEPLOYED                            | Manual Proxmox configuration     |
| vCPU       | 2                                      |                                  |
| RAM        | 2 GB                                   | Reduced from 4 GB after analysis |
| Storage    | 16 GB                                  |                                  |
| IP         | 192.168.10.1                           | Static (LAN gateway)             |
| Interfaces | net0: vmbr0 (LAN)<br>net1: vmbr1 (WAN) | Dual NIC for WAN/LAN isolation   |
| Autostart  | Yes                                    | Order 100, delay 60s             |

**Active features**:

- Routing (PPPoE to ISP)
- Firewall (pf)
- DHCP (range 192.168.10.100-200)
- DNS Forwarder (to AdGuard 192.168.10.2)

---

### VM 110 - Media Stack

| Parameter | Value                       | Notes                                  |
| --------- | --------------------------- | -------------------------------------- |
| Status    | 📋 PLANNED                  | Not deployed                           |
| vCPU      | 6                           | For transcoding parallelization + ML   |
| RAM       | 14 GB                       | Jellyfin (4-6 GB) + Immich (6-8 GB)    |
| Storage   | 100 GB                      |                                        |
| IP        | DHCP                        | Via OPNsense                           |
| GPU       | AMD Radeon 760M passthrough | Jellyfin transcoding + ML acceleration |
| Autostart | Yes                         | Order 90, delay 30s                    |

**Planned services**:

- Jellyfin (video streaming with GPU transcoding)
- Immich (photo/video with ML - face recognition, objects)
- Overseerr (media requests interface)

---

### VM 120 - Download Stack

| Parameter | Value          | Notes               |
| --------- | -------------- | ------------------- |
| Status    | 📋 PLANNED     | Not deployed        |
| vCPU      | 2              |                     |
| RAM       | 6 GB           |                     |
| Storage   | 50 GB          |                     |
| IP        | DHCP           | Via OPNsense        |
| Isolation | VPN Killswitch | Via Gluetun         |
| Autostart | Yes            | Order 90, delay 30s |

**Planned services**:

- Gluetun (VPN gateway with killswitch)
- qBittorrent
- Radarr (movies automation)
- Sonarr (TV shows automation)
- Prowlarr (indexer management)
- Bazarr (subtitles management)

---

### LXC 200 - Infrastructure

| Parameter | Value                  | Notes               |
| --------- | ---------------------- | ------------------- |
| Status    | 📋 PLANNED             | Not deployed        |
| Type      | Debian 12 unprivileged |                     |
| vCPU      | 2                      |                     |
| RAM       | 4 GB                   |                     |
| Storage   | 20 GB                  |                     |
| Features  | nesting=1              | For Docker in LXC   |
| Autostart | Yes                    | Order 80, delay 15s |

**Planned services**:

- Nginx Proxy Manager (reverse proxy + SSL)
- Authentik (SSO)
- Bitwarden (password manager)

---

### LXC 210 - Productivity

| Parameter | Value                  | Notes               |
| --------- | ---------------------- | ------------------- |
| Status    | 📋 PLANNED             | Not deployed        |
| Type      | Debian 12 unprivileged |                     |
| vCPU      | 2                      |                     |
| RAM       | 3 GB                   |                     |
| Storage   | 30 GB                  |                     |
| Features  | nesting=1              | For Docker in LXC   |
| Autostart | Yes                    | Order 80, delay 15s |

**Planned services**:

- Paperless-ngx (document management with OCR)
- Stirling-PDF (PDF manipulation)

**Alternative**: Could deploy on Raspberry Pi instead of Proxmox

---

### Proxmox Host

| Parameter       | Value                                            | Notes                |
| --------------- | ------------------------------------------------ | -------------------- |
| Reserved RAM    | 3 GB                                             | System cache and ARC |
| Version         | Proxmox VE 9.1                                   |                      |
| Network bridges | vmbr0 (LAN via enp1s0)<br>vmbr1 (WAN via enp2s0) |                      |
| IOMMU           | Enabled                                          | For GPU passthrough  |

**Planned improvement**: Increase cache to 6-12 GB after VM migrations for better I/O performance

---

## Resource Summary

### Current RAM Allocation

| Machine         | Total RAM | Used    | Free    | Usage  |
| --------------- | --------- | ------- | ------- | ------ |
| Raspberry Pi 5  | 8 GB      | ~3.8 GB | ~4.2 GB | 48%    |
| NAS Cargo       | 8 GB      | ~500 MB | ~7.5 GB | 6%     |
| Proxmox (total) | 32 GB     | ~5 GB   | ~27 GB  | 16% ✅ |

**Current state**: Proxmox has lots of free RAM (27 GB available) since only VM 100 (OPNsense) is deployed.

### Planned Proxmox RAM Allocation

| Instance               | RAM Allocated | Typical Usage | Efficiency             | Status      |
| ---------------------- | ------------- | ------------- | ---------------------- | ----------- |
| VM 100 (OPNsense)      | 2 GB          | ~1.6 GB       | ✅ Optimized           | ✅ Deployed |
| VM 110 (Media)         | 14 GB         | ~12-13 GB     | ⚠️ Tight               | 📋 Planned  |
| VM 120 (Downloads)     | 6 GB          | ~4-5 GB       | ✅ Good                | 📋 Planned  |
| LXC 200 (Infra)        | 4 GB          | ~3-3.5 GB     | ✅ Good                | 📋 Planned  |
| LXC 210 (Productivity) | 3 GB          | ~2.5 GB       | ✅ Good                | 📋 Planned  |
| Host Proxmox           | 3 GB          | -             | ✅ Current             | ✅ Active   |
| **TOTAL**              | **32 GB**     |               | **84% FREE currently** |             |

---

## Deployment Priorities

### Recently Deployed ✅

- Complete observability stack (Grafana + Prometheus + Loki + Promtail)
- Node Exporter on all hosts
- Grafana dashboard 1860 (Node Exporter Full)

### High Priority

- Uptime Kuma (service monitoring)
- VM 110 (Media Stack - Jellyfin + Immich + Overseerr)
- LXC 200 (Infrastructure - NPM + Authentik + Bitwarden)

### Medium Priority

- Scrutiny Web + Collector (disk health monitoring)
- Dozzle + Diun (Docker logs + update notifications)
- VM 120 (Download Stack - Gluetun + \*Arr stack)
- LXC 210 (Productivity - Paperless-ngx + Stirling-PDF)

---

## Deployment Plan

See `/docs/architecture/migration-plan.md` for full details.

### Phase 1: Observability (In Progress)

- ✅ Grafana/Prometheus/Loki/Promtail configured
- ✅ Node Exporter deployed on all hosts
- 📋 Deploy Uptime Kuma, Scrutiny, Dozzle, Diun

**Impact**: +2.8 GB RAM on RPi, complete monitoring active

### Phase 2: Proxmox Infrastructure (High Priority)

- 📋 Create VM 110 (Media Stack)
- 📋 Create LXC 200 (Infrastructure)
- 📋 Create VM 120 (Download Stack)

**Impact**: 24 GB RAM used on Proxmox (8 GB remaining)

### Phase 3: Additional Services (Medium Term)

- 📋 Deploy LXC 210 (Productivity) on Proxmox OR Raspberry Pi
- 📋 Deploy additional monitoring services
- 📋 Evaluate Immich migration to NAS if needed

---

## Maintenance Commands

```bash
# Check Raspberry Pi services
ssh control-tower.blackbox.homes
docker ps
docker stats

# Check Proxmox allocation
ssh pve.blackbox.homes
qm list              # VMs
pct list             # LXCs
free -h              # Host RAM

# Redeploy Raspberry Pi stack
cd /home/rvph/Projects/blackbox/ansible
ansible-playbook playbooks/deploy_rpi_stack.yml

# Check Backblaze B2 backups
ssh 192.168.10.5
cat /volume1/appdata/rclone/backup_status.json
```

---

## Cross-References

- Detailed architecture: `/docs/homelab.md`
- Compute allocation: `/docs/architecture/compute-allocation.md`
- Playbooks reference: `/docs/reference/playbooks.md`
- Migration plan: `/docs/architecture/migration-plan.md`
- Operations guide: `/docs/operations.md`

---

**Maintained by**: Ansible automation + manual documentation
