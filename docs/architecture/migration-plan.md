# 🚀 Plan de Déploiement et Architecture des Services

## 1. Contexte et Objectifs

### Situation Actuelle

**État actuel** : Infrastructure homelab en phase de déploiement initial.

- **Proxmox VE** : Seule la VM 100 (OPNsense) est déployée - **84% RAM libre** (27 GB / 32 GB)
- **Raspberry Pi 5** : Services critiques + stack observabilité déployés - **44% RAM utilisée** (3.5 GB / 8 GB)

**Ressources disponibles** :

- Raspberry Pi 5 : 8 GB RAM, ~4.5 GB libres pour nouveaux services
- NAS Cargo : Intel N100 + 8 GB DDR5, ~7.5 GB libres (actuellement stockage uniquement)
- Proxmox : 32 GB RAM, ~27 GB libres pour déploiement VMs/LXCs

**Objectifs du déploiement** :

1. ✅ Déployer stack observabilité complète (Grafana/Prometheus/Loki) sur Raspberry Pi
2. 📋 Créer infrastructure Proxmox (VMs pour Media & Downloads, LXCs pour services)
3. 📋 Maintenir résilience (services critiques DNS/Domotique sur Raspberry Pi)
4. 📋 Optimiser allocation RAM selon besoins réels
5. 📋 Préparer scalabilité future avec possibilité de migration vers NAS

---

## 2. Architecture Cible

### Raspberry Pi 5 (8 GB RAM)

```
┌─────────────────────────────────────────────────────────┐
│ SERVICES CRITIQUES (Actuels - 800 MB)                  │
│  ├─ AdGuard Home              (~200 MB)                 │
│  ├─ Home Assistant            (~500 MB)                 │
│  ├─ Homepage                  (~100 MB)                 │
│  └─ Tailscale                 (~50 MB)                  │
│                                                          │
│ OBSERVABILITÉ (Nouveau - 2.3 GB)                        │
│  ├─ Grafana                   (~300 MB)                 │
│  ├─ Prometheus                (~1.5 GB)                 │
│  │   └─ Retention: 15 jours                             │
│  ├─ Loki                      (~500 MB)                 │
│  │   └─ Retention: 30 jours                             │
│  └─ Promtail                  (~50 MB)                  │
│                                                          │
│ MONITORING (Nouveau - 500 MB)                           │
│  ├─ Uptime Kuma               (~200 MB)                 │
│  ├─ Scrutiny Web              (~150 MB)                 │
│  ├─ Dozzle                    (~100 MB)                 │
│  └─ Diun                      (~50 MB)                  │
│                                                          │
│ PRODUCTIVITY (Migration - 3 GB)                         │
│  ├─ Paperless-ngx             (~2.5 GB)                 │
│  └─ Stirling-PDF              (~500 MB)                 │
│                                                          │
│ TOTAL UTILISÉ : ~6.6 GB / 8 GB (17% marge)             │
└─────────────────────────────────────────────────────────┘
```

**Services déployés** : 15 conteneurs Docker
**RAM Peak estimée** : 7.2 GB (avec buffers)
**Marge sécurité** : 800 MB (~10%)

### NAS Cargo (Intel N100 + 8 GB DDR5)

```
┌─────────────────────────────────────────────────────────┐
│ STOCKAGE (Actuel)                                       │
│  ├─ Partages NFS (appdata, media, photos, backups)     │
│  ├─ Rclone → Backblaze B2     (~200 MB)                │
│  └─ LED Control               (~50 MB)                  │
│                                                          │
│ MONITORING (Actuel)                                     │
│  └─ Scrutiny Collector        (~100 MB)                 │
│                                                          │
│ MEDIA (Migration - 6 GB)                                │
│  └─ Immich                    (~6 GB)                   │
│      ├─ Machine Learning (TensorFlow Lite)             │
│      ├─ Reconnaissance faciale                          │
│      ├─ Classification objets                           │
│      └─ Recherche sémantique                            │
│                                                          │
│ TOTAL UTILISÉ : ~6.4 GB / 8 GB (20% marge)             │
└─────────────────────────────────────────────────────────┘
```

**Note** : Immich utilisera QuickSync (Intel UHD Graphics Gen 12) pour thumbnails vidéo.

