# Hardware - Spécifications Matérielles

Toutes les specs hardware du homelab dans un seul endroit. Mise à jour quand j'achète un truc.

## Vue d'ensemble

| Device               | Rôle                  | CPU                | RAM          | Stockage          | IP           |
| -------------------- | --------------------- | ------------------ | ------------ | ----------------- | ------------ |
| **GMKtec NucBox M6** | Proxmox (hyperviseur) | AMD Ryzen 5 7640HS | 32 GB DDR5   | 1 TB NVMe         | 192.168.1.2  |
| **Raspberry Pi 5**   | Control Tower         | ARM Cortex-A76     | 8 GB LPDDR4X | 128 GB SD         | 192.168.1.10 |
| **UGREEN DXP2800**   | NAS Cargo             | Intel N100         | 8 GB DDR5    | 2x 4TB + 1TB NVMe | 192.168.1.5  |
| **Switch PoE+**      | Réseau LAN            | -                  | -            | -                 | 192.168.1.3  |

---

## GMKtec NucBox M6 (Proxmox)

**Rôle** : Hyperviseur principal, héberge les VMs et LXCs
**IP Management** : 192.168.1.2
**Hostname** : pve.blackbox.homes

### Processeur

| Spec                | Détail                |
| ------------------- | --------------------- |
| **Modèle**          | AMD Ryzen 5 7640HS    |
| **Génération**      | Zen 4 (2023)          |
| **Architecture**    | x86-64, 4nm TSMC      |
| **Cores / Threads** | 6C / 12T              |
| **Fréquence Base**  | 4.3 GHz               |
| **Fréquence Boost** | 5.0 GHz               |
| **Cache L3**        | 16 MB                 |
| **TDP**             | 35-54W (configurable) |

**Pourquoi ce choix** :

- CPU moderne avec excellentes perfs single-thread
- Faible consommation vs performance
- Support virtualisation AMD-V/SVM
- iGPU intégré pour transcoding

### GPU Intégré

| Spec              | Détail                             |
| ----------------- | ---------------------------------- |
| **Modèle**        | AMD Radeon 760M (RDNA 3)           |
| **Compute Units** | 8 CUs                              |
| **Shaders**       | 512 stream processors              |
| **Fréquence**     | 2.6 GHz                            |
| **API Support**   | Vulkan 1.3, OpenGL 4.6, DirectX 12 |

**Hardware Acceleration** :

- H.264 encode/decode (AVC)
- H.265 encode/decode (HEVC) 10-bit
- AV1 decode
- VP9 encode/decode

**Usage** :

- Passthrough vers VM 110 (Media Stack) pour Jellyfin
- Transcoding hardware-accelerated via VA-API
- Support des codecs modernes (HEVC, AV1)

### Mémoire RAM

| Spec               | Détail                   |
| ------------------ | ------------------------ |
| **Capacité**       | 32 GB                    |
| **Type**           | DDR5 SDRAM               |
| **Fréquence**      | 5600 MT/s                |
| **Channels**       | Dual-channel (2x SODIMM) |
| **Bande passante** | ~89.6 GB/s               |

**Allocation Proxmox** :

- Host (Proxmox) : ~2 GB
- VM 100 (OPNsense) : 2 GB
- VM 110 (Media) : 8 GB
- VM 120 (Downloads) : 4 GB
- LXC 200-210 : 6 GB total
- Buffer : ~10 GB libre

### Stockage

| Spec            | Détail                            |
| --------------- | --------------------------------- |
| **Slot M.2**    | 1x NVMe PCIe 4.0 x4               |
| **Capacité**    | 1 TB                              |
| **Performance** | ~7000 MB/s read, ~5000 MB/s write |
| **Filesystem**  | LVM-Thin (Proxmox)                |

**Allocation** :

