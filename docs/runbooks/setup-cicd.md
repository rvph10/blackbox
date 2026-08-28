# Runbook — CI/CD GitHub Actions

Contexte et choix : [ADR-013](../adr/013-cicd-github-actions.md).

## 1. Vue d'ensemble

| Workflow | Déclencheur | Où | Rôle |
|---|---|---|---|
| `ci.yml` | PR + push `main` sur `bot/**` | runner GitHub | ruff + pytest |
| `release.yml` (job `build`) | push `main` sur `bot/**` | runner GitHub | build + push image GHCR |
| `release.yml` (job `deploy`) | après `build` | runner **self-hosted NucBox** | `docker compose pull/up` |

## 2. Rendre le package GHCR public

Au premier push sur `main`, `release.yml` crée le package
`ghcr.io/rvph10/blackbox-bot` (privé par défaut).

- GitHub → profil → **Packages** → `blackbox-bot` → **Package settings**
- **Danger Zone** → **Change visibility** → **Public**
- **Manage Actions access** : vérifier que le repo `rvph10/blackbox` a le
  rôle **Write** (ajouté automatiquement au premier push)

Package public = le NucBox tire l'image sans `docker login`.

## 3. Installer le runner self-hosted sur le NucBox

GitHub → repo `rvph10/blackbox` → **Settings** → **Actions** → **Runners**
→ **New self-hosted runner** → **Linux / x64**. Suivre les commandes
affichées (le token d'enregistrement est valable ~1h), en les adaptant :

```bash
ssh nucbox
sudo mkdir -p /opt/actions-runner && sudo chown kong:kong /opt/actions-runner
cd /opt/actions-runner
curl -o runner.tar.gz -L <URL affichée par GitHub>
tar xzf runner.tar.gz && rm runner.tar.gz

# --labels ajoute le label `nucbox` attendu par release.yml (job deploy :
# runs-on: [self-hosted, nucbox])
./config.sh --url https://github.com/rvph10/blackbox \
  --token <TOKEN GitHub> \
  --name nucbox \
  --labels nucbox \
  --unattended

# Service systemd (démarre au boot, tourne sous kong)
sudo ./svc.sh install kong
sudo ./svc.sh start
sudo ./svc.sh status
```

Le runner tourne sous `kong` → accès au socket Docker (`kong` est dans le
groupe `docker`, cf. [ADR-012](../adr/012-ansible-retrofit.md)) et à
`~/blackbox/prod/`.

### Vérifier

- GitHub → **Settings** → **Actions** → **Runners** : `nucbox` en
  **Idle** (point vert)
- `systemctl status 'actions.runner.*'` sur le NucBox

### Activer le job `deploy`

Tant que le runner n'est pas installé, le job `deploy` de `release.yml` est
ignoré (`if: vars.DEPLOY_ENABLED == 'true'`) et le workflow reste vert avec
le seul job `build`. Une fois le runner **Idle** :

```bash
gh variable set DEPLOY_ENABLED --body true --repo rvph10/blackbox
```

(ou GitHub → **Settings** → **Secrets and variables** → **Actions** →
**Variables** → **New repository variable** : `DEPLOY_ENABLED` = `true`)

## 4. Prérequis côté NucBox (déjà en place)

- `~/blackbox/prod/docker-compose.yml` et `~/blackbox/bot/.env` — créés par
  Ansible + étape 3 de [setup-bot.md](setup-bot.md)
- `docker compose` fonctionnel (rôle Ansible `docker`)

## 5. Premier passage

```bash
git push origin main          # après avoir créé le repo si besoin
```

- `ci.yml` doit passer au vert
- `release.yml` : `build` pousse l'image, `deploy` fait le `pull`/`up`
- `ssh nucbox "docker logs bot --tail 20"` → `Connecté en tant que ...`

## 6. Rollback

Pas de rollback automatique (tag `latest`). Pour revenir à une version
antérieure :

```bash
# option A — re-run du workflow sur un commit sain
gh workflow run release.yml --ref <sha-du-commit-sain>   # ou via l'UI Actions

# option B — épingler un tag sha- précis sur le NucBox
ssh nucbox
cd ~/blackbox/prod
docker compose pull   # liste les tags dispo : ghcr.io/rvph10/blackbox-bot
# éditer docker-compose.yml : image: ...blackbox-bot:sha-abc1234
docker compose up -d bot
```

## 7. Mise à jour / désinstallation du runner

```bash
cd /opt/actions-runner
sudo ./svc.sh stop && sudo ./svc.sh uninstall
./config.sh remove --token <nouveau token GitHub>
```

Le runner se met à jour tout seul (auto-update GitHub) tant que le service
tourne.

## 8. Développement local (avant de pousser)

```bash
cd bot
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && ruff format . && pytest -q
```
