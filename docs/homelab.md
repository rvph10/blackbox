# 🏗️ Document de Design Technique : Homelab "Nuke & Pave"

> **📊 État des Services** : Pour connaître précisément ce qui est déployé vs planifié, consultez [`docs/services-status.md`](services-status.md) (source de vérité).

> **🔄 Plan de Migration** : Architecture future et redistribution des services détaillées dans [`docs/architecture/migration-plan.md`](architecture/migration-plan.md).

## 1. Philosophie d'Architecture

- **Isolation Réseau :** Création d'un réseau Homelab dédié (Subnet `192.168.10.0/24`) isolé de la Box Proximus via une VM OPNsense en mode PPPoE Passthrough.
- **Cœur Virtualisé :** Le GMKtec NucBox M6 centralise le routage (OPNsense) et la puissance de calcul (Docker/LXC).
- **Accès Distant "Zéro Trust" :** Utilisation de la stratégie "DNS Public / IP Privée". Les services (Jellyfin, etc.) disposent d'un nom de domaine HTTPS valide (`*.blackbox.homes`) mais ne sont accessibles que via le réseau Mesh Tailscale, sans ouverture de ports.
- **Résilience des Services de Base :** Le DNS (AdGuard) et la Domotique (Home Assistant) sont externalisés sur un Raspberry Pi 5 pour rester fonctionnels indépendamment de la pile logicielle principale.
- **Acceptation du Risque :** En cas d'arrêt du GMKtec (maintenance Proxmox), le réseau local perd sa connectivité internet.
- **Stratégie de Sauvegarde 3-2-1 :** - **3 copies :** Données live, Backup local (NAS), Backup Cloud.
  - **2 supports :** RAID 1 (Miroir physique) et Btrfs Snapshots (Logique).
  - **1 copie hors-site :** Synchronisation quotidienne vers Backblaze B2.

---

## 2. Organisation Physique (Hardware - Rack Unifié)

Tous les équipements sont regroupés dans un même rack pour faciliter la gestion et le câblage.

### 🟢 Zone A : Infrastructure & Stockage

- **NAS (Cargo) :** Ugreen DXP2800 (IP: `192.168.10.5`).
  - **Stockage :** 3.6 To utiles (RAID 1 - Btrfs).
  - **Accélération :** SSD NVMe 1 To (500 Go alloués en cache de lecture).
- **Réseau :** Switch Manageable 5 ports PoE+.
  - **IP Statique :** `192.168.10.3`
  - **Web UI :** `http://192.168.10.3`
  - **Features actives :**
    - LEDs désactivées
    - IGMP Snooping (si multicast Home Assistant)

### 🔵 Zone B : Compute & Monitoring

- **Serveur Principal (GMKtec NucBox M6) :** - **OS :** Proxmox VE 9.1 (IP: `192.168.10.10`).
  - **Interface WAN :** `nic1` (direct vers Box FAI).
  - **Interface LAN :** `nic0` (vers Switch).
- **Tour de Contrôle (Raspberry Pi 5) :** - **IP Statique :** `192.168.10.2`.
  - **Écran :** Tactile 3.5" pour monitoring local via `status_dashboard.py`.

_Note : L'imprimante Bambu Lab A1 est exclue de l'infrastructure Homelab (connectée au Wi-Fi de la Box FAI)._

---

## 3. Stockage Centralisé (Arborescence Cargo)

Chaque dossier racine est un **Dossier Partagé** UGOS avec des permissions NFS spécifiques pour isoler les accès.

| Dossier Partagé   | Usage                                      | Client NFS            |
| :---------------- | :----------------------------------------- | :-------------------- |
| `proxmox-backups` | Sauvegardes .vma (VZDump)                  | Proxmox (10.10)       |
| `appdata`         | Persistance Conteneurs (AdGuard, HA, etc.) | RPi (10.2) & VM 110   |
| `media`           | Films, Séries, Téléchargements             | VM 110 (Docker Stack) |
| `photos`          | Bibliothèque Immich                        | VM 110                |
| `backups-configs` | Archives Ansible, Vault, Configs Routeur   | Tous (Lecture Seule)  |

