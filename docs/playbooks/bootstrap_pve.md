# 🔧 bootstrap_pve.yml

## Objectif

Configuration post-installation de Proxmox VE 9.1 sur le GMKtec NucBox M6 :
- Durcissement SSH (key-only, pas de root password)
- Configuration repositories (désactiver enterprise, activer no-subscription)
- Activation IOMMU pour GPU passthrough
- Mise à jour système

## Prérequis

### Variables Vault

| Variable | Description |
|----------|-------------|
| `vault_ssh_public_key` | Clé SSH publique pour accès sans mot de passe |

### État Système

- Proxmox VE 9.1 fraîchement installé
- Accès root temporaire activé (sera désactivé après)
- Connexion réseau fonctionnelle

## Actions du Playbook

### 1. Configuration SSH Hardening

**Modifications `/etc/ssh/sshd_config`** :
```
PasswordAuthentication no           # Uniquement clés SSH
PermitRootLogin prohibit-password   # Root seulement par clé
ChallengeResponseAuthentication no  # Pas d'auth interactive
PubkeyAuthentication yes            # Clés SSH activées
```

**Ajout clé publique** :
```bash
~/.ssh/authorized_keys  # Depuis vault_ssh_public_key
```

### 2. Repositories Proxmox

**Désactivation Enterprise** :
```bash
# /etc/apt/sources.list.d/pve-enterprise.list
# Commenté (nécessite licence payante)
```

**Activation No-Subscription** :
```
deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription
```

**Ajout Ceph (optionnel)** :
```
deb http://download.proxmox.com/debian/ceph-quincy bookworm no-subscription
```

### 3. Activation IOMMU (GPU Passthrough)

**GRUB Configuration** (`/etc/default/grub`) :
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet amd_iommu=on iommu=pt"
```

**Modules Kernel** (`/etc/modules`) :
```
vfio
vfio_iommu_type1
vfio_pci
vfio_virqfd
```

**Update GRUB** :
```bash
update-grub
```

**IMPORTANT** : Reboot requis pour activation IOMMU.

### 4. Mises à Jour Système

```bash
apt update
apt full-upgrade -y
apt autoremove -y
```

## Commande d'Exécution

```bash
ansible-playbook playbooks/bootstrap_pve.yml
```

### Post-Exécution

```bash
# Reboot pour activation IOMMU
ssh pve.blackbox.homes
reboot
```

## Vérification Post-Déploiement

### 1. SSH Key-Only

```bash
# Tester connexion par clé
ssh -i ~/.ssh/id_homelab root@192.168.10.10

# Vérifier auth password désactivée
ssh -o PreferredAuthentications=password root@192.168.10.10
# Devrait échouer : Permission denied
```

### 2. Repositories

```bash
ssh pve.blackbox.homes
apt update

# Vérifier aucune erreur enterprise
# Output ne doit PAS contenir "pve-enterprise: 401 Unauthorized"
```

### 3. IOMMU Activé

```bash
ssh pve.blackbox.homes
dmesg | grep -i iommu

# Output attendu :
# AMD-Vi: AMD IOMMUv2 loaded and initialized
```

### 4. GPU Passthrough Disponible

```bash
# Lister devices IOMMU
find /sys/kernel/iommu_groups/ -type l

# Vérifier GPU dans groupe IOMMU
lspci -nnk | grep -i vga
```

### 5. Modules VFIO

```bash
lsmod | grep vfio

# Output attendu :
# vfio_pci
# vfio_iommu_type1
# vfio
```

## Troubleshooting

### SSH Key Non Fonctionnelle

```bash
# Vérifier permissions
ls -la ~/.ssh/authorized_keys  # Doit être 600
chmod 600 ~/.ssh/authorized_keys

# Vérifier contenu clé
cat ~/.ssh/authorized_keys  # Doit correspondre à vault
```

### IOMMU Non Activé

```bash
# Vérifier GRUB config
cat /etc/default/grub | grep CMDLINE

# Re-update GRUB
update-grub
reboot

# Vérifier BIOS
# Activer AMD-Vi/IOMMU dans BIOS du GMKtec
```

### GPU Non Détecté pour Passthrough

```bash
# Lister PCI devices
lspci -nnk | grep -A3 VGA

# Identifier vendorID:deviceID (ex: 1002:15bf)
# Configurer vfio-pci dans /etc/modprobe.d/vfio.conf :
options vfio-pci ids=1002:15bf

# Rebuild initramfs
update-initramfs -u -k all
reboot
```

## Configuration Post-Bootstrap

### Créer VM avec GPU Passthrough

```bash
# Dans Proxmox Web UI
VM → Hardware → Add → PCI Device
- Raw Device : 0000:xx:00.0 (GPU AMD Radeon 760M)
- All Functions : Yes
- Primary GPU : No (sauf si headless)
- PCI-Express : Yes
```

### Configurer Stockage NFS

```bash
# Datacenter → Storage → Add → NFS
Name: nas-appdata
Server: 192.168.10.5
Export: /volume1/appdata
Content: VZDump backup files, Disk image
```

## Références

- Documentation complète : `docs/bootstrap/proxmox.md`
- Proxmox VE Admin Guide : [https://pve.proxmox.com/pve-docs/](https://pve.proxmox.com/pve-docs/)
- GPU Passthrough : [https://pve.proxmox.com/wiki/Pci_passthrough](https://pve.proxmox.com/wiki/Pci_passthrough)