### GMKtec NucBox M6 (Proxmox - 32 GB)

```
┌─────────────────────────────────────────────────────────┐
│ VM 100 - OPNsense             : 2 GB (inchangé)        │
│   └─ Routeur/Firewall/DHCP                             │
│                                                          │
│ VM 110 - Media Stack          : 8 GB (↓ de 14 GB)     │
│   ├─ Jellyfin                 (~6 GB)                   │
│   │   └─ GPU Passthrough AMD Radeon 760M               │
│   └─ Overseerr                (~2 GB)                   │
│                                                          │
│ VM 120 - Downloads            : 8 GB (↑ de 6 GB)      │
│   ├─ Gluetun + qBittorrent    (~4 GB)                   │
│   └─ Radarr/Sonarr/Prowlarr/Bazarr (~4 GB)            │
│                                                          │
│ LXC 200 - Infrastructure      : 4 GB (inchangé)        │
│   ├─ Nginx Proxy Manager      (~512 MB)                 │
│   ├─ Authentik                (~2.5 GB)                 │
│   └─ Bitwarden                (~512 MB)                 │
│                                                          │
│ LXC 210 - Productivity        : 0 GB (SUPPRIMÉ ✂️)     │
│                                                          │
│ Host Proxmox                  : 10 GB (↑ de 3 GB)     │
│   └─ Cache massif pour I/O NFS                         │
│                                                          │
│ TOTAL UTILISÉ : 32 GB                                   │
│   ├─ VMs/LXCs : 22 GB                                   │
│   └─ Host : 10 GB                                       │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Détails des Déploiements

### Option Future : Immich sur NAS Cargo (vs VM 110)

#### Analyse Performance

| Métrique                     | VM 110 (Ryzen 5 7640HS) | NAS (Intel N100) | Ratio             |
| ---------------------------- | ----------------------- | ---------------- | ----------------- |
| **ML Inférence** (1 photo)   | 1-2s                    | 5-8s             | 3-5x plus lent ⚠️ |
| **Indexation** (1000 photos) | 10-15 min               | 30-50 min        | 3-4x plus lent ⚠️ |
| **Thumbnails** (hardware)    | AMD VCE                 | QuickSync Gen 12 | Similaire ✅      |
| **Recherche sémantique**     | Instantanée             | 2-3s             | Acceptable ✅     |
| **Upload processing**        | Temps réel              | 5-10s            | Acceptable ✅     |

#### Verdict

✅ **Déploiement sur NAS viable** si usage photos ponctuel (10-50 photos/semaine)
❌ **Non recommandé** si upload quotidien massif (100+ photos/jour)
📋 **Recommandation actuelle** : Déployer d'abord sur VM 110, migrer vers NAS si besoin de RAM

#### Avantages Déploiement sur NAS

1. **Proximité stockage** : Photos déjà sur NAS `/volume1/photos` → I/O direct
2. **Libération RAM Proxmox** : +6 GB pour VM 110
3. **CPU moderne** : N100 (2023, Alder Lake-N) vs Celeron ancien
4. **QuickSync Gen 12** : Hardware encoding H264/HEVC efficace
5. **DDR5** : Bande passante élevée pour ML

#### Inconvénients à Accepter

⚠️ **Performance ML dégradée** :

- Reconnaissance faciale 3-5x plus lente
- Indexation initiale 1-2h au lieu de 15-20min
- Acceptable si bibliothèque statique/croissance lente

⚠️ **Charge CPU NAS** :

- Risque saturation pendant indexation
- Peut impacter latence NFS temporairement

#### Configuration Immich sur NAS

```yaml
# docker-compose.yml sur NAS Cargo
services:
  immich-server:
    image: ghcr.io/immich-app/immich-server:release
    environment:
      # Limiter charge CPU
      IMMICH_MACHINE_LEARNING_WORKERS: 2 # Au lieu de 4
      IMMICH_THUMBNAIL_WORKERS: 2
    volumes:
      - /volume1/photos:/usr/src/app/upload
      - /volume1/appdata/immich:/usr/src/app/upload/library
    deploy:
      resources:
        limits:
          cpus: "3" # Réserver 1 core pour UGOS
          memory: 6G # Max 6 GB sur 8 GB
