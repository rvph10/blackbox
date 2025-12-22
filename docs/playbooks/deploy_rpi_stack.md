# 📦 deploy_rpi_stack.yml

## Objectif

Déploie la stack Docker sur le Raspberry Pi 5 comprenant les services critiques :
- AdGuard Home (DNS)
- Home Assistant (domotique)
- Homepage (dashboard web)

Ce playbook génère le fichier `docker-compose.yml` depuis un template Jinja2 et lance tous les conteneurs.

## Prérequis

### Variables Vault Nécessaires

Aucune variable vault spécifique requise pour ce playbook (utilise configuration par défaut).

### Dépendances

- Raspberry Pi déjà bootstrappé via `bootstrap_rpi.yml`
- Docker installé et fonctionnel
- NFS mount `/mnt/appdata` configuré et accessible
- NAS Cargo (`192.168.10.5`) accessible avec partage NFS actif

### État Système

```bash
# Vérifier Docker
docker --version
docker ps

# Vérifier montage NFS
df -h | grep /mnt/appdata
ls -la /mnt/appdata/

# Vérifier connectivité NAS
ping -c 3 192.168.10.5
```

## Services Déployés

### 1. AdGuard Home

**Image** : `adguard/adguardhome`
**Ports** : 53 (DNS), 80 (Web), 3000 (Setup initial)
**Mode réseau** : `host` (accès direct au port 53)
**Volumes** :
- `/mnt/appdata/adguard/work` → `/opt/adguardhome/work`
- `/mnt/appdata/adguard/conf` → `/opt/adguardhome/conf`

**URL d'accès** : `http://192.168.10.2` ou `http://control-tower.blackbox.homes`

### 2. Home Assistant

**Image** : `ghcr.io/home-assistant/home-assistant:stable`
**Port** : 8123
**Mode réseau** : `host` (découverte automatique Zigbee/Z-Wave)
**Privilèges** : `privileged: true` (accès périphériques USB)
**Volumes** :
- `/mnt/appdata/homeassistant/config` → `/config`
- `/etc/localtime` → `/etc/localtime:ro` (synchronisation heure)
- `/run/dbus` → `/run/dbus:ro` (communication système)

**URL d'accès** : `http://192.168.10.2:8123`

### 3. Homepage

**Image** : `ghcr.io/gethomepage/homepage:latest`
**Port** : 8082 (mappé depuis 3000 pour éviter conflit AdGuard)
**Variables d'environnement** :
- `HOMEPAGE_ALLOWED_HOSTS: "*"` (accès depuis tous les clients)
**Volumes** :
- `/mnt/appdata/homepage/config` → `/app/config`
- `/var/run/docker.sock` → `/var/run/docker.sock:ro` (lecture stats Docker)

**URL d'accès** : `http://192.168.10.2:8082`

## Actions du Playbook

### 1. Préparation Système (Port 53)

```yaml
- Arrêt de systemd-resolved
- Suppression du lien symbolique /etc/resolv.conf
- Création d'un resolv.conf temporaire (Cloudflare 1.1.1.1)
```

**Raison** : AdGuard Home nécessite le port 53. `systemd-resolved` l'occupe par défaut sur Debian/Ubuntu.

### 2. Création Répertoires NFS

Création des dossiers de données sur le montage NFS :

```bash
/mnt/appdata/adguard/work
/mnt/appdata/adguard/conf
/mnt/appdata/homeassistant/config
/mnt/appdata/homepage/config
```

Permissions : `0755` (lecture/écriture propriétaire, lecture autres)

### 3. Déploiement Docker Compose

- Copie du template `../templates/rpi/docker-compose.yml.j2` → `/opt/blackbox/docker-compose.yml`
- Permissions : `0640` (lecture groupe `docker`)
- Lancement via `community.docker.docker_compose_v2` avec `pull: always`

## Commande d'Exécution

### Exécution Standard

```bash
cd /home/rvph/Projects/blackbox/ansible
ansible-playbook playbooks/deploy_rpi_stack.yml
```

### Dry-Run (Simulation)

```bash
ansible-playbook playbooks/deploy_rpi_stack.yml --check
```

### Re-déploiement Forcé

```bash
# Arrêter les conteneurs existants
ssh control-tower.blackbox.homes
cd /opt/blackbox
docker compose down

# Re-exécuter le playbook
ansible-playbook playbooks/deploy_rpi_stack.yml
```

## Vérification Post-Déploiement

### 1. Vérifier Conteneurs Actifs

```bash
ssh control-tower.blackbox.homes
docker ps
```

**Output attendu** :
```
CONTAINER ID   IMAGE                                        STATUS
abc123         adguard/adguardhome                          Up 5 minutes
def456         ghcr.io/home-assistant/home-assistant:stable Up 5 minutes
ghi789         ghcr.io/gethomepage/homepage:latest          Up 5 minutes
```

### 2. Tester Services Web

```bash
# AdGuard Home
curl -I http://192.168.10.2

# Home Assistant
curl -I http://192.168.10.2:8123

# Homepage
curl -I http://192.168.10.2:8082
```

### 3. Tester DNS (AdGuard)

