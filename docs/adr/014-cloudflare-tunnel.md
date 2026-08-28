# ADR 014 — Exposition publique via Cloudflare Tunnel + Terraform

**Statut :** Accepté (mise en œuvre partielle — voir §État)
**Date :** 2026-08-29

## Contexte

Jusqu'ici Jellyfin et Seerr ne sont accessibles qu'en LAN et via Tailscale
(admin). Pour que la dizaine d'utilisateurs s'en serve réellement, il faut
une entrée publique. Le brief ([homelab_projet.md](../homelab_projet.md) §6)
tranche déjà : **Cloudflare Tunnel**, pas de port forwarding, pas de
dépendance à la config NAT de la box. Terraform scopé aux seules ressources
Cloudflare ([homelab_projet.md](../homelab_projet.md) §9).

Ce chantier est préparé **avant la fibre** (prévue le 15/09) : le tunnel est
une connexion **sortante** depuis le NucBox, il fonctionne sur la connexion
actuelle. Ce qui attend la fibre, c'est le routeur/VLAN dédié (segmentation
réseau, cf. [audit §6](../audit_projet.md)) — pas le tunnel lui-même. On
pourra donc valider un flux distant réel dès maintenant.

## Décisions

### Tunnel à configuration distante (`config_src = "cloudflare"`)

Le tunnel et ses règles d'ingress sont déclarés dans Terraform
(`infra/terraform/`) et vivent côté Cloudflare. Le conteneur `cloudflared`
sur le NucBox ne reçoit qu'un **token** — aucun `config.yml` ni fichier de
credentials à gérer sur la machine. Cohérent avec l'objectif IaC : l'état
public est décrit dans le repo, reproductible.

### Terraform tourne depuis la machine de dev, pas le NucBox

Terraform gère des ressources cloud, pas la machine. Il n'a rien à faire sur
le NucBox. Le seul artefact qui transite vers le NucBox est le token, reporté
manuellement dans `~/blackbox/prod/.env` (`TUNNEL_TOKEN=`) — même principe que
tous les secrets du projet (jamais dans Git, jamais dans Ansible).

### État Terraform : backend `local`, gitignoré

`terraform.tfstate` reste local et hors Git (il contient le token du tunnel).
Écarté : backend distant (R2, HCP) — une ressource/dépendance de plus à
bootstrapper pour 4 ressources. La perte de l'état est peu grave : `terraform
import` reconstruit tout à partir des IDs visibles dans le dashboard. L'état
est tout de même à sauvegarder hors machine (copie chiffrée). Option backend
distant réévaluable si le périmètre Terraform grossit — pour l'instant il ne
doit pas.

### Pas de Cloudflare Access devant Jellyfin/Seerr

Zero Trust Access casserait les clients natifs (appli mobile Jellyfin,
Infuse…) qui ne savent pas passer un portail d'authentification. Jellyfin a
sa propre auth, Seerr utilise le SSO Jellyfin. L'exposition publique se
limite donc au tunnel + DNS. CrowdSec (prévu) reste la couche de protection
additionnelle côté NucBox. Access pourra servir plus tard pour d'éventuels
dashboards, mais ceux-ci restent sur Tailscale (cf. [audit §6](../audit_projet.md)).

### Sous-domaines thématiques

`screening.blackbox.homes` → Jellyfin (la salle de projection),
`boxoffice.blackbox.homes` → Seerr (le guichet où on demande une place).
Variables Terraform (`jellyfin_hostname`, `seerr_hostname`) — un seul endroit
à changer, DNS et ingress suivent.

### Zone DNS déplacée chez Cloudflare

`blackbox.homes` reste enregistré chez Porkbun ; seuls les nameservers
basculent vers Cloudflare (prérequis obligatoire pour un tunnel sur domaine
custom). Étape manuelle, ponctuelle, documentée dans le runbook.

## Conformité CGU Cloudflare

Le streaming vidéo « proxifié » via le CDN Cloudflare est historiquement
restreint par la section 2.8 des CGU. Cloudflare Tunnel / Zero Trust est une
couche réseau distincte, et l'usage domestique à petite échelle (≤ 10
utilisateurs, pas de revente) est très largement pratiqué. Risque assumé et
déjà acté dans le brief §6. Repli si blocage : bascule DNS en « DNS only »
(non proxifié) + port forwarding classique, ou Tailscale Funnel.

## Conséquences

- `infra/terraform/` : `versions.tf`, `variables.tf`, `main.tf`, `outputs.tf`,
  `terraform.tfvars.example`, `.gitignore`, `README.md`
- `infra/docker/prod/docker-compose.yml` : service `cloudflared` (sortant, 0
  port publié), `.env.example` : `TUNNEL_TOKEN`
- Runbook [setup-cloudflare-tunnel.md](../runbooks/setup-cloudflare-tunnel.md)
  (onboarding zone, jeton d'API, apply, config Jellyfin derrière proxy)
- Nouveau composant à surveiller : `cloudflared`. S'il tombe, l'accès public
  tombe (l'accès LAN/Tailscale, non). Pas de HA prévue à cette échelle.
- Le NucBox garde ses ports LAN (`8096`, `5055`…) pour l'accès local direct
  et Tailscale — le tunnel s'ajoute, ne remplace pas.

## État

- [x] Code Terraform + service compose écrits
- [ ] Zone `blackbox.homes` active sur Cloudflare (NS basculés)
- [ ] `terraform apply` exécuté
- [ ] `TUNNEL_TOKEN` déployé, conteneur `cloudflared` up
- [ ] Flux distant validé (hors LAN, ex. 4G)
- [ ] Jellyfin configuré pour le reverse proxy (known proxies / base URL)
