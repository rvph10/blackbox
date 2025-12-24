# Service Deployment

This guide covers deploying additional VMs and LXC containers on Proxmox for media services, downloads, infrastructure, and productivity tools.

## Overview

After completing the core infrastructure (Proxmox, OPNsense, Raspberry Pi), you can deploy specialized service stacks. The architecture uses a hybrid approach:

- **VMs** for services needing GPU access or kernel-level isolation
- **LXC containers** for lightweight services with shared kernel

All service data lives on the NAS via NFS mounts, making services disposable and easy to rebuild.

## Service Architecture

| Instance | Type | Purpose                                | Status      |
| -------- | ---- | -------------------------------------- | ----------- |
| VM 100   | VM   | OPNsense router                        | ✅ Deployed |
| VM 110   | VM   | Media stack (Jellyfin, Immich)         | 📋 Planned  |
| VM 120   | VM   | Download stack (\*arr, qBittorrent)    | 📋 Planned  |
| LXC 200  | LXC  | Infrastructure (NPM)                   | ✅ Deployed |
| LXC 210  | LXC  | Productivity (Paperless, Stirling-PDF) | 📋 Planned  |

## Resource Allocation

Current allocation across all VMs/LXCs:

| Resource | Allocated | Total                 | Reserved for Host |
| -------- | --------- | --------------------- | ----------------- |
| CPU      | 14 vCPU   | 12 cores (24 threads) | N/A (overcommit)  |
| RAM      | 29 GB     | 32 GB                 | 3 GB              |
| Storage  | 216 GB    | 1 TB NVMe             | ~784 GB free      |

## General VM/LXC Creation Process

### Creating VMs

Standard process for all VMs:

1. **Proxmox UI:** pve > Create VM
2. **General:**
   - VM ID: As per architecture (100, 110, 120)
   - Name: Descriptive (e.g., "Media-Stack")
   - Start at boot: Yes (except for maintenance VMs)
   - Start order: Lower priority than OPNsense (50-90)
3. **OS:**
   - ISO: Upload to local storage first
   - Type: Usually Linux for Docker hosts
4. **System:**
   - Machine: q35
   - BIOS: OVMF (UEFI) for modern OSes
   - SCSI Controller: VirtIO SCSI
5. **Disks:**
   - Bus: SCSI
   - Size: As per architecture
   - Cache: Write back
   - Discard: Yes (for SSD trim)
6. **CPU:**
   - Type: host (best performance)
   - Cores: As per architecture
7. **Memory:**
   - As per architecture
   - Ballooning: Yes
8. **Network:**
   - Bridge: vmbr0 (LAN)
   - Model: VirtIO

### Creating LXC Containers

Standard process for LXC:

1. **Proxmox UI:** pve > Create CT
2. **General:**
   - CT ID: As per architecture (200, 210)
   - Hostname: Descriptive
   - Password: Set strong root password
3. **Template:**
   - Storage: local
   - Template: Usually Ubuntu 22.04 or Debian 12
4. **Disks:**
   - Storage: local-lvm
   - Size: As per architecture
5. **CPU:**
   - Cores: As per architecture
6. **Memory:**
   - RAM: As per architecture
   - Swap: 512 MB (default)
7. **Network:**
   - Bridge: vmbr0
   - IPv4: DHCP (or static if preferred)
   - IPv6: SLAAC (or none)
8. **DNS:**
   - Use host settings: Yes

### Post-Creation Configuration

For both VMs and LXCs:

1. **Start the instance**
2. **Update system:**
   ```bash
   apt update && apt full-upgrade -y
   ```
3. **Install base tools:**
   ```bash
   apt install -y curl wget git vim htop
   ```
4. **Configure NFS mount** (if needed):

   ```bash
   apt install -y nfs-common
   mkdir -p /mnt/appdata /mnt/media /mnt/photos

   # Add to /etc/fstab:
   192.168.10.5:/volume1/appdata  /mnt/appdata  nfs  defaults,_netdev  0  0
   192.168.10.5:/volume1/media    /mnt/media    nfs  defaults,_netdev  0  0

   mount -a
   ```

5. **Install Docker** (for Docker-based stacks):
   ```bash
   curl -fsSL https://get.docker.com | sh
   usermod -aG docker $USER
   ```

