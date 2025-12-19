# 🏗️ Document de Design Technique : Homelab "Nuke & Pave"

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

- **IP de Management :** `192.168.10.10`
- **Passerelle :** `192.168.10.1` (VM OPNsense)

| VM/CT      | Service          | Description                                                  |
| :--------- | :--------------- | :----------------------------------------------------------- |
| **VM 100** | **OPNsense**     | Routeur, Pare-feu, DHCP (Plage .100 - .200).                 |
| **VM 110** | **Docker Stack** | (🚧 Planifié) Jellyfin, Suite \*Arr, Immich, **Tailscale**. |

### 🍓 Serveur B : Raspberry Pi 5 (Tour de Contrôle)

- **IP Statique :** `192.168.10.2` (Fixée via Ansible).
- **Persistance :** Dossiers montés en NFS via `/mnt/appdata`.
- **OS :** Raspberry Pi OS Lite 64-bit.

| Statut | Service            | Description                        | Configuration                                               |
| :----- | :----------------- | :--------------------------------- | :---------------------------------------------------------- |
| ✅     | **AdGuard Home**   | DNS Primaire du réseau.            | Upstream DoT/DoH + Réécritures locales.                     |
| ✅     | **Tailscale**      | Subnet Router (`192.168.10.0/24`). | AuthKey via Vault + MagicDNS activé.                        |
| ✅     | **Home Assistant** | Conteneur Docker.                  | Volume persistant : `/opt/blackbox/homeassistant`.          |
| ⚠️     | **Homepage**       | Dashboard.                         | Installé mais widgets non configurés (API Keys manquantes). |
| ✅     | **Mode Kiosk**     | Écran Tactile 3.5".                | Dashboard persistant sur le Pi.                             |

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

## 7. Procédure de Redémarrage (Ordre de priorité)

Pour assurer la cohérence des services lors d'une reconstruction ou d'une coupure :

1. **Démarrer le GMKtec :** Attendre le boot de Proxmox et le lancement auto de la VM OPNsense.
2. **Vérifier le WAN :** S'assurer que le tunnel PPPoE est établi sur OPNsense.
3. **Démarrer le Raspberry Pi :** Une fois le réseau actif, le Pi peut démarrer ses services DNS et monitoring.
4. **Démarrer les services Docker :** Montage des partages NAS et lancement des conteneurs.

---

## 6. Procédures de Maintenance

### Ordre de démarrage (Cold Start)

1. **Démarrer le GMKtec :** Attendre le boot de Proxmox et le lancement auto d'OPNsense.
2. **Démarrer le NAS (Cargo) :** Indispensable pour la disponibilité des partages NFS.
3. **Démarrer le Raspberry Pi :** Le script de bootstrap assure le montage de `/mnt/appdata` avant le lancement de Docker.

### Reconstruction "Nuke & Pave"

1. Réinstaller l'OS (Proxmox ou RPi OS).
2. Lancer le Playbook Ansible correspondant (`bootstrap_pve.yml` ou `bootstrap_rpi.yml`).
3. Pour le Pi, les services redémarrent instantanément avec leurs données NAS.
4. Pour Proxmox, restaurer les VM depuis le stockage `proxmox-backups`.
