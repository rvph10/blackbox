# Secrets - Gestion des Secrets

Comment gérer les mots de passe, clés API et autres secrets du homelab.

## Principe

Tous les secrets sont stockés dans Ansible Vault chiffré :

- Fichier : `ansible/inventory/group_vars/all/vault.yml`
- Chiffrement : AES256
- Mot de passe vault : À garder dans ton password manager

**Ne JAMAIS** :

- Commiter des secrets en clair dans Git
- Partager le mot de passe vault
- Stocker des secrets dans les playbooks/configs non chiffrés

## Configuration Initiale

### Première fois (après clone du repo)

```bash
cd ansible/

# Créer le fichier de mot de passe vault
echo "TON_MOT_DE_PASSE_VAULT_ICI" > .vault_pass
chmod 600 .vault_pass

# Vérifier que c'est ignoré par Git
cat .gitignore | grep .vault_pass
```

**CRITIQUE** :

- Sauvegarder le mot de passe vault dans Bitwarden
- Sans ce mot de passe, les playbooks Ansible sont inutilisables
- Titre suggestion Bitwarden : "Homelab Ansible Vault Password"

### Créer un nouveau vault (si vault.yml n'existe pas)

```bash
cd ansible/

# Créer vault.yml
ansible-vault create inventory/group_vars/all/vault.yml

# Tu seras prompt pour le mot de passe
# Ensuite, éditer les variables (voir section Variables ci-dessous)
```

## Éditer les Secrets

```bash
cd ansible/

# Éditer le vault (demande le mot de passe)
ansible-vault edit inventory/group_vars/all/vault.yml
```

**Si tu as configuré .vault_pass** :

```bash
# Pas besoin de taper le mot de passe
ansible-vault edit inventory/group_vars/all/vault.yml --vault-password-file .vault_pass
```

**Ansible playbooks** utilisent automatiquement `.vault_pass` s'il existe.

## Variables dans vault.yml

### Structure Standard

```yaml
# Credentials système
vault_sudo_password: "password_sudo"
vault_ssh_public_key: "ssh-rsa AAA..."

# Credentials réseau
vault_pppoe_username: "username@PROXIMUS"
vault_pppoe_password: "password_proximus"

# Credentials services
vault_adguard_password: "password_adguard"
vault_ha_secret_key: "longue_string_random_pour_ha"

# Credentials cloud
vault_backblaze_account_id: "account_id_b2"
vault_backblaze_application_key: "key_b2"
vault_rclone_password: "password_rclone_crypt"

# Credentials Tailscale
vault_tailscale_auth_key: "tskey-auth-xxx"

# Credentials NPM / SSL
vault_cloudflare_api_token: "token_cloudflare_dns"
vault_cloudflare_email: "email@domain.com"

# Credentials Authentik (futur)
vault_authentik_secret_key: "secret_key_authentik"
vault_authentik_postgres_password: "password_postgres"
```

### Générer des Secrets Aléatoires

```bash
# Secret générique (32 chars)
openssl rand -base64 32

# Secret pour Django/Authentik (50 chars alphanumeric)
openssl rand -base64 50 | tr -d "=+/" | cut -c1-50

# UUID
uuidgen

# Password fort (20 chars)
openssl rand -base64 20
```

## Utiliser les Variables dans Playbooks

### Dans un playbook

```yaml
- name: Configure service with password
  template:
    src: service.conf.j2
    dest: /etc/service/config.conf
  vars:
    service_password: "{{ vault_service_password }}"
```

### Dans un template Jinja2

```jinja
# service.conf.j2
username=admin
password={{ vault_service_password }}
api_key={{ vault_api_key }}
```

## Vérifier la Sécurité

### Avant un commit

```bash
# Script de vérification
./ansible/scripts/check-security.sh
```

Ce script vérifie :

- Pas de secrets en clair dans les fichiers
- vault.yml est bien chiffré
- .vault_pass est ignoré par Git

### Si secrets accidentellement commitées

```bash
# URGENT : Changer TOUS les secrets exposés immédiatement
# Puis :

# Supprimer du dernier commit
git reset HEAD~1
git add -A
git commit -m "Remove secrets"

# Si déjà push : utiliser git-filter-repo ou équivalent
# Mais TOUJOURS changer les secrets d'abord !
```

## Rotation des Secrets

### Quand rotationner ?

- Exposition accidentelle (commit public, etc.)
- Changement de team/accès
- Tous les 6-12 mois (best practice)
- Après incident de sécurité

### Procédure de Rotation

1. **Générer nouveaux secrets**