```

#### Étapes Déploiement Initial (VM 110 - Recommandé)

1. **Créer VM 110** sur Proxmox

   ```bash
   ssh pve
   # Créer VM avec Ubuntu Server
   # 6 vCPU, 14 GB RAM, 100 GB stockage
   # Configurer GPU passthrough AMD Radeon 760M
   ```

2. **Déployer stack Docker** avec Jellyfin + Immich + Overseerr

3. **Alternative : Déploiement sur NAS** (si VM 110 non créée)

   ```bash
   # Créer playbook deploy_nas_immich.yml
   ansible-playbook playbooks/deploy_nas_immich.yml
   ```

4. **Restaurer config**

   ```bash
   ssh 192.168.10.5
   docker exec immich-server immich-cli restore /backup/immich-backup.tar.gz
   ```

5. **Tester accès web**

   ```
   http://192.168.10.5:2283
   ```

6. **Mettre à jour Nginx Proxy Manager** (LXC 200)

   ```
   immich.blackbox.homes → 192.168.10.5:2283 (au lieu de VM 110)
   ```

7. **Supprimer Immich de VM 110**

   ```bash
   # Modifier docker-compose.yml VM 110
   # Retirer services immich-*
   docker compose up -d
   ```

8. **Réduire RAM VM 110** : 14 GB → 8 GB
   ```bash
   ssh pve.blackbox.homes
   qm set 110 --memory 8192
   ```

### Déploiement 2 : Paperless + Stirling-PDF (LXC 210 ou RPi 5)

#### Analyse Performance ARM

| Service                       | x86 (LXC 210) | ARM (RPi 5) | Impact          |
| ----------------------------- | ------------- | ----------- | --------------- |
| **Paperless OCR** (Tesseract) | ~30s/page     | ~60s/page   | 2x plus lent ⚠️ |
| **Stirling PDF**              | Temps réel    | Temps réel  | Similaire ✅    |
| **Indexation**                | Rapide        | Moyenne     | Acceptable ✅   |

#### Verdict

✅ **Déploiement sur RPi viable** si utilisation occasionnelle (quelques documents/mois)
⚠️ **Acceptable** si utilisation régulière (10-20 docs/mois)
❌ **Non recommandé** si scan quotidien massif (50+ pages/jour)
📋 **Recommandation actuelle** : Déployer sur LXC 210 Proxmox pour meilleures performances

#### Avantages Déploiement sur RPi

1. **Libération RAM Proxmox** : +3 GB
2. **Images ARM natives** : LinuxServer.io maintient images ARM64
3. **Raspberry Pi sous-utilisé** : 7.2 GB libres actuellement

#### Étapes Déploiement (LXC 210 - Recommandé)

1. **Créer LXC 210** sur Proxmox

   ```bash
   ssh pve
   # Créer LXC Debian 12 unprivileged
   # 2 vCPU, 3 GB RAM, 30 GB stockage
   # Activer nesting=1 pour Docker
   ```

2. **Déployer Paperless + Stirling-PDF** via Docker

#### Alternative : Déploiement sur RPi

1. **Ajouter services au docker-compose RPi**

   ```bash
   # Éditer ansible/templates/rpi/docker-compose.yml.j2
   vim ansible/templates/rpi/docker-compose.yml.j2
   # Ajouter sections paperless + stirling-pdf
   ```

2. **Déployer sur RPi**

   ```bash
   ansible-playbook playbooks/deploy_rpi_stack.yml
   ```

3. **Restaurer données**

   ```bash
   ssh control-tower.blackbox.homes
   docker exec paperless document_importer /backup
   ```

4. **Supprimer LXC 210**
   ```bash
   ssh pve.blackbox.homes
   pct stop 210
   pct destroy 210
   ```

### Déploiement 3 : Stack Observabilité (RPi 5) ✅ EN COURS

#### Services Déployés

**Grafana** : ✅ Conteneur actif et configuré

- Port : 3001
- Datasources : Prometheus + Loki configurés
- Dashboard 1860 (Node Exporter Full) importé

**Prometheus** : ✅ Conteneur actif et configuré

- Port : 9090
- Scrape targets : Node Exporter sur RPi, Proxmox, NAS Cargo
- Retention : 15 jours

**Loki** : ✅ Conteneur actif

- Port : 3100
- Retention : 30 jours (720h configuré)

**Promtail** : ✅ Conteneur actif

- Collecte logs Docker sur Raspberry Pi
- Envoie vers Loki

**Node Exporter** : ✅ Déployé sur tous hôtes

- RPi : 192.168.10.2:9100
- Proxmox : 192.168.10.10:9100
- NAS Cargo : 192.168.10.5:9100

#### Playbook Disponible

✅ **Playbook créé** : `ansible/playbooks/deploy_observability_stack.yml`
✅ **Templates créés** :

- `ansible/templates/rpi/prometheus.yml.j2`
- `ansible/templates/rpi/loki.yml.j2`
- `ansible/templates/rpi/docker-compose.yml.j2` (mise à jour avec stack observabilité)

**Pour déployer** :

```bash
cd /home/rvph/Projects/blackbox/ansible
ansible-playbook playbooks/deploy_observability_stack.yml
```

**État actuel** :

1. ✅ Conteneurs Grafana/Prometheus/Loki/Promtail lancés
2. ✅ Node Exporter déployé sur tous hôtes (RPi, Proxmox, NAS)
3. ✅ Datasources Grafana configurés
4. ✅ Dashboard 1860 (Node Exporter Full) importé
5. 📋 Configurer alerting (à faire)
6. 📋 Ajouter dashboards additionnels (Docker, Proxmox)

#### Dashboards Grafana Recommandés

1. **Proxmox Overview**

   - CPU/RAM/Disk par node
   - VMs/LXCs status
   - Network throughput

2. **Docker Containers**

   - Resource usage par conteneur
   - Restart count
   - Logs errors

3. **Network**

   - WAN throughput (depuis OPNsense)
   - Latency monitoring
   - DNS queries (AdGuard)

4. **Backups**
   - Last successful backup time
   - B2 sync status
   - Proxmox VZDump status

---

## 4. Progression du Déploiement

### Allocation RAM Actuelle vs Cible

| Machine          | Actuel | Après Déploiement Complet | Évolution             |
| ---------------- | ------ | ------------------------- | --------------------- |
| **Proxmox Host** | 3 GB   | 3-10 GB                   | Cache ajustable       |
| **VM 110**       | 0 GB   | 14 GB                     | +14 GB (à créer)      |
| **VM 120**       | 0 GB   | 6 GB                      | +6 GB (à créer)       |
| **LXC 200**      | 0 GB   | 4 GB                      | +4 GB (à créer)       |
| **LXC 210**      | 0 GB   | 3 GB (optionnel)          | +3 GB (à créer)       |
| **Raspberry Pi** | 3.5 GB | 6.6 GB (avec Promtail)    | +3.1 GB services      |
| **NAS Cargo**    | 0.5 GB | 0.5-6.5 GB                | +6 GB si Immich migré |

### Bénéfices du Déploiement

1. **Observabilité Complète** : ✅ EN COURS

   - Métriques temps réel (Prometheus) ✅ Actif
   - Logs centralisés (Loki) ✅ Actif
   - Dashboards visuels (Grafana) ✅ Actif
   - Alerting proactif 📋 À configurer

2. **Résilience Maintenue** :

   - Services critiques (DNS, domotique, monitoring) sur RPi ✅
   - Accessible même si Proxmox down ✅
   - Diagnostics possibles pendant pannes ✅

3. **Scalabilité** :
   - 27 GB RAM libres sur Proxmox pour VMs/LXCs
   - 4.5 GB RAM libres sur RPi pour services légers
   - Architecture modulaire permettant flexibilité

---

## 5. Risques et Mitigations

### Risque 1 : Performance Services sur NAS

**Impact** : Services (ex: Immich) pourraient être trop lents sur Intel N100.

**Mitigation** :

- ✅ Déployer d'abord sur VM 110 Proxmox (recommandé)
- ✅ Tester performance avant migration éventuelle vers NAS
- ✅ Garder option retour VM si NAS insuffisant

### Risque 2 : Saturation CPU NAS

**Impact** : Latence NFS augmentée pendant indexation Immich.

**Mitigation** :

- ✅ Limiter threads ML Immich (config `WORKERS: 2`)
- ✅ Limiter CPU via Docker (`cpus: '3'`)
- ✅ Monitoring Prometheus : Alertes si CPU > 90%

### Risque 3 : OCR Paperless Lent sur ARM

**Impact** : Frustration utilisateur si scan prend 2x plus de temps.

**Mitigation** :

- ✅ Tester performance avec documents types
- ✅ Si inacceptable : Garder Paperless sur LXC 210
- ✅ Alternative : Migrer seulement Stirling-PDF vers RPi

### Risque 4 : RAM Overflow Raspberry Pi

**Impact** : Crash services si pic RAM > 8 GB.

**Mitigation** :

- ✅ Monitoring Prometheus : Alertes si RAM > 90%
- ✅ Swap 2 GB configuré (urgence seulement)
- ✅ Limites Docker `memory: XG` sur chaque service

### Risque 5 : Données Corrompues Pendant Migration

**Impact** : Perte données Immich ou Paperless.

**Mitigation** :

- ✅ Backup complet avant migration (Rclone B2)
- ✅ Snapshot Proxmox VMs avant arrêt
- ✅ Validation intégrité post-migration
- ✅ Rollback plan testé

---

## 6. Timeline d'Implémentation

### Phase 1 : Stack Observabilité ✅ COMPLÉTÉ

- [x] Créer playbook `deploy_observability_stack.yml`
- [x] Créer templates Prometheus/Loki configs
- [x] Déployer Grafana/Prometheus/Loki sur RPi
- [x] Démarrer Promtail
- [x] Installer Node Exporter sur tous hôtes (RPi, Proxmox, NAS)
- [x] Configurer datasources Grafana (Prometheus + Loki)
- [x] Importer dashboard 1860 (Node Exporter Full)
- [ ] Configurer alerting (optionnel)
- [ ] Importer dashboards additionnels (Docker, Proxmox)

**Statut** : ✅ Stack observabilité opérationnelle et fonctionnelle

### Phase 2 : Infrastructure Proxmox (Prochaine priorité)

- [ ] Créer VM 110 (Media Stack) - Jellyfin + Immich + Overseerr
- [ ] Créer LXC 200 (Infrastructure) - NPM + Authentik + Bitwarden
- [ ] Créer VM 120 (Download Stack) - \*Arr + Gluetun + qBittorrent
- [ ] Configurer GPU passthrough pour VM 110
- [ ] Configurer VPN Gluetun pour VM 120

**Risque** : Moyen (nouvelles VMs/LXCs à créer)

### Phase 3 : Services Additionnels (Optionnel)

- [ ] Déployer LXC 210 (Productivity) sur Proxmox ou RPi
- [ ] Déployer services monitoring (Uptime Kuma, Scrutiny, Dozzle, Diun)
- [ ] Configurer checks services
- [ ] Intégrer avec Grafana

**Risque** : Faible

### Phase 4 : Migration Optionnelle Immich (Si besoin RAM Proxmox)

- [ ] Tester Immich sur NAS (bibliothèque test)
- [ ] Mesurer performances réelles
- [ ] Décision migration si performances acceptables
- [ ] Backup + migration complète si GO
- [ ] Validation intégrité données

**Risque** : Moyen (rollback possible)
**Note** : Migration uniquement si VM 110 manque de RAM

### Phase 5 : Finalisation

- [ ] Tests end-to-end tous services déployés
- [ ] Validation performances
- [ ] Mise à jour documentation
- [ ] Configuration alerting complet

**Risque** : Très faible

---

## 7. Plan de Rollback

### Rollback Immich (NAS → VM 110)

**Si migration vers NAS a été faite et performance inacceptable :**

```bash
# 1. Arrêter Immich sur NAS
ssh cargo
docker compose down