---

## 4. Stack Logicielle

### 💻 Serveur A : GMKtec (Proxmox VE 9.1)

- **OS Hôte :** Proxmox VE (Hyperviseur).
- **IP de Management :** `192.168.10.10`
- **Passerelle :** `192.168.10.1` (VM OPNsense)
- **Hardware :** AMD Ryzen 5 7640HS (6C/12T @ 5.0 GHz), 32 GB DDR5, 1 TB NVMe
- **Ressources :** Passthrough iGPU AMD Radeon 760M (Drivers `mesa-va-drivers`).

#### Architecture Hybride VM/LXC

| Instance    | Type | vCPU | RAM   | Stockage | Description                                  |
| :---------- | :--- | :--- | :---- | :------- | :------------------------------------------- |
| **VM 100**  | VM   | 2    | 2 GB  | 16 GB    | OPNsense (Routeur, Pare-feu, DHCP)           |
| **VM 110**  | VM   | 6    | 14 GB | 100 GB   | Media Stack (Jellyfin, Immich, Overseerr)    |
| **VM 120**  | VM   | 2    | 6 GB  | 50 GB    | Download Stack (Gluetun, \*Arr, qBittorrent) |
| **LXC 200** | LXC  | 2    | 4 GB  | 20 GB    | Infrastructure (NPM, Authentik, Bitwarden)   |
| **LXC 210** | LXC  | 2    | 3 GB  | 30 GB    | Productivité (Paperless-ngx, Stirling-PDF)   |
| **Hôte**    | PVE  | -    | 3 GB  | -        | Réserve Proxmox & Cache                      |

#### Services par Instance

**VM 100 - OPNsense (Réseau)**

- Routeur principal & Pare-feu
- DHCP (Plage `192.168.10.100` - `192.168.10.200`)
- DNS Forwarder vers AdGuard (`192.168.10.2`)

**VM 110 - Media Stack (Streaming & Photos)**

- **Jellyfin** : Streaming avec transcodage GPU (iGPU AMD passthrough)
- **Immich** : Gestion photos/vidéos avec ML (reconnaissance faciale)
- **Overseerr** : Interface de demande de médias

**VM 120 - Download Stack (Téléchargements)**

- **Gluetun** : VPN Gateway avec Killswitch (isolation réseau)
- **qBittorrent** : Client Torrent
- **Radarr, Sonarr, Prowlarr** : Automatisation médias
- **Bazarr** : Gestion sous-titres

**LXC 200 - Infrastructure (Accès & Sécurité)**

- **Nginx Proxy Manager** : Reverse Proxy & SSL
- **Authentik** : SSO (Single Sign-On)
- **Bitwarden** : Gestionnaire de mots de passe

**LXC 210 - Productivité (Documents)**

- **Paperless-ngx** : GED (Gestion Électronique de Documents)
- **Stirling-PDF** : Outils de manipulation PDF

### 🍓 Serveur B : Raspberry Pi 5 (La "Tour de Contrôle")

- **OS :** Docker sur Linux (Boot sur NVMe).
- **IP Statique :** `192.168.10.2`.
- **Rôle :** Services critiques (Infrastructure) et Dashboard.

