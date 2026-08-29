# Runbook — CrowdSec + Traefik

Contexte et choix : [ADR-016](../adr/016-crowdsec-traefik.md).

Objectif : chaque requête publique passe par Traefik → middleware CrowdSec →
Jellyfin / Seerr. Les IP en brute-force (détection locale) ou signalées par
la communauté CrowdSec sont bloquées. L'accès LAN / Tailscale n'est pas
concerné (direct sur les conteneurs).

---

## 1. Pré-requis

- Jellyfin loggue bien la vraie IP client (known proxy `cloudflared`
  configuré à l'étape 5 de [setup-cloudflare-tunnel.md](setup-cloudflare-tunnel.md)).
  Vérifier : `docker logs jellyfin | grep -i "10.\|192.\|<ton IP>"` sur une
  connexion distante — pas de `172.x`.
- Le sous-réseau LAN dans `traefik/dynamic.yml` (`clientTrustedIPs`) est
  `192.168.129.0/24` — l'ajuster si besoin (changera avec le routeur fibre).

## 2. Appliquer le changement Terraform (ingress → Traefik)

```bash
cd infra/terraform
export TF_VAR_cloudflare_api_token='...'
terraform apply       # 1 change : la config d'ingress pointe vers traefik:80
```

Tant que Traefik ne tourne pas sur le NucBox, `stream.` / `requests.`
renverront une erreur 502 — normal, on démarre Traefik juste après.

## 3. Bootstrap sur le NucBox

Ordre important : CrowdSec doit tourner pour générer la clé du bouncer que
Traefik lira au démarrage.

```bash
# depuis ta machine de dev — déploie compose + config Traefik/CrowdSec
cd infra/ansible
ansible-playbook playbooks/site.yml --ask-become-pass
# ↑ le playbook AVERTIT que traefik/lapi-key est absent et NE lance PAS
#   `docker compose up` (garde-fou secrets). C'est attendu à ce stade.

ssh nucbox
cd ~/blackbox/prod

# 1. créer le fichier clé VIDE d'abord, en tant que kong — sinon un
#    `docker compose up` ultérieur le crée en dossier root (bind-mount
#    source manquante auto-créée par le démon Docker).
touch traefik/lapi-key && chmod 600 traefik/lapi-key

# 2. démarrer CrowdSec seul
docker compose up -d crowdsec
docker compose logs -f crowdsec      # attendre "Starting processing data"

# 3. générer la clé du bouncer et l'écrire dans le fichier
docker exec crowdsec cscli bouncers add traefik-bouncer -o raw > traefik/lapi-key
cat traefik/lapi-key                 # vérifier : une clé, pas vide

# 4. démarrer le reste (traefik, cloudflared relancé, etc.)
docker compose up -d
```

Si `traefik/lapi-key` a déjà été créé en dossier root par un `up` prématuré :
`sudo rm -rf traefik/lapi-key` puis reprendre à l'étape 1. Vérifier au besoin
`sudo chown -R kong:kong ~/blackbox/prod/{traefik,crowdsec}`.

Relancer le playbook plus tard reprendra la main normalement (la clé existe
désormais).

## 4. Vérification

```bash
# le bouncer est bien enregistré et vu comme "validated"
docker exec crowdsec cscli bouncers list

# les collections sont là
docker exec crowdsec cscli collections list | grep -E "traefik|jellyfin|http-cve"

# métriques d'acquisition : traefik + jellyfin doivent apparaître avec des lignes lues
docker exec crowdsec cscli metrics

# Traefik a chargé le plugin sans erreur
docker logs traefik 2>&1 | grep -iE "crowdsec|plugin|error"
```

Test fonctionnel depuis un réseau **hors LAN** (4G) :
- `https://stream.blackbox.homes` répond normalement (login Jellyfin)
- simuler une décision : `docker exec crowdsec cscli decisions add --ip <IP de test> --duration 2m`
  → depuis cette IP, `stream.blackbox.homes` renvoie **403 Forbidden**
- `docker exec crowdsec cscli decisions delete --ip <IP de test>` pour lever

## 5. (Optionnel) CrowdSec Console

Dashboard web + visibilité sur les alertes, utile en vitrine :

```bash
# créer un compte sur app.crowdsec.net, récupérer la clé d'enrôlement
docker exec crowdsec cscli console enroll <clé>
docker compose restart crowdsec
```

Puis valider l'instance dans la console.

## 6. (Optionnel) Notifier Discord sur les bans

CrowdSec a un notifier HTTP. Config dans
`~/blackbox/prod/data/crowdsec/config/notifications/http.yaml` + profil dans
`profiles.yaml` pointant vers le webhook du salon admin. À documenter si on
l'active (cohérent avec les notifs Layer 1, ADR-009).

## 7. Incident

- **502 sur stream./requests.** : Traefik down ou ne joint pas l'app.
  `docker compose ps`, `docker logs traefik`.
- **403 sur tout, y compris toi** : une décision englobe ton IP.
  `cscli decisions list`, `cscli decisions delete --ip <toi>`, et vérifier
  que ton réseau est dans `clientTrustedIPs`.
- **Plugin Traefik en erreur (clé)** : `traefik/lapi-key` vide ou mauvaise.
  Regénérer via `cscli bouncers add` (supprimer l'ancien d'abord :
  `cscli bouncers delete traefik-bouncer`).
- **CrowdSec down** : le plugin est en mode `stream` avec fail-open — les
  requêtes légitimes passent, seul le blocage actif s'arrête. Redémarrer
  `crowdsec`.
- **Tout retirer** : repasser l'ingress Terraform sur `jellyfin:8096` /
  `seerr:5055`, `docker compose rm -sf traefik crowdsec`.
