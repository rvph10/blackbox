# Backup & Restore Guide

This guide covers the complete backup strategy for the homelab, from understanding the 3-2-1 principle to performing actual disaster recovery.

## The 3-2-1 Backup Strategy

The homelab follows the industry-standard 3-2-1 rule:

- **3 copies** of your data: Live data, local backup, off-site backup
- **2 different storage media**: RAID 1 (physical mirror) and Btrfs snapshots (logical)
- **1 copy off-site**: Daily sync to Backblaze B2 cloud storage

This means even if your house burns down (worst case), your data survives in the cloud.

## What Gets Backed Up

### Live Data Locations

All critical data lives on the NAS (Cargo - 192.168.10.5):

| Path | Content | Size | Backed Up To |
|------|---------|------|--------------|
| `/volume1/appdata` | Docker volumes (AdGuard, Home Assistant, Grafana, etc.) | ~50-100 GB | B2 + Btrfs snapshots |
| `/volume1/media` | Movies, TV shows, downloads | ~500 GB - 2 TB | B2 (if configured) |
| `/volume1/photos` | Immich photo library | ~100-500 GB | B2 + Btrfs snapshots |
| `/volume1/backups-configs` | Ansible vault, OPNsense configs, manual exports | ~1-5 GB | B2 + Btrfs snapshots |
| `/volume1/proxmox-backups` | VM/LXC backups (.vma files) | ~20-50 GB | Local only (regenerable) |

### What's NOT Backed Up

- Proxmox OS itself (reinstallable)
- Raspberry Pi OS (Ansible redeploys everything)
- OPNsense VM (config backed up, VM is regenerable)
- Docker images (re-pullable from registries)
- NAS OS/firmware (reinstallable)

## Backup Methods Explained

### 1. RAID 1 Mirror (Real-time Protection)

**What it does**: The NAS has 2x 4TB drives in RAID 1, meaning everything is written to both disks simultaneously.

**Protects against**: Single disk failure

**Does NOT protect against**: Accidental deletion, ransomware, corruption, NAS failure, theft, fire

**How to check status**:
```bash
# SSH to NAS (192.168.10.5)
cat /proc/mdstat
# Should show: md0 : active raid1 sda1[0] sdb1[1]
```

### 2. Btrfs Snapshots (Point-in-Time Recovery)

**What it does**: Creates instant, space-efficient snapshots of your filesystem daily at 04:00 AM.

**Protects against**: Accidental deletion, file corruption, "oops I overwrote that config"

**Does NOT protect against**: Hardware failure, theft, fire

**Retention policy** (configured in UGOS web UI):
- 7 daily snapshots
- 4 weekly snapshots
- 3 monthly snapshots

**How to restore from snapshot**:

Via UGOS Web UI (easiest):
1. Login to http://192.168.10.5
2. Navigate to Storage > Snapshots
3. Find the snapshot from before your mistake
4. Browse files or restore entire folder
5. Click "Restore" and select destination

Via SSH (for nerds):
```bash
# SSH to cargo@192.168.10.5

# List available snapshots
ls -la /.snapshots/

# View files from specific snapshot
ls -la /.snapshots/@GMT-2025.12.24-04.00.00/volume1/appdata/

# Copy specific file back
cp /.snapshots/@GMT-2025.12.24-04.00.00/volume1/appdata/adguard/AdGuardHome.yaml \
   /volume1/appdata/adguard/AdGuardHome.yaml.restored

# Restart the affected service
cd /volume1/appdata
docker-compose restart adguard
```

### 3. Rclone to Backblaze B2 (Off-site Cloud Backup)

**What it does**: Every night at 03:00 AM, rclone syncs your data to Backblaze B2 cloud storage.

**Protects against**: Everything - house fire, theft, total NAS failure, natural disaster

**Does NOT protect against**: Accidentally deleting files and waiting 24h (snapshot is faster)

