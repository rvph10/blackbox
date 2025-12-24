# Deployment Guide

This is your complete deployment guide for rebuilding the homelab from scratch. Follow these guides in order to get everything up and running.

## Prerequisites

Before starting any deployment:

1. **Hardware Ready**
   - GMKtec NucBox M6 (Proxmox host)
   - Raspberry Pi 5 with NVMe boot drive
   - Ugreen DXP2800 NAS (Cargo)
   - Managed switch (optional but recommended)
   - USB drives with installation media

2. **Installation Media**
   - Proxmox VE 9.1 ISO (on Ventoy USB)
   - Raspberry Pi OS Lite 64-bit
   - OPNsense 25.7 ISO

3. **Ansible Control Machine**
   - Laptop/desktop with Ansible installed
   - This repository cloned
   - Vault password configured in `.vault_pass`

4. **Network Planning**
   - LAN subnet: `192.168.10.0/24`
   - Gateway (OPNsense): `192.168.10.1`
   - DNS (AdGuard on Pi): `192.168.10.2`
   - Proxmox: `192.168.10.10`
   - NAS: `192.168.10.5`

## Deployment Order

Follow these guides in sequence. Each step depends on the previous ones.

### 1. Proxmox VE Installation
**Guide:** [01-proxmox.md](01-proxmox.md)

Install and configure the Proxmox hypervisor on the GMKtec NucBox. This is your foundation - everything else runs on or connects through this server.

**Time investment:** Plan for a couple hours including updates and reboots.

**Key outcomes:**
- Proxmox VE 9.1 running on 192.168.10.10
- IOMMU enabled for GPU passthrough
- SSH hardened (key-only access)
- Network bridges configured

### 2. OPNsense Router
**Guide:** [02-opnsense.md](02-opnsense.md)

Create and configure the OPNsense VM to handle routing, DHCP, and firewall duties. This VM must start before everything else.

**Key outcomes:**
- VM 100 running OPNsense
- PPPoE connection to ISP working
- DHCP serving 192.168.10.100-200
- DNS forwarding to Pi configured

### 3. Raspberry Pi Control Tower
**Guide:** [03-raspberry-pi.md](03-raspberry-pi.md)

Set up the Raspberry Pi as your critical services platform. This runs AdGuard (DNS), Home Assistant, and monitoring stack.

**Key outcomes:**
- Static IP 192.168.10.2 configured
- Docker installed and running
- NFS mount to NAS working
- AdGuard, Home Assistant, and monitoring stack deployed
- Tailscale VPN configured for remote access

### 4. Service Deployment
**Guide:** [04-services.md](04-services.md)

Deploy additional VMs and LXCs on Proxmox for media, downloads, infrastructure, and productivity services.

**Key outcomes:**
- VM/LXC templates ready
- Service-specific playbooks executed
- All services accessible and monitored

## Quick Reference

### Important IPs

| Device | IP | Access |
|--------|-----|--------|
| OPNsense | 192.168.10.1 | https://192.168.10.1 |
| Raspberry Pi | 192.168.10.2 | ssh admin@192.168.10.2 |
| AdGuard Home | 192.168.10.2 | http://192.168.10.2 |
| Home Assistant | 192.168.10.2 | http://192.168.10.2:8123 |
| Grafana | 192.168.10.2 | http://192.168.10.2:3100 |
| Proxmox | 192.168.10.10 | https://192.168.10.10:8006 |
| NAS (Cargo) | 192.168.10.5 | http://192.168.10.5 |

### Common Commands

```bash
# Run Proxmox bootstrap
cd /home/rvph/Projects/blackbox/ansible
ansible-playbook playbooks/bootstrap_pve.yml

# Run Raspberry Pi bootstrap
ansible-playbook playbooks/bootstrap_rpi.yml

# Deploy Pi Docker stack
ansible-playbook playbooks/deploy_rpi_stack.yml

# Install Tailscale
ansible-playbook playbooks/install_tailscale.yml

# Check all hosts
ansible all -m ping
```

### Ansible Vault

All sensitive data is stored in the encrypted vault file:

```bash
# Edit vault
ansible-vault edit ansible/inventory/group_vars/all/vault.yml

# View vault
ansible-vault view ansible/inventory/group_vars/all/vault.yml
```

The vault password should be in `.vault_pass` for automatic decryption.

## Disaster Recovery

If you need to rebuild everything from scratch (the "nuke and pave" scenario):

1. Follow guides 1-4 in order
2. Your data is safe on the NAS - services will reconnect to it
3. Proxmox VM backups are on `cargo:/proxmox-backups`
4. Off-site backups are on Backblaze B2

The entire homelab can be rebuilt in an afternoon thanks to Ansible automation. The only manual steps are OS installations and initial BIOS/network configs.

## Getting Help

- **Architecture overview:** `docs/homelab.md`
- **Service status tracking:** `docs/services-status.md`
- **Playbook details:** `docs/playbooks/`
- **Bootstrap guides:** `docs/bootstrap/`

## Post-Deployment

After completing all deployments:

1. Test DNS resolution from a client
2. Verify Tailscale subnet routing works
3. Test service access via Tailscale from external network
4. Verify NAS backup jobs are running
5. Check monitoring dashboards in Grafana
6. Document any custom configurations you add

Remember: this is personal infrastructure. Take notes, customize to your needs, and don't be afraid to experiment. Everything can be rebuilt.
