# Maintenance - Tâches Récurrentes

Guide des tâches de maintenance pour garder le homelab en bon état.

## Tâches Quotidiennes (Automatisées)

Ces tâches tournent en automatique, juste besoin de vérifier que ça marche :

### Backups (03:00 AM)

```bash
# Sur NAS Cargo
# Vérifie le dernier backup Rclone
rclone lsd b2_remote:blackbox-backup --max-depth 1

# Check les logs du dernier run
journalctl -u rclone-backup.service -n 50
```

**Si backup a échoué** :

- Vérifier connectivité Internet depuis NAS
- Vérifier crédits Backblaze B2
- Relancer manuellement : `systemctl start rclone-backup.service`

### LEDs NAS

- Extinction automatique : 23:00
- Allumage automatique : 09:00

**Contrôle manuel si besoin** :

```bash
# Sur NAS
sudo /volume1/appdata/ugreen-leds/scripts/leds-off.sh  # Éteindre
sudo /volume1/appdata/ugreen-leds/scripts/leds-on.sh   # Allumer
```

### Monitoring Services (Uptime Kuma - planifié)

Une fois déployé, checker le dashboard tous les matins :

- http://192.168.10.10:3002
- Tous les services doivent être verts
- Si rouge : voir [troubleshooting.md](./troubleshooting.md)

## Tâches Hebdomadaires

### Dimanche : Check Grafana

