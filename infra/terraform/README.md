# Terraform — ressources Cloudflare

Périmètre strictement limité au tunnel Cloudflare et à son DNS (tunnel,
config d'ingress, 2 CNAME). Les machines physiques relèvent d'Ansible, le
déploiement applicatif de Docker Compose. Voir
[ADR-014](../../docs/adr/014-cloudflare-tunnel.md).

## Prérequis

- `blackbox.homes` actif sur Cloudflare (nameservers basculés chez Porkbun) —
  procédure dans [setup-cloudflare-tunnel.md](../../docs/runbooks/setup-cloudflare-tunnel.md)
- Terraform >= 1.9

## Usage

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # renseigner account_id + zone_id
export TF_VAR_cloudflare_api_token='...'         # jamais dans un fichier

terraform init
terraform plan
terraform apply

# Token du tunnel à reporter dans ~/blackbox/prod/.env sur le NucBox
terraform output -raw tunnel_token
```

## État

Backend `local`. `terraform.tfstate` est **gitignoré** (il contient le token
du tunnel). Peu critique : 4 ressources, reconstructibles via `terraform
import` si l'état est perdu. Le sauvegarder tout de même (gestionnaire de
secrets ou copie chiffrée hors machine).

`.terraform.lock.hcl` est versionné pour figer la version du provider.
