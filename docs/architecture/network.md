# Réseau - Configuration Réseau Homelab

Toute la config réseau au même endroit. Si ça ping pas, c'est ici qu'il faut chercher.

## Vue d'ensemble

```
Internet (Box FAI)
       |
       | WAN (PPPoE)
       v
┌──────────────────┐
│ OPNsense Router  │ 192.168.10.1 (Gateway)
│   VM 100         │
└────────┬─────────┘
         | LAN (vmbr0)
         v
    ┌────────┐
    │ Switch │ 192.168.10.3
    └───┬────┘
        |
        ├─── Proxmox Host (192.168.10.10)
        ├─── Raspberry Pi (192.168.10.2) ← DNS AdGuard
        ├─── NAS Cargo (192.168.10.5)
        └─── VMs/LXCs (DHCP 192.168.10.100-250)
```

## Paramètres Réseau

### Subnet Principal

| Paramètre          | Valeur                                       |
| ------------------ | -------------------------------------------- |
| **Réseau**         | 192.168.10.0/24                              |
| **Gateway**        | 192.168.10.1 (OPNsense)                      |
| **DNS Primaire**   | 192.168.10.2 (AdGuard Home sur Raspberry Pi) |
| **DNS Secondaire** | 1.1.1.1 (Cloudflare - fallback)              |
| **DHCP Range**     | 192.168.10.100 - 192.168.10.250              |
| **DHCP Server**    | OPNsense (ISC DHCPv4)                        |

### IPs Statiques

| Device                | IP            | Hostname              | Rôle                |
| --------------------- | ------------- | --------------------- | ------------------- |
| **OPNsense (VM 100)** | 192.168.10.1  | router.blackbox.homes | Gateway/Firewall    |
| **Proxmox Host**      | 192.168.10.10 | pve.blackbox.homes    | Hyperviseur         |
| **Switch**            | 192.168.10.3  | switch.blackbox.homes | Switch manageable   |
| **NAS Cargo**         | 192.168.10.5  | cargo.blackbox.homes  | Stockage NFS        |
| **Raspberry Pi**      | 192.168.10.2  | tower.blackbox.homes  | Control Tower + DNS |

### DHCP Range (VMs/LXCs)

| Range                           | Usage                         |
| ------------------------------- | ----------------------------- |
| 192.168.10.100 - 192.168.10.150 | VMs Proxmox                   |
| 192.168.10.151 - 192.168.10.200 | LXCs Proxmox                  |
| 192.168.10.201 - 192.168.10.250 | Devices temporaires / invités |

## Configuration Proxmox

### Interfaces Physiques

| Interface       | Nom Kernel | Chipset          | Vitesse | Bridge |
| --------------- | ---------- | ---------------- | ------- | ------ |
| **NIC 0 (LAN)** | enp1s0     | Realtek RTL8125B | 2.5 GbE | vmbr0  |
| **NIC 1 (WAN)** | enp2s0     | Realtek RTL8125B | 2.5 GbE | vmbr1  |

### Bridges Proxmox

#### vmbr0 (LAN Bridge)

```
vmbr0
├─ Attached to: enp1s0 (NIC 0)
├─ IP Proxmox Host: 192.168.10.10/24
├─ Gateway: 192.168.10.1
├─ DNS: 192.168.10.10
└─ Connecté à:
   ├─ VM 100 (OPNsense) - net0 (LAN)
   ├─ VM 110 (Media Stack) - net0
   ├─ VM 120 (Downloads) - net0
   ├─ LXC 200 (Infrastructure) - net0
   └─ LXC 210 (Productivity) - net0
```

**Caractéristiques** :

