# ☁️ deploy_nas_backup.yml

## Objectif

Configure le NAS Cargo pour effectuer des sauvegardes quotidiennes automatiques vers **Backblaze B2** (stockage cloud off-site) via **Rclone**.

Implémente la stratégie de sauvegarde **3-2-1** :
- **3 copies** : Live + NAS RAID 1 + Backblaze B2
- **2 supports** : Btrfs RAID 1 + Cloud
- **1 off-site** : Backblaze B2 (hors réseau local)

## Concept : Sauvegarde 3-2-1

```
┌─────────────────────────────────────┐
│ Données Live (VMs, Conteneurs)     │
│  ├─ /mnt/appdata                   │ (1ère copie)
│  └─ Disques VMs Proxmox            │
└─────────────────────────────────────┘
           ↓ NFS Mount + VZDump
┌─────────────────────────────────────┐
│ NAS Cargo (RAID 1 Btrfs)           │
│  ├─ /volume1/appdata               │ (2ème copie)
│  ├─ /volume1/proxmox-backups       │
│  └─ /volume1/backups-configs       │
└─────────────────────────────────────┘
           ↓ Rclone sync (03:00 AM)
┌─────────────────────────────────────┐
│ Backblaze B2 (Cloud)               │
│  ├─ bucket/appdata/                │ (3ème copie - off-site)
│  ├─ bucket/backups-configs/        │
│  └─ [Proxmox backups optionnel]    │
└─────────────────────────────────────┘
```

## Prérequis

### Variables Vault Nécessaires

| Variable | Description | Exemple |
|----------|-------------|---------|
| `vault_b2_account_id` | Account ID Backblaze B2 | `0123456789abcdef` |
| `vault_b2_account_key` | Application Key B2 | `K001xxxxxxxxxxxxxxxxxx` |
| `vault_b2_bucket` | Nom du bucket B2 | `blackbox-homelab-backup` |

