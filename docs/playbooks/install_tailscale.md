# 🔐 install_tailscale.yml

## Objectif

Installe et configure Tailscale sur le Raspberry Pi 5 en mode **subnet router**, permettant l'accès distant au réseau homelab (`192.168.10.0/24`) via VPN mesh.

## Concept : Subnet Router

```
Internet (Mobile/Laptop)
    ↓
Tailscale Mesh (100.x.y.z)
    ↓
Raspberry Pi 5 (Subnet Router)
    ↓
Réseau Homelab (192.168.10.0/24)
    ├─ OPNsense (192.168.10.1)
    ├─ AdGuard (192.168.10.2)
    ├─ Proxmox (192.168.10.10)
    └─ NAS (192.168.10.5)
```

**Avantage** : Accès sécurisé à tous les services homelab sans ouvrir de ports sur le routeur.

## Prérequis

### Variables Vault Nécessaires

| Variable | Description | Exemple |
|----------|-------------|---------|
| `vault_tailscale_auth_key` | Clé d'authentification Tailscale (one-time ou reusable) | `tskey-auth-xxxxx` |

**Obtention de la clé** :
1. Connexion à [Tailscale Admin Console](https://login.tailscale.com/admin)
2. Settings → Keys → Generate auth key
3. Cocher "Reusable" et "Ephemeral" selon besoin
4. Copier la clé dans `vault.yml`

### Dépendances

- Raspberry Pi avec connexion internet
- Compte Tailscale actif (gratuit pour usage personnel)
- Kernel avec support IP forwarding

## Actions du Playbook

### 1. Installation Tailscale

```yaml
- Ajout de la clé GPG Tailscale
- Ajout du repository APT officiel (Debian Bookworm)
- Installation du package `tailscale`
```

**Repository** : `deb [signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg] https://pkgs.tailscale.com/stable/debian bookworm main`

### 2. Configuration Système (IP Forwarding)

Pour que le Raspberry Pi puisse router le trafic entre Tailscale et le LAN :

```yaml
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
```

Modifications appliquées via `sysctl` et rendues persistantes dans `/etc/sysctl.conf`.

### 3. Connexion et Advertisement

```bash
tailscale up \
  --authkey={{ vault_tailscale_auth_key }} \
  --advertise-routes=192.168.10.0/24 \
  --accept-routes \
  --reset
```

**Paramètres** :
- `--authkey` : Authentification automatique (pas de login manuel)
- `--advertise-routes` : Annonce le subnet 192.168.10.0/24 au réseau Tailscale
- `--accept-routes` : Accepte les routes d'autres subnet routers
- `--reset` : Force reconnexion avec nouveaux paramètres

## Commande d'Exécution

```bash
cd /home/rvph/Projects/blackbox/ansible
ansible-playbook playbooks/install_tailscale.yml
```

### Variables à Configurer

Avant exécution, vérifier que `vault_tailscale_auth_key` est définie :

```bash
# Éditer vault
ansible-vault edit inventory/group_vars/all/vault.yml

# Ajouter/vérifier
vault_tailscale_auth_key: "tskey-auth-xxxxxxxxxxxxxxxxxxxxx"
```

## Vérification Post-Déploiement

### 1. Vérifier Service Actif

```bash
ssh control-tower.blackbox.homes
sudo tailscale status
```

**Output attendu** :
```
100.x.y.z   control-tower    rvph@       linux   active; relay "fra", tx 1234 rx 5678
192.168.10.0/24  advertised  # ← Route annoncée
```

### 2. Vérifier IP Tailscale

```bash
ip addr show tailscale0
```

**Output attendu** :
```
5: tailscale0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP>
    inet 100.x.y.z/32 scope global tailscale0
```

### 3. Vérifier IP Forwarding

```bash
sysctl net.ipv4.ip_forward
sysctl net.ipv6.conf.all.forwarding
```

**Output attendu** :
```
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
```

### 4. Approuver Route dans Tailscale Admin

**IMPORTANT** : Par défaut, les routes subnet doivent être approuvées manuellement.

1. Aller sur [Tailscale Admin](https://login.tailscale.com/admin/machines)
2. Trouver `control-tower`
3. Cliquer sur "..." → "Edit route settings"
4. Cocher `192.168.10.0/24` dans "Subnet routes"
5. Sauvegarder

### 5. Tester Connectivité depuis Client Distant

```bash
# Sur laptop/mobile connecté à Tailscale
ping 192.168.10.2   # AdGuard
ping 192.168.10.10  # Proxmox

# Accès web
curl http://192.168.10.2:8123  # Home Assistant
```

## Troubleshooting

### Problème : Route non annoncée

**Symptôme** :
```bash
tailscale status
# Pas de ligne "192.168.10.0/24 advertised"
```

**Solution** :
```bash
# Forcer reconnexion
sudo tailscale down
sudo tailscale up \
  --authkey=<nouvelle-clé> \
  --advertise-routes=192.168.10.0/24 \
  --reset
```

### Problème : IP Forwarding non activé

**Symptôme** : Connexion Tailscale OK mais impossibilité de ping le LAN.

**Diagnostic** :
```bash
sysctl net.ipv4.ip_forward
# Si retourne 0 → forwarding désactivé
```

**Solution** :
```bash
# Activer temporairement
sudo sysctl -w net.ipv4.ip_forward=1

# Rendre permanent
echo "net.ipv4.ip_forward = 1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Problème : Auth key expirée

**Symptôme** :
```
Error: authkey expired
```

**Solution** :
1. Générer nouvelle auth key sur [Tailscale Admin](https://login.tailscale.com/admin/settings/keys)
2. Mettre à jour vault :
   ```bash
   ansible-vault edit inventory/group_vars/all/vault.yml
   ```
3. Re-exécuter playbook

### Problème : Conflit firewall

**Symptôme** : Tailscale connecté mais LAN inaccessible depuis client distant.

**Diagnostic** :
```bash
# Vérifier règles iptables
sudo iptables -L -n -v
```

**Solution** :
```bash
# Autoriser forwarding Tailscale → LAN
sudo iptables -A FORWARD -i tailscale0 -j ACCEPT
sudo iptables -A FORWARD -o tailscale0 -j ACCEPT

# Rendre permanent (installer iptables-persistent)
sudo apt install iptables-persistent
sudo netfilter-persistent save
```

## Configuration Avancée

### Désactiver Key Expiry

Par défaut, les devices Tailscale expirent après 180 jours.

**Désactivation** :
1. [Tailscale Admin](https://login.tailscale.com/admin/machines)
2. Sélectionner `control-tower`
3. "..." → "Disable key expiry"

### Exit Node (Optionnel)

Transformer le Raspberry Pi en exit node (tout le trafic internet passe par lui) :

```bash
sudo tailscale up \
  --advertise-exit-node \
  --advertise-routes=192.168.10.0/24
```

**Attention** : Augmente significativement la bande passante consommée.

### MagicDNS

Activer résolution DNS automatique (ex: `control-tower` au lieu de `100.x.y.z`) :

1. [Tailscale Admin](https://login.tailscale.com/admin/dns)
2. Enable MagicDNS
3. Ajouter suffixe personnalisé (ex: `blackbox.ts.net`)

Accès devient : `http://control-tower.blackbox.ts.net:8123`

## Stratégie "Zero Trust"

Tailscale est utilisé dans l'architecture homelab pour :

✅ **Accès distant sans port forwarding**
- Aucun port ouvert sur box FAI
- Pas d'exposition publique des services

✅ **Backup de connectivité**
- Si OPNsense crash, accès via Tailscale persiste
- Permet debug à distance

✅ **Authentification multi-facteur**
- Tailscale supporte SSO (Google, GitHub, etc.)
- Pas de mots de passe stockés

✅ **Chiffrement de bout-en-bout**
- WireGuard avec clés éphémères
- Aucun trafic en clair

## Intégration avec Services

### Accès Jellyfin via Tailscale

```
URL interne : http://192.168.10.100:8096  (depuis LAN)
URL Tailscale : http://192.168.10.100:8096  (via subnet router)
```

### DNS Split Horizon

Configuration DNS pour résolution différente selon origine :

**Sur AdGuard Home** :
- LAN : `jellyfin.blackbox.homes` → `192.168.10.100`
- Tailscale : `jellyfin.blackbox.homes` → `192.168.10.100` (via subnet)

**Avantage** : Même URL, routing automatique.

## Surveillance

### Metrics Tailscale

```bash
# Statistiques connexion
sudo tailscale status --json | jq '.Peer[] | {name: .HostName, tx: .TxBytes, rx: .RxBytes}'

# Test latence
sudo tailscale ping control-tower
```

### Logs

```bash
# Logs service systemd
sudo journalctl -u tailscaled -f

# Logs netfilter (debug routing)
sudo tailscale debug netfilter
```

## Sécurité

### ACLs Tailscale (Recommandé)

Limiter l'accès au subnet par utilisateur/device :

**Fichier ACL** (Tailscale Admin → Access Controls) :
```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["group:admins"],
      "dst": ["192.168.10.0/24:*"]
    },
    {
      "action": "accept",
      "src": ["group:family"],
      "dst": ["192.168.10.2:8123", "192.168.10.100:8096"]
    }
  ]
}
```

**Effet** :
- Admins : accès complet au LAN
- Famille : accès seulement Home Assistant + Jellyfin

### Audit Logs

Tailscale loggue tous les accès :
- [Admin Console](https://login.tailscale.com/admin/logs) → Logs
- Voir qui a accédé à quoi et quand

## Références

- Documentation officielle : [Tailscale Subnet Router](https://tailscale.com/kb/1019/subnets/)
- Architecture homelab : `docs/homelab.md`
- Variables vault : `ansible/inventory/group_vars/all/vault.yml`
- Bootstrap Raspberry Pi : `docs/bootstrap/control-tower.md`