- MTU : 1500 (standard)
- Jumbo Frames : Désactivés (pas nécessaire sur Gigabit)
- VLAN Aware : Non (pas de VLANs pour l'instant)

#### vmbr1 (WAN Bridge)

```
vmbr1
├─ Attached to: enp2s0 (NIC 1)
├─ IP: Aucune (passthrough physique)
└─ Connecté à:
   └─ VM 100 (OPNsense) - net1 (WAN)
```

**Pourquoi passthrough** :

- OPNsense gère directement la connexion PPPoE vers Box FAI
- Évite problèmes drivers Realtek 2.5G dans OPNsense
- Isolement complet WAN/LAN au niveau hardware

## Configuration OPNsense (VM 100)

### Interfaces OPNsense

| Interface | Device | Bridge Proxmox | Usage              | Config                   |
| --------- | ------ | -------------- | ------------------ | ------------------------ |
| **WAN**   | vtnet1 | vmbr1          | Connexion Internet | PPPoE                    |
| **LAN**   | vtnet0 | vmbr0          | Réseau Homelab     | Statique 192.168.10.1/24 |

### Configuration WAN (PPPoE Proximus)

```
Type: PPPoE
Username: <username>@PROXIMUS
Password: <password>
Service name: (vide)
Dial on demand: Non
Idle timeout: 0 (Always connected)
```

**Port physique Box FAI** : Port 1 (bridge mode)

**Validation WAN** :

```bash
# Via console OPNsense ou SSH
ping -c 3 1.1.1.1   # Test connectivité Internet
```

### Configuration LAN

```
IP Address: 192.168.10.1/24
Gateway: (aucune - c'est le gateway)
```

### DHCP Server (ISC DHCPv4)

**Pourquoi ISC DHCPv4 et pas Dnsmasq** :

- Permet de forcer proprement le DNS (AdGuard)
- Dnsmasq DHCP moins flexible pour DNS custom
- Dnsmasq DNS reste actif pour requêtes locales OPNsense

**Configuration ISC DHCP** :

```
Enable: Oui
Range: 192.168.10.100 - 192.168.10.250
DNS Servers: 192.168.10.2 (AdGuard Home)
Secondary DNS: 1.1.1.1 (fallback)
Gateway: 192.168.10.1 (OPNsense)
Domain: blackbox.homes
Lease time: 86400 (24h)
```

**Dnsmasq DNS** :

```
Enable: Oui
Enable DHCP: Non (désactivé, on utilise ISC)
```

### Règles Firewall

#### WAN Rules

```
1. Block RFC1918 Private Networks
2. Block Bogon Networks
3. Allow All (sortant depuis LAN vers Internet)
```

#### LAN Rules

```
1. Allow All (trafic LAN vers WAN)
2. Allow DNS to AdGuard (192.168.10.10:53)
3. Allow Web UI OPNsense (192.168.10.1:443)
```

**NAT Outbound** : Automatic (masquerade vers WAN)

### Autostart OPNsense

**Proxmox VM Settings** :

```bash
qm set 100 --onboot 1 --startup order=100,up=60
```

- **Order 100** : Démarre en premier (priorité max)
- **Up delay 60s** : Attend 60s avant de démarrer les autres VMs
- **Pourquoi** : DHCP/Gateway doit être UP avant les autres services

## DNS Strategy

### Flow DNS

```
Client
  |
  v
192.168.10.2 (AdGuard Home sur Raspberry Pi)
  ├─ Requêtes internes (*.blackbox.homes) → Réponses locales
  ├─ Blocage Ads/Trackers
  └─ Upstream DNS → 1.1.1.1 (Cloudflare)
```

### Records DNS Locaux (AdGuard)

| Hostname          | IP             |
| ----------------- | -------------- |
| \*.blackbox.homes | 192.168.10.121 |
| blackbox.homes    | 192.168.10.121 |

**Upstream DNS (AdGuard)** :

- Primaire : 1.1.1.1 (Cloudflare)
- Secondaire : 1.0.0.1 (Cloudflare backup)
- DoH/DoT : Optionnel (pas nécessaire pour usage perso)

## Accès Distant (Tailscale)

### Stratégie "DNS Public / IP Privée"

Tous les services disposent d'un nom de domaine HTTPS valide mais ne sont accessibles que via Tailscale.

**Principe** :

1. Domaine : `*.blackbox.homes` (DNS public)
2. Certificat SSL : Let's Encrypt via DNS Challenge (Cloudflare)
3. IP : Pointe vers IP Tailscale (100.x.y.z) ou IP LAN (192.168.10.x)
4. Firewall : Aucun port ouvert sur WAN

**Services exposés** :

- jellyfin.blackbox.homes → Jellyfin (VM 110)
- home.blackbox.homes → Home Assistant (Raspberry Pi)
- vault.blackbox.homes → Vaultwarden (LXC 200)
- etc.

**Accès** :

- Depuis LAN : Direct via IP/hostname local
- Depuis Internet : Via Tailscale uniquement

### Tailscale Config

**Devices dans Tailnet** :

- Raspberry Pi (192.168.10.2) → Subnet Router
- Laptop/Phone → Exit nodes

**Subnet Routing** :

```bash
# Sur Raspberry Pi
sudo tailscale up --advertise-routes=192.168.10.0/24 --accept-routes
```

**Exit Node** : Non utilisé (on veut juste accès au LAN)

## NFS Mounts

### Exports NAS Cargo

| Share           | Path                     | Clients         | Permissions              |
| --------------- | ------------------------ | --------------- | ------------------------ |
| appdata         | /volume1/appdata         | 192.168.10.0/24 | rw,sync,no_subtree_check |
| media           | /volume1/media           | 192.168.10.0/24 | rw,sync,no_subtree_check |
| photos          | /volume1/photos          | 192.168.10.0/24 | rw,sync,no_subtree_check |
| proxmox-backups | /volume1/proxmox-backups | 192.168.10.10   | rw,sync,no_subtree_check |
| backups-configs | /volume1/backups-configs | 192.168.10.0/24 | ro,sync,no_subtree_check |

### Montages

#### Raspberry Pi (192.168.10.2)

```bash
# /etc/fstab
192.168.10.5:/volume1/appdata /mnt/appdata nfs defaults,_netdev 0 0
```

#### VM 110 (Media Stack)

```bash
# /etc/fstab
192.168.10.5:/volume1/media /mnt/media nfs defaults,_netdev 0 0
192.168.10.5:/volume1/photos /mnt/photos nfs defaults,_netdev 0 0
192.168.10.5:/volume1/appdata /mnt/appdata nfs defaults,_netdev 0 0
```

#### Proxmox Host

```bash
# Via Web UI: Datacenter > Storage > Add > NFS
# ID: nas-backups
# Server: 192.168.10.5
# Export: /volume1/proxmox-backups
# Content: VZDump backup file
```

**Options NFS** :

- Version : NFSv4
- Options : hard,intr,rsize=8192,wsize=8192

## Performances Réseau

### Benchmarks

**NFS Performance (Raspberry Pi → NAS)** :

```bash
# Write test
dd if=/dev/zero of=/mnt/appdata/test bs=1M count=1024
# ~110 MB/s (Gigabit Ethernet saturé)

# Read test
dd if=/mnt/appdata/test of=/dev/null bs=1M
# ~115 MB/s
```

**Latence LAN** :

```bash
# Raspberry Pi → NAS
ping -c 100 192.168.10.5
# ~0.3-0.8 ms (excellent)

# Proxmox → Raspberry Pi
ping -c 100 192.168.10.2
# ~0.2-0.5 ms
```

### Limites Actuelles

| Lien                  | Bande Passante Théorique | Réel Mesuré                        |
| --------------------- | ------------------------ | ---------------------------------- |
| Proxmox ↔ Switch      | 2.5 Gbps                 | Non testé                          |
| Raspberry Pi ↔ Switch | 1 Gbps                   | ~115 MB/s (920 Mbps)               |
| NAS ↔ Switch          | 2.5 Gbps                 | ~115 MB/s (limité par client 1GbE) |

**Bottleneck actuel** : Raspberry Pi avec Ethernet 1GbE

**Upgrade futur possible** :

- Switch full 2.5GbE
- Upgrade Raspberry Pi vers device 2.5GbE (pas prioritaire)

## Ordre de Démarrage (Cold Start)

Ordre critique pour que tout boot correctement :

```
1. NAS Cargo (192.168.10.5)
   └─ Exports NFS disponibles
      ↓
2. Proxmox Host (192.168.10.10)
   └─ OPNsense VM 100 démarre automatiquement
      ├─ Priority: 100 (first)
      └─ Delay: 60s
      ↓
3. OPNsense (192.168.10.1)
   └─ DHCP/Gateway opérationnel
      ↓
4. Raspberry Pi (192.168.10.2)
   └─ Monte /mnt/appdata via NFS
   └─ Démarre Docker stack (AdGuard, etc.)
      ↓
5. Proxmox VMs/LXCs (automatique)
   ├─ VM 110 (Media) - Priority 90, Delay 30s
   ├─ VM 120 (Downloads) - Priority 90, Delay 30s
   ├─ LXC 200 (Infra) - Priority 80, Delay 15s
   └─ LXC 210 (Productivity) - Priority 80, Delay 15s
```

**Temps total boot complet** : ~3-4 minutes

## Troubleshooting Réseau

### Pas d'Internet

```bash
# Sur OPNsense
ping 1.1.1.1  # Test connectivité WAN
ping google.com  # Test DNS

# Sur client LAN
ping 192.168.10.1  # Test gateway
ping 192.168.10.2  # Test DNS server
ping 1.1.1.1  # Test Internet
nslookup google.com 192.168.10.2  # Test résolution DNS
```

### NFS Mount Failed

```bash
# Vérifier NFS server accessible
ping 192.168.10.5

# Vérifier exports
showmount -e 192.168.10.5

# Tester montage manuel
sudo mount -t nfs 192.168.10.5:/volume1/appdata /mnt/test

# Vérifier logs
sudo journalctl -u nfs-client.target
```

### DNS Ne Résout Pas

```bash
# Tester AdGuard directement
nslookup google.com 192.168.10.2

# Vérifier DNS reçu en DHCP
cat /etc/resolv.conf

# Forcer renouvellement DHCP
sudo dhclient -r && sudo dhclient
```

## Notes

- Pas de VLANs pour l'instant (single flat network = simple)
- Pas de Jumbo Frames (pas nécessaire sur Gigabit/2.5G)
- Pas de Link Aggregation (single link suffit pour usage perso)
- IPv6 : Désactivé (pas utilisé)
