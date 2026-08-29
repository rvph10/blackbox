# ADR 016 — CrowdSec derrière Traefik pour protéger l'exposition publique

**Statut :** Accepté — en production depuis le 2026-08-29

## Contexte

[ADR-014](014-cloudflare-tunnel.md) a rendu Jellyfin et Seerr publics.
Jellyfin n'a ni limitation de débit ni verrouillage de compte natifs : la
page de login est donc exposée au credential-stuffing / brute-force. Le
brief ([homelab_projet.md](../homelab_projet.md) §1) et l'audit
([§1](../audit_projet.md), CrowdSec « plus utile que Fail2ban seul »)
prévoient CrowdSec.

Problème d'architecture : avec Cloudflare Tunnel, il n'y a **aucun port
entrant** et **aucun reverse proxy** sur l'hôte. CrowdSec a besoin d'un
point d'application (« bouncer ») quelque part.

## Options étudiées

| Option | Verdict |
|---|---|
| `crowdsecurity/cloudflare-bouncer` (daemon classique, bannit via IP Access Rules) | **Écarté** — image Docker non maintenue depuis ~2 ans, CrowdSec l'a abandonné |
| Cloudflare **Worker Bouncer** (blocage à l'edge) | Écarté — tire Workers + KV (limites du plan Free), impose d'exposer la LAPI publiquement ou de passer par CrowdSec Console (SaaS), déploiement du Worker via intégration GitHub. Disproportionné pour 10 utilisateurs |
| **Traefik + `crowdsec-bouncer-traefik-plugin`** | **Retenu** — plugin très actif (v1.7.1, juillet 2026), LAPI reste sur le réseau Docker, aucune dépendance SaaS, AppSec disponible plus tard |

## Décisions

### Traefik en reverse proxy interne

```
Cloudflare edge → cloudflared → traefik:80 → {jellyfin:8096, seerr:5055}
                                    │ middleware CrowdSec sur chaque route
crowdsec (moteur) ← logs Traefik + logs Jellyfin
```

- Traefik ne publie **aucun port** : seul `cloudflared` le joint, via le
  réseau Docker. Les règles d'ingress Cloudflare pointent toutes vers
  `http://traefik:80` (changement Terraform), Traefik route par `Host`.
- **L'accès LAN / Tailscale reste direct** sur `jellyfin:8096` et
  `seerr:5055` — il ne passe ni par Traefik ni par CrowdSec. Modèle de
  confiance assumé : le LAN et le tailnet sont déjà des zones de confiance
  (Tailscale = admin authentifié, cf. [ADR-015](015-tailscale.md)). CrowdSec
  protège le seul vecteur non fiable : Internet.
- **File provider, pas de socket Docker monté.** `traefik.yml` (statique) +
  `dynamic.yml` (routeurs, services, middleware). Traefik avec accès à
  `/var/run/docker.sock` = équivalent root ; l'éviter sur un composant en
  façade d'Internet vaut la petite verbosité du fichier de config.

### CrowdSec : moteur seul, décisions via LAPI locale

- Conteneur `crowdsec`, aucun port publié. Le plugin Traefik interroge la
  LAPI sur `crowdsec:8080` (réseau Docker).
- Collections : `crowdsecurity/traefik`, `crowdsecurity/http-cve`,
  `LePresidente/jellyfin` (parser + scénario brute-force Jellyfin maintenu).
- Acquisition : `access.log` de Traefik + `*.log` de Jellyfin (montés en
  lecture seule).
- Mode `stream` : le plugin met en cache les décisions (rafraîchies toutes
  les 60 s), pas d'appel LAPI par requête.
- La **blocklist communautaire** (CAPI) est consommée automatiquement au
  premier démarrage, sans compte — les IP signalées par la communauté
  CrowdSec sont bloquées en plus des détections locales.

### Vraie IP client

`cloudflared` transmet l'IP réelle dans `X-Forwarded-For`. Traefik lui fait
confiance (`forwardedHeaders.trustedIPs: 172.16.0.0/12` — sous-réseaux
Docker, et seul `cloudflared` atteint Traefik). Le plugin lit donc la vraie
IP, pas `172.x`. `clientTrustedIPs` (LAN + CGNAT tailnet) contourne toute
vérification — pas de self-ban possible.

### Clé du bouncer : fichier, généré par l'outil

`dynamic.yml` référence `crowdsecLapiKeyFile: /etc/traefik/lapi-key`. La clé
est générée par `cscli bouncers add` puis écrite dans ce fichier sur le
NucBox (hors Git, hors Ansible) — même principe que les `.env`. Le fichier
de config lui-même, sans secret, reste versionné.

## Conséquences

- `infra/docker/prod/` : `traefik/{traefik.yml,dynamic.yml}`,
  `crowdsec/acquis.yaml` ; services `traefik` et `crowdsec` dans le compose
  (aucun port publié) ; `cloudflared` dépend désormais de `traefik`
- `infra/terraform/main.tf` : ingress → `http://traefik:80`
- Rôle Ansible `deploy` : déploie la config Traefik/CrowdSec (pas
  `lapi-key`), qui est ajoutée à la liste des secrets vérifiés
- `.gitignore` : `infra/docker/prod/traefik/lapi-key`
- Runbook [setup-crowdsec.md](../runbooks/setup-crowdsec.md)
- Nouveaux composants sur le NucBox : `traefik`, `crowdsec`. Si Traefik
  tombe, l'accès **public** tombe (l'accès LAN/Tailscale, non). Si CrowdSec
  tombe, le plugin Traefik est en `stream` : il continue sur le dernier
  cache de décisions, `bypass` si le cache expire (fail-open, choix par
  défaut du plugin — un incident CrowdSec ne coupe pas l'accès légitime).
- AppSec / WAF (virtual patching, règles ModSecurity) : possible en ajoutant
  le mode `appsec` au plugin plus tard, hors périmètre ici.
- Le chemin public gagne un hop (cloudflared → traefik → app) ; négligeable
  en LAN 2.5 GbE, invisible pour l'utilisateur.
