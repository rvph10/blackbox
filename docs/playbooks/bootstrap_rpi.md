# 🍓 bootstrap_rpi.yml

## Objectif

Configuration initiale du Raspberry Pi 5 après installation de Raspberry Pi OS :
- Configuration hostname et IP statique
- Installation Docker
- Montage NFS automatique depuis NAS Cargo
- Préparation pour déploiement stack Docker

## Prérequis

### Variables Vault

| Variable | Description | Exemple |
|----------|-------------|---------|
| `vault_rpi_ip` | IP statique Raspberry Pi | `192.168.10.2` |
| `vault_rpi_hostname` | Hostname | `control-tower` |
| `vault_gateway_ip` | Gateway (OPNsense) | `192.168.10.1` |
| `vault_cargo_ip` | IP NAS | `192.168.10.5` |

### État Système

- Raspberry Pi OS (64-bit, Debian Bookworm) installé
- Connexion réseau temporaire (DHCP) fonctionnelle
- Accès SSH activé

## Actions du Playbook

### 1. Configuration Réseau (NetworkManager)

**IP Statique** via `nmcli` :
```bash
nmcli con mod "Wired connection 1" \
  ipv4.addresses {{ vault_rpi_ip }}/24 \
  ipv4.gateway {{ vault_gateway_ip }} \
  ipv4.dns {{ vault_rpi_ip }} \
  ipv4.method manual
```

**DNS** : Pointe vers lui-même (192.168.10.2) car AdGuard Home sera installé.

### 2. Configuration Hostname

```bash
hostnamectl set-hostname {{ vault_rpi_hostname }}
# Résultat : control-tower
```

### 3. Installation Docker

**Méthode** : Script officiel Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

**Ajout utilisateur au groupe docker** :
```bash
usermod -aG docker {{ ansible_user }}
```

Permet exécution `docker` sans sudo.

### 4. Montage NFS depuis NAS

**Création point de montage** :
```bash
mkdir -p /mnt/appdata
```

**Configuration fstab** :
```
192.168.10.5:/volume1/appdata  /mnt/appdata  nfs  defaults,_netdev  0  0
```

**Paramètre `_netdev`** : Attend disponibilité réseau avant montage (évite erreurs boot).

**Montage immédiat** :
```bash
mount -a
```

### 5. Systemd Service Auto-Mount

**Fichier** : `/etc/systemd/system/mnt-appdata.mount`
```ini
[Unit]
Description=NFS mount for appdata
After=network-online.target
Requires=network-online.target

[Mount]
What=192.168.10.5:/volume1/appdata
Where=/mnt/appdata
Type=nfs
Options=defaults,_netdev

[Install]
WantedBy=multi-user.target
```

**Activation** :
```bash
systemctl enable mnt-appdata.mount
systemctl start mnt-appdata.mount
```

Garantit montage NFS au boot, même après reboot réseau.

## Commande d'Exécution

```bash
ansible-playbook playbooks/bootstrap_rpi.yml
```

### Post-Exécution

```bash
# Reboot pour appliquer changements réseau
ssh {{ vault_rpi_ip }}
reboot

# Attendre 1-2 minutes puis reconnecter
ssh control-tower.blackbox.homes
```

## Vérification Post-Déploiement

### 1. Réseau

```bash
ssh control-tower.blackbox.homes

# Vérifier IP statique
ip addr show eth0 | grep inet

# Output attendu :
# inet 192.168.10.2/24 brd 192.168.10.255 scope global eth0

# Vérifier gateway
ip route | grep default

# Output :
# default via 192.168.10.1 dev eth0
```

### 2. Hostname

```bash
hostnamectl

# Output :
# Static hostname: control-tower
```

### 3. Docker

```bash
docker --version

# Output :
# Docker version 24.x.x, build xxxxx

# Vérifier groupe
groups | grep docker

# Test run
docker run hello-world
```

### 4. Montage NFS

```bash
# Vérifier montage actif
mount | grep /mnt/appdata

# Output :
# 192.168.10.5:/volume1/appdata on /mnt/appdata type nfs (rw,...)

# Tester écriture
touch /mnt/appdata/test.txt
ls -la /mnt/appdata/

# Cleanup
rm /mnt/appdata/test.txt
```

### 5. Systemd NFS Service

```bash
systemctl status mnt-appdata.mount

# Output :
# Active: active (mounted)
```

## Troubleshooting

### IP Statique Non Appliquée

```bash
# Vérifier config NetworkManager
nmcli con show "Wired connection 1"

# Forcer reapply
nmcli con down "Wired connection 1"
nmcli con up "Wired connection 1"
```

### Docker Erreur Permission

```bash
# Re-ajouter user au groupe
sudo usermod -aG docker $USER

# Logout/login pour appliquer
exit
ssh control-tower.blackbox.homes
```

### NFS Mount Échoue

```bash
# Vérifier connectivité NAS
ping 192.168.10.5

# Vérifier exports NFS disponibles
showmount -e 192.168.10.5

# Output attendu :
# Export list for 192.168.10.5:
# /volume1/appdata *

# Tester montage manuel
sudo mount -t nfs 192.168.10.5:/volume1/appdata /mnt/appdata
```

### Montage NFS Pas Persistant au Reboot

```bash
# Vérifier fstab
cat /etc/fstab | grep appdata

# Vérifier systemd mount
systemctl list-unit-files | grep mnt-appdata

# Re-enable si nécessaire
systemctl enable mnt-appdata.mount
```

## Prochaines Étapes

Après bootstrap réussi :

1. **Déployer stack Docker** :
   ```bash
   ansible-playbook playbooks/deploy_rpi_stack.yml
   ```

2. **Installer Tailscale** :
   ```bash
   ansible-playbook playbooks/install_tailscale.yml
   ```

3. **Activer dashboard tactile** (si écran présent) :
   ```bash
   ansible-playbook playbooks/deploy_kiosk.yml
   ```

## Références

- Documentation complète : `docs/bootstrap/control-tower.md`
- Architecture : `docs/homelab.md`
- Services status : `docs/services-status.md`
- Playbooks suivants : `docs/playbooks/deploy_rpi_stack.md`
