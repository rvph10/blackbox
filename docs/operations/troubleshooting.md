# Troubleshooting Guide

When things break (and they will), this guide helps you fix them fast. Organized by symptom, not by component.

## Quick Diagnostic Checklist

Before diving into specific issues, run this quick health check:

```bash
# From your workstation
ping 192.168.10.1   # OPNsense (gateway)
ping 192.168.10.2   # Raspberry Pi (DNS)
ping 192.168.10.5   # NAS (storage)
ping 192.168.10.10  # Proxmox (hypervisor)
ping 1.1.1.1        # Internet connectivity
```

If all respond: Network is fine, issue is service-specific.
If some fail: Network issue (see Network Problems below).

## Network Problems

### "No Internet Access" - Everything is Down

**Symptoms**: Can't browse web, apps timeout, DNS fails

**Most likely cause**: AdGuard Home (DNS) is down on Raspberry Pi

**Quick diagnosis**:
```bash
# Can you reach the gateway?
ping 192.168.10.1

# Can you reach the Pi?
ping 192.168.10.2

# Can you reach internet IPs directly?
ping 1.1.1.1
```

**If you CAN ping 1.1.1.1 but NOT browse web**: DNS is broken

**Emergency fix** (restore internet immediately):

1. Connect to OPNsense web UI:
   - Navigate to http://192.168.10.1
   - Login (credentials in vault.yml)

2. Change DNS server temporarily:
   - Go to Services > ISC DHCPv4 > [LAN]
   - Find "DNS servers" field
   - Change from `192.168.10.2` to `1.1.1.1`
   - Save and Apply

3. Reconnect your devices or run on each client:
   ```bash
   # Linux/Mac
   sudo dhclient -r && sudo dhclient

   # Windows
   ipconfig /release && ipconfig /renew
   ```

4. Internet should work now (without ad blocking)

**Permanent fix** (restart AdGuard):
```bash
ssh pi@192.168.10.2
cd /opt/docker
docker-compose ps | grep adguard  # Check status

# If it's stopped or unhealthy
docker-compose restart adguard

# Check logs for errors
docker-compose logs --tail=50 adguard
```

**After fixing AdGuard, restore DNS in OPNsense**:
- Change DNS back from `1.1.1.1` to `192.168.10.2`
- Renew DHCP leases on clients again

### "Can't Reach Raspberry Pi (192.168.10.2)"

**Symptoms**: Pi services unavailable, SSH timeouts

