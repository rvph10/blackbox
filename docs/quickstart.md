# Quickstart - Déploiement 0 à 60

Guide rapide pour reconstruire tout le homelab depuis zéro. Pour ma mémoire future quand j'aurai tout cassé.

## Vue d'ensemble

Ordre de déploiement :

1. OPNsense (routeur/firewall)
2. Proxmox (hyperviseur)
3. Raspberry Pi (services critiques + observabilité)
4. Services sur Proxmox (media, downloads, etc.)

Temps total estimé : ~4-6h selon ton café.

## Prérequis

**Matériel nécessaire** :

- GMKtec NucBox M6 (Proxmox)
- Raspberry Pi 5 8GB (Control Tower)
- NAS Cargo Intel N100 8GB (stockage)
- Clé USB pour installation Proxmox
- Accès clavier/écran pour config initiale

**Logiciels à télécharger** :

- [Proxmox VE ISO](https://www.proxmox.com/en/downloads)
- [Raspberry Pi OS Lite 64-bit](https://www.raspberrypi.com/software/)
- [OPNsense ISO](https://opnsense.org/download/)

**Infos à avoir sous la main** :

- Vault password Ansible
- Credentials Backblaze B2
- Accès GitHub pour récupérer ce repo

## Déploiement rapide

### 1. OPNsense (30 min)

**Installation** :

1. Flasher l'ISO OPNsense sur clé USB
2. Booter le GMKtec dessus et installer sur le disque
3. Config initiale : WAN sur DHCP, LAN sur 192.168.10.1/24

**Config réseau** :

```bash
# Interfaces
WAN: DHCP (box internet)
LAN: 192.168.10.1/24

# DHCP Server
Range: 192.168.10.100-192.168.10.250
DNS: 192.168.10.2 (AdGuard Home sur Raspberry Pi)
```

**Validation** :

- Web UI accessible sur https://192.168.10.1
- Devices récupèrent IP via DHCP
- Internet fonctionne depuis LAN

→ Détails : [deployment/02-opnsense.md](./deployment/02-opnsense.md)

### 2. Proxmox (45 min)

**Installation** :

1. Flasher ISO Proxmox sur clé USB
2. Installer sur le GMKtec
3. IP statique : 192.168.10.10

**Config de base** :

```bash
# Via SSH sur 192.168.10.10
# Désactiver enterprise repo
# Activer no-subscription repo
# Configurer stockage
```

**Utiliser le playbook** :

```bash
cd ansible/
ansible-playbook -i inventory/hosts.yml playbooks/bootstrap_pve.yml --ask-vault-pass
```

**Validation** :

- Web UI accessible : https://192.168.10.10:8006
- Storage configuré
- Updates installés

→ Détails : [deployment/01-proxmox.md](./deployment/01-proxmox.md)

### 3. Raspberry Pi (1h)

**Installation OS** :

1. Flasher Raspberry Pi OS Lite 64-bit
2. Activer SSH (fichier `ssh` vide dans `/boot`)
3. Configurer WiFi si besoin
4. IP statique : 192.168.10.2

**Bootstrap avec Ansible** :

```bash
cd ansible/
ansible-playbook -i inventory/hosts.yml playbooks/bootstrap_rpi.yml --ask-vault-pass
```

Ce playbook installe :

- Docker + Docker Compose
- Configuration NFS mount vers NAS
- Configuration système (timezone, hostname, etc.)

**Déployer la stack** :

```bash
ansible-playbook -i inventory/hosts.yml playbooks/deploy_rpi_stack.yml --ask-vault-pass
```

Services déployés :

- AdGuard Home (DNS : 192.168.10.2)
- Home Assistant (domotique)
- Homepage (dashboard)
- Tailscale (VPN)
- Grafana/Prometheus/Loki (observabilité)
- Uptime Kuma, Scrutiny, Dozzle, Diun (monitoring)

**Validation** :

```bash
# Vérifier que tous les conteneurs tournent
ssh rvph@192.168.10.2
docker ps

# Tester DNS
nslookup google.com 192.168.10.2

# Accéder aux UIs
# Homepage : http://192.168.10.2:3000
# Grafana : http://192.168.10.2:3001
# AdGuard : http://192.168.10.2:3002
```

→ Détails : [deployment/03-raspberry-pi.md](./deployment/03-raspberry-pi.md)

### 4. Services Proxmox (2h)

**Créer les VMs/LXCs** :

Via l'interface Proxmox ou avec Terraform (si j'ai le courage).

**VMs** :

- VM 110 : Media Stack (Ubuntu 24.04, 8GB RAM, GPU passthrough)
- VM 120 : Downloads (Ubuntu 24.04, 4GB RAM)

**LXCs** :

- LXC 200 : Infrastructure (Debian 12, 4GB RAM)
- LXC 220 : Misc services (Debian 12, 2GB RAM)

**Déployer les services** :

Pour chaque VM/LXC, utiliser les playbooks appropriés ou docker-compose.

→ Détails : [deployment/04-services.md](./deployment/04-services.md)

## Post-Installation

**Configurer les backups** :

```bash
ansible-playbook -i inventory/hosts.yml playbooks/deploy_nas_backup.yml --ask-vault-pass
```

**Vérifier le monitoring** :

- Tous les services dans Uptime Kuma
- Dashboards Grafana configurés
- Alertes Prometheus opérationnelles

**Configurer Tailscale** :

- Authentifier tous les devices
- Configurer subnet routing si besoin

## En cas de problème

**OPNsense ne route pas** :

- Vérifier les règles firewall WAN/LAN
- Vérifier que NAT outbound est configuré

**Proxmox injoignable** :

- Vérifier IP statique correcte
- Vérifier câble réseau
- Accès console directe si besoin

**Raspberry Pi ne boot pas** :

- Vérifier alimentation (5V 3A minimum)
- Re-flasher la carte SD
- Vérifier LED d'activité

**Services Docker ne démarrent pas** :

- Vérifier montages NFS : `mount | grep nfs`
- Vérifier logs : `docker compose logs`
- Vérifier ressources : `docker stats`

→ Plus de détails : [operations/troubleshooting.md](./operations/troubleshooting.md)

## Checklist finale

Avant de considérer que c'est terminé :

- [ ] Internet fonctionne via OPNsense
- [ ] Proxmox accessible et fonctionnel
- [ ] DNS résolu par AdGuard Home
- [ ] Services critiques UP (HA, Homepage)
- [ ] Monitoring opérationnel (Grafana, Uptime Kuma)
- [ ] Backups configurés et testés
- [ ] Tailscale connecté
- [ ] Toutes les UIs accessibles

Si tout est coché : bravo, tu peux aller te faire un café.

## Next Steps

- Configurer les dashboards Grafana
- Ajouter les alertes Prometheus
- Configurer Home Assistant
- Personnaliser Homepage
- Tester le restore des backups

→ Voir [operations/maintenance.md](./operations/maintenance.md) pour la maintenance régulière
