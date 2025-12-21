# 🛠️ Guide d'Opérations et Maintenance

Ce document complète la documentation d'architecture en détaillant les tâches quotidiennes d'administration, la gestion des secrets et les procédures de dépannage.

## 🔐 1. Gestion des Secrets (Ansible Vault)

Toute la configuration sensible (mots de passe, clés API, clés SSH) est chiffrée dans le fichier `ansible/inventory/group_vars/all/vault.yml`.

### A. Configuration Initiale (Post-Clone)

Pour exécuter les playbooks, vous devez créer le fichier de mot de passe (ignoré par Git) :

```bash
# À la racine du dossier ansible/
echo "VOTRE_MOT_DE_PASSE_VAULT" > .vault_pass
chmod 600 .vault_pass
```

> ⚠️ **CRITIQUE :** Ce mot de passe doit être sauvegardé dans votre gestionnaire de mots de passe (ex: Bitwarden). Sans lui, la configuration est inutilisable.

### B. Modifier les variables chiffrées

Ne jamais éditer `vault.yml` directement avec un éditeur de texte. Utiliser :

```bash
cd ansible/
ansible-vault edit inventory/group_vars/all/vault.yml
```

### C. Vérifier la sécurité avant commit

Un script est disponible pour éviter de commiter des secrets en clair :

```bash
./ansible/scripts/check-security.sh
```

---

## 🚀 2. Cheatsheet Ansible

Commandes courantes à exécuter depuis le dossier `ansible/`.

### Déploiements complets

```bash
# Tout le homelab (rarement utilisé)
ansible-playbook -i inventory/hosts.ini playbooks/site.yml

# Uniquement la stack Raspberry Pi (Docker, DNS, etc.)
ansible-playbook -i inventory/hosts.ini playbooks/deploy_rpi_stack.yml

# Mise à jour de la configuration Proxmox
ansible-playbook -i inventory/hosts.ini playbooks/bootstrap_pve.yml
```

### Maintenance ciblée

```bash
# Mettre à jour uniquement Tailscale sur le Pi
ansible-playbook -i inventory/hosts.ini playbooks/install_tailscale.yml --tags tailscale

# Forcer la mise à jour des conteneurs Docker (pull latest)
ansible-playbook -i inventory/hosts.ini playbooks/deploy_rpi_stack.yml --extra-vars "force_pull=true"
```

---

## 💾 3. Procédures de Restauration des Données

### A. Restauration Rapide (Panne Compute)

Si le RPi ou la VM Docker meurt, les données sont sauves sur le NAS (`/volume1/appdata`).

1. **Réinstaller l'OS / VM.**
2. **Relancer le Playbook Ansible correspondant.**
   - Le playbook remonte automatiquement les partages NFS.
   - Les conteneurs redémarrent en utilisant les données existantes sur le NAS.

### B. Restauration Désastre (Perte NAS)

Si le NAS est perdu (incendie, vol, panne disques multiples), les données sont chez **Backblaze B2**.

1. **Reconstruire le NAS (Hardware + OS).**
2. **Configurer Rclone** (via Ansible `deploy_nas_backup.yml`).
3. **Lancer la restauration** (depuis le NAS en SSH) :

```bash
# Lister les snapshots disponibles
rclone lsd b2_remote:nom-du-bucket

# Restaurer appdata (Exemple)
rclone copy b2_remote:nom-du-bucket/appdata /volume1/appdata --progress
```

---

## 🩺 4. Dépannage Courant

### Problème DNS (Plus d'internet)

Si AdGuard (sur le Pi) est planté, tout le réseau perd la résolution DNS.

**Solution d'urgence :**

1. Se connecter à OPNsense (`192.168.10.1`).
2. Aller dans **Services > ISC DHCPv4 > [LAN]**.
3. Changer le DNS de `192.168.10.2` (Pi) vers `1.1.1.1` (Cloudflare).
4. Redémarrer les clients ou reconnecter le réseau.

### Problème Montage NFS

Si les conteneurs Docker ne démarrent pas, vérifier le montage NAS sur le client :

```bash
# Sur le client (RPi ou VM)
df -h | grep /mnt/appdata
```

Si vide :

1. Vérifier que le NAS est pingable (`192.168.10.5`).
2. Tenter un montage manuel pour voir l'erreur :
   ```bash
   sudo mount -a -v
   ```

### Contrôle des LEDs NAS

Les LEDs du NAS UGREEN s'éteignent automatiquement à 23h et se rallument à 9h.

**Contrôle manuel :**

```bash
# Éteindre immédiatement
sudo /volume1/appdata/ugreen-leds/scripts/leds-off.sh

# Rallumer immédiatement
sudo /volume1/appdata/ugreen-leds/scripts/leds-on.sh
```

**Reconfiguration :**
Si les horaires doivent être modifiés, éditer le playbook `deploy_nas_leds.yml` et redéployer.
