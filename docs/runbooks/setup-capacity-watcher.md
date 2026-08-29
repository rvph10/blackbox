# Runbook — autorégulation capacité + bande passante

Contexte et choix : [ADR-019](../adr/019-autoregulation-capacite-bande-passante.md).
Deux morceaux : **Jellystat** (observation) + **capacity-watcher**
(script + timer systemd qui agit sur les seuils).

## 1. Jellystat

### 1.1 Secrets

```bash
ssh nucbox
cd ~/blackbox/prod
# Ajouter au .env existant (deux valeurs aléatoires DISTINCTES) :
echo "JELLYSTAT_DB_PASSWORD=$(openssl rand -base64 32)" >> .env
echo "JELLYSTAT_JWT_SECRET=$(openssl rand -base64 32)"  >> .env
```

### 1.2 Déploiement

Le `docker-compose.yml` porte déjà les services `jellystat` + `jellystat-db`
(déployé par Ansible, rôle `deploy`). Sinon :

```bash
cd ~/blackbox/prod
docker compose up -d jellystat-db jellystat
```

### 1.3 Première configuration

1. Ouvrir `http://nucbox:3000` **via Tailscale** (jamais exposé publiquement).
2. Créer le compte admin (premier écran).
3. Settings → **Jellyfin** :
   - Server URL : `http://jellyfin:8096`
   - API Key : Jellyfin Dashboard → Advanced → API Keys → nouvelle clé
     « Jellystat »
4. Lancer un **Full Sync** (Settings → Tasks). L'historique se remplit au
   fil des lectures ensuite.

## 2. capacity-watcher

### 2.1 Clé API Jellyfin dédiée

Jellyfin Dashboard → Advanced → API Keys → nouvelle clé **capacity-watcher**
(clé distincte de celle du bot et de Jellystat, pour pouvoir la révoquer
indépendamment).

### 2.2 `.env`

```bash
ssh nucbox "cat > ~/blackbox/scripts/capacity-watcher/.env <<'EOF'
ADMIN_ALERT_WEBHOOK_URL=<même webhook admin que gluetun-healthcheck>
COMMUNITY_WEBHOOK_URL=<webhook du salon communautaire, ou vide>
JELLYFIN_URL=http://localhost:8096
JELLYFIN_API_KEY=<clé capacity-watcher de l'étape 2.1>
MEDIA_MOUNT=/mnt/nas-media
DISK_WARN_PCT=85
DISK_CRIT_PCT=92
UPLOAD_WARN_MBPS=14
UPLOAD_CRIT_MBPS=17
QBT_URL=http://localhost:8080
QBT_USER=<utilisateur WebUI qBittorrent>
QBT_PASS=<mot de passe WebUI qBittorrent>
EOF
chmod 600 ~/blackbox/scripts/capacity-watcher/.env"
```

`jq` doit être présent (`sudo apt install -y jq` — sinon fourni par le rôle
Ansible `base`).

### 2.3 Limite alternative d'upload qBittorrent

Pour que l'action CRITIQUE serve à quelque chose, définir la limite dans
qBittorrent : WebUI → Options → **Vitesse** → *Débits alternatifs* →
**Upload** = ~30 % du débit montant (ex. 6144 KiB/s → mettre plutôt en
Ko : viser ~5 Mbit/s soit ~600 Kio/s aujourd'hui). Le watcher ne fait que
**basculer** ce mode, il ne le configure pas.

Laisser `QBT_USER`/`QBT_PASS` vides désactive proprement cette action
(alertes Discord seules).

### 2.4 Script + timer

Déployés par Ansible (`deploy` → script, `systemd_timers` → unité). Manuel :

```bash
scp infra/scripts/capacity-watcher/check-capacity.sh nucbox:~/blackbox/scripts/capacity-watcher/
scp infra/scripts/capacity-watcher/capacity-watcher.service \
    infra/scripts/capacity-watcher/capacity-watcher.timer nucbox:~/
ssh nucbox '
sudo mv ~/capacity-watcher.service ~/capacity-watcher.timer /etc/systemd/system/ &&
sudo systemctl daemon-reload &&
sudo systemctl enable --now capacity-watcher.timer &&
chmod +x ~/blackbox/scripts/capacity-watcher/check-capacity.sh
'
```

### 2.5 Test manuel

```bash
ssh nucbox "~/blackbox/scripts/capacity-watcher/check-capacity.sh; echo EXIT=\$?"
cat ~/blackbox/scripts/capacity-watcher/.last_state   # OK / WARN / CRIT
```

`EXIT=0` attendu. Le script n'alerte qu'au **changement** de niveau
(fichier `.last_state`). Pour forcer un test d'alerte : baisser
temporairement `UPLOAD_WARN_MBPS=0` dans le `.env`, relancer, vérifier le
message Discord, remettre la valeur, relancer (retour OK).

Vérifier la planification :
```bash
ssh nucbox "systemctl list-timers capacity-watcher.timer --no-pager"
```

## 3. Après la fibre (15/09)

```bash
ssh nucbox "speedtest --simple"   # noter l'upload réel
# éditer ~/blackbox/scripts/capacity-watcher/.env :
#   UPLOAD_WARN_MBPS ≈ 70 % de l'upload mesuré
#   UPLOAD_CRIT_MBPS ≈ 85 % de l'upload mesuré
ssh nucbox "sudo systemctl restart capacity-watcher.timer"
```

Rien d'autre à toucher — pas de changement de code.

## 4. Ce qui n'est pas couvert

- Jellystat (`data/jellystat/`) n'est **pas** dans le backup restic : la
  base Postgres se reconstruit depuis l'historique Jellyfin (Full Sync).
- Le watcher ne régule pas le transcodage lui-même (nombre de flux) — c'est
  Jellyfin qui plafonne (`MaxStreamingBitrate`, limites par utilisateur).
  Le watcher agit sur le **partage** du lien montant entre streaming et
  seeding.