**Check 1: Is the Pi powered on?**
- Look for green LED on Pi
- Look at screen (if dashboard is running, it's booting)

**Check 2: Is the Pi's network connected?**
```bash
# From another machine on the network
ping 192.168.10.2

# Try SSH
ssh pi@192.168.10.2
```

**Check 3: Boot logs** (if you have physical access):
- Connect keyboard/monitor to Pi
- Check what's stuck during boot
- Common issue: Waiting for NFS mount

**If NFS mount is hanging boot**:

1. Force boot without NFS:
   ```bash
   # At Proxmox/another machine, SSH to Pi's IP if it gets one via DHCP
   # Or connect keyboard/monitor and use local console

   # Comment out NFS mount temporarily
   sudo nano /etc/fstab
   # Add # in front of NFS line

   sudo reboot
   ```

2. After Pi boots, diagnose NFS (see NFS section below)

3. Fix NFS, uncomment /etc/fstab, reboot

### "Specific Device Can't Connect to Internet"

**Symptoms**: Your laptop/phone can't browse, but others can

**Check 1: DHCP lease**
```bash
# On the affected device (Linux/Mac)
ip addr show

# Look for 192.168.10.x address
# If you see 169.254.x.x - DHCP failed
```

**Fix**: Renew DHCP lease
```bash
# Linux
sudo dhclient -r eth0 && sudo dhclient eth0

# Mac
sudo ipconfig set en0 DHCP

# Windows
ipconfig /release && ipconfig /renew
```

**Check 2: DNS settings**
```bash
cat /etc/resolv.conf

# Should show:
# nameserver 192.168.10.2
```

**If DHCP keeps failing**:
- Check OPNsense DHCP pool isn't exhausted
- Login to http://192.168.10.1
- Services > ISC DHCPv4 > Leases
- Pool is 192.168.10.100-200 (100 addresses)
- If full, extend range or remove old leases

### "Internet is Slow / High Latency"

**Check 1: Speedtest from OPNsense itself**
```bash
ssh root@192.168.10.1
speedtest-cli

# Or from web UI: Interfaces > Diagnostics > Speedtest
```

If OPNsense speed is good but clients are slow: Internal network issue

**Check 2: DNS latency**
```bash
# From client
dig @192.168.10.2 google.com

# Check query time at bottom
# Should be < 50ms
```

If DNS is slow (>500ms):
```bash
ssh pi@192.168.10.2
docker-compose logs --tail=100 adguard
# Look for upstream DNS timeout errors
```

**Check 3: NFS causing slowness**
```bash
# On Pi or any client using NFS
nfsstat -m

# Look for retransmits or timeouts
```

If NFS is timing out, see NFS Troubleshooting section.

**Check 4: System resource exhaustion**
```bash
ssh pi@192.168.10.2
htop

# Look for:
# - CPU at 100% constantly
# - Memory usage near 8GB
# - Load average > 4.0
```

If resources maxed out:
```bash
# Find the hog
docker stats

# Restart the problematic container
docker-compose restart <service-name>
```

## NFS Mount Failures

NFS (Network File System) is how Pi and VMs access data on the NAS. When it breaks, Docker containers won't start.

### "Docker Containers Won't Start - NFS Mount Missing"

**Symptoms**:
- Docker services stuck in restart loop
- `/mnt/appdata` is empty
- Boot hangs at "Mounting /mnt/appdata"

**Diagnosis**:
```bash
# SSH to Pi (or affected machine)
ssh pi@192.168.10.2

# Check if NFS is mounted
df -h | grep /mnt/appdata

# If empty - not mounted
mount | grep /mnt/appdata

# Try manual mount to see error
sudo mount -a -v
```

**Common errors and fixes**:

#### Error: "No route to host"
```
mount.nfs: No route to host
```

**Cause**: NAS is unreachable

**Fix**:
```bash
# Can you ping the NAS?
ping 192.168.10.5

# If not, NAS is down or network is broken
# 1. Check NAS physical power/link LEDs
# 2. Try accessing NAS web UI: http://192.168.10.5
# 3. Check switch port LEDs for NAS cable
```

#### Error: "Permission denied"
```
mount.nfs: access denied by server
```

**Cause**: NFS export permissions wrong on NAS

**Fix**:
1. Login to NAS web UI: http://192.168.10.5
2. Go to File Sharing > NFS
3. Find the export for `/volume1/appdata`
4. Check "Allowed Clients" includes:
   - `192.168.10.2` (Pi)
   - `192.168.10.10` (Proxmox host)
   - Or entire subnet: `192.168.10.0/24`
5. Permissions should be `rw,sync,no_root_squash`
6. Save and try mounting again

#### Error: "Stale file handle"
```
ls: cannot access '/mnt/appdata': Stale file handle
```

**Cause**: NAS was rebooted while NFS was mounted

**Fix**:
```bash
# Force unmount
sudo umount -f /mnt/appdata

# Or if that fails, lazy unmount
sudo umount -l /mnt/appdata

# Clean mount
sudo mount -a
```

### "NFS is Slow - Docker Commands Timeout"

**Symptoms**: `docker-compose up` takes forever, file operations lag

**Check 1: Network speed**
```bash
# On client
nfsstat -m | grep rtt

# Look for high RTT (round trip time)
# Normal: < 5ms
# Slow: > 50ms
# Broken: > 500ms
```

**Check 2: NAS load**
```bash
ssh cargo@192.168.10.5
uptime

# Load average should be < 2.0 for 4-core N100
```

**Check 3: Switch issues**
```bash
# Check for packet loss
ping -c 100 192.168.10.5 | grep loss

# 0% loss is good
# >1% loss indicates network issue
```

**Fix**:
- Reboot switch if packet loss detected
- Check network cables for damage
- Try different switch port

## Docker Container Issues

### "Container Won't Start"

**Diagnosis**:
```bash
ssh pi@192.168.10.2
cd /opt/docker

# Check container status
docker-compose ps

# Check recent logs
docker-compose logs --tail=50 <service-name>

# Try starting manually
docker-compose up <service-name>
```

**Common errors**:

#### "Port already in use"
```
Error: bind: address already in use
```

**Fix**:
```bash
# Find what's using the port (e.g., port 80)
sudo netstat -tulpn | grep :80

# Kill the process or stop conflicting container
docker-compose stop <conflicting-service>
docker-compose up <service-name>
```

#### "Cannot connect to Docker daemon"
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Fix**:
```bash
# Check Docker service status
sudo systemctl status docker

# If stopped, start it
sudo systemctl start docker

# Check your user is in docker group
groups | grep docker

# If not
sudo usermod -aG docker $USER
# Log out and back in
```

#### "Image pull failed"
```
Error response from daemon: pull access denied
```

**Fix**:
```bash
# Check internet connectivity
ping 1.1.1.1

# Try pulling manually
docker pull <image-name>

# If authentication error, login to registry
docker login

# Force re-pull in compose
docker-compose pull <service-name>
docker-compose up -d <service-name>
```

### "Container is Running but Service Unreachable"

**Check 1: Is it actually running?**
```bash
docker-compose ps

# Look for "Up" status, not "Restarting"
```

**Check 2: Check container logs**
```bash
docker-compose logs --tail=100 <service-name>

# Look for error messages like:
# - "Failed to bind to port"
# - "Configuration error"
# - "Database connection failed"
```

**Check 3: Can you reach it from inside the Pi?**
```bash
# Example: AdGuard on port 3000
curl http://localhost:3000

# If this works but external access fails: Firewall issue
```

**Check 4: Check port binding**
```bash
docker-compose ps

# Look at PORTS column
# Should show: 0.0.0.0:3000->3000/tcp
# NOT: 127.0.0.1:3000->3000/tcp (that's localhost-only)
```

**Fix**: Edit docker-compose.yml ports section
```yaml
# Wrong (localhost only)
ports:
  - "127.0.0.1:3000:3000"

# Correct (accessible from network)
ports:
  - "3000:3000"
```

### "Container Keeps Restarting"

**Symptoms**: `docker-compose ps` shows "Restarting (1) 10 seconds ago"

**Diagnosis**:
```bash
# Watch logs in real-time
docker-compose logs -f <service-name>

# Check exit code
docker inspect <container-name> | grep -A 5 State
```

**Common causes**:

1. **Missing config file**:
   ```
   Error: config.yaml not found
   ```
   Fix: Check NFS mount, verify config exists in `/mnt/appdata/<service>/`

2. **Permission denied**:
   ```
   Error: Permission denied writing to /data
   ```
   Fix: Check ownership
   ```bash
   ls -la /mnt/appdata/<service>/
   sudo chown -R 1000:1000 /mnt/appdata/<service>/
   ```

3. **Out of memory**:
   ```bash
   # Check dmesg for OOM killer
   dmesg | grep -i "out of memory"

   # Fix: Add memory limit to docker-compose.yml
   services:
     service-name:
       mem_limit: 2g
   ```

## Service-Specific Troubleshooting

### AdGuard Home

**Web UI**: http://192.168.10.2

**Logs**:
```bash
ssh pi@192.168.10.2
docker-compose logs --tail=100 adguard
```

**Common issues**:

#### "Queries not being blocked"
1. Check AdGuard is set as DNS in OPNsense (see Network Problems above)
2. Check blocklists are enabled:
   - Web UI > Filters > DNS blocklists
   - Should have at least 1 enabled list
   - Click "Update filters" to refresh

#### "Can't access Web UI"
```bash
# Check container is running
docker-compose ps | grep adguard

# Check port 3000
sudo netstat -tulpn | grep :3000

# Check from Pi itself
curl http://localhost:3000

# If that works, problem is network-level
```

#### "Upstream DNS servers not responding"
- Web UI > Settings > DNS settings
- Test upstream servers (1.1.1.1, 8.8.8.8)
- Try adding Cloudflare secondary: `1.0.0.1`

### Home Assistant

**Web UI**: http://192.168.10.2:8123

**Logs**:
```bash
docker-compose logs --tail=200 homeassistant
```

**Common issues**:

#### "Devices not responding"
1. Check if it's one device or all devices
2. For Zigbee/Z-Wave: Check USB dongle is passed through
   ```bash
   ls -la /dev/ttyUSB* /dev/ttyACM*

   # Should show your Zigbee coordinator
   # If missing, check docker-compose.yml devices section
   ```

3. Restart Home Assistant:
   ```bash
   docker-compose restart homeassistant
   ```

#### "Can't login - Authentication failed"
- Reset password via CLI:
  ```bash
  docker exec -it homeassistant bash
  hass --script auth change_password homeassistant newpassword
  ```

#### "Integrations offline after update"
- Check breaking changes: https://www.home-assistant.io/blog/
- Check config:
  ```bash
  docker exec -it homeassistant hass --script check_config
  ```

### Grafana

**Web UI**: http://192.168.10.2:3001

**Default login**: admin/admin (change on first login)

**Logs**:
```bash
docker-compose logs --tail=100 grafana
```

**Common issues**:

#### "Dashboards show 'No Data'"
1. Check Prometheus datasource:
   - Configuration > Data Sources > Prometheus
   - URL should be: `http://prometheus:9090`
   - Click "Test" - should show "Data source is working"

2. Check Prometheus is scraping:
   - Open http://192.168.10.2:9090
   - Status > Targets
   - All should be "UP"

3. Check Loki datasource:
   - URL should be: `http://loki:3100`
   - Test connection

#### "Dashboard not found / 404"
- Re-import dashboard:
  - Click "+" > Import
  - Enter dashboard ID: 1860 (Node Exporter Full)
  - Select Prometheus datasource
  - Import

### Prometheus

**Web UI**: http://192.168.10.2:9090

**Logs**:
```bash
docker-compose logs --tail=100 prometheus
```

**Common issues**:

#### "Targets down"
1. Check Status > Targets page
2. For each DOWN target, note the error
3. Common errors:
   - "Connection refused": Service not running
   - "Timeout": Firewall or network issue
   - "404": Wrong scrape path

#### "High memory usage"
- Prometheus stores metrics in memory
- Check retention settings in docker-compose.yml:
  ```yaml
  command:
    - '--storage.tsdb.retention.time=15d'  # Reduce if needed
  ```

### OPNsense (VM 100)

**Web UI**: http://192.168.10.1

**Console access**: Via Proxmox noVNC

**Logs**: System > Log Files

**Common issues**:

#### "Can't login to web UI"
1. Try from console (Proxmox noVNC)
2. Reset password:
   - Boot to single user mode
   - Select option 8 (Shell)
   - Run: `/usr/local/sbin/opnsense-shell password`

#### "PPPoE not connecting"
1. Check Interfaces > PPPoE > Status
2. Check ISP credentials in vault.yml
3. Restart PPPoE:
   ```bash
   # From OPNsense shell
   /etc/rc.d/ppp restart
   ```

#### "DHCP not giving out leases"
1. Services > ISC DHCPv4 > [LAN]
2. Check "Enable DHCP server" is ticked
3. Check range: 192.168.10.100 - 192.168.10.200
4. Check Leases tab for conflicts

#### "Firewall rule not working"
1. Firewall > Rules > LAN
2. Rules are processed top-to-bottom
3. Check rule counter (# packets matched)
4. Check logs: Firewall > Log Files > Live View

### Raspberry Pi Issues

#### "Pi won't boot"
1. Check power supply (official Pi 5 adapter = 5V 5A)
2. Check for red LED patterns:
   - Solid red: Power OK
   - Flashing red: Under-voltage (bad adapter)
   - No red: No power

3. Check SD card / NVMe:
   - Try booting from different media
   - Reflash OS if corrupted

#### "Pi boots but no network"
1. Check Ethernet cable + link LEDs
2. Check DHCP lease from OPNsense
3. Try static IP:
   ```bash
   # Connect monitor + keyboard
   sudo nano /etc/dhcpcd.conf

   # Add:
   interface eth0
   static ip_address=192.168.10.2/24
   static routers=192.168.10.1
   static domain_name_servers=1.1.1.1

   sudo reboot
   ```

#### "Dashboard screen is blank"
1. Check HDMI cable connected to correct port
2. Check screen power
3. Check Python script is running:
   ```bash
   systemctl status status-dashboard

   # View logs
   journalctl -u status-dashboard -f
   ```

4. Restart dashboard:
   ```bash
   sudo systemctl restart status-dashboard
   ```

## Diagnostic Commands Reference

### Network Diagnostics

```bash
# Ping test
ping -c 4 192.168.10.1

# DNS lookup
nslookup google.com 192.168.10.2
dig @192.168.10.2 google.com

# Trace route
traceroute 8.8.8.8

# Port test
nc -zv 192.168.10.2 3000
telnet 192.168.10.2 3000

# Check open ports on host
sudo netstat -tulpn | grep LISTEN
sudo ss -tulpn | grep LISTEN

# Network interface stats
ip -s link show eth0
```

### System Resource Checks

```bash
# CPU and memory (live)
htop

# Disk space
df -h

# Disk I/O
iostat -x 1

# Memory details
free -h

# Load average
uptime

# Top processes by CPU
top -o %CPU

# Top processes by memory
top -o %MEM

# Check for OOM kills
dmesg | grep -i "out of memory"
```

### Docker Diagnostics

```bash
# Container status
docker ps -a
docker-compose ps

# Container resource usage (live)
docker stats

# Logs
docker logs <container-name>
docker-compose logs <service-name>

# Logs with timestamps
docker logs -t <container-name>

# Follow logs live
docker logs -f <container-name>

# Inspect container config
docker inspect <container-name>

# Execute command in container
docker exec -it <container-name> bash
docker exec -it <container-name> sh

# Check container networks
docker network ls
docker network inspect <network-name>

# Prune unused resources
docker system prune -a
```

### NFS Diagnostics

```bash
# Show NFS mounts
mount | grep nfs
df -h | grep nfs

# NFS statistics
nfsstat -m

# Force unmount
sudo umount -f /mnt/appdata

# Lazy unmount (when stale)
sudo umount -l /mnt/appdata

# Re-mount all from /etc/fstab
sudo mount -a -v

# Check NFS server exports (from NAS)
showmount -e 192.168.10.5
```

### Proxmox Diagnostics

```bash
# VM status
qm list

# VM config
qm config 100

# Start/stop VM
qm start 100
qm stop 100
qm shutdown 100

# VM console (noVNC alternative)
qm terminal 100

# Backup job status
pvesh get /cluster/backup

# Storage status
pvesm status

# Cluster status
pvecm status
```

## Where to Find Logs

### Raspberry Pi Services

```bash
ssh pi@192.168.10.2

# Docker container logs
cd /opt/docker
docker-compose logs <service-name>

# System logs
sudo journalctl -xe

# Specific service logs
sudo journalctl -u docker -f
sudo journalctl -u status-dashboard -f

# Kernel logs (hardware issues)
dmesg | tail -50

# Boot logs
sudo journalctl -b
```

### NAS Logs

```bash
ssh cargo@192.168.10.5

# Rclone backup logs
cat /volume1/appdata/rclone/backup.log
tail -f /volume1/appdata/rclone/backup.log

# UGOS system logs
# Via web UI: System > Logs

# Docker logs (if running containers on NAS)
docker logs <container-name>
```

### Proxmox Logs

```bash
ssh root@192.168.10.10

# VM logs
cat /var/log/pve/tasks/active

# Proxmox system logs
journalctl -u pve*

# Backup job logs
grep vzdump /var/log/syslog

# Proxmox web UI logs
tail -f /var/log/pveproxy/access.log
```

### OPNsense Logs

Via web UI only (easier):
- System > Log Files > General
- Firewall > Log Files > Live View
- Services > Unbound DNS > Log Files

Or via SSH:
```bash
ssh root@192.168.10.1

# System log
clog /var/log/system.log

# Firewall log
clog /var/log/filter.log

# DHCP log
clog /var/log/dhcpd.log
```

## Getting Help

When asking for help (forums, Discord, IRC), include:

1. **What you were trying to do**
2. **What happened instead**
3. **Relevant logs** (paste to pastebin, not inline)
4. **Your environment**:
   ```bash
   uname -a
   docker version
   docker-compose version
   ```
5. **What you've already tried**

**Good example**:
> I'm trying to start AdGuard Home but it keeps restarting. Logs show "permission denied /data/AdGuardHome.yaml". I've checked the NFS mount is working and the file exists. Docker-compose logs: [pastebin link]. Running on Raspberry Pi 5 with Docker 24.0.6.

**Bad example**:
> adguard doesnt work help

## Advanced Troubleshooting Techniques

### Network Packet Capture

If you suspect network issues:
```bash
# Capture traffic on eth0 interface
sudo tcpdump -i eth0 -w /tmp/capture.pcap

# Capture only DNS traffic
sudo tcpdump -i eth0 port 53 -w /tmp/dns-capture.pcap

# Capture specific host
sudo tcpdump -i eth0 host 192.168.10.5

# Analyze with tshark
tshark -r /tmp/capture.pcap
```

### Stress Testing

Find bottlenecks:
```bash
# CPU stress test
sudo apt install stress
stress --cpu 4 --timeout 60s

# Memory stress test
stress --vm 2 --vm-bytes 2G --timeout 60s

# Disk I/O test
dd if=/dev/zero of=/tmp/test.img bs=1M count=1024 oflag=direct
```

### Performance Profiling

```bash
# CPU profiling
perf top

# I/O wait analysis
iostat -x 1 10

# Network bandwidth test
iperf3 -s  # On server
iperf3 -c 192.168.10.2  # On client
```

## Preventive Maintenance

To avoid issues before they happen:

### Weekly Checks
- [ ] Check Grafana dashboards for anomalies
- [ ] Review AdGuard query logs for weird traffic
- [ ] Check Homepage dashboard - all services green?

### Monthly Checks
- [ ] Update Docker images: `cd /opt/docker && docker-compose pull && docker-compose up -d`
- [ ] Check disk space: `df -h`
- [ ] Review Prometheus alerts (when configured)
- [ ] Test snapshot restore (see backup-restore.md)

### Quarterly Checks
- [ ] Update Raspberry Pi OS: `sudo apt update && sudo apt upgrade`
- [ ] Update Proxmox: `apt update && apt dist-upgrade`
- [ ] Update OPNsense: System > Firmware > Updates
- [ ] Test B2 restore (see backup-restore.md)
- [ ] Review firewall rules for unused/old rules

### Annually Checks
- [ ] Replace weak passwords
- [ ] Audit Ansible vault secrets
- [ ] Review and update documentation
- [ ] Check UPS battery health (if you have one)
- [ ] Clean dust from NAS/Pi/NUC fans

## Known Issues & Workarounds

### Issue: NFS mount delays Pi boot by 90 seconds

**Workaround**: Add timeout to fstab:
```bash
sudo nano /etc/fstab

# Add timeo=10 to NFS mount line
192.168.10.5:/volume1/appdata /mnt/appdata nfs defaults,timeo=10,_netdev 0 0
```

### Issue: Docker containers start before NFS is mounted

**Workaround**: Systemd dependency in Ansible playbook ensures mount happens before Docker

### Issue: UGOS NAS web UI slow after reboot

**Workaround**: Wait 5 minutes for services to fully initialize. It's normal.

### Issue: Homepage dashboard doesn't show service status

**Workaround**: Check API keys are configured in `services.yaml`, restart Homepage container

## References

- Ansible playbooks: `ansible/playbooks/`
- Architecture docs: `docs/homelab.md`
- Services status: `docs/services-status.md`
- Backup guide: `docs/operations/backup-restore.md`
