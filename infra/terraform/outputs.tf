output "tunnel_id" {
  description = "ID du tunnel (visible aussi dans Zero Trust > Networks > Tunnels)."
  value       = cloudflare_zero_trust_tunnel_cloudflared.blackbox.id
}

output "tunnel_token" {
  description = <<-EOT
    Token à passer au conteneur cloudflared sur le NucBox.
    Récupération : terraform output -raw tunnel_token
    À coller dans ~/blackbox/prod/.env  (TUNNEL_TOKEN=...), création manuelle
    comme tous les secrets du projet — voir docs/runbooks/setup-cloudflare-tunnel.md.
  EOT
  value       = data.cloudflare_zero_trust_tunnel_cloudflared_token.blackbox.token
  sensitive   = true
}

output "public_urls" {
  description = "URLs publiques une fois le conteneur cloudflared démarré."
  value = {
    jellyfin = "https://${local.jellyfin_fqdn}"
    seerr    = "https://${local.seerr_fqdn}"
  }
}