**What gets synced**:
- `/volume1/appdata` → `b2://your-bucket/appdata`
- `/volume1/backups-configs` → `b2://your-bucket/backups-configs`
- Optional: `/volume1/media`, `/volume1/photos` (if you have the B2 space)

**Configuration file**: Deployed by Ansible playbook `deploy_nas_backup.yml`

**How to check backup status**:

```bash
# SSH to cargo@192.168.10.5

# Check last backup log
tail -50 /volume1/appdata/rclone/backup.log

# Check backup status JSON (used by Homepage dashboard)
cat /volume1/appdata/rclone/backup_status.json

# Manually trigger backup (test run)
/volume1/appdata/rclone/backup_to_b2.sh
```

**How to view what's in B2**:

```bash
# SSH to NAS
docker run --rm -v /volume1/appdata/rclone/config:/config/rclone \
  rclone/rclone lsd b2_remote:your-bucket-name

# List files in appdata folder
docker run --rm -v /volume1/appdata/rclone/config:/config/rclone \
  rclone/rclone ls b2_remote:your-bucket-name/appdata | head -20

# Check total size
docker run --rm -v /volume1/appdata/rclone/config:/config/rclone \
  rclone/rclone size b2_remote:your-bucket-name
```

### 4. Proxmox VM Backups (VZDump)

**What it does**: Proxmox creates complete VM/LXC backups every 5 hours, storing them on the NAS.

**Schedule**: Every 5 hours, keeps last 5 backups (25h retention)

**Storage location**: NAS `/volume1/proxmox-backups/dump/`

**File format**: `.vma.zst` (compressed VM archives)

**How to check backups**:

Via Proxmox Web UI:
1. Login to https://192.168.10.10:8006
2. Navigate to Datacenter > Backup
3. View backup jobs and history

Via SSH:
```bash
# SSH to root@192.168.10.10

# List recent backups
ls -lh /mnt/pve/cargo-proxmox-backups/dump/

# Check backup logs
cat /var/log/pve/tasks/active
```

**What gets backed up**:
- VM 100 (OPNsense) - Full VM backup
- VM 110, 120 (when deployed) - Full VM backups
- LXC 200, 210 (when deployed) - Container backups

## How to Restore From Each Backup Type

### Scenario 1: "Oops, I Deleted a File" (Use Btrfs Snapshot)

**Time to restore**: 2-5 minutes

**Steps**:
1. SSH to NAS: `ssh cargo@192.168.10.5`
2. Find the snapshot from before you screwed up:
   ```bash
   ls -la /.snapshots/
   # Look for @GMT-YYYY.MM.DD-04.00.00 format
   ```
3. Verify the file exists:
   ```bash
   ls -la /.snapshots/@GMT-2025.12.23-04.00.00/volume1/appdata/adguard/
   ```
4. Copy it back:
   ```bash
   cp /.snapshots/@GMT-2025.12.23-04.00.00/volume1/appdata/adguard/AdGuardHome.yaml \
      /volume1/appdata/adguard/
   ```
5. Restart the service:
   ```bash
   # On Raspberry Pi (if AdGuard runs there)
   ssh pi@192.168.10.2
   cd /opt/docker
   docker-compose restart adguard
   ```

### Scenario 2: "My Raspberry Pi Died" (Fast Recovery)

**Time to restore**: 30-60 minutes (mostly OS install time)

**Data location**: Safe on NAS `/volume1/appdata`

