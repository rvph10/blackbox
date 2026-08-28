# Runbook — Cloudflare Tunnel

Contexte et choix : [ADR-014](../adr/014-cloudflare-tunnel.md).
Code : [`infra/terraform/`](../../infra/terraform/).

Résultat visé :
- `https://stream.blackbox.homes` → Jellyfin
- `https://requests.blackbox.homes` → Seerr

Aucun port ouvert sur la box, connexion sortante uniquement.

---

## 1. Prérequis — zone `blackbox.homes` sur Cloudflare

Le domaine reste enregistré chez **Porkbun**, seule la gestion DNS passe à
Cloudflare (obligatoire pour un tunnel sur domaine custom).

1. Compte Cloudflare (gratuit) → **Add a site** → `blackbox.homes` → plan
   **Free**
2. Cloudflare scanne les enregistrements existants — vérifier qu'il n'y a
   rien d'important à conserver (le domaine n'était que réservé)
3. Cloudflare affiche 2 nameservers (ex. `xxx.ns.cloudflare.com`)
4. **Porkbun** → domaine `blackbox.homes` → **Authoritative Nameservers** →
   remplacer par les 2 de Cloudflare → sauvegarder
5. Attendre la propagation (souvent < 1 h, parfois jusqu'à 24 h). Cloudflare
   envoie un mail « blackbox.homes is now active » et la zone passe en
   **Active**.

Ne pas continuer tant que la zone n'est pas **Active**.

## 2. Jeton d'API Cloudflare

**My Profile → API Tokens → Create Token → Create Custom Token** :

| Type | Ressource | Permission |
|---|---|---|
| Account | Cloudflare Tunnel | Edit |
| Zone | DNS | Edit |
| Zone | Zone | Read |

Scope : Account = ton compte, Zone = `blackbox.homes`. Copier le jeton
(affiché une seule fois).

Récupérer aussi :
- **Account ID** : dashboard → barre latérale, ou fin de l'URL
- **Zone ID** : zone `blackbox.homes` → **Overview** → colonne de droite, API

## 3. `terraform apply` (depuis la machine de dev)

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# renseigner cloudflare_account_id et cloudflare_zone_id dans terraform.tfvars

export TF_VAR_cloudflare_api_token='<jeton de l'étape 2>'

terraform init
terraform plan      # attendu : 4 à créer (tunnel, config, 2 CNAME)
terraform apply
```

Vérifs post-apply :
- Cloudflare → **Zero Trust → Networks → Tunnels** : `blackbox-nucbox`
  présent, statut **Down** (normal, le conteneur n'existe pas encore)
- Zone DNS : 2 CNAME `stream` / `requests` → `<id>.cfargotunnel.com`,
  proxifiés (nuage orange)

## 4. Déployer le token sur le NucBox

```bash
terraform output -raw tunnel_token        # depuis infra/terraform/

ssh nucbox
# ajouter la ligne dans le .env prod existant (ne pas écraser le fichier)
nano ~/blackbox/prod/.env
#   TUNNEL_TOKEN=<valeur copiée>
```

Puis, via la CI/CD (push touchant `infra/docker/prod/`… — en pratique
`docker-compose.yml` est synchronisé par le job `deploy`) **ou** à la main :

```bash
ssh nucbox "cd ~/blackbox/prod && docker compose up -d cloudflared"
docker logs cloudflared --tail 20
```

Log attendu : `Registered tunnel connection` (x4, une par datacenter edge).
Le tunnel passe **Healthy** dans le dashboard.

## 5. Configurer Jellyfin derrière le proxy

Jellyfin Dashboard → **Networking** :
- **Known proxies** : ajouter `cloudflared` (le conteneur) — ou laisser vide
  et cocher **Enable published server URI**… selon la version. But : que
  Jellyfin voie l'IP réelle du client via `CF-Connecting-IP`, pas l'IP du
  conteneur.
- Ne **pas** définir de base URL (les sous-domaines dédiés servent la racine).

Seerr : **Settings → General → Application URL** = `https://requests.blackbox.homes`.

## 6. Vérification finale

- Depuis un réseau **hors LAN** (4G, partage de connexion) :
  `https://stream.blackbox.homes` → page de login Jellyfin, lecture d'un
  média OK (le transcodage éventuel se fait sur le NucBox comme d'habitude)
- `https://requests.blackbox.homes` → Seerr, connexion via compte Jellyfin
- Jellyfin Dashboard → une session active affiche bien l'IP publique du
  client, pas `172.x`

## 7. Rollback / incident

- **Tunnel bloqué par Cloudflare (streaming)** : zone DNS → passer les 2
  CNAME en **DNS only** (nuage gris) ne suffit pas (cfargotunnel exige le
  proxy). Repli réel : recréer les enregistrements en A vers l'IP WAN +
  port forwarding `443` sur la box, ou Tailscale Funnel. Voir ADR-014.
- **`cloudflared` down** : l'accès LAN/Tailscale n'est pas affecté.
  `docker compose restart cloudflared`, vérifier `TUNNEL_TOKEN`.
- **Tout détruire** : `terraform destroy` (supprime tunnel + DNS ; le
  conteneur `cloudflared` se retrouve alors sans backend, le stopper).

## 8. État Terraform

`infra/terraform/terraform.tfstate` — gitignoré, contient le token. Le
copier dans un gestionnaire de secrets / une archive chiffrée hors machine.
En cas de perte : `terraform import` sur chaque ressource à partir des IDs
du dashboard (4 ressources, cf. `infra/terraform/README.md`).
