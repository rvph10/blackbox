# 🏗️ Document de Design Technique : Homelab "Nuke & Pave"

## 1. Philosophie d'Architecture

- **Isolation Réseau :** Création d'un réseau Homelab dédié (Subnet `192.168.10.0/24`) isolé de la Box Proximus via une VM OPNsense en mode PPPoE Passthrough.
- **Cœur Virtualisé :** Le GMKtec NucBox M6 centralise le routage (OPNsense) et la puissance de calcul (Docker/LXC).
- **Accès Distant "Zéro Trust" :** Utilisation de la stratégie "DNS Public / IP Privée". Les services (Jellyfin, etc.) disposent d'un nom de domaine HTTPS valide (`*.blackbox.homes`) mais ne sont accessibles que via le réseau Mesh Tailscale, sans ouverture de ports.
- **Résilience des Services de Base :** Le DNS (AdGuard) et la Domotique (Home Assistant) sont externalisés sur un Raspberry Pi 5 pour rester fonctionnels indépendamment de la pile logicielle principale.
- **Acceptation du Risque :** En cas d'arrêt du GMKtec (maintenance Proxmox), le réseau local perd sa connectivité internet.

---

## 2. Organisation Physique (Hardware - Rack Unifié)

Tous les équipements sont regroupés dans un même rack pour faciliter la gestion et le câblage.

### 🟢 Zone A : Infrastructure & Stockage

- **Réseau :** Switch Manageable 5 ports PoE+.
- **Stockage (NAS) :** Ugreen DXP2800 (8To). Connecté en Ethernet au Switch.
- **Backup :** Disque Dur USB Externe (8To). Connecté en USB au NAS.

### 🔵 Zone B : Compute & Monitoring

- **Serveur Principal (GMKtec NucBox M6) :** \* Port Eth 1 (nic1/vmbr1) : Arrivée WAN (Câble direct vers Port 1 de la Box Proximus).
  - Port Eth 2 (nic0/vmbr0) : Sortie LAN (Câble vers Switch).
- **Tour de Contrôle (Raspberry Pi 5) :** Écran tactile 7" pour le monitoring local. Connecté au Switch.

_Note : L'imprimante Bambu Lab A1 est exclue de l'infrastructure Homelab (connectée au Wi-Fi de la Box FAI)._

---

## 3. Stack Logicielle

### 💻 Serveur A : GMKtec (Proxmox VE 9.1)

- **IP de Management :** `192.168.10.10`
- **Passerelle :** `192.168.10.1` (VM OPNsense)

| VM/CT      | Service          | Description                                                  |
| :--------- | :--------------- | :----------------------------------------------------------- |
| **VM 100** | **OPNsense**     | Routeur, Pare-feu, DHCP (Plage .100 - .200).                 |
| **VM 110** | **Docker Stack** | Jellyfin, Suite \*Arr, Immich, **Tailscale (Node Partagé)**. |

### 🍓 Serveur B : Raspberry Pi 5

- **IP Statique :** `192.168.10.2` (Configurée hors plage DHCP).
- **Rôle :** DNS de sortie et Dashboard local.

| Catégorie      | Services           | Description                                           |
| :------------- | :----------------- | :---------------------------------------------------- |
| **Réseau**     | **AdGuard Home**   | DNS filtrant. Point de passage obligé avant OPNsense. |
|                | **Tailscale**      | Accès de secours (Subnet Router) & Admin.             |
| **Domotique**  | **Home Assistant** | Cerveau domotique (Intégration monitoring).           |
| **Monitoring** | **Homepage**       | Dashboard principal affiché sur l'écran 7".           |

---

## 4. Configuration Réseau & Flux

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

## 5. Procédure de Redémarrage (Ordre de priorité)

Pour assurer la cohérence des services lors d'une reconstruction ou d'une coupure :

1. **Démarrer le GMKtec :** Attendre le boot de Proxmox et le lancement auto de la VM OPNsense.
2. **Vérifier le WAN :** S'assurer que le tunnel PPPoE est établi sur OPNsense.
3. **Démarrer le Raspberry Pi :** Une fois le réseau actif, le Pi peut démarrer ses services DNS et monitoring.
4. **Démarrer les services Docker :** Montage des partages NAS et lancement des conteneurs.