**Steps**:
1. Install fresh Raspberry Pi OS on new SD/NVMe
2. Basic setup:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install git ansible -y
   ```
3. Clone the blackbox repo:
   ```bash
   cd ~
   git clone <your-repo-url> blackbox
   cd blackbox/ansible
   ```
4. Set up vault password:
   ```bash
   echo "YOUR_VAULT_PASSWORD" > .vault_pass
   chmod 600 .vault_pass
   ```
5. Run the bootstrap playbook:
   ```bash
   ansible-playbook -i inventory/hosts.ini playbooks/bootstrap_rpi.yml
   ```
6. Deploy the full stack:
   ```bash
   ansible-playbook -i inventory/hosts.ini playbooks/deploy_rpi_stack.yml
   ```

The playbook will:
- Mount NFS share from NAS
- Pull Docker images
- Start all containers using existing data
- AdGuard, Home Assistant, etc. come back exactly as they were

### Scenario 3: "My NAS Died But I Have a New One" (Disaster Recovery)

**Time to restore**: 2-6 hours (depends on data size and internet speed)

**Prerequisites**:
- New NAS installed and accessible
- Backblaze B2 bucket still exists
- Vault password to decrypt rclone config

**Steps**:

1. **Set up new NAS hardware**:
   - Install drives in RAID 1
   - Configure network (IP: 192.168.10.5)
   - Create shared folders: `appdata`, `backups-configs`, `proxmox-backups`, `media`, `photos`
   - Enable SSH access

2. **Deploy rclone configuration**:
   ```bash
   # From your workstation
   cd ~/blackbox/ansible
   ansible-playbook -i inventory/hosts.ini playbooks/deploy_nas_backup.yml
   ```

3. **Restore from Backblaze B2**:
   ```bash
   # SSH to new NAS
   ssh cargo@192.168.10.5

   # List available backups
   docker run --rm -v /volume1/appdata/rclone/config:/config/rclone \
     rclone/rclone lsd b2_remote:your-bucket-name

   # Restore appdata (Docker volumes)
   docker run --rm \
     -v /volume1/appdata/rclone/config:/config/rclone \
     -v /volume1/appdata:/restore \
     rclone/rclone sync b2_remote:your-bucket-name/appdata /restore --progress

   # Restore configs
   docker run --rm \
     -v /volume1/appdata/rclone/config:/config/rclone \
     -v /volume1/backups-configs:/restore \
     rclone/rclone sync b2_remote:your-bucket-name/backups-configs /restore --progress

   # Optional: Restore photos if Immich is deployed
   docker run --rm \
     -v /volume1/appdata/rclone/config:/config/rclone \
     -v /volume1/photos:/restore \
     rclone/rclone sync b2_remote:your-bucket-name/photos /restore --progress
   ```

4. **Restart services**:
   ```bash
   # On Raspberry Pi
   ssh pi@192.168.10.2
   cd /opt/docker
   docker-compose down
   docker-compose up -d
   ```

5. **Verify everything works**:
   - Check AdGuard Home: http://192.168.10.2
   - Check Home Assistant: http://192.168.10.2:8123
   - Check Grafana dashboards

**What you lost**:
- Proxmox VM backups (but those VMs are recreatable via Ansible)
- Data written after last 03:00 AM backup (up to 24h)

**What's fully restored**:
- All Docker service configurations and data
- Ansible configs and secrets
- OPNsense exported configs

### Scenario 4: "I Need to Restore a Proxmox VM"

**Time to restore**: 10-30 minutes (depends on VM size)

**When you need this**: OPNsense VM got corrupted, you want to rollback a VM, testing

**Steps**:

Via Proxmox Web UI:
1. Login to https://192.168.10.10:8006
2. Click on Datacenter > Backup Storage (cargo-proxmox-backups)
3. Find the backup you want to restore (sorted by date)
4. Click "Restore"
5. Choose:
   - VM ID (100 to restore in-place, or new ID like 150 for test)
   - Storage target (local-lvm)
   - Start VM after restore: Yes/No
6. Click "Restore" and wait

Via CLI:
```bash
# SSH to Proxmox host
ssh root@192.168.10.10

# List available backups
ls -lh /mnt/pve/cargo-proxmox-backups/dump/

# Restore specific backup
qmrestore /mnt/pve/cargo-proxmox-backups/dump/vzdump-qemu-100-2025_12_24-10_00_00.vma.zst 100

# Or restore to new VM ID for testing
qmrestore /mnt/pve/cargo-proxmox-backups/dump/vzdump-qemu-100-2025_12_24-10_00_00.vma.zst 150
```

## Test Procedures (Validate Your Backups)

Never trust a backup you haven't tested. Here's how to verify each method works.

### Test 1: Btrfs Snapshot Restore (Monthly)

```bash
# SSH to NAS
ssh cargo@192.168.10.5

