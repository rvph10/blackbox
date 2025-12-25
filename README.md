# Blackbox Homelab

Mon infrastructure personnelle homelab. Documentation complète, playbooks Ansible, et configs.

## Vue d'ensemble

Homelab basé sur 3 machines :

- **GMKtec NucBox M6** (Proxmox) : Hyperviseur principal, VMs/LXCs
- **Raspberry Pi 5** (Control Tower) : Services critiques + Observabilité
- **UGREEN DXP2800** (NAS Cargo) : Stockage centralisé 4TB

**Architecture** :

- Réseau isolé (192.168.10.0/24) via OPNsense
- Services critiques sur Raspberry Pi (DNS, domotique)
- Media/Downloads sur VMs Proxmox
- Backup 3-2-1 (RAID 1 + Snapshots + Backblaze B2)

## Documentation

Toute la doc est dans `/docs` avec une organisation claire :

**Guides rapides** :

- [docs/README.md](docs/README.md) - Point d'entrée de la documentation
- [docs/quickstart.md](docs/quickstart.md) - Déploiement 0 à 60 en 1h30

**Architecture** (`docs/architecture/`) :

- [Philosophy](docs/architecture/philosophy.md) - Pourquoi ces choix ?
- [Hardware](docs/architecture/hardware.md) - Specs matérielles complètes
- [Network](docs/architecture/network.md) - Config réseau détaillée
- [Services](docs/architecture/services.md) - Catalogue de tous les services

**Déploiement** (`docs/deployment/`) :

- [01-Proxmox](docs/deployment/01-proxmox.md) - Installation Proxmox
- [02-OPNsense](docs/deployment/02-opnsense.md) - Config routeur/firewall
- [03-Raspberry Pi](docs/deployment/03-raspberry-pi.md) - Setup Control Tower
- [04-Services](docs/deployment/04-services.md) - Déploiement VMs/LXCs

**Operations** (`docs/operations/`) :

- [Maintenance](docs/operations/maintenance.md) - Tâches récurrentes
- [Backup & Restore](docs/operations/backup-restore.md) - Stratégie 3-2-1
- [Secrets](docs/operations/secrets.md) - Gestion Ansible Vault
- [Troubleshooting](docs/operations/troubleshooting.md) - Résolution problèmes

**Reference** (`docs/reference/`) :

- [Playbooks](docs/reference/playbooks.md) - Index playbooks Ansible
- [Status](docs/reference/status.md) - État déploiements actuel

## Démarrage Rapide

### Premier déploiement

```bash
# 1. Clone le repo
git clone <url>
cd blackbox

# 2. Configure Ansible Vault
cd ansible/
echo "TON_MOT_DE_PASSE_VAULT" > .vault_pass
chmod 600 .vault_pass

# 3. Déploie Proxmox
ansible-playbook -i inventory/hosts.yml playbooks/bootstrap_pve.yml

# 4. Déploie Raspberry Pi
ansible-playbook -i inventory/hosts.yml playbooks/bootstrap_rpi.yml
ansible-playbook -i inventory/hosts.yml playbooks/deploy_rpi_stack.yml

# 5. Voir docs/quickstart.md pour la suite
```

### Commandes courantes

```bash
# Redéployer stack Raspberry Pi
ansible-playbook -i inventory/hosts.yml playbooks/deploy_rpi_stack.yml

# Update images Docker
ansible-playbook -i inventory/hosts.yml playbooks/deploy_rpi_stack.yml --extra-vars "force_pull=true"

# Configurer backups NAS
ansible-playbook -i inventory/hosts.yml playbooks/deploy_nas_backup.yml
```

## Structure du Repo

```
blackbox/
├── ansible/                    # Configuration Ansible
│   ├── inventory/
│   │   ├── hosts.yml          # Inventaire hôtes
│   │   └── group_vars/
│   │       └── all/
│   │           └── vault.yml  # Secrets chiffrés
│   ├── playbooks/             # Playbooks Ansible
│   └── roles/                 # Roles réutilisables
├── docs/                       # Documentation complète
│   ├── architecture/          # Design & specs
│   ├── deployment/            # Guides d'installation
│   ├── operations/            # Maintenance & ops
│   └── reference/             # Status & playbooks
└── scripts/                    # Scripts utilitaires

```

## Principes

**Nuke & Pave** : Tout peut être reconstruit en ~1h30 via Ansible

**3-2-1 Backup** :

- 3 copies (live, snapshots, cloud)
- 2 supports (RAID 1, Btrfs)
- 1 hors-site (Backblaze B2)

**Simplicité > Fonctionnalités** : Pas de Kubernetes, pas de over-engineering

**Zero Trust** : Accès distant via Tailscale uniquement, pas de ports ouverts

## Services Principaux

**Déployés** :

- AdGuard Home (DNS + ad blocking)
- Home Assistant (domotique)
- Grafana/Prometheus/Loki (observabilité)
- OPNsense (router/firewall)
- Tailscale (VPN mesh)

**Planifiés** :

- Jellyfin (media server)
- Immich (photos)
- \*arr stack (automation)

Voir [docs/reference/status.md](docs/reference/status.md) pour l'état complet.

## Contribuer (pour moi-même)

**Avant de commit** :

```bash
# Vérifier pas de secrets en clair
./ansible/scripts/check-security.sh
```

**Update documentation** :

- Changement architecture → `docs/architecture/`
- Nouveau service → `docs/reference/status.md`
- Nouveau playbook → `docs/reference/playbooks.md`

## Ressources

**Hardware** :

- GMKtec M6 : Ryzen 5 7640HS, 32GB DDR5, 1TB NVMe
- Raspberry Pi 5 : 8GB RAM
- NAS Cargo : Intel N100, 8GB DDR5, 4TB RAID 1

**Réseau** :

- Subnet : 192.168.10.0/24
- Gateway : 192.168.10.1 (OPNsense)
- DNS : 192.168.10.2 (AdGuard)

**Consommation** : ~33W idle, ~71W charge moyenne

## Support

Pour moi-même dans le futur :

- Si problème : voir [docs/operations/troubleshooting.md](docs/operations/troubleshooting.md)
- Si j'ai tout cassé : voir [docs/quickstart.md](docs/quickstart.md)
- Si je veux comprendre un choix : voir [docs/architecture/philosophy.md](docs/architecture/philosophy.md)

**Status** : Documentation réorganisée, architecture stable