**Vérifier les métriques** (http://192.168.10.10:3001) :

- CPU usage : doit rester < 60% en moyenne
- RAM usage : vérifier pas de leak mémoire
- Disk I/O : pas de pic anormal
- Network : pas de saturation

**Dashboards à checker** :

- Node Exporter Full (ID 1860)
- Docker metrics
- Disk health (si Scrutiny déployé)

**Si anomalie** :

- Identifier le service qui consomme
- Vérifier logs avec `docker logs <container>`
- Restart si besoin : `docker restart <container>`

### Dimanche : Updates Système

#### Proxmox

```bash
# SSH vers 192.168.10.2
ssh root@192.168.10.2

# Check updates disponibles
apt update
apt list --upgradable

# Installer (si pas de breaking changes)
apt upgrade -y

# Reboot si kernel update
# ATTENTION : Redémarrer seulement si OPNsense peut redémarrer après
reboot
```

#### Raspberry Pi

```bash
# SSH vers 192.168.10.10
ssh rvph@192.168.10.10

# Updates OS
sudo apt update && sudo apt upgrade -y

# Updates Docker images (si force_pull activé dans playbook)
cd /opt/blackbox
docker compose pull
docker compose up -d

# Alternative : via Ansible
cd ~/Projects/blackbox/ansible
ansible-playbook -i inventory/hosts.yml playbooks/deploy_rpi_stack.yml --extra-vars "force_pull=true"
```

#### OPNsense

Via Web UI (https://192.168.10.1) :

1. System > Firmware > Check for updates
2. Installer si disponible
3. Reboot si demandé

**ATTENTION** : Redémarrage OPNsense = coupure Internet homelab pendant ~2 min

## Tâches Mensuelles

### Premier du mois : Vérifier Backups

```bash
# Tester restoration d'un fichier random depuis B2
rclone copy b2_remote:blackbox-backup/appdata/adguardhome/AdGuardHome.yaml /tmp/test-restore.yaml

# Vérifier que le fichier est OK
cat /tmp/test-restore.yaml

# Cleanup
rm /tmp/test-restore.yaml
```

**Si restore échoue** :

- Vérifier credentials Backblaze
- Vérifier retention policy (30 jours)
- Voir [backup-restore.md](./backup-restore.md)

### Premier du mois : Snapshot Btrfs (NAS)

Via Web UI NAS (http://192.168.10.5) :

1. Storage > Snapshots
2. Vérifier qu'il y a des snapshots récents
3. Créer snapshot manuel si besoin
4. Nettoyer vieux snapshots (> 30 jours)

### Premier du mois : Check Disques (S.M.A.R.T)

**Via NAS Web UI** :

- Storage > Disks > S.M.A.R.T Status
- Vérifier : Passed
- Température : < 50°C

**Si Scrutiny déployé** :

- http://192.168.10.10:8080
- Dashboard santé disques
- Alerts automatiques si dégradation

### Premier du mois : Clean Docker

```bash
# Sur Raspberry Pi ET VMs Docker
docker system prune -a --volumes -f

# Libère espace des images/volumes inutilisés
```

**ATTENTION** : Ne supprime QUE les volumes non utilisés. Appdata sur NFS est safe.

## Tâches Trimestrielles

### Vérifier Consommation Électrique

Avec un wattmètre, mesurer conso du rack :

- Idle : devrait être ~33W
- Charge moyenne : ~70W

**Si dérive importante** :

- Check température devices (surchauffe = conso)
- Vérifier pas de process anormal (htop/top)

### Test Restore Complet

Une fois par trimestre, tester un restore from scratch d'un service :

1. Choisir un service non-critique (ex: Homepage)
2. Supprimer son appdata : `rm -rf /mnt/appdata/homepage`
3. Restaurer depuis B2 : `rclone copy b2_remote:blackbox-backup/appdata/homepage /mnt/appdata/homepage`
4. Redémarrer le conteneur : `docker restart homepage`
5. Vérifier que ça fonctionne

**Si restore échoue** :

- Réévaluer stratégie backup
- Vérifier intégrité données B2

## Tâches Annuelles

### Renouvellement Certificats SSL

Certificats Let's Encrypt via Nginx Proxy Manager sont automatiques (renouvellement 60j avant expiration).

**Vérifier** :

- NPM Web UI > SSL Certificates
- Toutes les dates d'expiration > 30 jours

**Si proche expiration** :

- Force renew dans NPM
- Vérifier DNS Challenge fonctionne (credentials Cloudflare)

### Review Architecture

Une fois par an, relire [architecture/philosophy.md](../architecture/philosophy.md) et vérifier :

- Les choix sont toujours valides ?
- Y a-t-il de la complexité inutile accumulée ?
- Des services jamais utilisés à retirer ?

**Principe** : Simplifier > Accumuler

## Cheatsheet Ansible

Commandes courantes pour maintenance :

```bash
# Tout redéployer (rarement nécessaire)
ansible-playbook -i inventory/hosts.yml playbooks/site.yml

# Stack Raspberry Pi uniquement
ansible-playbook -i inventory/hosts.yml playbooks/deploy_rpi_stack.yml

# Proxmox config
ansible-playbook -i inventory/hosts.yml playbooks/bootstrap_pve.yml

# Tailscale update
ansible-playbook -i inventory/hosts.yml playbooks/install_tailscale.yml

# NAS backup config
ansible-playbook -i inventory/hosts.yml playbooks/deploy_nas_backup.yml

# Force pull nouvelles images Docker
ansible-playbook -i inventory/hosts.yml playbooks/deploy_rpi_stack.yml --extra-vars "force_pull=true"
```

## Monitoring Proactif

**Ce qu'il faut surveiller** :

| Métrique       | Seuil Alerte    | Action                               |
| -------------- | --------------- | ------------------------------------ |
| CPU Usage      | > 80% sustained | Identifier process gourmand          |
| RAM Usage      | > 90%           | Check memory leaks, restart services |
| Disk Usage     | > 85%           | Cleanup ou expand storage            |
| Disk Temp      | > 55°C          | Améliorer ventilation                |
| Network Errors | > 0.1%          | Check câbles/switch                  |

**Outils** :

- Grafana dashboards (temps réel)
- Uptime Kuma (disponibilité services)
- Scrutiny (santé disques)
- Logs centralisés (Loki)

## En Cas de Problème

Si quelque chose ne va pas :

1. Vérifier [troubleshooting.md](./troubleshooting.md)
2. Vérifier logs Grafana/Loki
3. Vérifier status services : `docker ps -a`
4. Vérifier réseau : `ping 192.168.10.1` (gateway)

**Principe de debug** :

1. Identifier le problème (quel service ?)
2. Vérifier logs (`docker logs`)
3. Vérifier dépendances (réseau, NFS, DNS)
4. Restart si besoin
5. Si ça persiste : restore depuis backup