# Create a test file
echo "original content" > /volume1/appdata/test-restore.txt

# Wait for next snapshot (or trigger one via UGOS UI)

# Modify the file
echo "modified content" > /volume1/appdata/test-restore.txt

# Restore from snapshot
cp /.snapshots/@GMT-$(date +%Y.%m.%d)-04.00.00/volume1/appdata/test-restore.txt \
   /volume1/appdata/test-restore-recovered.txt

# Verify
cat /volume1/appdata/test-restore-recovered.txt
# Should show: "original content"

# Cleanup
rm /volume1/appdata/test-restore*
```

### Test 2: B2 Restore (Quarterly)

```bash
# SSH to NAS
ssh cargo@192.168.10.5

# Create test directory for restore
mkdir -p /tmp/b2-restore-test

# Restore a small folder from B2
docker run --rm \
  -v /volume1/appdata/rclone/config:/config/rclone \
  -v /tmp/b2-restore-test:/restore \
  rclone/rclone copy b2_remote:your-bucket-name/appdata/adguard /restore --progress

# Verify files exist and are readable
ls -lh /tmp/b2-restore-test/
cat /tmp/b2-restore-test/AdGuardHome.yaml

# Cleanup
rm -rf /tmp/b2-restore-test
```

### Test 3: Proxmox VM Restore (Bi-annually)

```bash
# Via Proxmox UI or CLI
# Restore OPNsense VM 100 to a new ID 150
qmrestore /mnt/pve/cargo-proxmox-backups/dump/vzdump-qemu-100-*.vma.zst 150

# Start the test VM
qm start 150

# Verify it boots (check via noVNC console)

# Delete test VM
qm stop 150
qm destroy 150
```

## Disaster Recovery Scenarios & Playbooks

### DR Scenario 1: Total Infrastructure Loss (House Fire)

**What survived**: Backblaze B2 cloud backups

**Recovery steps**:
1. Buy new hardware (NAS minimum, rest can wait)
2. Install NAS, configure network
3. Restore from B2 (see Scenario 3 above)
4. Buy new Pi, install OS, run Ansible
5. Services are back online

**RTO (Recovery Time Objective)**: 1-3 days (mostly waiting for hardware delivery)
**RPO (Recovery Point Objective)**: Up to 24 hours of data loss (last B2 sync)

### DR Scenario 2: Ransomware / Corruption

**What happened**: Your files got encrypted or corrupted but backups are safe

**Recovery steps**:
1. **DO NOT panic and delete everything**
2. **Isolate the NAS** from network immediately
3. SSH to NAS, check if backups are intact:
   ```bash
   ls -la /.snapshots/
   # Snapshots are read-only, ransomware can't touch them
   ```
4. Restore from snapshot (see Scenario 1)
5. Or if snapshots compromised, restore from B2 (see Scenario 3)
6. Investigate how ransomware got in, patch the vulnerability

**RTO**: 2-8 hours
**RPO**: 0-24 hours (snapshot vs B2)

### DR Scenario 3: Single Disk Failure in RAID 1

**What happened**: One of your NAS drives died

**How you know**:
- UGOS shows degraded RAID status
- Email alert (if configured)
- Red LED on failed drive bay

**Recovery steps**:
1. Order replacement drive (same size or larger)
2. Shutdown NAS gracefully:
   ```bash
   ssh cargo@192.168.10.5
   sudo shutdown -h now
   ```
3. Remove failed drive from bay
4. Insert new drive
5. Power on NAS
6. Via UGOS UI: Storage > RAID > Rebuild
7. Wait 4-8 hours for rebuild to complete
8. **DO NOT shutdown during rebuild**

**RTO**: 4-8 hours rebuild time
**RPO**: Zero (RAID 1 is live mirroring)

### DR Scenario 4: OPNsense VM Corruption

**What happened**: OPNsense won't boot, network is down

**Quick fix** (restore from backup):
```bash
# SSH to Proxmox via direct IP (bypass OPNsense)
ssh root@192.168.10.10

