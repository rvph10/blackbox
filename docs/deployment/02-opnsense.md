# OPNsense Router Deployment

This guide covers creating and configuring the OPNsense VM on Proxmox. This VM acts as your router, firewall, and DHCP server - it's critical infrastructure that must start before anything else.

## Overview

OPNsense replaces your ISP's router and provides:
- PPPoE connection to Proximus ISP
- Routing between WAN and LAN
- DHCP server for the 192.168.10.0/24 network
- DNS forwarding to AdGuard on Raspberry Pi
- Firewall protection

**Important:** With this setup, if the GMKtec is down, the entire network loses internet. This is an accepted trade-off for having full control over routing.

## VM Creation

### Via Proxmox Web UI

1. **Navigate to:** pve > Create VM

2. **General Tab:**
   - VM ID: `100`
   - Name: `OPNsense-router`
   - Start at boot: **Yes** (critical!)
   - Start/Shutdown order: `100` (highest priority)
   - Startup delay: `60` seconds (ensures it's fully ready)

3. **OS Tab:**
   - ISO image: `OPNsense-25.7-amd64.iso` (upload to local storage first)
   - Guest OS Type: Other
   - Version: Default

4. **System Tab:**
   - Machine: q35
   - BIOS: **OVMF (UEFI)**
   - Add EFI Disk: Yes
   - EFI Storage: local-lvm
   - SCSI Controller: VirtIO SCSI single
   - Qemu Agent: No (not supported by default)

5. **Disks Tab:**
   - Bus/Device: SCSI
   - Storage: local-lvm
   - Disk size: `16 GB`
   - Cache: Default (write back)
   - Discard: Yes (for SSD trim)

6. **CPU Tab:**
   - Sockets: 1
   - Cores: `2`
   - Type: **host** (better performance)

7. **Memory Tab:**
   - Memory: `2048 MB` (2 GB)
   - Ballooning: Yes

8. **Network Tab:**
   - Bridge: `vmbr0` (LAN bridge)
   - Model: VirtIO (paravirtualized)
   - This creates net0 - the LAN interface

9. **Review and Create**
   - Don't start the VM yet
   - Click Finish

### Add WAN Interface

After creation, add the second network interface for WAN:

1. VM 100 > Hardware > Add > Network Device
2. **Bridge:** `vmbr1` (WAN bridge connected to physical WAN port)
3. **Model:** VirtIO
4. **Firewall:** No
5. Click "Add"

Now you should have:
- `net0` on `vmbr0` (LAN)
- `net1` on `vmbr1` (WAN)

### Disable Secure Boot

OPNsense doesn't support Secure Boot with UEFI:

1. Start the VM
2. Quickly press `ESC` during BIOS splash screen
3. Navigate: Device Manager > Secure Boot Configuration
4. **Uncheck** "Attempt Secure Boot"
5. Press F10 to save
6. ESC back to main menu
7. Select "Continue" to boot

## OPNsense Installation

1. **Boot from ISO**
   - VM will boot into OPNsense installer
   - Login: `installer` / `opnsense`

2. **Select Installation Type**
   - Choose "Install (ZFS)"
   - ZFS provides better data integrity for router config

3. **ZFS Configuration**
   - Pool type: stripe (single disk)
   - Select the 16GB virtual disk
   - Confirm installation

4. **Wait for Installation**
   - Takes a few minutes
   - Will reboot automatically when done

5. **Remove ISO**
   - Before VM reboots, go to VM 100 > Hardware > CD/DVD Drive
   - Edit > Do not use any media
   - This prevents booting from ISO again

## Initial Console Configuration

After first boot, you'll see the console menu:

### 1. Interface Assignment

The installer will ask to assign interfaces:

```
Do you want to set up VLANs now? [y/n] n

Enter the WAN interface name: vtnet1
Enter the LAN interface name: vtnet0

Do you want to proceed? [y/n] y
```

**Important mapping:**
- `vtnet0` = net0 = vmbr0 = LAN (192.168.10.0/24)
- `vtnet1` = net1 = vmbr1 = WAN (connects to ISP)

### 2. Configure LAN IP

From console menu, select option `2` (Set interface IP address):

```
Select interface: 2 (LAN)
Configure IPv4 via DHCP? [y/n] n
Enter IP address: 192.168.10.1
Enter subnet mask: 24
Configure IPv6 via DHCP6? [y/n] n
Enable DHCP server on LAN? [y/n] n  (we'll configure this in web UI)
Revert to HTTP as web protocol? [y/n] n  (keep HTTPS)
```

Now you can access the web UI at `https://192.168.10.1`

**Default credentials:**
- Username: `root`
- Password: `opnsense`

## Web UI Configuration

Connect a computer to the LAN (either via switch or directly) and access `https://192.168.10.1`. You'll get a certificate warning - accept it.

### Initial Setup Wizard

1. **Welcome Screen**
   - Click Next

2. **General Information**
   - Hostname: `router`
   - Domain: `blackbox.homes`
   - Primary DNS: `1.1.1.1` (temporary)
   - Secondary DNS: `1.1.1.1` (we'll change these later)
   - Click Next

3. **Time Server**
   - Timezone: Your timezone
   - NTP Server: `pool.ntp.org`
   - Click Next

4. **WAN Interface** (skip for now)
   - Type: DHCP (temporary)
   - Click Next
   - We'll configure PPPoE after the wizard

5. **LAN Interface**
   - Should show 192.168.10.1/24
   - Click Next

6. **Root Password**
   - Change from default 'opnsense'
   - Use a strong password
   - Click Next

7. **Reload**
   - Click "Reload" to apply settings
   - Login again with new root password

### Configure WAN (PPPoE)

After wizard completion:

1. **Interfaces > WAN**
2. **IPv4 Configuration Type:** PPPoE
3. **PPPoE Configuration:**
   - Username: `your_id@PROXIMUS` (your Proximus login)
   - Password: Your Proximus password
   - Service Name: (leave empty)
   - Dial on demand: Unchecked (always on)
   - Idle timeout: 0
4. Click "Save"
5. Click "Apply Changes"

**Physical connection:** Ensure the physical WAN port on GMKtec (nic1) is connected to **Port 1** of your Proximus modem.

### Configure DHCP Server

We're using ISC DHCPv4 instead of Dnsmasq for better control over DNS settings.

#### 1. Disable Dnsmasq DHCP

1. **Services > Dnsmasq DNS > Settings**
2. **Uncheck:** "Enable DHCP"
3. **Keep checked:** "Enable Dnsmasq" (still needed for local DNS)
4. Click "Save"

#### 2. Enable ISC DHCP

1. **Services > ISC DHCPv4 > [LAN]**
2. **Enable:** Check this box
3. **Range:**
   - From: `192.168.10.100`
   - To: `192.168.10.200`
4. **DNS servers:** `192.168.10.2` (AdGuard on Pi - must deploy Pi first!)
5. **Secondary DNS servers:** `1.1.1.1` (fallback)
6. **Gateway:** `192.168.10.1` (OPNsense itself)
7. **Domain name:** `blackbox.homes`
8. Click "Save"
9. Click "Apply Changes"

**Note:** The Raspberry Pi must be deployed and running AdGuard before clients will get proper DNS. Until then, clients will use the fallback 1.1.1.1.

### Configure DNS Forwarding

Make OPNsense forward DNS queries to AdGuard:

1. **System > Settings > General**
2. **DNS Servers:**
   - Primary: `192.168.10.2` (AdGuard)
   - Secondary: `1.1.1.1` (fallback)
3. **Allow DNS server list to be overridden by DHCP/PPP on WAN:** Uncheck
4. Click "Save"

## Autostart Configuration

Critical: OPNsense must start before other VMs to provide routing.

### Via CLI

```bash
ssh root@192.168.10.10
qm set 100 --onboot 1 --startup order=100,up=60
```

### Via Web UI

1. VM 100 > Options > Start at boot
2. Double-click to edit
3. **Start at boot:** Yes
4. **Startup order:** 100 (highest)
5. **Startup delay:** 60 seconds
6. Click "OK"

This ensures:
- OPNsense starts automatically when Proxmox boots
- It gets priority over other VMs
- Other VMs wait 60s for network to be ready

## Verification

### 1. Check WAN Connection

1. **Interfaces > Overview**
2. WAN interface should show:
   - Status: up
   - IP address from ISP (via PPPoE)
   - Gateway reachable

### 2. Test Internet from OPNsense

1. **Interfaces > Diagnostics > Ping**
2. Hostname: `1.1.1.1` or `google.com`
3. Should get replies

### 3. Test DHCP

Connect a client device to LAN:

```bash
# Release and renew DHCP
sudo dhclient -r
sudo dhclient

# Check IP
ip addr show
# Should get IP in range 192.168.10.100-200

# Check DNS
cat /etc/resolv.conf
# Should show 192.168.10.2 (once Pi is deployed)
```

### 4. Test Routing from Client

Once client has DHCP lease:

```bash
# Test gateway
ping 192.168.10.1

# Test internet (if DNS working)
ping google.com

# Test with IP (if DNS not ready yet)
ping 1.1.1.1
```

### 5. Check Firewall Logs

1. **Firewall > Log Files > Live View**
2. Should see traffic passing through
3. Watch for blocked traffic (troubleshooting)

### 6. Verify Autostart

```bash
ssh root@192.168.10.10
qm config 100 | grep -E "onboot|startup"

# Should show:
# onboot: 1
# startup: order=100,up=60
```

## Common Issues

### No Internet Connection

**Symptom:** OPNsense can't connect via PPPoE

**Checks:**
1. Physical cable connected to Port 1 of modem?
2. Correct Proximus credentials?
3. Check Interfaces > Overview - is WAN up?
4. Check System > Log Files > General for PPPoE errors

**Fix:**
- Double-check username format: `your_id@PROXIMUS`
- Verify password (no special characters causing issues)
- Try disconnecting/reconnecting WAN in web UI

### DHCP Not Working

**Symptom:** Clients don't get IP addresses

**Checks:**
1. ISC DHCP enabled? (Services > ISC DHCPv4)
2. Dnsmasq DHCP disabled? (Services > Dnsmasq DNS)
3. Clients on correct network/VLAN?
4. Check Services > ISC DHCPv4 > Leases for active leases

**Fix:**
```bash
# Restart DHCP service via CLI
ssh root@192.168.10.1
service isc-dhcpd restart
```

### Secure Boot Error

**Symptom:** VM won't boot, stuck at UEFI screen

**Fix:**
1. Reset VM
2. Press ESC immediately
3. Device Manager > Secure Boot Configuration
4. Uncheck "Attempt Secure Boot"
5. Save and continue

### DNS Not Resolving

**Symptom:** Can ping IPs but not hostnames

**Temporary Fix (until Pi deployed):**
```bash
# On OPNsense
# System > Settings > General
# Set DNS servers to:
# - 1.1.1.1
# - 9.9.9.9

# On clients, manually set DNS:
echo "nameserver 1.1.1.1" | sudo tee /etc/resolv.conf
```

**Permanent Fix:**
- Deploy Raspberry Pi with AdGuard
- DNS will automatically work once AdGuard is running

### Can't Access Web UI

**Symptom:** https://192.168.10.1 not loading

**Checks:**
1. Connected to LAN network?
2. Client has IP in 192.168.10.0/24?
3. Try from OPNsense console: option 11 (Ping host)
4. Firewall blocking? Check rules

**Fix:**
- Reset firewall rules to defaults: System > Settings > Administration > Reset to defaults
- Try HTTP instead: System > Settings > Administration > Enable HTTP redirect

## Advanced Configuration

### Static DHCP Leases

For servers that need consistent IPs:

1. **Services > ISC DHCPv4 > [LAN]**
2. Scroll to "Static DHCP"
3. Click "+" to add
4. **MAC Address:** Device's MAC
5. **IP Address:** Desired static IP
6. **Description:** Device name
7. Save and apply

Already configured:
- Pi: 192.168.10.2
- NAS: 192.168.10.5
- Proxmox: 192.168.10.10 (configured directly on host)

### Firewall Rules

Default LAN rules allow all outbound traffic. To restrict:

1. **Firewall > Rules > LAN**
2. Add rules as needed
3. Remember: rules process top-to-bottom
4. Default deny at bottom

### Local DNS Records

To resolve local hostnames:

1. **Services > Dnsmasq DNS > Settings**
2. Scroll to "Host Overrides"
3. Add entries:
   - `router.blackbox.homes` → `192.168.10.1`
   - `pve.blackbox.homes` → `192.168.10.10`
   - `control-tower.blackbox.homes` → `192.168.10.2`
4. Save and apply

Or add these in AdGuard once it's deployed.

## Backup Configuration

Always backup OPNsense config after changes:

1. **System > Configuration > Backups**
2. Click "Download configuration"
3. Save to secure location (NAS backups folder)
4. Store in git repository for version control

Restore via: System > Configuration > Backups > Restore configuration

## Next Steps

Once OPNsense is fully operational:

1. **Deploy Raspberry Pi** - Follow [03-raspberry-pi.md](03-raspberry-pi.md)
2. **Update DHCP DNS** - After AdGuard is running, verify clients get 192.168.10.2 as DNS
3. **Configure Tailscale** - For remote access to OPNsense web UI
4. **Set up monitoring** - Add OPNsense to Prometheus/Grafana

## Reference

- **Full bootstrap docs:** `docs/bootstrap/opnsense.md`
- **Architecture:** `docs/homelab.md`
- **OPNsense documentation:** https://docs.opnsense.org/
- **PPPoE Proximus guide:** https://forum.opnsense.org/index.php?topic=xxxxx