- Proxmox system : 100 GB
- VMs disks : 166 GB (VM 100: 16GB, VM 110: 100GB, VM 120: 50GB)
- LXCs disks : 50 GB
- Backups locaux temporaires : ~684 GB libre

### Réseau

| Interface      | Vitesse | Usage                     | IP          |
| -------------- | ------- | ------------------------- | ----------- |
| **nic0 (LAN)** | 2.5 GbE | Vers Switch (vmbr0)       | 192.168.1.2 |
| **nic1 (WAN)** | 2.5 GbE | Passthrough vers OPNsense | -           |

**Chipset** : Realtek RTL8125B (2.5 Gigabit)
**Jumbo Frames** : Supportés (MTU 9000)

### Connectique

| Port                    | Quantité  | Usage                                |
| ----------------------- | --------- | ------------------------------------ |
| USB 3.2 Gen 2 (10 Gbps) | 4x Type-A | Périphériques, backup externe        |
| USB-C 3.2 Gen 2         | 1x        | Display ou stockage externe          |
| HDMI 2.1                | 2x        | Displays (rarement utilisé headless) |
| RJ45 2.5G               | 2x        | WAN + LAN                            |
| Audio Jack 3.5mm        | 1x        | Non utilisé                          |

---

## Raspberry Pi 5 (Control Tower)

**Rôle** : Services critiques + Observabilité
**IP Statique** : 192.168.1.10
**Hostname** : tower.blackbox.homes

### Processeur

| Spec                | Détail                     |
| ------------------- | -------------------------- |
| **Modèle**          | Broadcom BCM2712           |
| **Architecture**    | ARM Cortex-A76 (ARMv8.2-A) |
| **Cores / Threads** | 4C / 4T                    |
| **Fréquence**       | 2.4 GHz                    |
| **Cache L2**        | 512 KB per core            |
| **Cache L3**        | 2 MB shared                |

**Performance** :

- ~2-3x plus rapide que Raspberry Pi 4
- Support instructions AES, SHA, CRC

### Mémoire RAM

| Spec               | Détail        |
| ------------------ | ------------- |
| **Capacité**       | 8 GB          |
| **Type**           | LPDDR4X SDRAM |
| **Fréquence**      | 4267 MT/s     |
| **Bande passante** | ~34 GB/s      |

**Allocation** :

- Services critiques (AdGuard, HA, Homepage) : ~800 MB
- Observabilité (Grafana, Prometheus, Loki) : ~2.3 GB
- Monitoring (Uptime Kuma, Scrutiny, etc.) : ~500 MB
- Productivity (Paperless, Stirling) : ~3 GB
- System + Buffer : ~1.4 GB

### Stockage

| Spec         | Détail                         |
| ------------ | ------------------------------ |
| **Slot**     | microSD UHS-I                  |
| **Capacité** | 128 GB                         |
| **Classe**   | A2 (Application Performance)   |
| **Vitesse**  | ~100 MB/s read, ~70 MB/s write |

**Appdata** : Stocké sur NFS (Cargo `/appdata`)

### Réseau

| Interface    | Vitesse              | Usage                  | IP           |
| ------------ | -------------------- | ---------------------- | ------------ |
| **Ethernet** | 1 GbE                | Connexion principale   | 192.168.1.10 |
| **WiFi**     | 802.11ac (2.4/5 GHz) | Backup/config initiale | -            |

**Chipset Ethernet** : Broadcom BCM54213PE (Gigabit)

### Connectique