# 2. Restaurer sur VM 110
ssh vm110
cd /opt/media-stack
# Restaurer config depuis backup
docker compose up -d immich-server immich-ml immich-web

# 3. Remettre RAM VM 110 si nécessaire
ssh pve
qm set 110 --memory 14336

# 4. Mettre à jour Nginx Proxy
# immich.blackbox.homes → VM 110:2283
```

**Temps rollback** : 30-60 minutes
**Note** : Ne s'applique que si migration NAS effectuée

### Suppression VMs/LXCs (Si erreur déploiement)

```bash
# Supprimer VM
ssh pve
qm stop <VMID>
qm destroy <VMID>

# Supprimer LXC
pct stop <CTID>
pct destroy <CTID>
```

**Temps rollback** : 5-10 minutes

---

## 8. Monitoring Post-Déploiement

### Métriques à Surveiller

**Proxmox** :

- Cache hit rate (doit augmenter après +7 GB cache)
- I/O wait (doit diminuer)
- RAM usage host

**Raspberry Pi** :

- RAM usage (seuil alerte : >90%)
- CPU load (seuil : >3.0)
- Température (seuil : >70°C)

**NAS Cargo** :

- CPU usage pendant indexation Immich (seuil : <90%)
- RAM usage (seuil : <7 GB)
- Latence NFS (doit rester <10ms)

**Immich Performance** :

- Temps indexation photos (baseline : documenter avant/après)
- Temps recherche sémantique
- Feedback utilisateur subjectif

### Dashboards Grafana

**Dashboard "Migration Health"** :

- RAM usage par machine (gauge)
- CPU usage par machine (graph)
- Latence NFS (graph temps réel)
- Services status (table up/down)

---

## 9. Validation Succès

Le déploiement est considéré réussi si **TOUS** les critères sont remplis :

✅ **Observabilité** : COMPLÉTÉ

- [x] Grafana/Prometheus/Loki actifs
- [x] Promtail démarré et fonctionnel
- [x] Node Exporter déployé sur tous hôtes (RPi, Proxmox, NAS)
- [x] Dashboard 1860 (Node Exporter Full) importé
- [x] Datasources configurés
- [ ] Alertes configurées et testées (optionnel)
- [ ] Dashboards additionnels (Docker, Proxmox) - optionnel

✅ **Infrastructure Proxmox** : À FAIRE

- [ ] VM 100 (OPNsense) fonctionnelle ✅ (déjà fait)
- [ ] VM 110 (Media) créée et opérationnelle
- [ ] VM 120 (Download) créée et opérationnelle
- [ ] LXC 200 (Infrastructure) créé et opérationnel
- [ ] GPU passthrough VM 110 fonctionnel
- [ ] VPN Gluetun VM 120 fonctionnel

✅ **Stabilité** :

- [ ] Aucun crash service 7 jours post-déploiement
- [ ] RAM usage <90% sur toutes machines
- [ ] Pas de latence NFS > 50ms

✅ **Documentation** :

- [ ] `docs/services-status.md` à jour
- [ ] `docs/homelab.md` aligné
- [ ] Playbooks documentés

---

## 10. Prochaines Actions

### Priorité Immédiate

1. **Stack Observabilité** ✅ COMPLÉTÉ

   - [x] Grafana/Prometheus/Loki déployés
   - [x] Promtail démarré
   - [x] Node Exporter déployé sur tous hôtes
   - [x] Datasources Grafana configurés
   - [x] Dashboard 1860 importé
   - [ ] Alerting (optionnel)
   - [ ] Dashboards additionnels (optionnel)

2. **Créer Infrastructure Proxmox** 📋 PRIORITÉ ÉLEVÉE
   - [ ] Créer VM 110 (Media Stack)
   - [ ] Créer LXC 200 (Infrastructure)
   - [ ] Créer VM 120 (Download Stack)
   - [ ] Configurer GPU passthrough
   - [ ] Configurer VPN Gluetun

### Priorité Moyenne

3. **Services Additionnels**
   - [ ] Uptime Kuma, Scrutiny, Dozzle, Diun
   - [ ] LXC 210 (Productivity) - optionnel

### Optionnel (Si besoin)

4. **Migration Immich vers NAS**
   - Uniquement si VM 110 manque de RAM
   - Tester performances avant migration

---

## Références

- État actuel : `docs/services-status.md`
- Spécifications NAS : `docs/architecture/nas-specs.md`
- Allocation compute : `docs/architecture/compute-allocation.md`
- Architecture globale : `docs/homelab.md`