# Restore latest backup
qmrestore /mnt/pve/cargo-proxmox-backups/dump/vzdump-qemu-100-*.vma.zst 100 --force

# Start VM
qm start 100
```

**Alternative** (restore config only):
1. Reinstall OPNsense VM from scratch
2. Access web UI via direct connection
3. System > Configuration > Backups
4. Restore latest XML config from `/volume1/backups-configs/opnsense/`

## Backup Monitoring & Alerts

### Check Backup Health Dashboard

Homepage dashboard (http://192.168.10.2:8082) shows:
- Cloud Appdata: Last sync status (OK/Error)
- Cloud Configs: Last sync status
- PVE Backups: Last VM backup timestamp

### Manual Health Checks

```bash
# Rclone backup status
ssh cargo@192.168.10.5
cat /volume1/appdata/rclone/backup_status.json

# Proxmox backup jobs
ssh root@192.168.10.10
pvesh get /cluster/backup

# RAID status
ssh cargo@192.168.10.5
cat /proc/mdstat

# Btrfs snapshots
ssh cargo@192.168.10.5
ls -la /.snapshots/ | tail -10
```

### Setting Up Alerts (Future Enhancement)

Currently manual monitoring. Planned integrations:
- Uptime Kuma: Alert if backup script fails
- Grafana: Alert on old backup timestamps
- Prometheus: Alert on RAID degradation
- Scrutiny: Alert on disk SMART warnings

## Backup Costs & Storage Usage

### Backblaze B2 Pricing (as of 2025)

- Storage: $6/TB/month
- Download: $10/TB (only when restoring)
- Upload: Free

### Estimated Costs

| Backup Size | Monthly Cost | Annual Cost |
|-------------|--------------|-------------|
| 100 GB | $0.60 | $7.20 |
| 500 GB | $3.00 | $36.00 |
| 1 TB | $6.00 | $72.00 |
| 2 TB | $12.00 | $144.00 |

**Disaster recovery cost**: Add ~$10-20 one-time download fee

### Current Usage

Check with:
```bash
docker run --rm -v /volume1/appdata/rclone/config:/config/rclone \
  rclone/rclone size b2_remote:your-bucket-name
```

## Frequently Asked Questions

**Q: Can I restore a single Docker container's data?**
A: Yes. Find the container's volume in `/volume1/appdata/<service-name>` and restore just that folder from snapshot or B2.

**Q: What if I accidentally delete something and the 03:00 AM backup already ran?**
A: Use Btrfs snapshots - they're taken at 04:00 AM and kept for 7 days. You have a 1-hour window.

**Q: Can I pause the nightly B2 backup?**
A: Yes. SSH to NAS and `crontab -e`, comment out the backup job. Don't forget to re-enable it.

**Q: How do I change the B2 backup schedule?**
A: Edit `ansible/playbooks/deploy_nas_backup.yml`, modify the cron task, re-run playbook.

**Q: What happens if my internet is down during 03:00 AM backup?**
A: Rclone will fail, log the error, and retry the next night. Your local snapshots are unaffected.

**Q: Can I restore to a different NAS brand (Synology, TrueNAS)?**
A: Yes. The B2 backups are just files. Restore them to any Linux system with rclone installed.

**Q: Should I back up the Proxmox VM backups to B2?**
A: Optional. They're large and can be regenerated (Ansible + restored appdata = working VM). Prioritize appdata and configs.

## References

- Rclone documentation: https://rclone.org/docs/
- Backblaze B2 docs: https://www.backblaze.com/b2/docs/
- Btrfs wiki: https://btrfs.wiki.kernel.org/
- Ansible playbook: `ansible/playbooks/deploy_nas_backup.yml`
- NAS specs: `docs/architecture/nas-specs.md`
