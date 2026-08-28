terraform {
  required_version = ">= 1.9"

  # État local (terraform.tfstate, gitignoré — il contient le token du tunnel
  # et l'ID de zone). Peu d'enjeu : 4 ressources seulement, entièrement
  # reconstructibles via `terraform import` en cas de perte. Voir
  # docs/adr/014-cloudflare-tunnel.md et le README de ce dossier.
  backend "local" {}

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      # >= 5.8.2 : sérialisation de zero_trust_tunnel_cloudflared_config
      # corrigée (bugs #5508 / #6308 des premières 5.x).
      version = "~> 5.8"
    }
  }
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}