## VM 110: Media Stack

**Purpose:** Streaming and photo management with GPU transcoding

**Resources:**

- vCPU: 6 cores
- RAM: 14 GB
- Storage: 100 GB
- GPU: AMD Radeon 760M passthrough

### Services

- **Jellyfin:** Media streaming with hardware transcoding
- **Immich:** Photo management with ML recognition
- **Overseerr:** Media request interface

### Creation Steps

1. Create VM as per general process
2. **Add GPU passthrough:**
   - VM 110 > Hardware > Add > PCI Device
   - Select AMD Radeon 760M (look for VGA device)
   - All Functions: Yes
   - PCI-Express: Yes
   - Primary GPU: No
3. **Install Ubuntu Server 22.04**
4. **Install Docker and Docker Compose**
5. **Mount NFS shares:**
   - `/mnt/appdata` - configuration data
   - `/mnt/media` - movies, TV shows
   - `/mnt/photos` - Immich library

### Docker Compose Example

Create `/opt/media-stack/docker-compose.yml`:

```yaml
version: "3.8"

services:
  jellyfin:
    image: jellyfin/jellyfin:latest
    container_name: jellyfin
    restart: unless-stopped
    ports:
      - "8096:8096"
    volumes:
      - /mnt/appdata/jellyfin/config:/config
      - /mnt/appdata/jellyfin/cache:/cache
      - /mnt/media:/media:ro
    devices:
      - /dev/dri:/dev/dri # GPU for transcoding
    environment:
      - JELLYFIN_PublishedServerUrl=jellyfin.blackbox.homes

  immich-server:
    image: ghcr.io/immich-app/immich-server:release
    container_name: immich_server
    restart: unless-stopped
    ports:
      - "2283:3001"
    volumes:
      - /mnt/photos:/usr/src/app/upload
      - /mnt/appdata/immich:/usr/src/app/config
    depends_on:
      - immich-postgres
      - immich-redis

  immich-postgres:
    image: tensorchord/pgvecto-rs:pg14-v0.2.0
    container_name: immich_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: immich
      POSTGRES_PASSWORD: immich_password
      POSTGRES_DB: immich
    volumes:
      - /mnt/appdata/immich/postgres:/var/lib/postgresql/data

  immich-redis:
    image: redis:7-alpine
    container_name: immich_redis
    restart: unless-stopped
```

Deploy:

```bash
cd /opt/media-stack
docker compose up -d
```

### Verification

- Jellyfin: http://192.168.10.100:8096
- Immich: http://192.168.10.100:2283
- Check GPU transcoding: Play a video in Jellyfin, check if GPU is used

## VM 120: Download Stack

**Purpose:** Automated media downloads with VPN isolation

**Resources:**

- vCPU: 2 cores
- RAM: 6 GB
- Storage: 50 GB

### Services

- **Gluetun:** VPN container with killswitch
- **qBittorrent:** Torrent client
- **Radarr:** Movie automation
- **Sonarr:** TV show automation
- **Prowlarr:** Indexer manager
- **Bazarr:** Subtitle management

### Creation Steps

1. Create VM as per general process
2. Install Ubuntu Server 22.04
3. Install Docker and Docker Compose
4. Mount NFS shares:
   - `/mnt/appdata` - configuration
   - `/mnt/media` - download destination

### Docker Compose Example

Create `/opt/download-stack/docker-compose.yml`:

```yaml
version: "3.8"

services:
  gluetun:
    image: qmcgaw/gluetun:latest
    container_name: gluetun
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun:/dev/net/tun
    ports:
      - "8080:8080" # qBittorrent
      - "7878:7878" # Radarr
      - "8989:8989" # Sonarr
      - "9696:9696" # Prowlarr
    environment:
      - VPN_SERVICE_PROVIDER=your_vpn
      - VPN_TYPE=openvpn
      - OPENVPN_USER=your_username
      - OPENVPN_PASSWORD=your_password
    volumes:
      - /mnt/appdata/gluetun:/gluetun

  qbittorrent:
    image: linuxserver/qbittorrent:latest
    container_name: qbittorrent
    restart: unless-stopped
    network_mode: "service:gluetun"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Brussels
      - WEBUI_PORT=8080
    volumes:
      - /mnt/appdata/qbittorrent:/config
      - /mnt/media/downloads:/downloads

  radarr:
    image: linuxserver/radarr:latest
    container_name: radarr
    restart: unless-stopped
    network_mode: "service:gluetun"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Brussels
    volumes:
      - /mnt/appdata/radarr:/config
      - /mnt/media:/media

  sonarr:
    image: linuxserver/sonarr:latest
    container_name: sonarr
    restart: unless-stopped
    network_mode: "service:gluetun"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Brussels
    volumes:
      - /mnt/appdata/sonarr:/config
      - /mnt/media:/media
```