| Port             | Quantité  | Usage                        |
| ---------------- | --------- | ---------------------------- |
| USB 3.0 (5 Gbps) | 2x Type-A | Périphériques                |
| USB 2.0          | 2x Type-A | Clavier config initiale      |
| USB-C            | 1x        | Power (5V 5A, 25W)           |
| HDMI Micro       | 2x        | Display (écran 3.5" tactile) |
| GPIO             | 40 pins   | Écran tactile SPI            |
| RJ45             | 1x        | Ethernet Gigabit             |

### Écran Tactile

| Spec           | Détail     |
| -------------- | ---------- |
| **Taille**     | 3.5"       |
| **Résolution** | 480x320    |
| **Interface**  | SPI (GPIO) |
| **Touch**      | Resistive  |

**Usage** : Dashboard monitoring local (`status_dashboard.py`)

---

## UGREEN DXP2800 (NAS Cargo)

**Rôle** : Stockage centralisé + Backups + Services ML
**IP Statique** : 192.168.1.5
**Hostname** : cargo.blackbox.homes
**Firmware** : UGOS (propriétaire UGREEN)

### Processeur

| Spec                | Détail                         |
| ------------------- | ------------------------------ |
| **Modèle**          | Intel N100 (Alder Lake-N)      |
| **Génération**      | 12th gen (2023)                |
| **Architecture**    | x86-64, 10nm Enhanced SuperFin |
| **Cores / Threads** | 4C / 4T (E-cores only)         |
| **Fréquence Base**  | 0.8 GHz                        |
| **Fréquence Turbo** | 3.4 GHz (single-core)          |
| **Cache**           | 6 MB Intel Smart Cache         |
| **TDP**             | 6W (configurable jusqu'à 15W)  |

**Instruction Sets** :

- SSE4.1, SSE4.2, AVX, AVX2
- AES-NI (encryption hardware)
- SHA extensions

**Performance** :

- ~2x plus rapide que Celeron N5105
- ~30% d'un Ryzen 5 7640HS (single-thread)
- Parfait pour NAS, transcoding léger, ML inference

### GPU Intégré

| Spec                | Détail                               |
| ------------------- | ------------------------------------ |
| **Modèle**          | Intel UHD Graphics (Gen 12)          |
| **Execution Units** | 24 EUs                               |
| **Fréquence**       | 300 MHz - 750 MHz                    |
| **API Support**     | DirectX 12.1, OpenGL 4.6, Vulkan 1.3 |

**QuickSync Video (Gen 12)** :

- H.264 encode/decode
- H.265 encode/decode (10-bit)
- VP9 encode/decode
- AV1 decode only

**Usage prévu** :

- Thumbnails vidéo Immich (hardware-accelerated)
- Transcoding léger si besoin
- Pas de charge CPU pour vidéo

### Mémoire RAM

| Spec               | Détail                          |
| ------------------ | ------------------------------- |
| **Capacité**       | 8 GB                            |
| **Type**           | DDR5 SDRAM                      |
| **Fréquence**      | 4800 MT/s                       |
| **Channels**       | Single-channel (SODIMM)         |
| **Bande passante** | ~38.4 GB/s                      |
| **Extensible**     | Oui, jusqu'à 16 GB (slot libre) |

**Comparaison DDR5 vs DDR4** :

- Bande passante : +50% vs DDR4-3200
- Efficacité énergétique : -20% consommation

**Allocation** :

- UGOS system : ~500 MB
- NFS services : ~200 MB
- Rclone backups : ~200 MB
- Scrutiny collector : ~100 MB
- Immich (futur) : ~6 GB
- Buffer : ~1 GB

### Stockage

#### Baies Disques 3.5"

| Spec               | Détail               |
| ------------------ | -------------------- |
| **Baies**          | 2x SATA III (6 Gbps) |
| **Configuration**  | RAID 1 (miroir)      |
| **Capacité Brute** | 2x 4 TB = 8 TB       |
| **Capacité Utile** | 3.6 TB (RAID 1)      |
| **Filesystem**     | Btrfs                |

**Disques** : HDD 3.5" 7200 RPM SATA III (modèle à documenter)

#### Cache NVMe

| Spec                 | Détail                            |
| -------------------- | --------------------------------- |
| **Slot M.2**         | 1x NVMe PCIe 3.0 x2               |
| **Capacité**         | 1 TB                              |
| **Allocation Cache** | 500 GB (lecture)                  |
| **Performance**      | ~1500 MB/s read, ~1000 MB/s write |

**Rôle du cache** :

- Accélère accès fichiers fréquents
- Métadonnées Btrfs
- Docker layers

### Réseau

| Interface | Vitesse | Usage                     | IP          |
| --------- | ------- | ------------------------- | ----------- |
| **eth0**  | 2.5 GbE | Connexion principale      | 192.168.1.5 |
| **eth1**  | 2.5 GbE | Non utilisé (backup/LACP) | -           |

**Chipset** : Realtek RTL8125B
**Link Aggregation** : LACP supporté
**Jumbo Frames** : MTU 9000 supporté

**Performance NFS théorique** :

- Single link : ~295 MB/s (2.5 Gbit/s)
- Latence LAN : 0.5-2 ms

### Connectique

| Port                   | Quantité  | Usage                      |
| ---------------------- | --------- | -------------------------- |
| USB 3.2 Gen 1 (5 Gbps) | 2x Type-A | Backup externe             |
| HDMI 2.0               | 1x        | Display (rarement utilisé) |
| RJ45 2.5G              | 2x        | Réseau (1 actif, 1 backup) |
| Power DC               | 1x        | 12V/5A (60W max)           |

---

## Switch PoE+ Manageable

**Rôle** : Réseau LAN homelab
**IP Management** : 192.168.1.3
**Hostname** : switch.blackbox.homes

### Spécifications

| Spec                 | Détail                     |
| -------------------- | -------------------------- |
| **Ports**            | 5x RJ45 Gigabit            |
| **PoE+**             | 802.3at (jusqu'à 30W/port) |
| **Budget PoE Total** | À documenter               |
| **Backplane**        | 10 Gbps                    |
| **Management**       | Web UI + CLI               |

### Features

- **VLANs** : 802.1Q (jusqu'à 4096 VLANs)
- **IGMP Snooping** : Pour multicast (Home Assistant)
- **Jumbo Frames** : MTU 9000
- **QoS** : 802.1p prioritization
- **Link Aggregation** : LACP support

### Configuration

**Ports** :

1. Port 1 : Uplink Box FAI (non utilisé actuellement)
2. Port 2 : Proxmox (192.168.1.2)
3. Port 3 : Raspberry Pi (192.168.1.10)
4. Port 4 : NAS Cargo (192.168.1.5)
5. Port 5 : Libre

**Settings** :

- LEDs : Désactivées
- Jumbo Frames : Activés (MTU 9000)
- IGMP Snooping : Activé

---

## Consommation Électrique

Estimation de la consommation du homelab :

| Device             | Idle | Charge | Max              |
| ------------------ | ---- | ------ | ---------------- |
| **GMKtec M6**      | 15W  | 35W    | 54W              |
| **Raspberry Pi 5** | 3W   | 8W     | 25W (avec écran) |
| **NAS Cargo**      | 10W  | 20W    | 60W              |
| **Switch**         | 5W   | 8W     | 15W              |
| **TOTAL**          | ~33W | ~71W   | ~154W            |

**Coût électrique annuel** (à 0.25€/kWh) :

- Idle 24/7 : ~72€/an
- Charge moyenne : ~156€/an

**Pourquoi du low-power** :

- Tourne 24/7, la conso compte
- Équipements modernes = bon ratio perf/watt
- Évite surchauffe en rack fermé

---

## Évolutions Futures

**Court terme** :

- Ajouter slot RAM sur NAS (16 GB total)
- Documenter modèle exact des HDD

**Moyen terme** :

- Upgrade disques NAS : 2x 8TB ou 2x 12TB
- Ajouter UPS pour shutdowns propres

**Long terme** :

- Possibilité second nœud Proxmox pour HA
- Upgrade switch vers 2.5GbE ou 10GbE SFP+

## Notes

Si tu achètes du nouveau matos, mets à jour ce fichier !
