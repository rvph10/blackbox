# Playbooks Reference

Quick index of all Ansible playbooks. For detailed docs, see `/docs/playbooks/`.

## Bootstrap (Initial Setup)

### bootstrap_pve.yml
**What**: Configure Proxmox VE fresh install
**When**: After installing Proxmox on GMKtec NucBox M6
**Does**:
- SSH hardening (key-only, no root password)
- Configure repositories (disable enterprise, enable no-subscription)
- Enable IOMMU for GPU passthrough
- System updates

```bash
ansible-playbook playbooks/bootstrap_pve.yml
# Then reboot for IOMMU activation
```

Docs: `/docs/playbooks/bootstrap_pve.md`

---

### bootstrap_rpi.yml
**What**: Initial setup of Raspberry Pi 5
**When**: After fresh Raspberry Pi OS install
**Does**:
- Set static IP and hostname
- Install Docker
- Configure NFS mount from NAS
- Systemd auto-mount service

```bash
ansible-playbook playbooks/bootstrap_rpi.yml
# Then reboot to apply network changes
```

Docs: `/docs/playbooks/bootstrap_rpi.md`

---

## Deployment (Services)

### deploy_rpi_stack.yml
**What**: Deploy core Docker services on Raspberry Pi
**When**: After bootstrap_rpi.yml
**Does**:
- Deploy AdGuard Home (DNS)
- Deploy Home Assistant (home automation)
- Deploy Homepage (dashboard)
- Stop systemd-resolved (port 53 conflict)

```bash
ansible-playbook playbooks/deploy_rpi_stack.yml
```

Docs: `/docs/playbooks/deploy_rpi_stack.md`

---

### deploy_observability_stack.yml
**What**: Deploy Grafana/Prometheus/Loki monitoring stack
**When**: After deploy_rpi_stack.yml
**Does**:
- Add Grafana, Prometheus, Loki, Promtail to docker-compose
- Configure data retention and storage
- Set up log aggregation

```bash
ansible-playbook playbooks/deploy_observability_stack.yml
```

Status: Deployed (see services-status.md)

---

### deploy_kiosk.yml
**What**: Deploy touchscreen dashboard on Raspberry Pi
**When**: If you have the 3.5" touchscreen installed
**Does**:
- Install Python dependencies
- Configure kernel modules (fb_ili9486, ads7846)
- Deploy custom Python dashboard app
- Configure systemd service for auto-start

```bash
ansible-playbook playbooks/deploy_kiosk.yml
```

Docs: `/docs/playbooks/deploy_kiosk.md`

---

### deploy_nas_backup.yml
**What**: Configure automated backups to Backblaze B2
**When**: After NAS is accessible via NFS
**Does**:
- Install and configure Rclone
- Create backup script (sync to B2 cloud)
- Schedule daily cron job (03:00 AM)
- Generate JSON status file for monitoring

```bash
ansible-playbook playbooks/deploy_nas_backup.yml
```

Implements 3-2-1 backup strategy. Backs up appdata and configs to off-site cloud storage.

Docs: `/docs/playbooks/deploy_nas_backup.md`

---

### deploy_nas_leds.yml
**What**: Automated LED control for UGREEN NAS
**When**: If you want to schedule LED on/off times
**Does**:
- Clone ugreen_leds_controller from GitHub
- Compile LED control binary
- Create cron jobs (off at 23:00, on at 09:00)
- Load i2c-dev kernel module

```bash
ansible-playbook playbooks/deploy_nas_leds.yml
```

Docs: `/docs/playbooks/deploy_nas_leds.md`

---

## Infrastructure

### install_tailscale.yml
**What**: Install Tailscale VPN in subnet router mode
**When**: After bootstrap_rpi.yml for remote access
**Does**:
- Install Tailscale from official repo
- Enable IP forwarding
- Advertise 192.168.10.0/24 subnet
- Auto-connect with auth key

```bash
ansible-playbook playbooks/install_tailscale.yml
# Then approve subnet route in Tailscale admin console
```

Enables secure remote access to entire homelab without port forwarding.

Docs: `/docs/playbooks/install_tailscale.md`

---

### install_node_exporter.yml
**What**: Deploy Prometheus Node Exporter for metrics
**When**: After deploy_observability_stack.yml
**Does**:
- Install node_exporter on all hosts
- Expose system metrics (CPU, RAM, disk, network)
- Configure Prometheus scraping

```bash
ansible-playbook playbooks/install_node_exporter.yml
```

Deploy on: Raspberry Pi, Proxmox, NAS Cargo

---

## Deprecated

### setup_screen.yml
**Status**: DEPRECATED
**Replaced by**: deploy_kiosk.yml

Legacy playbook for basic screen setup. Use deploy_kiosk.yml instead for full dashboard deployment.

---

## Quick Start Sequences

### New Raspberry Pi Setup
```bash
# 1. Bootstrap
ansible-playbook playbooks/bootstrap_rpi.yml
ssh control-tower.blackbox.homes reboot

# 2. Deploy core services
ansible-playbook playbooks/deploy_rpi_stack.yml

# 3. Add monitoring
ansible-playbook playbooks/deploy_observability_stack.yml
ansible-playbook playbooks/install_node_exporter.yml

# 4. Optional: Tailscale for remote access
ansible-playbook playbooks/install_tailscale.yml

# 5. Optional: Touchscreen dashboard
ansible-playbook playbooks/deploy_kiosk.yml
```

### New Proxmox Setup
```bash
# 1. Bootstrap
ansible-playbook playbooks/bootstrap_pve.yml
ssh pve.blackbox.homes reboot

# 2. Install monitoring agent
ansible-playbook playbooks/install_node_exporter.yml
```

### NAS Setup
```bash
# 1. Configure backups
ansible-playbook playbooks/deploy_nas_backup.yml

# 2. Optional: LED scheduling
ansible-playbook playbooks/deploy_nas_leds.yml

# 3. Install monitoring agent
ansible-playbook playbooks/install_node_exporter.yml
```

---

## Tips

**Dry run**: Add `--check` to preview changes without applying
```bash
ansible-playbook playbooks/deploy_rpi_stack.yml --check
```

**Target specific host**: Use `--limit`
```bash
ansible-playbook playbooks/install_node_exporter.yml --limit rpi
```

**Vault password**: Playbooks use encrypted vault for secrets
```bash
# Edit vault
ansible-vault edit inventory/group_vars/all/vault.yml
```

---

See also:
- Deployment status: `/docs/reference/status.md`
- Detailed playbook docs: `/docs/playbooks/`
- Architecture: `/docs/homelab.md`