Deploy:

```bash
cd /opt/download-stack
docker compose up -d
```

### VPN Killswitch Verification

Test that downloads stop if VPN disconnects:

```bash
# Check VPN IP
docker exec gluetun wget -qO- ifconfig.me

# Should NOT be your ISP's IP

# Stop VPN
docker stop gluetun

# Try downloading - should fail
```

## LXC 200: Infrastructure

**Purpose:** Reverse proxy, authentication, password management

**Resources:**

- vCPU: 2 cores
- RAM: 4 GB
- Storage: 20 GB

### Services

- **Nginx Proxy Manager:** Reverse proxy with SSL (Deployed)
- **Authentik:** SSO/authentication provider (Planned)
- **Vaultwarden:** Bitwarden-compatible password manager (Planned)

### Creation Steps

1. Create LXC container (Ubuntu 22.04)
2. Install Docker
3. Deploy services via Docker Compose (see `ansible/playbooks/deploy_npm.yml`)

### Docker Compose Example

Current deployment uses local storage for simplicity.

```yaml
services:
  app:
    image: "jc21/nginx-proxy-manager:latest"
    restart: unless-stopped
    ports:
      - "80:80"
      - "81:81"
      - "443:443"
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
```

Note: Future services (Authentik, Vaultwarden) will be added to this stack.

### Configure Nginx Proxy Manager

1. Access: http://192.168.10.200:81
2. Default credentials: admin@example.com / changeme
3. Change password immediately
4. Add proxy hosts for each service
5. Configure SSL via Let's Encrypt DNS challenge

## LXC 210: Productivity

**Purpose:** Document management and PDF tools

**Resources:**

- vCPU: 2 cores
- RAM: 3 GB
- Storage: 30 GB

### Services

- **Paperless-ngx:** Document management system
- **Stirling-PDF:** PDF manipulation tools

### Docker Compose Example

```yaml
version: "3.8"

services:
  paperless-ngx:
    image: ghcr.io/paperless-ngx/paperless-ngx:latest
    container_name: paperless
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - /mnt/appdata/paperless/data:/usr/src/paperless/data
      - /mnt/appdata/paperless/media:/usr/src/paperless/media
      - /mnt/appdata/paperless/export:/usr/src/paperless/export
      - /mnt/appdata/paperless/consume:/usr/src/paperless/consume
    environment:
      - PAPERLESS_REDIS=redis://paperless-redis:6379
      - PAPERLESS_DBHOST=paperless-db
    depends_on:
      - paperless-db
      - paperless-redis

  stirling-pdf:
    image: frooodle/s-pdf:latest
    container_name: stirling-pdf
    restart: unless-stopped
    ports:
      - "8090:8080"
    volumes:
      - /mnt/appdata/stirling-pdf:/configs
    environment:
      - DOCKER_ENABLE_SECURITY=false
```

## Using Ansible Playbooks

While not all services have dedicated playbooks yet, you can create reusable playbooks for common deployment patterns.

### Example: Generic Docker Stack Playbook

Create `playbooks/deploy_docker_stack.yml`:

```yaml
---
- name: Deploy Docker Stack
  hosts: "{{ target_host }}"
  become: yes

  vars:
    stack_name: "{{ stack }}"
    stack_path: "/opt/{{ stack_name }}"

  tasks:
    - name: Install Docker
      shell: curl -fsSL https://get.docker.com | sh
      args:
        creates: /usr/bin/docker

    - name: Install Docker Compose
      apt:
        name: docker-compose-plugin
        state: present

    - name: Create stack directory
      file:
        path: "{{ stack_path }}"
        state: directory
        mode: "0755"

    - name: Copy docker-compose.yml
      template:
        src: "templates/{{ stack_name }}/docker-compose.yml.j2"
        dest: "{{ stack_path }}/docker-compose.yml"
        mode: "0644"

    - name: Start stack
      community.docker.docker_compose_v2:
        project_src: "{{ stack_path }}"
        state: present
```

