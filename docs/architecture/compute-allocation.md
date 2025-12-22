# 🧮 Architecture d'Allocation des Ressources Compute

Ce document détaille la stratégie d'allocation des ressources sur le GMKtec NucBox M6 et les justifications techniques.

## 1. Spécifications Matérielles

**GMKtec NucBox M6 - Serveur Principal**
- **Processeur :** AMD Ryzen 5 7640HS (6 cœurs / 12 threads, jusqu'à 5.0 GHz)
- **Fabrication :** TSMC 4 nm, TDP 35-50W
- **RAM :** 32 GB DDR5 4800 MT/s (extensible jusqu'à 128 GB)
- **Stockage :** 1 TB NVMe PCIe 4.0
- **GPU Intégré :** AMD Radeon 760M (iGPU)
- **Réseau :** Double LAN 2.5G, WiFi 6E, Bluetooth 5.2

---

## 2. Architecture Hybride VM/LXC

### Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────┐
│  GMKtec NucBox M6 - Proxmox VE 9.1                     │
│  32 GB RAM | 6C/12T @ 5.0 GHz | 1 TB NVMe             │
└─────────────────────────────────────────────────────────┘
           │
           ├─ VM 100: OPNsense (2 GB)
           │  └─ Routeur, Pare-feu, DHCP
           │
           ├─ VM 110: Media Stack (14 GB) ⭐
           │  └─ Jellyfin (iGPU), Immich, Overseerr
           │
           ├─ VM 120: Download Stack (6 GB)
           │  └─ Gluetun, qBittorrent, *Arr
           │
           ├─ LXC 200: Infrastructure (4 GB)
           │  └─ Nginx Proxy, Authentik, Bitwarden
           │
           └─ LXC 210: Productivity (3 GB)
              └─ Paperless-ngx, Stirling-PDF
```

### Tableau Récapitulatif

| Instance    | Type | vCPU | RAM   | Stockage | IP Assignée    | Autostart |
| :---------- | :--- | :--- | :---- | :------- | :------------- | :-------- |
| **VM 100**  | VM   | 2    | 2 GB  | 16 GB    | 192.168.10.1   | Oui       |
| **VM 110**  | VM   | 6    | 14 GB | 100 GB   | DHCP (Docker)  | Oui       |
| **VM 120**  | VM   | 2    | 6 GB  | 50 GB    | DHCP (Docker)  | Oui       |
| **LXC 200** | LXC  | 2    | 4 GB  | 20 GB    | DHCP (Docker)  | Oui       |
| **LXC 210** | LXC  | 2    | 3 GB  | 30 GB    | DHCP (Docker)  | Oui       |
| **Hôte**    | PVE  | -    | 3 GB  | -        | 192.168.10.10  | -         |
| **TOTAL**   | -    | 14   | 32 GB | 216 GB   | -              | -         |

---

## 3. Justifications Techniques

### VM 100 - OPNsense (2 GB au lieu de 4 GB)

**Décision :** Réduction de 4 GB → 2 GB après analyse `top`.

**Analyse de Consommation :**
```
Mem: 29M Active, 265M Inact, 1377M Wired, 2190M Free
     └─ Usage réel : ~1.6 GB
     └─ Libre : 2.2 GB (55% de gaspillage)
```

**Justifications :**
- OPNsense utilise ~1.6 GB en production sans IDS/IPS
- Pas de Suricata/Snort/Zenarmor actifs
- 2 GB offrent **25% de marge** (400 MB libres)
- Services actifs : Routing, Firewall, DHCPv4, DNS Forwarder

**Services Actifs :**
- `filterlo`, `bpf` : Pare-feu pf
- `dhcpd6c` : DHCP Client
- `ntpd` : Synchronisation temps
- `lighttpd` : Interface Web
- `php-cgi` : Backend UI

**Rollback Possible :** Si besoin futur (IDS/IPS), remonter à 4 GB en 2 clics.

---

### VM 110 - Media Stack (14 GB)

**Rôle :** Streaming multimédia et gestion photos.

**Services Hébergés :**
- **Jellyfin** : Streaming vidéo avec transcodage GPU
- **Immich** : Gestion photos/vidéos + ML (reconnaissance faciale)
- **Overseerr** : Interface de requêtes médias

**Besoins RAM :**
| Service     | RAM Minimale | RAM Recommandée | Raison                           |
| :---------- | :----------- | :-------------- | :------------------------------- |
| Jellyfin    | 2 GB         | 4-6 GB          | Transcodage simultané 4K         |
| Immich      | 4 GB         | 6-8 GB          | ML (TensorFlow), indexation      |
| Overseerr   | 512 MB       | 1 GB            | Interface Web légère             |
| **TOTAL**   | **6.5 GB**   | **14 GB**       | Marge pour pics de charge        |

**Allocation CPU :** 6 vCPU pour paralléliser transcodage + analyse ML.

**GPU Passthrough :** iGPU AMD Radeon 760M dédié (drivers `mesa-va-drivers`).

**Configuration Proxmox :**
```bash
# /etc/pve/qemu-server/110.conf
hostpci0: 0000:xx:00.0,pcie=1,x-vga=1
cpu: host
cores: 6
memory: 14336
```

---

### VM 120 - Download Stack (6 GB)

**Rôle :** Téléchargements isolés via VPN.

**Services Hébergés :**
- **Gluetun** : VPN Gateway avec Killswitch
- **qBittorrent** : Client Torrent
- **Radarr, Sonarr, Prowlarr** : Automatisation
- **Bazarr** : Sous-titres

**Isolation Réseau :**
```
Internet → Gluetun (VPN) → qBittorrent + *Arr
              ↓ (si VPN down)
           Killswitch → STOP
```

**Justifications :**
- **Séparation des risques** : Coupure VPN n'affecte pas Jellyfin
- **Debug facilité** : Logs VPN isolés
- **Sécurité** : Aucun leak IP si Gluetun crash

**Besoins RAM :**
- Gluetun : ~200 MB
- qBittorrent : 1-2 GB (selon torrents actifs)
- Radarr/Sonarr/Prowlarr : ~1.5 GB total
- Bazarr : ~512 MB
- **Marge** : 2 GB pour pics de téléchargement

---

### LXC 200 - Infrastructure (4 GB)

**Rôle :** Services d'accès et sécurité.

**Services Hébergés :**
- **Nginx Proxy Manager** : Reverse Proxy & SSL (Let's Encrypt)
- **Authentik** : SSO (Single Sign-On)
- **Bitwarden** : Gestionnaire de mots de passe auto-hébergé

**Pourquoi LXC au lieu de VM ?**
| Critère          | VM     | LXC    | Choix      |
| :--------------- | :----- | :----- | :--------- |
| Overhead RAM     | ~512MB | ~50MB  | **LXC**    |
| Temps de boot    | ~30s   | ~5s    | **LXC**    |
| Snapshots        | Oui    | Oui    | Égalité    |
| Isolation réseau | Forte  | Bonne  | Suffisant  |

**Besoins RAM :**
- Nginx Proxy Manager : ~512 MB
- Authentik : 2-3 GB (SSO avec base de données)
- Bitwarden : ~512 MB
- **Total** : 4 GB confortable

**Configuration LXC :**
```bash
pct create 200 local:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst \
  --hostname proxy-auth \
  --cores 2 \
  --memory 4096 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --rootfs local-lvm:20 \
  --unprivileged 1 \
  --features nesting=1
```

---

### LXC 210 - Productivity (3 GB)

**Rôle :** Gestion documentaire et outils PDF.

**Services Hébergés :**
- **Paperless-ngx** : GED avec OCR
- **Stirling-PDF** : Manipulation PDF

**Justifications LXC :**
- Services utilisés ponctuellement (pas 24/7 haute charge)
- Pas de GPU nécessaire
- Économie overhead VM (~400 MB)

**Besoins RAM :**
- Paperless-ngx : 2-2.5 GB (OCR Tesseract)
- Stirling-PDF : ~512 MB
- **Total** : 3 GB suffisant

---

## 4. Stratégie d'Allocation Réseau

### Interfaces Physiques Proxmox

| Interface | Nom Kernel | Bridge  | Usage            |
| :-------- | :--------- | :------ | :--------------- |
| NIC 0     | enp1s0     | vmbr0   | LAN (Switch)     |
| NIC 1     | enp2s0     | vmbr1   | WAN (Box FAI)    |

### Bridges Proxmox

**vmbr0 (LAN Bridge)**
- IP Hôte : `192.168.10.10/24`
- Gateway : `192.168.10.1` (OPNsense)
- Connecté à : VM 100 (net0), VM 110, VM 120, LXC 200, LXC 210

**vmbr1 (WAN Bridge)**
- Pas d'IP (passthrough physique)
- Connecté à : VM 100 (net1) uniquement
- Évite problèmes drivers Realtek 2.5G dans OPNsense

### Attribution IP

| Instance    | IP             | Mode      | DNS          |
| :---------- | :------------- | :-------- | :----------- |
| VM 100      | 192.168.10.1   | Statique  | -            |
| Proxmox     | 192.168.10.10  | Statique  | 192.168.10.2 |
| VM 110-120  | Plage DHCP     | DHCP      | 192.168.10.2 |
| LXC 200-210 | Plage DHCP     | DHCP      | 192.168.10.2 |

---

## 5. Ordre de Démarrage (Autostart)

```
1. VM 100 (OPNsense)       → Priorité 100, Délai 60s
   └─ Réseau + DHCP opérationnels

2. VM 110 (Media)          → Priorité 90, Délai 30s
   VM 120 (Downloads)      → Priorité 90, Délai 30s
   └─ Services principaux

3. LXC 200 (Infrastructure)→ Priorité 80, Délai 15s
   LXC 210 (Productivity)  → Priorité 80, Délai 15s
   └─ Services légers
```

**Configuration Proxmox :**
```bash
# VM 100 (OPNsense)
qm set 100 --onboot 1 --startup order=100,up=60

# VM 110-120
qm set 110 --onboot 1 --startup order=90,up=30
qm set 120 --onboot 1 --startup order=90,up=30

# LXC 200-210
pct set 200 --onboot 1 --startup order=80,up=15
pct set 210 --onboot 1 --startup order=80,up=15
```

---

## 6. Montages NFS (Stockage NAS)

Chaque instance Docker monte `/mnt/appdata` depuis le NAS Cargo (`192.168.10.5`).

**Configuration fstab (exemple VM 110) :**
```bash
192.168.10.5:/volume1/appdata  /mnt/appdata  nfs  defaults,_netdev  0 0
```

**Arborescence :**
```
/mnt/appdata/
├── jellyfin/          → VM 110
├── immich/            → VM 110
├── overseerr/         → VM 110
├── gluetun/           → VM 120
├── qbittorrent/       → VM 120
├── radarr/            → VM 120
├── sonarr/            → VM 120
├── prowlarr/          → VM 120
├── bazarr/            → VM 120
├── nginx-proxy/       → LXC 200
├── authentik/         → LXC 200
├── bitwarden/         → LXC 200
├── paperless/         → LXC 210
└── stirling-pdf/      → LXC 210
```

---

## 7. Évolutivité & Upgrade Path

### Scénario 1 : Upgrade RAM (64 GB)

**Redistribution recommandée :**
```
VM 110 (Media)      : 14 GB → 24 GB  (+10 GB pour Immich ML)
VM 120 (Downloads)  : 6 GB  → 8 GB   (+2 GB pour plus de torrents)
Proxmox (Hôte)      : 3 GB  → 6 GB   (+3 GB pour ZFS ARC cache)
Autres              : Inchangé
```

### Scénario 2 : Ajout Stockage (2 TB NVMe)

**Stratégie :**
- Monter 2ème NVMe comme stockage VM/LXC dédié
- Migrer VM 110 (gourmande) sur nouveau disque
- Libérer espace sur disque principal pour snapshots

### Scénario 3 : Séparation Immich

Si Immich devient trop gourmand :
```
VM 110 (14 GB) →  VM 110 : Jellyfin (8 GB)
                  VM 115 : Immich (12 GB) + GPU passthrough
```

---

## 8. Monitoring & Métriques

### Outils de Surveillance

| Outil        | Localisation       | Métriques                          |
| :----------- | :----------------- | :--------------------------------- |
| Proxmox UI   | 192.168.10.10:8006 | CPU, RAM, I/O par VM/LXC           |
| Uptime Kuma  | RPi (10.2)         | Disponibilité services             |
| Homepage     | RPi (10.2)         | Dashboard unifié                   |
| Scrutiny     | RPi + NAS          | Santé disques (S.M.A.R.T)          |

### Seuils d'Alerte Recommandés

**RAM :**
- **Attention** : Utilisation > 80% sur une instance
- **Critique** : Utilisation > 90% (risque OOM)

**CPU :**
- **Attention** : Load Average > nombre de vCPU × 0.7
- **Critique** : Load Average > nombre de vCPU × 1.5

**Stockage :**
- **Attention** : Disk usage > 80%
- **Critique** : Disk usage > 90%

---

## 9. Checklist de Déploiement

### Phase 1 : Optimisation OPNsense
- [ ] Arrêter VM 100
- [ ] Réduire RAM : 4 GB → 2 GB
- [ ] Démarrer VM 100
- [ ] Vérifier `top` : usage < 1.8 GB
- [ ] Tester connectivité internet

### Phase 2 : Création LXC
- [ ] Télécharger template Debian 12
- [ ] Créer LXC 200 (Infrastructure)
- [ ] Créer LXC 210 (Productivity)
- [ ] Configurer nesting=1 (pour Docker)
- [ ] Installer Docker via Ansible

### Phase 3 : Réorganisation Services
- [ ] Créer VM 120 (Downloads)
- [ ] Migrer Gluetun + *Arr depuis VM 110
- [ ] Tester VPN Killswitch
- [ ] Migrer NPM/Authentik vers LXC 200
- [ ] Migrer Paperless vers LXC 210

### Phase 4 : Augmentation VM 110
- [ ] Arrêter VM 110
- [ ] Augmenter RAM : 12 GB → 14 GB
- [ ] Démarrer VM 110
- [ ] Vérifier Jellyfin + Immich opérationnels

### Phase 5 : Validation
- [ ] Tester tous les services
- [ ] Vérifier montages NFS
- [ ] Configurer autostart
- [ ] Snapshot initial de chaque instance
- [ ] Documenter configuration finale

---

## 10. Troubleshooting

### VM ne démarre pas (Out of Memory)

**Symptôme :** Proxmox refuse de démarrer une VM/LXC.

**Solution :**
```bash
# Vérifier RAM disponible
free -h

# Lister toutes les instances actives
qm list
pct list

# Arrêter temporairement une instance non critique
qm stop 210
```

### Performance dégradée Jellyfin

**Causes possibles :**
1. GPU passthrough non actif
2. RAM insuffisante (swapping)
3. Disque NAS saturé

**Vérifications :**
```bash
# Dans VM 110
lspci | grep VGA        # Vérifier GPU visible
free -h                 # Vérifier swap usage
iostat -x 1             # Vérifier I/O wait
```

### LXC Docker ne démarre pas

**Erreur courante :** `Failed to create endpoint`

**Solution :**
```bash
# Vérifier nesting activé
pct config 200 | grep features

# Si absent, ajouter :
pct set 200 --features nesting=1

# Redémarrer LXC
pct reboot 200
```

---

## Références

- [Proxmox VE Documentation](https://pve.proxmox.com/pve-docs/)
- [OPNsense Hardware Sizing](https://docs.opnsense.org/manual/hardware.html)
- [LXC vs VM Performance](https://pve.proxmox.com/wiki/Linux_Container)
- [Docker in LXC Best Practices](https://blog.simos.info/how-to-run-docker-in-lxc-containers/)
