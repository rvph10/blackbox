# Blackbox Homelab

Dépôt central de configuration et documentation pour l'infrastructure "Blackbox".

## Architecture

Ce homelab repose sur une philosophie "Nuke & Pave" avec un cœur virtualisé sur GMKtec NucBox M6.

- **Hyperviseur :** Proxmox VE 9.1
- **Routeur :** OPNsense (Virtualisé)
- **Services :** Docker (VM Debian) & Raspberry Pi 5 (DNS/Domotique)

👉 [Voir la documentation d'architecture complète](docs/homelab.md)
👉 [Guide d'Opérations & Maintenance (Secrets, Restauration)](docs/operations.md)

## Démarrage rapide

### Pré-requis

- Ansible installé sur la machine de contrôle.
- Accès SSH configuré vers `root@192.168.10.10` (Proxmox).

### Structure

- `ansible/` : Playbooks pour la configuration des hôtes (Proxmox, VMs).
- `docker/` : Stacks docker-compose pour les services (Jellyfin, etc.).
- `docs/` : Procédures de reconstruction et notes techniques.

## ⚠️ Notes de sécurité

- Les fichiers `.env` contenant les mots de passe ne sont pas versionnés.
- Utiliser `.env.example` comme modèle pour recréer les secrets.
