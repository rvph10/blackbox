# Runbook — backup restic (NAS local + Backblaze B2)

Contexte et choix : [ADR-011](../adr/011-backup-restic-rclone.md) puis
[ADR-017](../adr/017-backup-b2.md) (B2 remplace Google Drive — le remote
rclone/Drive tapait dans le quota OAuth partagé de rclone et tombait en
`403 RATE_LIMIT_EXCEEDED`).

## 1. Bucket + clé Backblaze B2

À faire par l'utilisateur (compte perso B2) :

1. Compte sur [backblaze.com](https://www.backblaze.com/sign-up/cloud-storage) →
   **B2 Cloud Storage**
2. **Buckets → Create a Bucket** : nom global unique (ex. `blackbox-backups`),
   **Private**, chiffrement + object lock laissés par défaut
3. **Application Keys → Add a New Application Key** :
   - Name : `blackbox`
   - **Allow access to Bucket(s)** : le bucket créé ci-dessus (clé restreinte)
   - Type of access : **Read and Write**
   - noter `keyID` et `applicationKey` (affichée une seule fois)

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
B2_ACCOUNT_ID=<keyID de l'étape 1>
B2_ACCOUNT_KEY=<applicationKey de l'étape 1>
REPO_LOCAL=/mnt/nas-media/backups/restic
REPO_REMOTE=b2:<nom-du-bucket>:restic
EOF
chmod 600 ~/blackbox/scripts/backup/.env"

ssh nucbox "mkdir -p /mnt/nas-media/backups/restic"
```

`rclone` n'est plus nécessaire (retiré du rôle Ansible `base`) —
`sudo apt remove rclone` si tu veux nettoyer. L'ancien remote Drive peut
être purgé : `rclone purge gdrive:blackbox-backups` avant désinstallation.

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
ssh nucbox 'cd ~/blackbox/scripts/backup && source .env && \
  export RESTIC_PASSWORD B2_ACCOUNT_ID B2_ACCOUNT_KEY && \
  restic -r "$REPO_LOCAL"  snapshots --compact && \
  restic -r "$REPO_REMOTE" snapshots --compact'
```

## 8. Restauration à blanc (testée le 2026-08-29)

Procédure complète : préparer l'env, vérifier l'intégrité des deux dépôts
(`restic check --read-data` en local, `--read-data-subset` sur B2),
restaurer `latest` dans `~/restore-test/`, valider l'arborescence, les
bases SQLite (`PRAGMA integrity_check`) et les `.env`, puis nettoyer.

```bash
ssh nucbox
cd ~/blackbox/scripts/backup && source .env
export RESTIC_PASSWORD B2_ACCOUNT_ID B2_ACCOUNT_KEY
mkdir -p ~/restore-test

restic -r "$REPO_LOCAL"  check --read-data
restic -r "$REPO_REMOTE" check --read-data-subset=10%

restic -r "$REPO_LOCAL" restore latest --target ~/restore-test
find ~/restore-test -path '*/config/*.db' ! -name '*.db-*' \
  -exec sh -c 'echo -n "$1: "; sqlite3 "$1" "PRAGMA integrity_check;"' _ {} \;
find ~/restore-test -name '.env' -exec sh -c 'echo "$1: $(wc -l < "$1") lignes"' _ {} \;

rm -rf ~/restore-test
```

**Résultat 2026-08-29 (dépôt NAS local)** : `check --read-data` sans erreur,
1338 fichiers restaurés, toutes les bases SQLite `integrity_check = ok`, les
3 `.env` non vides. Restauration locale validée. Le dépôt B2 (nouveau, cf.
ADR-017) est à revalider au premier run complet.

Ne jamais restaurer directement sur les données live sans vérification
préalable dans un dossier séparé.

## 9. Ce qui n'est pas couvert

- La médiathèque elle-même (films/séries/téléchargements) — protégée par
  le RAID1 du NAS, pas dupliquée dans ces backups (volume trop important,
  re-téléchargeable via la suite *arr* si besoin)
- Le dossier `.git` du repo — déjà versionné et poussé sur GitHub
  séparément
