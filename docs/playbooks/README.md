# 📚 Documentation des Playbooks Ansible

Ce répertoire contient la documentation détaillée de chaque playbook Ansible du homelab.

## Playbooks Disponibles

| Playbook | Objectif | Hôte(s) Cible | Documentation |
|----------|----------|---------------|---------------|
| `bootstrap_pve.yml` | Configuration initiale Proxmox VE | `proxmox` | [Lien](bootstrap_pve.md) |
| `bootstrap_rpi.yml` | Configuration initiale Raspberry Pi | `raspberry` | [Lien](bootstrap_rpi.md) |
| `deploy_rpi_stack.yml` | Déploiement stack Docker Raspberry Pi | `raspberry` | [Lien](deploy_rpi_stack.md) |
| `install_tailscale.yml` | Installation VPN Tailscale | `raspberry` | [Lien](install_tailscale.md) |
| `deploy_kiosk.yml` | Déploiement dashboard tactile | `raspberry` | [Lien](deploy_kiosk.md) |
| `deploy_nas_backup.yml` | Configuration backups Backblaze B2 | `nas` | [Lien](deploy_nas_backup.md) |
| `deploy_nas_leds.yml` | Configuration contrôle LEDs NAS | `nas` | [Lien](deploy_nas_leds.md) |
| `setup_screen.yml` | Configuration écran (legacy) | `raspberry` | [Lien](setup_screen.md) |

## Utilisation Générale

### Prérequis

```bash
# Installer Ansible
sudo apt install ansible

# Cloner le repo
git clone <repo-url>
cd blackbox/ansible

# Configurer le vault password
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass
```

### Exécution d'un Playbook

```bash
# Vérifier la syntaxe
ansible-playbook playbooks/<playbook>.yml --syntax-check

# Dry-run (simulation)
ansible-playbook playbooks/<playbook>.yml --check

# Exécution réelle
ansible-playbook playbooks/<playbook>.yml

# Verbose mode (debugging)
ansible-playbook playbooks/<playbook>.yml -vvv
```

### Inventaire

Les hôtes sont définis dans `inventory/hosts.ini` :

```ini
[proxmox]
pve ansible_host=192.168.10.10

[raspberry]
control-tower ansible_host=192.168.10.2

[nas]
cargo ansible_host=192.168.10.5
```

### Variables Vault

Variables sensibles stockées dans `inventory/group_vars/all/vault.yml` (encryptées) :
- IPs et credentials
- Clés API (Tailscale, Backblaze B2, OPNsense)
- Clés SSH publiques

## Structure Recommandée

Chaque documentation de playbook contient :
1. **Objectif** : Ce que fait le playbook
2. **Prérequis** : Variables vault nécessaires, dépendances
3. **Services/Configurations Déployés** : Liste détaillée
4. **Commande d'Exécution** : Exemple pratique
5. **Vérification** : Comment tester le succès
6. **Troubleshooting** : Problèmes courants et solutions

## Ordre de Déploiement Recommandé

Pour un setup from scratch :

1. `bootstrap_pve.yml` - Configurer Proxmox VE
2. Créer manuellement les VMs/LXCs dans Proxmox
3. `bootstrap_rpi.yml` - Configurer Raspberry Pi OS
4. `install_tailscale.yml` - Activer VPN mesh
5. `deploy_rpi_stack.yml` - Lancer services Docker (AdGuard, HA, etc.)
6. `deploy_kiosk.yml` - Activer dashboard tactile
7. `deploy_nas_backup.yml` - Configurer backups cloud
8. `deploy_nas_leds.yml` - Configurer LEDs NAS

## Références

- Inventaire : `ansible/inventory/`
- Templates : `ansible/templates/`
- Scripts : `ansible/scripts/`
- Configuration Ansible : `ansible/ansible.cfg`
