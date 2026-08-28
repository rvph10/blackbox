# ADR 013 — CI/CD GitHub Actions pour le bot Discord

**Statut :** Accepté
**Date :** 2026-08-29

## Contexte

Le brief ([homelab_projet.md](../homelab_projet.md) §9) prévoyait une
chaîne CI/CD GitHub Actions : lint/tests → build d'images multi-arch →
push GHCR → déploiement via runner self-hosted sur le NucBox. Jusqu'ici le
bot ([ADR-010](010-bot-layer2.md)) était déployé à la main : `rsync` du
code vers `~/blackbox/bot/` puis `docker compose up -d --build bot` sur le
NucBox, avec le piège de chemin relatif `build: ../bot` documenté dans
ADR-010. Aucun test, aucun lint automatisé.

Le bot est le seul composant du projet qui est du code applicatif écrit
maison — le reste, ce sont des images tierces (Jellyfin, suite *arr*) et de
l'infra déclarative (compose, Ansible). C'est donc le seul candidat
pertinent pour une chaîne CI/CD, et l'occasion de mettre en place le
pattern pour un futur Layer 3.

## Décision

### Deux workflows

- **`ci.yml`** — sur pull request et push `main` touchant `bot/**` :
  `ruff check`, `ruff format --check`, `pytest`. Tourne sur
  `ubuntu-latest` (runner GitHub hébergé), Python 3.12 (= version de
  l'image).
- **`release.yml`** — sur push `main` touchant `bot/**` : build de l'image
  `ghcr.io/rvph10/blackbox-bot`, push GHCR (tags `latest` + `sha-<court>`),
  puis job `deploy` sur le runner self-hosted.

Pas de re-run des tests dans `release.yml` : un push sur `main` a déjà été
validé par `ci.yml` sur la PR. Assumé pour un projet à un seul mainteneur.

### x86_64 uniquement, pas de multi-arch

Le brief parlait de build multi-arch (x86_64 + arm64) à l'époque où
l'archi cible incluait un RPi5. Depuis [ADR-005](005-nucbox-always-on.md)
il n'y a plus aucune machine ARM dans l'archi : le bot ne tourne que sur
le NucBox (Ryzen, x86_64). Un build arm64 via QEMU doublerait la durée du
job pour une image jamais utilisée. `platforms: linux/amd64` seul.

### Runner self-hosted plutôt que SSH depuis le cloud

Le job `deploy` tourne sur un runner self-hosted installé sur le NucBox
(labels `self-hosted`, `nucbox`). Alternative écartée : workflow cloud se
connectant en SSH au NucBox via une clé privée stockée en secret GitHub —
cela exposerait une clé d'accès à la machine dans un secret de repo, et le
NucBox n'a de toute façon aucun port entrant ouvert (pas encore de
routeur/tunnel, cf. README). Le runner sort en connexion sortante
uniquement, cohérent avec la posture réseau du projet.

Le job `deploy` : `checkout`, copie de `infra/docker/prod/docker-compose.yml`
vers `~/blackbox/prod/`, puis `docker compose pull bot && docker compose up -d bot`.
`concurrency: release-bot` (`cancel-in-progress: false`) sérialise les
déploiements.

### Image GHCR publique

Le package `ghcr.io/rvph10/blackbox-bot` est rendu public. L'image ne
contient que `discord.py` + `main.py` (les secrets sont dans `.env`, jamais
dans l'image), donc rien à protéger, et cela évite d'avoir à gérer un
`docker login ghcr.io` avec un PAT sur le NucBox juste pour tirer l'image.

### Compose prod : `image:` remplace `build:`

`infra/docker/prod/docker-compose.yml` passe de `build: ../bot` à
`image: ghcr.io/rvph10/blackbox-bot:latest`. Conséquence : le code du bot
n'est plus déployé sur le NucBox (le rôle Ansible `deploy` ne le copie
plus), seul `~/blackbox/bot/.env` y subsiste. Le piège de chemin relatif
`build: ../bot` de ADR-010 disparaît. Le handler Ansible `docker compose up`
fait désormais `pull` avant `up -d`.

### Tag `latest`, rollback manuel

Le compose suit `latest`. Pas de mécanisme de rollback automatique : pour
revenir en arrière, re-run du workflow sur un commit antérieur, ou sur le
NucBox `docker compose` en épinglant un tag `sha-<court>` précis. Suffisant
à cette échelle (10 utilisateurs, bot en lecture seule non critique).

## Secrets et permissions

- Aucun secret de repo ajouté. `release.yml` utilise le `GITHUB_TOKEN`
  automatique avec `permissions: packages: write` pour pousser sur GHCR.
- Le runner self-hosted tourne sous l'utilisateur `kong` (accès au socket
  Docker et à `~/blackbox/prod/`). Son token d'enregistrement est généré à
  l'installation et n'est pas versionné — voir
  [setup-cicd.md](../runbooks/setup-cicd.md).

## Conséquences

- `.github/workflows/` : `ci.yml`, `release.yml`
- `bot/` : `pyproject.toml` (config ruff + pytest), `requirements-dev.txt`,
  `tests/test_main.py` (logique pure + HTTP mocké). `main.py` ne lance
  `client.run` que sous `if __name__ == "__main__"` et lit ses variables
  d'environnement de façon tolérante — nécessaire pour l'import en test.
- Nouveau runbook [setup-cicd.md](../runbooks/setup-cicd.md) : installation
  du runner, visibilité du package GHCR.
- Tout futur code maison (Layer 3 du bot notamment) réutilise cette chaîne.
- Le runner self-hosted est un nouveau composant à maintenir sur le NucBox
  (service systemd `actions.runner.*`). Point de défaillance sans gravité :
  s'il tombe, le déploiement bascule en manuel (une commande SSH), le bot
  en cours d'exécution n'est pas affecté.