**Obtention des credentials Backblaze B2** :
1. Créer compte sur [Backblaze](https://www.backblaze.com/b2/sign-up.html)
2. Créer bucket : Buckets → Create a Bucket
   - Bucket Name : `blackbox-homelab-backup`
   - Files in Bucket : Private
   - Default Encryption : Disabled (Rclone peut chiffrer)
3. Créer Application Key :
   - App Keys → Add a New Application Key
   - Name : `rclone-homelab`
   - Access : Read and Write
   - Bucket : `blackbox-homelab-backup`
4. Copier `keyID` (Account ID) et `applicationKey`

### Dépendances

- NAS Cargo accessible via SSH (`192.168.10.5`)
- Docker installé sur NAS (UGOS inclut Docker)
- Partages NFS déjà créés :
  - `/volume1/appdata`
  - `/volume1/backups-configs`
  - `/volume1/proxmox-backups`

## Actions du Playbook

### 1. Création Répertoires Configuration

```yaml
/volume1/appdata/rclone/config/  # Config rclone.conf
/volume1/appdata/rclone/         # Scripts et logs
```

Permissions : `0755` (propriétaire = user ansible)

### 2. Déploiement rclone.conf

Génération depuis template `../templates/nas/rclone.conf.j2` :

```ini
[b2_remote]
type = b2
account = {{ vault_b2_account_id }}
key = {{ vault_b2_account_key }}
hard_delete = false  # Soft delete pour protection
```

Permissions : `0600` (lecture/écriture propriétaire uniquement - SÉCURITÉ)

### 3. Création Script de Backup

Script bash `/volume1/appdata/rclone/backup_to_b2.sh` :

**Fonctions** :
- Sync `/volume1/appdata` → `b2:bucket/appdata`
- Sync `/volume1/backups-configs` → `b2:bucket/backups-configs`
- Vérification backups Proxmox (fichiers `.vma` < 24h)
- Génération JSON status (`/volume1/appdata/rclone/backup_status.json`)
- Logs dans `/volume1/appdata/rclone/backup.log`

**Méthode Rclone** : `sync` (unidirectionnel, destination = copie exacte source)

### 4. Planification Cron

```cron
0 3 * * * /volume1/appdata/rclone/backup_to_b2.sh
```

Exécution quotidienne à **03:00 AM** (heure creuse).

## Données Sauvegardées

| Source NAS | Destination B2 | Contenu | Taille Estimée |
|------------|----------------|---------|----------------|
| `/volume1/appdata/` | `bucket/appdata/` | Données persistantes conteneurs Docker (AdGuard, HA, Jellyfin, Immich, etc.) | 50-200 GB |
| `/volume1/backups-configs/` | `bucket/backups-configs/` | Configs Ansible, vault, exports OPNsense | < 1 GB |
| `/volume1/proxmox-backups/` | ❌ Non syncé | Backups VZDump VMs (vérification présence seulement) | 100-500 GB |

**Note** : Backups Proxmox VZDump ne sont PAS syncés vers B2 (trop volumineux). Seulement vérification qu'un backup < 24h existe.

**Alternative si besoin sync Proxmox** : Modifier script pour ajouter ligne :
```bash
docker run --rm -v {{ rclone_config_dir }}:/config/rclone -v /volume1/proxmox-backups:/data:ro rclone/rclone sync /data b2_remote:{{ vault_b2_bucket }}/proxmox-backups --fast-list
```

## Commande d'Exécution

```bash
cd /home/rvph/Projects/blackbox/ansible
ansible-playbook playbooks/deploy_nas_backup.yml
```

### Dry-Run (Simulation)

```bash
ansible-playbook playbooks/deploy_nas_backup.yml --check
```

## Vérification Post-Déploiement

### 1. Vérifier Fichiers Créés

```bash
ssh 192.168.10.5

# Config rclone
ls -la /volume1/appdata/rclone/config/
cat /volume1/appdata/rclone/config/rclone.conf  # Vérifier credentials (ATTENTION SECRET)

# Script backup
ls -la /volume1/appdata/rclone/backup_to_b2.sh
cat /volume1/appdata/rclone/backup_to_b2.sh
```

### 2. Tester Connexion Backblaze B2

```bash
# Tester Rclone depuis NAS (via Docker)
ssh 192.168.10.5
docker run --rm -v /volume1/appdata/rclone/config:/config/rclone rclone/rclone lsd b2_remote:{{ vault_b2_bucket }}
```

**Output attendu** :
```
          -1 2024-12-22 03:00:00        -1 appdata
          -1 2024-12-22 03:00:00        -1 backups-configs
```

### 3. Vérifier Cron Configuré

```bash
ssh 192.168.10.5
crontab -l | grep backup_to_b2
```

**Output attendu** :
```
0 3 * * * /volume1/appdata/rclone/backup_to_b2.sh
```

### 4. Exécution Manuelle Test

```bash
ssh 192.168.10.5
/volume1/appdata/rclone/backup_to_b2.sh

# Suivre logs en temps réel
tail -f /volume1/appdata/rclone/backup.log
```

### 5. Vérifier Status JSON

```bash
ssh 192.168.10.5
cat /volume1/appdata/rclone/backup_status.json | jq .
```

**Output attendu** :
```json
{
  "cloud_appdata": {
    "label": "Cloud Appdata",
    "status": "ok",
    "last_run": "2024-12-22T03:15:42"
  },
  "cloud_configs": {
    "label": "Cloud Configs",
    "status": "ok",
    "last_run": "2024-12-22T03:16:10"
  },
  "pve_backups": {
    "label": "PVE Backups",
    "status": "ok",
    "last_run": "2024-12-22T02:00:00"
  }
}
```

### 6. Vérifier Données dans Backblaze B2

**Via Web UI** :
1. Login [Backblaze](https://secure.backblaze.com/user_signin.htm)
2. Buckets → `blackbox-homelab-backup`
3. Browse Files → Vérifier présence `appdata/` et `backups-configs/`

**Via Rclone** :
```bash
# Lister fichiers dans bucket
docker run --rm -v /volume1/appdata/rclone/config:/config/rclone rclone/rclone ls b2_remote:{{ vault_b2_bucket }}/appdata --max-depth 2

# Vérifier taille totale
docker run --rm -v /volume1/appdata/rclone/config:/config/rclone rclone/rclone size b2_remote:{{ vault_b2_bucket }}
```

## Troubleshooting

### Problème : Erreur authentification B2

**Symptôme** :
```
Failed to create file system for "b2_remote:bucket":
authorization failure: Application Key is incorrect
```

**Solution** :
```bash
# Vérifier credentials dans vault
ansible-vault view inventory/group_vars/all/vault.yml | grep b2

# Re-générer Application Key sur Backblaze
# Mettre à jour vault
ansible-vault edit inventory/group_vars/all/vault.yml

# Re-déployer
ansible-playbook playbooks/deploy_nas_backup.yml
```

### Problème : Bucket non trouvé

**Symptôme** :
```
directory not found
```

**Solution** :
```bash
# Vérifier nom bucket exact
# Sur Backblaze Web → Buckets → Nom exact du bucket

# Mettre à jour vault
vault_b2_bucket: "nom-exact-du-bucket"  # Attention à la casse !
```

### Problème : Script backup ne s'exécute pas (cron)

**Diagnostic** :
```bash
# Vérifier cron actif
ssh 192.168.10.5
systemctl status cron  # Ou crond selon système

# Vérifier logs cron
tail /var/log/syslog | grep CRON
tail /var/log/cron | grep backup_to_b2
```

**Solution** :
```bash
# Si cron pas actif
systemctl enable cron
systemctl start cron

# Tester exécution manuelle d'abord
/volume1/appdata/rclone/backup_to_b2.sh
```

### Problème : Backup très lent

**Symptôme** : Sync prend > 2h pour quelques GB.

**Causes possibles** :
- Bande passante upload limitée
- Trop de petits fichiers (overhead)
- B2 région lointaine

**Optimisations** :
```bash
# Ajouter flags rclone dans script :
--transfers 8          # Parallélisation uploads (défaut: 4)
--checkers 16          # Parallélisation vérifications
--fast-list            # Utilise moins d'API calls (déjà inclus)
--bwlimit 10M          # Limiter bande passante (si saturation)

# Exemple modifié :
docker run --rm -v /config/rclone -v /data:ro rclone/rclone sync /data b2_remote:bucket/appdata --fast-list --transfers 8 --checkers 16
```

### Problème : Coûts B2 élevés

**Tarification Backblaze B2** (2024) :
- Stockage : **$0.006/GB/mois** (6$ pour 1 TB)
- Download : $0.01/GB (premiers 3x stockage gratuit)
- API Calls : 2500 gratuits/jour, puis $0.004/10k

**Optimisations coûts** :
```bash
# Lifecycle rules (dans Backblaze Web)
# Supprimer anciennes versions après 30 jours
Bucket Settings → Lifecycle Settings → Keep prior versions for 30 days

# Filtrer fichiers à ne pas sauvegarder
# Dans script backup, exclure :
--exclude "*.tmp" --exclude "*.log" --exclude "cache/**"
```

## Surveillance du Backup

### Monitoring Status via Dashboard

Le fichier JSON `/volume1/appdata/rclone/backup_status.json` est conçu pour être lu par le dashboard Python du Raspberry Pi.

**Intégration** :
```python
# Dans ansible/templates/rpi/dashboard/monitor.py
import json
import requests

def check_backup_status():
    url = "http://192.168.10.5/appdata/rclone/backup_status.json"  # Via NFS ou HTTP
    status = json.load(open("/mnt/appdata/rclone/backup_status.json"))

    for key, data in status.items():
        if data['status'] != 'ok':
            alert(f"Backup {data['label']} failed!")
```

### Alerting (Recommandé)

**Option 1 : Healthchecks.io**
```bash
# Ajouter à la fin du script backup_to_b2.sh
if [ $RES_APP -eq 0 ] && [ $RES_CONF -eq 0 ]; then
    curl -fsS https://hc-ping.com/your-uuid-here > /dev/null
fi
```

**Option 2 : Email via msmtp**
```bash
# Si backup échoue, envoyer email
if [ $RES_APP -ne 0 ]; then
    echo "Backup appdata failed!" | mail -s "Backup Error" admin@example.com
fi
```

## Restauration depuis Backblaze B2

### Restauration Complète (Disaster Recovery)

**Scénario** : NAS crashé, données perdues.

```bash
# Sur nouveau NAS ou NAS réparé
# 1. Réinstaller UGOS/OS
# 2. Reconfigurer Rclone via Ansible
ansible-playbook playbooks/deploy_nas_backup.yml

# 3. Restaurer données depuis B2
ssh 192.168.10.5
docker run --rm -v /volume1/appdata/rclone/config:/config/rclone -v /volume1/appdata:/data rclone/rclone copy b2_remote:{{ vault_b2_bucket }}/appdata /data --progress

docker run --rm -v /volume1/appdata/rclone/config:/config/rclone -v /volume1/backups-configs:/data rclone/rclone copy b2_remote:{{ vault_b2_bucket }}/backups-configs /data --progress

# 4. Redémarrer services
# VMs Proxmox restaurées depuis backups locaux ou manuels
# Conteneurs Docker redémarrent avec données restaurées
```

**RPO (Recovery Point Objective)** : 24h max (dernière sync quotidienne)
**RTO (Recovery Time Objective)** : 2-6h (téléchargement + restauration)

### Restauration Fichier Spécifique

```bash
# Restaurer seulement config Home Assistant
ssh 192.168.10.5
docker run --rm -v /volume1/appdata/rclone/config:/config/rclone -v /volume1/appdata:/data rclone/rclone copy b2_remote:{{ vault_b2_bucket }}/appdata/homeassistant /data/homeassistant --progress
```

## Coûts Estimés

**Exemple configuration type** :
- Données : 100 GB (appdata + configs)
- Sync quotidien (incrémental, ~5 GB changements/jour)

**Coûts mensuels** :
```
Stockage : 100 GB × $0.006 = $0.60
Download : Quasi nul (seulement restaurations)
API Calls : Inclus dans gratuit
──────────────────────────────────
TOTAL : ~$0.60-1.00/mois (négligeable)
```

Pour 1 TB : ~$6-7/mois

## Sécurité

### Chiffrement

**Option 1 : Chiffrement Backblaze** (Default Encryption dans bucket)
- Chiffrement côté serveur (SSE)
- Clés gérées par Backblaze

**Option 2 : Chiffrement Rclone (Recommandé)**
```ini
# Dans rclone.conf
[b2_encrypted]
type = crypt
remote = b2_remote:{{ vault_b2_bucket }}
password = {{ vault_rclone_encryption_password }}  # À ajouter dans vault
password2 = {{ vault_rclone_encryption_salt }}
```

**Avantage** : Backblaze ne peut pas lire vos données (zero-knowledge).

### Rotation Credentials

```bash
# Tous les 90 jours, regénérer Application Key B2
# 1. Backblaze Web → App Keys → Delete old key
# 2. Create new key
# 3. Mettre à jour vault
ansible-vault edit inventory/group_vars/all/vault.yml

# 4. Re-déployer
ansible-playbook playbooks/deploy_nas_backup.yml
```

## Références

- Rclone B2 documentation : [https://rclone.org/b2/](https://rclone.org/b2/)
- Backblaze B2 Pricing : [https://www.backblaze.com/b2/cloud-storage-pricing.html](https://www.backblaze.com/b2/cloud-storage-pricing.html)
- Template source : `ansible/templates/nas/rclone.conf.j2`
- Stratégie 3-2-1 : `docs/homelab.md` (section 5)
- Variables vault : `ansible/inventory/group_vars/all/vault.yml`
