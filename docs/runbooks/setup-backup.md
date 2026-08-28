# Runbook — backup restic (NAS local + Google Drive)

Contexte et choix : [ADR-011](../adr/011-backup-restic-rclone.md).

## 1. Remote rclone (Google Drive)

Étape à faire par l'utilisateur (connexion à son propre compte Google, pas
automatisable) :

```bash
ssh nucbox
rclone config
# n (new remote) → nom "gdrive" → storage "18" (Google Drive)
# client_id / client_secret : laisser vide
# scope : "1" (accès complet)
# Use auto config : n (si SSH sans navigateur graphique)
# → suivre l'URL "rclone authorize" donnée, coller le token retourné
# Configure as Shared Drive : n
```

Vérifier : `rclone lsd gdrive:`

## 2. `restic`

```bash
ssh nucbox "sudo apt update && sudo apt install -y restic"
```

## 3. Passphrase et secrets

```bash
PASSPHRASE=$(openssl rand -base64 32)
# Sauvegarder $PASSPHRASE dans un gestionnaire de mots de passe IMMÉDIATEMENT
# — c'est la seule fois qu'elle est affichée. Voir ADR-011.

ssh nucbox "cat > ~/blackbox/scripts/backup/.env <<EOF
RESTIC_PASSWORD=$PASSPHRASE
ADMIN_ALERT_WEBHOOK_URL=<même webhook admin que gluetun-healthcheck>
REPO_LOCAL=/mnt/nas-media/backups/restic
REPO_REMOTE=rclone:gdrive:blackbox-backups
EOF
chmod 600 ~/blackbox/scripts/backup/.env"

ssh nucbox "mkdir -p /mnt/nas-media/backups/restic"
```

## 4. Déploiement du script

```bash
ssh nucbox "mkdir -p ~/blackbox/scripts/backup"
scp infra/scripts/backup/backup.sh nucbox:~/blackbox/scripts/backup/
ssh nucbox "chmod +x ~/blackbox/scripts/backup/backup.sh"
```

## 5. Test manuel avant automatisation

```bash
ssh nucbox "~/blackbox/scripts/backup/backup.sh; echo EXIT_CODE=\$?"
```

`EXIT_CODE=0` attendu. En cas d'échec, consulter
`~/blackbox/scripts/backup/last_run.log` sur le serveur (écrasé à chaque
run) plutôt que de relancer en mode debug.

**Erreur rencontrée au premier test** : `restic backup` retournait le code
3 ("some source files could not be read") à cause de
`jellyfin/config/temp/mm-exhelper.so.*` (fichiers temporaires root,
illisibles par `kong`) — un snapshot valide était quand même créé, mais le
script les considérait comme un échec. Corrigé en excluant ce dossier
(`--exclude .../jellyfin/config/temp`), sans intérêt à restaurer de toute
façon (recréé au démarrage de Jellyfin).

## 6. Automatisation (systemd)

```bash
scp infra/scripts/backup/blackbox-backup.service \
    infra/scripts/backup/blackbox-backup.timer nucbox:~/
ssh nucbox '
sudo mv ~/blackbox-backup.service ~/blackbox-backup.timer /etc/systemd/system/ &&
sudo systemctl daemon-reload &&
sudo systemctl enable --now blackbox-backup.timer &&
systemctl status blackbox-backup.timer --no-pager
'
```

Planifié tous les jours à 4h du matin. Vérifier la prochaine exécution :
```bash
ssh nucbox "systemctl list-timers blackbox-backup.timer --no-pager"
```

## 7. Vérification des snapshots

```bash
ssh nucbox "cd ~/blackbox/scripts/backup && source .env && \
  export RESTIC_PASSWORD RCLONE_CONFIG=\$HOME/.config/rclone/rclone.conf && \
  restic -r \"\$REPO_LOCAL\" snapshots --compact && \
  restic -r \"\$REPO_REMOTE\" snapshots --compact"
```

## 8. Restauration (procédure de référence, non testée en conditions réelles)

```bash
# Lister les snapshots disponibles
restic -r <REPO_LOCAL ou REPO_REMOTE> snapshots

# Restaurer un snapshot dans un dossier temporaire (jamais directement
# sur les données live sans vérification préalable)
restic -r <repo> restore <snapshot-id> --target /tmp/restore-test
```

À tester réellement (restauration à blanc) dès que possible plutôt que de
supposer que ça fonctionnera le jour où ce sera nécessaire — point ouvert.

## 9. Ce qui n'est pas couvert

- La médiathèque elle-même (films/séries/téléchargements) — protégée par
  le RAID1 du NAS, pas dupliquée dans ces backups (volume trop important,
  re-téléchargeable via la suite *arr* si besoin)
- Le dossier `.git` du repo — déjà versionné et poussé sur GitHub
  séparément