Usage:

```bash
ansible-playbook playbooks/deploy_docker_stack.yml \
  -e "target_host=media_stack" \
  -e "stack=jellyfin"
```

## Monitoring Services

Add monitoring for all services via Prometheus exporters.

### Add Node Exporter to Each VM/LXC

```bash
# On each VM/LXC
docker run -d \
  --name=node_exporter \
  --restart=unless-stopped \
  --net=host \
  --pid=host \
  -v /:/rootfs:ro \
  prom/node-exporter:latest \
  --path.rootfs=/rootfs
```

### Configure Prometheus to Scrape

Edit Prometheus config on Raspberry Pi:

```yaml
scrape_configs:
  - job_name: "media-stack"
    static_configs:
      - targets: ["192.168.10.100:9100"]

  - job_name: "download-stack"
    static_configs:
      - targets: ["192.168.10.101:9100"]

  - job_name: "infrastructure"
    static_configs:
      - targets: ["192.168.10.200:9100"]
```

Restart Prometheus:

```bash
docker restart prometheus
```

## Backup Strategy

All service data is on the NAS and backed up automatically:

1. **NFS mounts** provide real-time persistence
2. **Btrfs snapshots** on NAS for point-in-time recovery
3. **Backblaze B2** for off-site backups
4. **Proxmox VZDump** backs up entire VMs to NAS

To backup a VM manually:

```bash
ssh root@192.168.10.10
vzdump 110 --storage nas-backups --mode snapshot --compress zstd
```

## Service Access

After deploying services, configure DNS and access:

1. **Add DNS entries in AdGuard:**

   - jellyfin.blackbox.homes → 192.168.10.100
   - radarr.blackbox.homes → 192.168.10.101
   - npm.blackbox.homes → 192.168.10.200

2. **Configure Nginx Proxy Manager** for SSL:

   - Create proxy hosts for each service
   - Use Let's Encrypt DNS challenge for certs
   - Access via https://service.blackbox.homes

3. **Access via Tailscale:**
   - All services accessible remotely via subnet route
   - Use same URLs: https://jellyfin.blackbox.homes

## Validation Checklist

For each deployed service:

- [ ] VM/LXC created with correct resources
- [ ] OS installed and updated
- [ ] NFS mounts working
- [ ] Docker installed
- [ ] Services running (`docker ps`)
- [ ] Web UI accessible
- [ ] DNS entry added
- [ ] Monitoring configured
- [ ] Data persisting to NAS
- [ ] Service working after reboot

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker logs <container_name>

# Common issues:
# - Port already in use: netstat -tulpn | grep <port>
# - NFS mount missing: df -h | grep /mnt
# - Permissions: ls -la /mnt/appdata/<service>
```

### Can't Access Web UI

```bash
# Check container is running
docker ps | grep <service>

# Check port binding
docker port <container_name>

# Test locally
curl http://localhost:<port>

# Check firewall
iptables -L | grep <port>
```

### GPU Not Working (Jellyfin)

```bash
# Check GPU passthrough
lspci | grep VGA

# Check /dev/dri exists
ls -la /dev/dri

# Check permissions
groups
# Should include 'render' or 'video'

# Add user to groups if needed
usermod -aG render,video $USER
```

## Next Steps

After deploying services:

1. **Configure integrations** between services (Radarr → qBittorrent, etc.)
2. **Set up automated monitoring** alerts in Grafana
3. **Configure external access** via Nginx Proxy Manager
4. **Test disaster recovery** by rebuilding a VM from backup
5. **Document any custom configurations** you add

## Reference

- **Service status:** `docs/services-status.md`
- **Architecture:** `docs/homelab.md`
- **Playbooks:** `docs/playbooks/`
- **Migration plan:** `docs/architecture/migration-plan.md`