```bash
# Depuis un client du réseau
nslookup google.com 192.168.10.2

# Vérifier blocage pub
nslookup ads.google.com 192.168.10.2
# Devrait retourner 0.0.0.0
```

### 4. Vérifier Logs

```bash
# Logs AdGuard
docker logs adguard

# Logs Home Assistant
docker logs homeassistant

# Logs Homepage
docker logs homepage
```

## Troubleshooting

### Problème : Port 53 déjà utilisé

**Symptôme** :
```
Error starting userland proxy: listen tcp4 0.0.0.0:53: bind: address already in use
```

**Solution** :
```bash
# Vérifier processus sur port 53
sudo lsof -i :53

# Si systemd-resolved toujours actif
sudo systemctl stop systemd-resolved
sudo systemctl disable systemd-resolved

# Supprimer lien symbolique
sudo rm /etc/resolv.conf
echo "nameserver 1.1.1.1" | sudo tee /etc/resolv.conf
```

### Problème : NFS mount non accessible

**Symptôme** :
```
Error: cannot create directory '/mnt/appdata/adguard': No such file or directory
```

**Solution** :
```bash
# Vérifier montage NFS
mount | grep /mnt/appdata

# Si absent, vérifier fstab
cat /etc/fstab | grep appdata

# Remonter manuellement
sudo mount -a

# Vérifier accessibilité NAS
ping 192.168.10.5
showmount -e 192.168.10.5
```

### Problème : Conteneurs ne démarrent pas

**Symptôme** :
```
docker ps  # Aucun conteneur actif
```

**Solution** :
```bash
# Vérifier erreurs Docker Compose
cd /opt/blackbox
docker compose logs

# Vérifier fichier docker-compose.yml
cat docker-compose.yml

# Tenter démarrage manuel
docker compose up -d

# Vérifier erreurs spécifiques
docker logs adguard
docker logs homeassistant
```

### Problème : Home Assistant erreur permissions USB

**Symptôme** :
```
Error: Permission denied /dev/ttyUSB0
```

**Solution** :
```bash
# Ajouter utilisateur au groupe dialout
sudo usermod -aG dialout $USER

# Ou utiliser mode privileged (déjà configuré dans template)
# privileged: true dans docker-compose.yml
```

## Mise à Jour des Services

### Mise à Jour Images Docker

```bash
ssh control-tower.blackbox.homes
cd /opt/blackbox

# Pull nouvelles images
docker compose pull

# Recréer conteneurs
docker compose up -d

# Nettoyer anciennes images
docker image prune -a
```

### Modification Configuration

```bash
# Éditer template
vim /home/rvph/Projects/blackbox/ansible/templates/rpi/docker-compose.yml.j2

# Re-déployer
ansible-playbook playbooks/deploy_rpi_stack.yml
```

## Configuration Post-Installation

### AdGuard Home

1. Accéder à `http://192.168.10.2:3000` (premier lancement)
2. Suivre wizard :
   - Port Web : 80 (défaut)
   - Port DNS : 53 (défaut)
   - Créer compte admin
3. Configurer upstreams DNS :
   - `tls://1.1.1.1` (Cloudflare DoT)
   - `tls://dns.quad9.net` (Quad9 DoT)
4. Activer listes de blocage (EasyList, etc.)

### Home Assistant

1. Accéder à `http://192.168.10.2:8123`
2. Créer compte propriétaire
3. Configurer intégrations :
   - Zigbee/Z-Wave (si dongles USB présents)
   - Wi-Fi devices
   - AdGuard Home integration

### Homepage

1. Accéder à `http://192.168.10.2:8082`
2. Configuration dans `/mnt/appdata/homepage/config/`
3. Fichiers YAML à éditer :
   - `services.yaml` : Liste des services
   - `widgets.yaml` : Widgets dashboard
   - `bookmarks.yaml` : Liens favoris

## Fichiers Générés

| Fichier | Localisation | Description |
|---------|--------------|-------------|
| `docker-compose.yml` | `/opt/blackbox/` | Stack Docker générée depuis template |
| AdGuard config | `/mnt/appdata/adguard/conf/` | Configuration AdGuard (backup important) |
| HA config | `/mnt/appdata/homeassistant/config/` | Configuration Home Assistant |
| Homepage config | `/mnt/appdata/homepage/config/` | YAML configuration Homepage |

## Données Persistantes

Toutes les données sont stockées sur NFS (`/mnt/appdata/`) :
- Sauvegardées quotidiennement vers Backblaze B2 via Rclone
- Incluses dans snapshots Btrfs du NAS
- Stratégie 3-2-1 appliquée

**En cas de crash Raspberry Pi** :
1. Réinstaller Raspberry Pi OS
2. Exécuter `bootstrap_rpi.yml`
3. Exécuter `deploy_rpi_stack.yml`
4. Services redémarrent avec données existantes (RPO < 5 minutes)

## Références

- Template source : `ansible/templates/rpi/docker-compose.yml.j2`
- Inventaire : `ansible/inventory/hosts.ini`
- Bootstrap RPi : `docs/bootstrap/control-tower.md`
- Services status : `docs/services-status.md`
- Architecture : `docs/homelab.md`
