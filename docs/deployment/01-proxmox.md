# Proxmox VE Deployment

This guide covers installing and configuring Proxmox VE 9.1 on the GMKtec NucBox M6. This is your hypervisor foundation - everything else runs on top of it.

## Hardware Setup

**Device:** GMKtec NucBox M6

**Specs:**

- AMD Ryzen 5 7640HS (6C/12T @ 5.0 GHz)
- 32 GB DDR5 RAM
- 1 TB NVMe SSD
- Dual 2.5G NICs (Realtek)
- AMD Radeon 760M iGPU

**Network connections:**

- `nic0` (enp1s0): LAN - connects to switch
- `nic1` (enp...): WAN - connects directly to ISP modem

## BIOS Configuration

Boot into BIOS/UEFI and configure these settings before OS installation:

**Virtualization:**

- SVM Mode (AMD-V): **Enabled**
- IOMMU: **Enabled**

**Security:**

- Secure Boot: **Disabled** (Proxmox won't boot with this enabled)

Save and reboot with your Ventoy USB drive inserted.

## OS Installation

1. **Boot from USB**

   - Select Proxmox VE 9.1 ISO from Ventoy menu
   - Choose the graphical installer

2. **Disk Selection**

   - Select the 1TB NVMe drive
   - Filesystem: ext4 (default) or ZFS if you want snapshots
   - Use entire disk

3. **Location and Time Zone**

   - Set your country and timezone
   - This affects update mirrors and system time

4. **Root Password**

   - Set a temporary password (you'll disable password auth later)
   - Note: you'll be using SSH keys after bootstrap

5. **Management Network**

   - Interface: Select `nic0` (enp1s0)
   - Hostname: `pve.blackbox.homes`
   - IP Address: `192.168.10.10/24`
   - Gateway: `192.168.10.1` (this will be OPNsense later)
   - DNS Server: `1.1.1.1` (temporary - will use AdGuard after Pi deployment)

6. **Confirm and Install**
   - Review settings
   - Click install and wait (takes 5-10 minutes)
   - Reboot when prompted

After reboot, you should be able to access the web UI at `https://192.168.10.10:8006` (you'll get a certificate warning - that's normal).

## Post-Install Configuration

You can do these manually via SSH or let the Ansible playbook handle them. The playbook is recommended for consistency.

### Manual Configuration (Optional)

If you want to configure manually instead of using Ansible:

#### 1. Repository Configuration

```bash
# SSH to Proxmox
ssh root@192.168.10.10

# Disable enterprise repo (requires paid subscription)
sed -i "s/^deb/#deb/g" /etc/apt/sources.list.d/pve-enterprise.list

# Add no-subscription repo (Debian 13 Trixie for PVE 9.1)
echo "deb http://download.proxmox.com/debian/pve trixie pve-no-subscription" > /etc/apt/sources.list.d/pve-no-subscription.list

# Update package lists
apt update
apt full-upgrade -y
```

#### 2. IOMMU Activation

For GPU passthrough capability:

```bash
# Edit GRUB config
nano /etc/default/grub

# Find GRUB_CMDLINE_LINUX_DEFAULT and modify it:
GRUB_CMDLINE_LINUX_DEFAULT="quiet amd_iommu=on iommu=pt"

# Update GRUB
update-grub

# Add VFIO modules
cat >> /etc/modules <<EOF
vfio
vfio_iommu_type1
vfio_pci
vfio_virqfd
EOF

# Rebuild initramfs
update-initramfs -u -k all

# Reboot to apply
reboot
```

#### 3. Network Bridge for WAN

Create a second bridge for the WAN interface (used by OPNsense):

1. Web UI: Datacenter > pve > System > Network
2. Click "Create" > "Linux Bridge"
3. Name: `vmbr1`
4. Bridge ports: `nic1` (your second physical NIC)
5. Comment: `WAN-Physical`
6. **Do not assign an IP address**
7. Click "Create"
8. Click "Apply Configuration"

### Automated Configuration (Recommended)

Use the Ansible playbook to handle all post-install configuration:

```bash
# On your control machine (laptop)
cd /home/rvph/Projects/blackbox/ansible

# First, ensure you can SSH with password temporarily
# You'll need to allow password auth just for the bootstrap
ssh root@192.168.10.10

# Run the bootstrap playbook
ansible-playbook playbooks/bootstrap_pve.yml

# After completion, reboot Proxmox
ssh root@192.168.10.10 reboot
```

**What the playbook does:**

- Configures SSH hardening (key-only access, no passwords)
- Installs your SSH public key from vault
- Configures repositories (disables enterprise, enables no-subscription)
- Enables IOMMU for GPU passthrough
- Adds VFIO kernel modules
- Updates all packages

## Verification

After configuration (manual or automated) and reboot:

### 1. Check SSH Access

```bash
# Should work with your SSH key
ssh root@192.168.10.10

# Should fail (password auth disabled)
ssh -o PreferredAuthentications=password root@192.168.10.10
```

### 2. Verify Repository Configuration

```bash
ssh root@192.168.10.10
apt update

# Should NOT see any "401 Unauthorized" errors
# Should see pve-no-subscription repository listed
```

### 3. Verify IOMMU

```bash
ssh root@192.168.10.10
dmesg | grep -i iommu

# Should see something like:
# AMD-Vi: AMD IOMMUv2 loaded and initialized
```

### 4. Check VFIO Modules

```bash
lsmod | grep vfio

# Should see:
# vfio_pci
# vfio_iommu_type1
# vfio
```

### 5. Verify Network Bridges

```bash
ip link show

# Should see both:
# vmbr0: connected to nic0 (LAN)
# vmbr1: connected to nic1 (WAN)
```

Or check in web UI: Datacenter > pve > System > Network - you should see both bridges.

### 6. List IOMMU Groups

Check if GPU is properly isolated for passthrough:

```bash
find /sys/kernel/iommu_groups/ -type l | sort

# Look for your AMD GPU in the list
lspci | grep -i vga
# Should show: AMD Radeon 760M
```

## Storage Configuration

Configure NFS storage from the NAS for VM backups:

### Via Web UI

1. Datacenter > Storage > Add > NFS
2. **ID:** `nas-backups`
3. **Server:** `192.168.10.5`
4. **Export:** `/volume1/proxmox-backups`
5. **Content:** VZDump backup file, Disk image
6. Click "Add"

### Via CLI

```bash
pvesm add nfs nas-backups \
  --server 192.168.10.5 \
  --export /volume1/proxmox-backups \
  --content backup,images
```

Verify:

```bash
pvesm status
# Should show nas-backups as available
```

## Common Issues

### Enterprise Repository Errors

**Symptom:** `apt update` shows "401 Unauthorized" for pve-enterprise

**Fix:**

```bash
# Ensure enterprise repo is disabled
cat /etc/apt/sources.list.d/pve-enterprise.list
# All lines should be commented with #

# If not:
sed -i "s/^deb/#deb/g" /etc/apt/sources.list.d/pve-enterprise.list
apt update
```

### IOMMU Not Active

**Symptom:** `dmesg | grep -i iommu` shows nothing

**Fix:**

1. Check BIOS - ensure SVM and IOMMU are enabled
2. Verify GRUB config has `amd_iommu=on`
3. Rebuild GRUB and reboot:

```bash
update-grub
reboot
```

### Cannot Access Web UI

**Symptom:** Can't reach https://192.168.10.10:8006

**Fix:**

- Check network cable is connected to `nic0`
- Verify IP with `ip addr show`
- Check firewall: `iptables -L` (Proxmox allows 8006 by default)
- Try from a different machine on same network

### SSH Key Not Working

**Symptom:** SSH key auth fails after bootstrap

**Fix:**

```bash
# Check authorized_keys file
ssh root@192.168.10.10  # using password temporarily
cat ~/.ssh/authorized_keys

# Ensure it matches your public key
# Check permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

## Next Steps

Once Proxmox is fully configured and verified:

1. **Create OPNsense VM** - Follow [02-opnsense.md](02-opnsense.md)
2. **Configure VM autostart** - OPNsense needs to start before other VMs
3. **Set up backup schedule** - Configure VZDump to backup VMs to NAS

## Additional Configuration

### GPU Passthrough Setup

Once you create VMs that need GPU access (like Jellyfin for transcoding):

1. VM > Hardware > Add > PCI Device
2. Select: `0000:xx:00.0` (AMD Radeon 760M)
3. **All Functions:** Yes
4. **Primary GPU:** No (unless headless)
5. **PCI-Express:** Yes
6. **ROM-Bar:** Yes

### Backup Schedule

Configure automatic VM backups:

1. Datacenter > Backup > Add
2. **Storage:** nas-backups
3. **Schedule:** `0 */5 * * *` (every 5 hours)
4. **Selection mode:** All
5. **Retention:** Keep last 5
6. **Compression:** ZSTD
7. **Mode:** Snapshot

### Update Procedure

Keep Proxmox updated regularly:

```bash
ssh root@192.168.10.10
apt update
apt full-upgrade -y
apt autoremove -y

# Reboot if kernel was updated
reboot
```

Or via web UI: pve > Updates > Refresh > Upgrade

## Reference

- **Full bootstrap docs:** `docs/bootstrap/proxmox.md`
- **Playbook details:** `docs/playbooks/bootstrap_pve.md`
- **Architecture:** `docs/homelab.md`
- **Proxmox documentation:** https://pve.proxmox.com/pve-docs/
- **GPU passthrough guide:** https://pve.proxmox.com/wiki/Pci_passthrough