```bash
# Exemple : nouveau password AdGuard
NEW_PASSWORD=$(openssl rand -base64 20)
echo $NEW_PASSWORD  # Copier
```

2. **Éditer vault.yml**

```bash
ansible-vault edit inventory/group_vars/all/vault.yml
# Remplacer ancien secret par nouveau
```

3. **Redéployer services affectés**

```bash
# Exemple : Redéployer stack Raspberry Pi
ansible-playbook -i inventory/hosts.yml playbooks/deploy_rpi_stack.yml
```

4. **Vérifier que services fonctionnent**

```bash
# Tester login avec nouveau password
curl -u admin:$NEW_PASSWORD http://192.168.10.10/api/status
```

5. **Update password manager**

- Mettre à jour Bitwarden avec nouveau secret

## Backup du Vault

### Backup Automatique (via Git)

Le `vault.yml` est versionné dans Git (chiffré), donc backup automatique.

**MAIS** : Le mot de passe vault n'est PAS dans Git !

### Backup Manuel du Mot de Passe Vault

**CRITICAL** : Sauvegarder dans plusieurs endroits :

1. **Bitwarden** : Entrée dédiée "Homelab Ansible Vault"
2. **Papier physique** : Coffre/Safe
3. **Backup encrypted** : Export Bitwarden chiffré sur autre support

**Si perte du mot de passe vault** :

- vault.yml est irrécupérable
- Il faut recréer tous les secrets from scratch
- Redéployer TOUT le homelab

## Secrets Externes (hors Ansible)

Certains secrets ne sont pas dans Ansible :

### OPNsense

- Password root : Défini lors installation
- Password web UI : Défini lors config initiale

**Storage** :

- Bitwarden : "Homelab OPNsense Root"
- Bitwarden : "Homelab OPNsense Web UI"

**Backup config** :

- OPNsense > System > Configuration > Backups
- Download XML, stocker dans `/backups-configs` sur NAS

### Proxmox

- Password root : Défini lors installation

**Storage** :

- Bitwarden : "Homelab Proxmox Root"

**Backup config** :

- Pas de config à backup (reconstruit via Ansible)

### NAS UGOS

- Password admin : Défini lors setup

**Storage** :

- Bitwarden : "Homelab NAS Cargo Admin"

**Backup config** :

- UGOS > Settings > Backup/Restore
- Download backup file monthly

### Services Docker (appdata)

Certains services créent leurs propres secrets dans appdata :

- AdGuard : `appdata/adguardhome/AdGuardHome.yaml`
- Home Assistant : `appdata/homeassistant/.storage/`
- etc.

**Backup** :

- Via Rclone → Backblaze B2 (quotidien)
- Via Btrfs snapshots (quotidien)

## Troubleshooting

### "ERROR: Decryption failed"

**Cause** : Mauvais mot de passe vault

**Solution** :

```bash
# Vérifier .vault_pass contient le bon mot de passe
cat ansible/.vault_pass

# Ou utiliser --ask-vault-pass pour taper manuellement
ansible-playbook -i inventory/hosts.yml playbooks/site.yml --ask-vault-pass
```

### "vault.yml not found"

**Cause** : Fichier vault manquant ou mauvais chemin

**Solution** :

```bash
# Vérifier existence
ls -la ansible/inventory/group_vars/all/vault.yml

# Si manquant, créer
cd ansible/
ansible-vault create inventory/group_vars/all/vault.yml
```

### J'ai perdu le mot de passe vault

**Pas de solution** : AES256 ne peut pas être cassé

**Recovery** :

1. Créer nouveau vault.yml avec nouveau mot de passe
2. Recréer TOUS les secrets (passwords, API keys, etc.)
3. Redéployer tout le homelab
4. Temps estimé : plusieurs heures

**Prévention** :

- Sauvegarder mot de passe vault dans 3+ endroits
- Tester régulièrement accès au mot de passe

## Best Practices

1. **Ne jamais commit secrets en clair**

   - Toujours utiliser vault.yml
   - Vérifier avec `check-security.sh`

2. **Rotation régulière**

   - Secrets critiques : Tous les 6 mois
   - Secrets exposés : Immédiatement

3. **Backup redondant**

   - Mot de passe vault dans 3+ endroits
   - Tester recovery régulièrement

4. **Secrets forts**

   - Minimum 20 caractères
   - Générer avec `openssl rand`
   - Ne pas réutiliser entre services

5. **Principle of Least Privilege**
   - Chaque service a ses propres secrets
   - Pas de "master password" partagé

**RAPPEL** : Sans mot de passe vault, le homelab est irrécupérable. BACKUP !
