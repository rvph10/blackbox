# Documentation Blackbox Homelab

Bienvenue dans la documentation de mon homelab. Cette doc est mon guide personnel pour maintenir et faire évoluer mon infrastructure.

## Par où commencer ?

- **Premier déploiement ?** → Voir [Quickstart](./quickstart.md)
- **Comprendre l'architecture ?** → Voir [Architecture](./architecture/README.md)
- **Déployer un service ?** → Voir [Déploiement](./deployment/README.md)
- **Maintenance quotidienne ?** → Voir [Operations](./operations/maintenance.md)
- **Chercher un playbook ?** → Voir [Référence Playbooks](./reference/playbooks.md)

## Organisation de la doc

```
docs/
├── quickstart.md              # Déploiement rapide 0-60
├── architecture/              # Comment tout est conçu
│   ├── README.md             # Vue d'ensemble
│   ├── philosophy.md         # Pourquoi ces choix ?
│   ├── hardware.md           # Specs matérielles
│   ├── network.md            # Configuration réseau
│   └── services.md           # Catalogue des services
├── deployment/                # Comment tout déployer
│   ├── README.md             # Ordre des opérations
│   ├── 01-proxmox.md         # Installation Proxmox
│   ├── 02-opnsense.md        # Configuration OPNsense
│   ├── 03-raspberry-pi.md    # Setup Raspberry Pi (Control Tower)
│   └── 04-services.md        # Déploiement des services
├── operations/                # Maintenance au quotidien
│   ├── maintenance.md        # Tâches récurrentes
│   ├── backup-restore.md     # Stratégie de backup
│   ├── secrets.md            # Gestion du vault
│   └── troubleshooting.md    # Résolution de problèmes
└── reference/                 # Info de référence
    ├── playbooks.md          # Documentation des playbooks Ansible
    ├── status.md             # État actuel des déploiements

```

## Navigation rapide

### Architecture

- [Vue d'ensemble](./architecture/README.md)
- [Philosophie & Principes](./architecture/philosophy.md)
- [Hardware](./architecture/hardware.md)
- [Réseau](./architecture/network.md)
- [Services](./architecture/services.md)

### Déploiement

- [Guide d'installation](./deployment/README.md)
- [Proxmox](./deployment/01-proxmox.md)
- [OPNsense](./deployment/02-opnsense.md)
- [Raspberry Pi](./deployment/03-raspberry-pi.md)
- [Services](./deployment/04-services.md)

### Operations

- [Maintenance](./operations/maintenance.md)
- [Backup & Restore](./operations/backup-restore.md)
- [Secrets & Vault](./operations/secrets.md)
- [Troubleshooting](./operations/troubleshooting.md)

### Référence

- [Playbooks Ansible](./reference/playbooks.md)
- [Status des déploiements](./reference/status.md)

## Principe d'organisation

Cette documentation suit une logique simple :

1. **Architecture** = Ce que j'ai construit et pourquoi
2. **Deployment** = Comment le construire de zéro
3. **Operations** = Comment le maintenir au quotidien
4. **Reference** = Info ponctuelle et état actuel

Chaque section a un `README.md` qui explique le contenu et guide vers les bons fichiers.
