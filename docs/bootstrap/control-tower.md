# 🍓 Guide de Reconstruction : Tour de Contrôle (Raspberry Pi 5)

Ce document détaille l'installation du serveur de services critiques (DNS, Domotique, Accès Secours).

## 1. Installation OS (Imager)

- **OS :** Raspberry Pi OS Lite (64-bit).
- **Hostname :** `control-tower`.
- **Utilisateur :** `admin` (Même user que défini dans Ansible Vault).
- **SSH :** Activé (Clé publique recommandée).
- **Réseau :** Laisser en DHCP pour le premier boot (Câble Ethernet connecté).

## 2. Provisioning (Ansible)

Une fois le Pi démarré, récupérer son IP temporaire et lancer les playbooks depuis le contrôleur :

```bash
# 1. Préparation système & IP Fixe (192.168.10.2)
ansible-playbook -i inventory/hosts.ini playbooks/bootstrap_rpi.yml

# 2. Déploiement des services (Docker Stack)
ansible-playbook -i inventory/hosts.ini playbooks/deploy_rpi_stack.yml

# 3. Installation VPN de secours (Tailscale)
ansible-playbook -i inventory/hosts.ini playbooks/install_tailscale.yml
```

## 3. Configuration Post-Install (Manuelle)

### A. AdGuard Home

- **URL :** `http://192.168.10.2:3000` (Setup initial).
- **Ports Admin :** `80` (Web) et `53` (DNS).
- **Paramètres DNS (Une fois installé) :**
  - _Upstream DNS (DoT/DoH) :_
    ```text
    tls://1.1.1.1
    tls://9.9.9.9
    [https://dns.cloudflare.com/dns-query](https://dns.cloudflare.com/dns-query)
    ```
  - _Réécritures DNS (Local) :_
    - `router.blackbox.homes` -> `192.168.10.1`
    - `pve.blackbox.homes` -> `192.168.10.10`
    - `control-tower.blackbox.homes` -> `192.168.10.2`

### B. Tailscale (Accès Distant)

1. **Approbation Subnet Router :**
   - Aller sur [Admin Console > Machines](https://login.tailscale.com/admin/machines).
   - Sur `control-tower` > Edit route settings > Activer `192.168.10.0/24`.
2. **DNS Global :**
   - Aller sur [DNS](https://login.tailscale.com/admin/dns).
   - Ajouter Nameserver > Custom > `192.168.10.2`.
   - Activer **"Override local DNS"**.

## 4. Services Actifs

| Service            | URL Interne                | Description                                       |
| :----------------- | :------------------------- | :------------------------------------------------ |
| **AdGuard Home**   | `http://192.168.10.2`      | Serveur DNS & Bloqueur de pubs.                   |
| **Home Assistant** | `http://192.168.10.2:8123` | Domotique.                                        |
| **Homepage**       | `http://192.168.10.2:8082` | Dashboard (Config dans `/opt/blackbox/homepage`). |
