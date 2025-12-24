# Raspberry Pi Control Tower Deployment

This guide covers setting up the Raspberry Pi 5 as your critical services platform. This hosts AdGuard (DNS), Home Assistant (home automation), and the monitoring stack (Prometheus/Grafana/Loki).

## Overview

The Raspberry Pi serves as the "control tower" - critical infrastructure that stays up even if Proxmox is down. It runs:

- **AdGuard Home:** Network-wide DNS and ad blocking
- **Home Assistant:** Home automation hub
- **Homepage:** Web dashboard
- **Monitoring Stack:** Prometheus, Loki, Grafana for metrics and logs
- **Tailscale:** VPN mesh for remote access

All data is stored on the NAS via NFS, so the Pi can be rebuilt quickly without data loss.

## Hardware Setup

**Device:** Raspberry Pi 5

**Accessories:**
- NVMe SSD for boot drive (faster and more reliable than SD card)
- NVMe HAT/adapter
- Power supply (official 27W recommended)
- Ethernet cable to switch
- Optional: 3.5" touchscreen for local dashboard

**Network:**
- Connect Ethernet to switch
- Wi-Fi disabled (hardwired only for reliability)

## OS Installation

Use the Raspberry Pi Imager tool on your laptop.

### 1. Download Imager

Get it from: https://www.raspberrypi.com/software/

### 2. Configure Image

1. **OS:** Raspberry Pi OS Lite (64-bit)
   - No desktop environment needed
   - Saves resources for services

2. **Storage:** Your NVMe drive (via USB adapter or in the Pi)

3. **Settings (Gear icon):**
   - Hostname: `control-tower`
   - Username: `admin` (must match Ansible vault!)
   - Password: Set a password (used only until SSH keys deployed)
   - Wi-Fi: Skip (using Ethernet)
   - Locale: Your timezone and keyboard layout
   - SSH: **Enable with password authentication**

4. **Write and Boot:**
   - Write the image
   - Insert NVMe in Pi and boot
   - Wait 1-2 minutes for first boot

### 3. Find the Pi's IP

The Pi will initially get DHCP from your temporary network setup:

```bash
# Option 1: Check DHCP leases on OPNsense
# Services > ISC DHCPv4 > Leases
# Look for hostname "control-tower"

# Option 2: Scan network
nmap -sn 192.168.10.0/24 | grep -B 2 "Raspberry"

# Option 3: Try the hostname (if DNS working)
ping control-tower.local
```

Note the temporary IP address - you'll need it for the bootstrap playbook.

## Bootstrap with Ansible

The bootstrap playbook handles all initial configuration:
- Sets static IP to 192.168.10.2
- Installs Docker
- Mounts NFS share from NAS
- Configures systemd for NFS auto-mount at boot

### Prerequisites

1. **Vault configured** - Your Ansible vault should have these variables:
   - `vault_rpi_ip`: `192.168.10.2`
   - `vault_rpi_hostname`: `control-tower`
   - `vault_gateway_ip`: `192.168.10.1`
   - `vault_cargo_ip`: `192.168.10.5`
   - `vault_rpi_user`: `admin`
   - SSH public key for authentication

2. **NAS accessible** - The NAS must be running and NFS share `/volume1/appdata` must be configured

3. **Update inventory** - Temporarily set the Pi's DHCP IP in inventory for first run

### Run Bootstrap

```bash
cd /home/rvph/Projects/blackbox/ansible

# First, test connectivity with temporary DHCP IP
ansible raspberry -m ping

# Run the bootstrap playbook
ansible-playbook playbooks/bootstrap_rpi.yml

# The playbook will:
# 1. Configure static IP 192.168.10.2
# 2. Set hostname to control-tower
# 3. Install Docker
# 4. Mount NFS from NAS
# 5. Configure systemd for auto-mount
```

After bootstrap completes, the Pi will have static IP 192.168.10.2. You'll need to wait a moment, then:

```bash
# Reconnect with new static IP
ssh admin@192.168.10.2

# Or use hostname
ssh admin@control-tower.blackbox.homes
```

### What Bootstrap Configures

1. **Network:**
   - Static IP: 192.168.10.2/24
   - Gateway: 192.168.10.1
   - DNS: 192.168.10.2 (itself, for AdGuard)

2. **Hostname:**
   - System hostname: control-tower
   - FQDN: control-tower.blackbox.homes

3. **Docker:**
   - Installed via official script
   - User added to docker group (no sudo needed)

4. **NFS Mount:**
   - Mount point: `/mnt/appdata`
   - Target: `192.168.10.5:/volume1/appdata`
   - Systemd service for auto-mount at boot
   - Uses `_netdev` option to wait for network

## Verification After Bootstrap

### 1. Check Network

```bash
ssh admin@192.168.10.2

# Verify IP
ip addr show eth0 | grep inet
# Should show: inet 192.168.10.2/24

# Verify gateway
ip route | grep default
# Should show: default via 192.168.10.1

# Test internet
ping 1.1.1.1
ping google.com
```

### 2. Check Hostname

```bash
hostnamectl
# Should show: Static hostname: control-tower
```

### 3. Check Docker

```bash
docker --version
# Should show Docker version 24.x or newer

# Test without sudo
docker run hello-world
# Should work without permission errors

# Check user groups
groups
# Should include 'docker'
```

### 4. Check NFS Mount

```bash
# Verify mount is active
mount | grep /mnt/appdata
# Should show: 192.168.10.5:/volume1/appdata on /mnt/appdata type nfs

# Test write access
touch /mnt/appdata/test.txt
ls -la /mnt/appdata/
rm /mnt/appdata/test.txt

# Check systemd service
systemctl status mnt-appdata.mount
# Should show: Active: active (mounted)
```

## Deploy Docker Stack

Now deploy the actual services (AdGuard, Home Assistant, monitoring, etc.):

```bash
cd /home/rvph/Projects/blackbox/ansible
ansible-playbook playbooks/deploy_rpi_stack.yml
```

This playbook:
1. Stops systemd-resolved (frees port 53 for AdGuard)
2. Creates NFS directories for each service
3. Deploys docker-compose.yml from template
4. Starts all containers

**Services deployed:**
- AdGuard Home (DNS, port 53, 80, 3000)
- Home Assistant (home automation, port 8123)
- Homepage (dashboard, port 8082)
- Prometheus (metrics, port 9090)
- Loki (log aggregation, port 3100)
- Grafana (visualization, port 3000)
- Promtail (log collection)
- Node Exporter (system metrics, port 9100)

### Verify Services

```bash
ssh admin@192.168.10.2

# Check running containers
docker ps

# Should see:
# - adguard
# - homeassistant
# - homepage
# - prometheus
# - loki
# - grafana
# - promtail
# - node_exporter

# Check logs if any issues
docker logs adguard
docker logs homeassistant
```

### Test Service Access

From your laptop/desktop:

```bash
# AdGuard (initial setup on port 3000, then port 80)
curl -I http://192.168.10.2:3000

# Home Assistant
curl -I http://192.168.10.2:8123

# Homepage
curl -I http://192.168.10.2:8082

# Grafana
curl -I http://192.168.10.2:3000

# Prometheus
curl -I http://192.168.10.2:9090
```

Or open in browser:
- AdGuard: http://192.168.10.2:3000 (first time) or http://192.168.10.2
- Home Assistant: http://192.168.10.2:8123
- Homepage: http://192.168.10.2:8082
- Grafana: http://192.168.10.2:3000

## Configure AdGuard Home

AdGuard is your DNS server - all network clients use it.

### Initial Setup

1. **Access setup wizard:** http://192.168.10.2:3000
2. **Admin interface:** Port `80` (default)
3. **DNS server:** Port `53` (default)
4. **Create admin account** with username and password
5. Click through wizard to finish

### Configure DNS Settings

After initial setup, configure upstream DNS servers:

1. **Settings > DNS Settings**
2. **Upstream DNS servers:**
   ```
   tls://1.1.1.1
   tls://9.9.9.9
   https://dns.cloudflare.com/dns-query
   ```
   This uses DNS-over-TLS and DNS-over-HTTPS for privacy

3. **Bootstrap DNS:** `1.1.1.1`
4. **Private reverse DNS servers:** (leave empty)
5. Click "Save"

### Configure DNS Rewrites (Local Resolution)

Add local hostnames so they resolve on your network:

1. **Filters > DNS Rewrites**
2. Add these entries:

| Domain | Answer |
|--------|--------|
| router.blackbox.homes | 192.168.10.1 |
| pve.blackbox.homes | 192.168.10.10 |
| control-tower.blackbox.homes | 192.168.10.2 |
| nas.blackbox.homes | 192.168.10.5 |
| cargo.blackbox.homes | 192.168.10.5 |

3. Click "Save" after each entry

### Enable Blocking Lists

1. **Filters > DNS Blocklists**
2. Enable recommended lists:
   - AdGuard DNS filter
   - AdAway Default Blocklist
   - Peter Lowe's List
3. Click "Save" and "Update filters"

### Test DNS

From a client that's using AdGuard as DNS:

```bash
# Test normal resolution
nslookup google.com 192.168.10.2

# Test local resolution
nslookup pve.blackbox.homes 192.168.10.2
# Should return: 192.168.10.10

# Test blocking
nslookup ads.google.com 192.168.10.2
# Should return: 0.0.0.0 (blocked)
```

## Configure Home Assistant

Home Assistant is your home automation hub.

### Initial Setup

1. **Access:** http://192.168.10.2:8123
2. **Create account:** First account is the owner
3. **Set up home:**
   - Name: Your home name
   - Location: Set on map
   - Timezone: Should auto-detect
   - Unit system: Metric or Imperial
4. Click "Create"

### Basic Configuration

1. **Enable Advanced Mode:**
   - Profile (bottom left) > Toggle "Advanced Mode"