| Catégorie      | Services           | Statut | Description                                    |
| :------------- | :----------------- | :----: | :--------------------------------------------- |
| **Réseau**     | **AdGuard Home**   | ✅ | DNS Master, Bloqueur de pubs.                  |
|                | **Tailscale**      | ✅ | VPN Mesh (Accès de secours).                   |
| **Domotique**  | **Home Assistant** | ✅ | Cerveau domotique (Z-Wave/Zigbee/WiFi).        |
| **Monitoring** | **Homepage**       | ✅ | Dashboard principal (Affichage Écran Tactile). |
|                | **Uptime Kuma**    | 📋 | Monitoring disponibilité (planifié).           |
|                | **Scrutiny (Web)** | 📋 | Dashboard santé disques (planifié).            |
|                | **Dozzle**         | 📋 | Visualiseur logs Docker (planifié).            |
|                | **Diun**           | 📋 | Notifications updates Docker (planifié).       |
|                | **Grafana**        | 📋 | Visualisation métriques (planifié).            |
|                | **Prometheus**     | 📋 | Collecte métriques (planifié).                 |
|                | **Loki**           | 📋 | Agrégation logs (planifié).                    |

**Légende** : ✅ Déployé | 📋 Planifié | 🔄 En cours

### 💾 Stockage : Ugreen NAS

- **Rôle :** Stockage brut & Backup.

| Catégorie      | Service / Rôle              | Statut | Description                                                             |
| :------------- | :-------------------------- | :----: | :---------------------------------------------------------------------- |
| **Partage**    | **SMB / NFS**               | ✅ | Partages pour Proxmox (ISOs/Backups) et PC.                             |
| **Sauvegarde** | **Rclone → Backblaze B2**   | ✅ | Backup off-site quotidien (03:00 AM).                                   |
| **Automation** | **LED Control**             | ✅ | Extinction/allumage LEDs programmé.                                     |
| **Monitoring** | **Scrutiny (Collector)**    | 📋 | Agent S.M.A.R.T (planifié).                                             |

**Légende** : ✅ Déployé | 📋 Planifié

---

## 5. Stratégie de Sauvegarde & Résilience

| Type                  | Méthode           | Destination              | Fréquence                   |
| :-------------------- | :---------------- | :----------------------- | :-------------------------- |
| **VM Proxmox**        | VZDump (Snapshot) | `cargo:/proxmox-backups` | Toutes les 5h (Rétention 5) |
| **Données Services**  | Montage NFS       | `cargo:/appdata`         | Temps réel (RAID 1)         |
| **Protection Erreur** | Btrfs Snapshots   | Local (NAS)              | Quotidien (04h00)           |
| **Off-site (Cloud)**  | Rclone (Docker)   | **Backblaze B2**         | Quotidien (03h00)           |

---

## 6. Configuration Réseau & Flux

### 🛠️ Paramètres IP Unifiés

- **Réseau LAN :** `192.168.10.0/24`
- **Passerelle (OPNsense) :** `192.168.10.1`
- **DNS Primaire (AdGuard) :** `192.168.10.2`
- **Proxmox Host :** `192.168.10.10`

### 🔗 Stratégie DNS & Accès

1. **Interne :** Les clients DHCP reçoivent le Pi (`.2`) comme DNS.
2. **Externe (Amis/Mobile) :** Accès via URL `https://service.blackbox.homes` qui pointe vers l'IP Tailscale (`100.x.y.z`).
3. **Sécurité :** Nginx Proxy Manager (sur VM 110) gère les certificats SSL via DNS Challenge.

---

## 7. Procédure de Redémarrage & Maintenance

### Ordre de démarrage (Cold Start)

1. **Démarrer le GMKtec :** Attendre le boot de Proxmox et le lancement auto d'OPNsense.
2. **Démarrer le NAS (Cargo) :** Indispensable pour la disponibilité des partages NFS.
3. **Démarrer le Raspberry Pi :** Le script de bootstrap assure le montage de `/mnt/appdata` avant le lancement de Docker.

### Reconstruction "Nuke & Pave"

1. Réinstaller l'OS (Proxmox ou RPi OS).
2. Lancer le Playbook Ansible correspondant (`bootstrap_pve.yml` ou `bootstrap_rpi.yml`).
3. Pour le Pi, les services redémarrent instantanément avec leurs données NAS.
4. Pour Proxmox, restaurer les VM depuis le stockage `proxmox-backups`.
