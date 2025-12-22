# 💾 Spécifications Détaillées NAS Cargo

**Modèle** : UGREEN DXP2800
**IP** : 192.168.10.5
**Hostname** : cargo.blackbox.homes
**Firmware** : UGOS (propriétaire UGREEN)

---

## 1. Spécifications Hardware

### Processeur

| Spécification | Détail |
|---------------|--------|
| **Modèle** | Intel N100 (Alder Lake-N) |
| **Génération** | 12th gen (2023) |
| **Architecture** | x86-64, 10nm Enhanced SuperFin |
| **Cores / Threads** | 4C / 4T (E-cores uniquement) |
| **Fréquence Base** | 0.8 GHz |
| **Fréquence Turbo** | 3.4 GHz (single-core) |
| **Cache** | 6 MB Intel Smart Cache |
| **TDP** | 6W (configurable jusqu'à 15W) |
| **Node fabrication** | Intel 7 (10nm ESF) |

**Instruction Sets** :
- SSE4.1, SSE4.2, AVX, AVX2
- AES-NI (encryption hardware)
- SHA extensions

**Performance Relative** :
- **~2x plus rapide** que Celeron N5105 (génération précédente)
- **~30% de Ryzen 5 7640HS** (single-thread)
- **~15% de Ryzen 5 7640HS** (multi-thread)

### GPU Intégré

| Spécification | Détail |
|---------------|--------|
| **Modèle** | Intel UHD Graphics (Gen 12) |
| **Execution Units** | 24 EUs |
| **Fréquence** | 300 MHz - 750 MHz |
| **API Support** | DirectX 12.1, OpenGL 4.6, Vulkan 1.3 |
| **Displays** | Max 3 displays simultanés |
| **Résolution Max** | 4K@60Hz (HDMI 2.0) |

**QuickSync Video (Génération 12)** :
- Encode/Decode H.264 (AVC) : Oui ✅
- Encode/Decode H.265 (HEVC) : Oui ✅ (10-bit)
- Encode/Decode VP9 : Oui ✅
- Encode/Decode AV1 : **Oui ✅** (décode uniquement)
- Qualité : Excellente (présets rapides)

**Implications pour Immich** :
- ✅ Thumbnails vidéo hardware-accelerated
- ✅ Transcoding H.264/HEVC sans charge CPU
- ✅ Génération 12 = qualité comparable dédiés GPU

### Mémoire RAM

| Spécification | Détail |
|---------------|--------|
| **Capacité** | 8 GB |
| **Type** | DDR5 SDRAM |
| **Fréquence** | 4800 MT/s |
| **Channels** | Single-channel (SODIMM) |
| **Bande passante** | ~38.4 GB/s |
| **Extensible** | Oui, jusqu'à 16 GB (slot libre) |

**Comparaison DDR5 vs DDR4** :
- Bande passante : **+50%** vs DDR4-3200
- Latence : Similaire (compensée par vitesse)
- Efficacité éner génie : **-20%** consommation

**Implications pour ML (Immich)** :
- ✅ TensorFlow Lite profite haute bande passante
- ✅ Matrices ML chargées rapidement
- ⚠️ Single-channel limite performance vs dual-channel

### Stockage

#### Baies Disques

| Spécification | Détail |
|---------------|--------|
| **Baies 3.5"** | 2x SATA III (6 Gbps) |
| **Configuration** | RAID 1 (miroir) |
| **Capacité Brute** | 2x 4 TB = 8 TB |
| **Capacité Utile** | 3.6 TB (RAID 1) |
| **Filesystem** | Btrfs |

**Disques installés** : (À documenter - modèle exact inconnu)
- Type : HDD 3.5" 7200 RPM (supposé)
- Interface : SATA III 6 Gbps
- Cache : 128-256 MB typique

#### Cache NVMe

| Spécification | Détail |
|---------------|--------|
| **Slot M.2** | 1x NVMe PCIe 3.0 x2 |
| **Capacité** | 1 TB |
| **Allocation Cache** | 500 GB (lecture) |
| **Performance** | ~1500 MB/s read, ~1000 MB/s write (estimé PCIe 3.0 x2) |

**Rôle Cache** :
- Lecture (read cache) : Accélère accès fichiers fréquents
- Métadonnées Btrfs : Accélère traversée filesystem
- Docker layers : Accélère pull/start conteneurs

### Réseau

| Spécification | Détail |
|---------------|--------|
| **Ethernet** | 2x RJ45 2.5 Gigabit |
| **Chipset** | Realtek RTL8125B (supposé) |
| **Link Aggregation** | Oui (LACP supporté) |
| **Jumbo Frames** | Oui (MTU 9000) |

**Configuration Actuelle** :
- 1 port utilisé : 192.168.10.5/24
- Gateway : 192.168.10.1 (OPNsense)
- DNS : 192.168.10.2 (AdGuard Home)

**Performance NFS Théorique** :
- Single link : ~295 MB/s (2.5 Gbit/s)
- Latence typique : 0.5-2 ms (LAN)

### Connectique

| Port | Quantité | Usage |
|------|----------|-------|
| USB 3.2 Gen 1 (5 Gbps) | 2x Type-A | Périphériques / Backup externe |
| HDMI 2.0 | 1x | Display (rarement utilisé NAS) |
| RJ45 2.5G | 2x | Réseau (1 actif, 1 backup) |
| Power DC | 1x | Alimentation 12V/5A (60W max) |

---

## 2. Caractéristiques Système

### Firmware UGOS

**Version** : (À documenter - vérifier via web UI)
**Base** : Linux Debian/Ubuntu modifié
**Interface** : Web UI propriétaire UGREEN

**Fonctionnalités Clés** :
- ✅ Gestion RAID (0, 1, JBOD)
- ✅ Snapshots Btrfs
- ✅ Partages SMB/NFS/AFP
- ✅ Docker intégré
- ✅ Task Scheduler (cron-like)
- ✅ DLNA Media Server
- ⚠️ Pas de SSH natif (activation manuelle requise)

### Système de Fichiers Btrfs

**Caractéristiques** :
```
Filesystem: Btrfs
RAID Level: raid1 (mirror)
Devices: /dev/sda1, /dev/sdb1
Data profile: RAID1
Metadata profile: RAID1
```

**Avantages Btrfs** :
- ✅ Snapshots instantanés (Copy-on-Write)
- ✅ Compression transparente (lzo, zstd)
- ✅ Checksums données + métadonnées (détection corruption)
- ✅ Self-healing (corrige erreurs via miroir)
- ✅ Quota par subvolume

**Snapshot Strategy** :
- Fréquence : Quotidien 04:00 AM (via UGOS scheduler)
- Rétention : 7 daily, 4 weekly, 3 monthly
- Stockage : Local uniquement (même pool)

---

## 3. Consommation Énergétique

### Mesures Estimées

| État | Consommation | Note |
|------|-------------|------|
| **Idle** (disques spin-down) | ~8-12W | N100 très efficace (6W TDP) |
| **Actif** (I/O léger) | ~15-20W | Disques HDD ~5-7W chacun |
| **Charge Max** (rebuild RAID) | ~35-40W | Pic CPU + disques + ventilateurs |

**Coût Électrique Annuel** :
```
Moyenne : 18W × 24h × 365j = 157.7 kWh/an
Tarif : 0.25€/kWh (Europe moyenne)
Coût annuel : ~39€
```

**Comparaison** :
- Synology DS920+ (similaire) : ~30-35W
- QNAP TS-453D : ~40-45W
- **UGREEN DXP2800 : 15-20W** ✅ (plus efficace)

### Mode Économie d'Énergie

**Configuration UGOS** :
- Spin-down HDD : Après 15 min inactivité
- Veille réseau : Wake-on-LAN activé
- LEDs : Auto off 23:00, on 09:00 (via Ansible)

**Impact** :
- Économie : ~3-5W pendant spin-down (nuit)
- Latence réveil : ~3-5s (premier accès fichier)

---

## 4. Performance Benchmarks

### CPU (Intel N100)

**Geekbench 5** (estimé) :
- Single-Core : ~1100-1200
- Multi-Core : ~3000-3200

**Comparaison** :
```
Intel N100 (DXP2800)    : 1150 SC, 3100 MC
Celeron N5105 (ancien)  : 580 SC, 1800 MC  (2x moins rapide)
Ryzen 5 7640HS (NUC)    : 2100 SC, 11500 MC (3.5x plus rapide)
```

### Stockage (HDD RAID 1 + Cache NVMe)

**Sequential Read** :
- HDD seul : ~180-220 MB/s
- Avec cache NVMe (hit) : ~1200-1500 MB/s
- Ratio speedup : **6-8x**

**Sequential Write** :
- HDD RAID 1 : ~160-200 MB/s
- Limité par vitesse HDD (pas de write cache)

**Random 4K IOPS** :
- HDD : 80-120 IOPS
- NVMe cache : 15000-20000 IOPS
- Ratio speedup : **~150x**

**Implications** :
- ✅ Fichiers fréquents (configs, DB) : Ultra rapides (cache)
- ⚠️ Gros fichiers (vidéos) : Vitesse HDD (pas cachés)
- ✅ Métadonnées : Très rapides (Btrfs sur cache)

### Réseau (NFS Performance)

**iperf3 Tests** (théorique) :
```
LAN 1G → NAS 2.5G : ~950 Mbps (~118 MB/s)
LAN 2.5G → NAS 2.5G : ~2.3 Gbps (~287 MB/s)
```

**NFS Real-World** :
- Small files (<1 MB) : 50-100 MB/s (métadonnées overhead)
- Large files (>100 MB) : 200-250 MB/s
- Latence : 1-3 ms (LAN gigabit)

**Bottleneck** : HDD write (~180 MB/s) limite transferts gros fichiers.

---

## 5. Capacités Compute pour Services

### Profil Actuel (Stockage Uniquement)

**Services Déployés** :
- SMB/NFS servers (natif UGOS)
- Rclone backup (Docker, ~200 MB RAM)
- LED control (script cron, ~50 MB RAM)

**Utilisation** :
- CPU : <5% idle, pics 20-30% pendant scrubs Btrfs
- RAM : ~400-500 MB / 8 GB (94% libre!)
- Disques : ~1.2 TB / 3.6 TB (67% libre)

### Capacités Disponibles pour Docker

**RAM Disponible** : ~7 GB
**CPU Disponible** : ~3 cores (réserver 1 core pour UGOS)

**Workloads Possibles** :

| Service | RAM | CPU | Verdict |
|---------|-----|-----|---------|
| **Immich** | 6 GB | 2-3 cores | ✅ **Viable** (ML lent mais acceptable) |
| **Plex/Jellyfin** | 4-6 GB | 2-4 cores | ✅ Possible (QuickSync pour transcoding) |
| **PhotoPrism** | 4-6 GB | 2-3 cores | ✅ Similaire à Immich |
| **Nextcloud** | 2-4 GB | 1-2 cores | ✅ Excellent fit |
| **GitLab** | 4-8 GB | 2-4 cores | ⚠️ Tendu (8 GB limite) |
| **Elasticsearch** | 4-8 GB | 2-4 cores | ❌ Trop gourmand |

**Recommandation** : 1-2 services medium-weight max (ex: Immich seul OU Nextcloud+Photoprism).

### Limitations Hardware

❌ **Pas de VM** : UGOS ne supporte pas KVM/VirtualBox
❌ **Docker seulement** : Conteneurs uniquement
⚠️ **Pas de GPU ML** : QuickSync pour video seulement, pas TensorFlow GPU
⚠️ **Single-channel RAM** : Limite bande passante vs dual-channel
⚠️ **4 cores max** : Parallélisme limité

---

## 6. TensorFlow Lite Performance (Immich ML)

### Benchmarks Estimés

**Model Inférence** (mobilenet_v2) :

| Hardware | Temps 1 Image | Throughput |
|----------|---------------|------------|
| **Ryzen 5 7640HS** (6C/12T) | 1-2s | 30-60 img/min |
| **Intel N100** (4C/4T) | 5-8s | 8-12 img/min |
| **Raspberry Pi 5** (ARM) | 8-12s | 5-7 img/min |

**Ratio Performance** : N100 = **~30%** vitesse Ryzen 5

### Optimisations Possibles

1. **Quantization INT8** : Models 4x plus petits, 2x plus rapides
   ```python
   # Dans Immich config
   MACHINE_LEARNING_MODEL_PRECISION: "int8"
   ```

2. **Batch Processing** : Grouper images par lots
   ```python
   MACHINE_LEARNING_BATCH_SIZE: 4  # Au lieu de 1
   ```

3. **Threading Optimisé** :
   ```python
   IMMICH_MACHINE_LEARNING_WORKERS: 2  # Limiter à 2 threads
   TENSORFLOW_NUM_THREADS: 4  # Utiliser 4 cores
   ```

4. **Cache Agressif** :
   ```python
   # Activer caching embeddings
   IMMICH_CACHE_ML_EMBEDDINGS: true
   ```

**Gain Attendu** : 1.5-2x speedup avec optimisations.

---

## 7. Monitoring et Santé Disques

### S.M.A.R.T Monitoring

**Scrutiny Architecture** :
```
┌─────────────────────────────────┐
│ NAS Cargo (192.168.10.5)       │
│  └─ Scrutiny Collector (Docker)│
│      └─ Lit S.M.A.R.T via       │
│         smartctl (smartmontools)│
└─────────────────────────────────┘
           ↓ HTTP POST
┌─────────────────────────────────┐
│ Raspberry Pi (192.168.10.2)     │
│  └─ Scrutiny Web (Dashboard)    │
│      └─ Affiche état disques    │
└─────────────────────────────────┘
```

**Métriques S.M.A.R.T Surveillées** :
- Reallocated Sectors Count
- Current Pending Sector Count
- Offline Uncorrectable Sectors
- Temperature
- Power-On Hours
- Start/Stop Count

**Alertes Critiques** :
- Reallocated sectors > 10 → ⚠️ Disque en fin de vie
- Temperature > 55°C → 🔥 Surchauffe
- Pending sectors > 5 → ❌ Erreurs lecture

### Températures Opérationnelles

**Plages Normales** :
```
CPU (N100)       : 35-55°C idle, 60-75°C charge
HDD              : 30-45°C (optimal 35-40°C)
Chipset          : 40-60°C
Case ambient     : 25-35°C
```

**Refroidissement** :
- 1x ventilateur 80mm arrière (PWM)
- Grilles ventilation latérales
- Airflow : Front → Back

---

## 8. Scénarios d'Upgrade Futur

### Upgrade 1 : RAM 8 GB → 16 GB

**Coût** : ~50-80€ (SODIMM DDR5 4800 8GB)
**Gain** :
- ✅ Immich + Nextcloud simultanément
- ✅ Marge confortable (50% libre)
- ✅ Pas de risque OOM

**Installation** : Physique (ouvrir boîtier, slot libre)

### Upgrade 2 : Ajout NVMe 2 TB

**Coût** : ~100-150€
**Gain** :
- ✅ Cache 1 TB → 2 TB (plus de fichiers hot)
- ✅ Possibilité pool Btrfs avec tiering

### Upgrade 3 : Remplacement HDD par SSD

**Coût** : ~400-600€ (2x SSD 4TB)
**Gain** :
- ✅ Performance I/O **x10-20**
- ✅ Latence < 1ms (vs 10-15ms HDD)
- ✅ Silence total
- ✅ Consommation -5W

**Pertinence** : Dépend budget vs bénéfice (HDD suffisant pour homelab).

### Upgrade 4 : Réseau 10 GbE

**Prérequis** : Switch 10G + carte réseau 10G
**Coût** : ~300€ total
**Gain** :
- ✅ Transferts **x4** (1 GB/s au lieu de 250 MB/s)
- ⚠️ Limité par HDD write (~200 MB/s)

**Pertinence** : Faible (bottleneck HDD, pas réseau).

---

## 9. Comparaison avec Alternatives

### UGREEN DXP2800 vs Synology DS224+

| Critère | UGREEN DXP2800 | Synology DS224+ |
|---------|----------------|-----------------|
| **CPU** | Intel N100 (4C, 3.4 GHz) | Intel Celeron J4125 (4C, 2.7 GHz) |
| **RAM** | 8 GB DDR5 | 2 GB DDR4 (extensible 6 GB) |
| **Prix** | ~300-350€ | ~350-400€ |
| **Firmware** | UGOS (limité) | DSM (très mature) |
| **Apps** | Docker générique | Package Center riche |
| **Support** | Communauté | Officiel Synology |
| **Performance** | **+30% CPU, +4x RAM** ✅ | Écosystème supérieur |

**Verdict** : UGREEN = meilleur rapport perf/prix, Synology = écosystème.

### UGREEN DXP2800 vs Build Custom (Mini PC + USB)

| Critère | UGREEN DXP2800 | Mini PC (ex: Beelink) |
|---------|----------------|----------------------|
| **Intégration** | Tout-en-un ✅ | DIY (Mini PC + boîtier disques) |
| **Hot-swap** | Oui ✅ | Non (USB externe) |
| **RAID Hardware** | Oui (firmware) | Logiciel (mdadm/ZFS) |
| **Consommation** | 15-20W | 20-35W |
| **Prix** | 300-350€ (disques non inclus) | 250€ (Mini PC) + 100€ (boîtier) |
| **Flexibilité** | Limitée (UGOS) | Totale (Linux/TrueNAS) ✅ |

**Verdict** : UGREEN = simplicité, Custom = contrôle total.

---

## 10. Recommandations d'Utilisation

### ✅ Excellents Use Cases

1. **Stockage Centralisé** : Rôle principal, optimal
2. **Backup Target** : Rclone, Borg, rsync
3. **Media Server** (léger) : Photos, musique (pas 4K transcoding 24/7)
4. **Immich** : Viable avec expectations réalistes (indexation lente OK)
5. **Nextcloud** : Excellent fit (files + contacts + calendar)

### ⚠️ Use Cases Acceptables avec Limites

1. **Jellyfin/Plex** : Transcoding limité (1-2 streams 1080p max via QuickSync)
2. **Docker Stacks** : 1-2 services medium-weight simultanés
3. **Home Automation** : Possible mais RPi plus adapté (toujours on)

### ❌ Use Cases Déconseillés

1. **Databases Production** : MySQL/Postgres haute charge (I/O HDD limité)
2. **Virtualisation** : KVM/Proxmox non supporté
3. **Compute Intensif** : Encodage vidéo 4K massivement parallèle
4. **Services Critiques 24/7** : Préférer hardware dédié (uptime)

---

## Références

- Datasheet Intel N100 : [ark.intel.com](https://ark.intel.com/content/www/us/en/ark/products/231803/intel-processor-n100-6m-cache-up-to-3-40-ghz.html)
- QuickSync Support Matrix : [Intel Media SDK](https://www.intel.com/content/www/us/en/developer/articles/technical/quick-sync-video-features-by-generation.html)
- UGREEN DXP2800 Manuel : [ugreen.com](https://www.ugreen.com/products/ugreen-dxp2800-2-bay-nas)
- Btrfs Documentation : [btrfs.wiki.kernel.org](https://btrfs.wiki.kernel.org)
- Plan Migration : `docs/architecture/migration-plan.md`
- Services Status : `docs/services-status.md`
