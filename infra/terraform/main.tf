# Tunnel Cloudflare pour exposer Jellyfin et Seerr sans port forwarding.
# Config gérée à distance (config_src = "cloudflare") : les règles d'ingress
# vivent dans ce Terraform, le conteneur cloudflared sur le NucBox ne reçoit
# qu'un token. Voir docs/adr/014-cloudflare-tunnel.md.

locals {
  jellyfin_fqdn = "${var.jellyfin_hostname}.${var.zone}"
  seerr_fqdn    = "${var.seerr_hostname}.${var.zone}"
}

resource "cloudflare_zero_trust_tunnel_cloudflared" "blackbox" {
  account_id = var.cloudflare_account_id
  name       = var.tunnel_name
  config_src = "cloudflare"
}

data "cloudflare_zero_trust_tunnel_cloudflared_token" "blackbox" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.blackbox.id
}

resource "cloudflare_zero_trust_tunnel_cloudflared_config" "blackbox" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.blackbox.id

  config = {
    ingress = [
      {
        hostname = local.jellyfin_fqdn
        service  = "http://jellyfin:8096"
      },
      {
        hostname = local.seerr_fqdn
        service  = "http://seerr:5055"
      },
      # Règle attrape-tout obligatoire (dernière position, sans hostname).
      {
        service = "http_status:404"
      },
    ]
  }
}

# CNAME proxifiés vers <tunnel-id>.cfargotunnel.com. `ttl = 1` = automatique
# (imposé quand proxied = true).
resource "cloudflare_dns_record" "jellyfin" {
  zone_id = var.cloudflare_zone_id
  name    = var.jellyfin_hostname
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.blackbox.id}.cfargotunnel.com"
  ttl     = 1
  proxied = true
  comment = "Jellyfin via tunnel — géré par Terraform (infra/terraform)"
}

resource "cloudflare_dns_record" "seerr" {
  zone_id = var.cloudflare_zone_id
  name    = var.seerr_hostname
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.blackbox.id}.cfargotunnel.com"
  ttl     = 1
  proxied = true
  comment = "Seerr via tunnel — géré par Terraform (infra/terraform)"
}
