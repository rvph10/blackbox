# Runbook — bot Discord Layer 2

Contexte et choix : [ADR-010](../adr/010-bot-layer2.md).

## 1. Application Discord

- https://discord.com/developers/applications → **New Application** →
  `Blackbox`
- Onglet **Bot** → **Reset Token** (ou **Copy** si c'est la première
  génération) → le token n'est affiché qu'une fois, à copier immédiatement
- Pas d'intent privilégié nécessaire (le bot ne lit pas le contenu des
  messages, seulement les interactions de commandes slash)

## 2. Clé API Jellyfin dédiée

Dashboard Jellyfin → **Advanced** → **API Keys** → nouvelle clé, nom
`Bot` — permet de garder une clé distincte de celles utilisées par
Seerr/Jellyfin-Enhanced, révocable indépendamment si besoin.

## 3. Secrets

```bash
ssh nucbox "cat > ~/blackbox/bot/.env <<'EOF'
DISCORD_BOT_TOKEN=<token du Developer Portal>
JELLYFIN_URL=http://jellyfin:8096
JELLYFIN_API_KEY=<clé API "Bot">
EOF
chmod 600 ~/blackbox/bot/.env"
```

## 4. Déploiement

Automatisé via GitHub Actions depuis [ADR-013](../adr/013-cicd-github-actions.md) :
un push sur `main` touchant `bot/` lint + teste le code, construit l'image
`ghcr.io/rvph10/blackbox-bot`, la pousse sur GHCR, puis le runner
self-hosted du NucBox fait `docker compose pull bot && docker compose up -d bot`.
Voir [setup-cicd.md](setup-cicd.md) pour l'installation du runner.

Le compose prod référence désormais `image:` (plus `build:`), donc le code
du bot n'a plus besoin d'être présent sur le NucBox — seul `~/blackbox/bot/.env`
y reste (créé à l'étape 3).

Déploiement manuel de secours (runner indisponible) :

```bash
ssh nucbox "cd ~/blackbox/prod && docker compose pull bot && docker compose up -d bot"
```

## 5. Inviter le bot sur le serveur

```
https://discord.com/oauth2/authorize?client_id=<CLIENT_ID>&scope=bot%20applications.commands&permissions=19456
```

`19456` = Voir les salons + Envoyer des messages + Intégrer des liens.
Choisir le serveur Blackbox, valider.

## 6. Vérification

```bash
ssh nucbox "docker logs bot --tail 30"
```

Doit afficher `Connecté en tant que <nom du bot>#xxxx`. Puis tester
`/status` et `/streams` directement sur le serveur Discord.

## 7. Commandes actuelles

| Commande | Accès | Comportement |
|---|---|---|
| `/status` | Tout le monde | "En ligne" / "Hors ligne" sur Jellyfin, rien de plus (volontairement simplifié) |
| `/streams` | Tout le monde | Liste utilisateur + titre pour chaque session de lecture en cours, avec identités visibles (décision assumée, voir ADR-010) |

Aucune tâche de fond, aucun état conservé entre deux appels, aucun accès à
Gluetun/ESP8266/comptes/NAS — strictement Layer 2. Layer 3 (création de
compte, gamification) pas commencé.