2. **Integrations:**
   - Settings > Devices & Services > Add Integration
   - Search for and add:
     - AdGuard Home (URL: http://192.168.10.2)
     - Raspberry Pi (local system stats)
     - Any smart home devices you have

3. **Check USB Devices** (if using Zigbee/Z-Wave):
   ```bash
   ssh admin@192.168.10.2
   ls -la /dev/tty*
   # Should see /dev/ttyUSB0 or similar for USB dongles
   ```

## Configure Grafana

Grafana provides visualization for metrics and logs.

### Initial Setup

1. **Access:** http://192.168.10.2:3000
2. **Default credentials:**
   - Username: `admin`
   - Password: `admin`
3. **Change password** when prompted

### Add Data Sources

#### Prometheus (Metrics)

1. **Configuration > Data Sources > Add data source**
2. Select "Prometheus"
3. **URL:** `http://prometheus:9090`
4. **Access:** Server (default)
5. Click "Save & Test"

#### Loki (Logs)

1. **Add data source**
2. Select "Loki"
3. **URL:** `http://loki:3100`
4. **Access:** Server
5. Click "Save & Test"

### Import Dashboards

1. **Dashboards > Import**
2. **Import Dashboard 1860** (Node Exporter Full):
   - Enter `1860` in "Import via grafana.com"
   - Click "Load"
   - Select "Prometheus" as data source
   - Click "Import"

3. **Repeat for other useful dashboards:**
   - 15172: Node Exporter Quickstart
   - 13639: Loki & Promtail
   - 7362: Docker monitoring (if monitoring containers)

### View Metrics

You should now see system metrics:
- CPU usage
- Memory usage
- Disk I/O
- Network traffic
- System logs

## Install Tailscale

Tailscale provides secure remote access to your homelab.

```bash
cd /home/rvph/Projects/blackbox/ansible
ansible-playbook playbooks/install_tailscale.yml
```

### Approve Subnet Route

After installation:

1. **Go to:** https://login.tailscale.com/admin/machines
2. **Find:** control-tower
3. **Click:** "..." > "Edit route settings"
4. **Enable:** `192.168.10.0/24` subnet route
5. **Save**

### Configure MagicDNS

1. **Go to:** https://login.tailscale.com/admin/dns
2. **Enable:** MagicDNS
3. **Add nameserver:**
   - Custom: `192.168.10.2` (AdGuard)
4. **Enable:** "Override local DNS"

Now when connected to Tailscale, you can:
- Access services via `http://192.168.10.2:8123` even when away
- DNS queries go through AdGuard (ad blocking everywhere)
- Fully encrypted via WireGuard

### Test Remote Access

From phone/laptop on cellular/different network:

```bash
# Connect to Tailscale
# Then test access:
ping 192.168.10.2
curl http://192.168.10.2:8123
```

## Common Issues

### Port 53 Already in Use

**Symptom:** AdGuard won't start, port 53 conflict

**Fix:**
```bash
ssh admin@192.168.10.2

# Check what's using port 53
sudo lsof -i :53

# Usually systemd-resolved
sudo systemctl stop systemd-resolved
sudo systemctl disable systemd-resolved

# Remove resolv.conf symlink
sudo rm /etc/resolv.conf
echo "nameserver 1.1.1.1" | sudo tee /etc/resolv.conf

# Restart AdGuard
docker restart adguard
```

### NFS Mount Fails

**Symptom:** `/mnt/appdata` not mounted, services fail to start

**Fix:**
```bash
# Check NAS is accessible
ping 192.168.10.5

# Check NFS exports
showmount -e 192.168.10.5

# Manual mount test
sudo mount -t nfs 192.168.10.5:/volume1/appdata /mnt/appdata

# Check systemd service
systemctl status mnt-appdata.mount

# Restart if needed
sudo systemctl restart mnt-appdata.mount
```

### Docker Permission Denied

**Symptom:** `docker: permission denied` errors

**Fix:**
```bash
# Add user to docker group
sudo usermod -aG docker admin

# Logout and back in
exit
ssh admin@192.168.10.2

# Verify
groups
docker ps
```

### Services Not Starting

**Symptom:** Docker containers exit immediately

**Fix:**
```bash
# Check logs
docker logs <container_name>

# Common issues:
# - NFS mount not working (check /mnt/appdata)
# - Port conflicts (check with: sudo lsof -i :<port>)
# - Permissions (check NFS share permissions)

# Restart all services
cd /opt/blackbox
docker compose down
docker compose up -d
```

## Validation Checklist

Before moving on, verify:

- [ ] Pi has static IP 192.168.10.2
- [ ] Hostname is control-tower.blackbox.homes
- [ ] Docker is installed and working
- [ ] NFS mount to NAS is working
- [ ] AdGuard is running on ports 53, 80
- [ ] Home Assistant is accessible on port 8123
- [ ] Grafana is showing metrics
- [ ] Tailscale is connected and subnet route approved
- [ ] DNS resolution works from clients
- [ ] Ad blocking is working
- [ ] Remote access via Tailscale works

## Next Steps

Once the Pi is fully deployed:

1. **Update OPNsense DHCP** - Ensure clients get 192.168.10.2 as DNS
2. **Configure monitoring** - Add more exporters for Proxmox, NAS, etc.
3. **Deploy additional services** - Follow [04-services.md](04-services.md)
4. **Set up backups** - Ensure NAS backup job includes appdata

## Reference

- **Full bootstrap docs:** `docs/bootstrap/control-tower.md`
- **Bootstrap playbook:** `docs/playbooks/bootstrap_rpi.md`
- **Stack deployment:** `docs/playbooks/deploy_rpi_stack.md`
- **Tailscale setup:** `docs/playbooks/install_tailscale.md`
- **Architecture:** `docs/homelab.md`
- **Service status:** `docs/services-status.md`
