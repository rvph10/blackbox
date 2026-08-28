variable "cloudflare_api_token" {
  description = <<-EOT
    Jeton d'API Cloudflare (My Profile > API Tokens > Create Token).
    Permissions minimales :
      - Account | Cloudflare Tunnel        | Edit
      - Zone    | DNS                       | Edit
      - Zone    | Zone                      | Read
    Passé via la variable d'environnement TF_VAR_cloudflare_api_token,
    jamais écrit dans un fichier versionné.
  EOT
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "ID du compte Cloudflare (dashboard > barre latérale, ou n'importe quelle URL de zone)."
  type        = string
}

variable "cloudflare_zone_id" {
  description = "ID de la zone blackbox.homes (Overview de la zone > API, colonne de droite)."
  type        = string
}

variable "zone" {
  description = "Nom de domaine de la zone."
  type        = string
  default     = "blackbox.homes"
}

variable "tunnel_name" {
  description = "Nom du tunnel côté Cloudflare (Zero Trust > Networks > Tunnels)."
  type        = string
  default     = "blackbox-nucbox"
}

# Sous-domaines — thème « salle de cinéma ». Changer ici suffit : le tunnel
# config et les enregistrements DNS suivent.
variable "jellyfin_hostname" {
  description = "Sous-domaine pour Jellyfin (sans le domaine)."
  type        = string
  default     = "screening"
}

variable "seerr_hostname" {
  description = "Sous-domaine pour Seerr (demandes de contenu)."
  type        = string
  default     = "boxoffice"
}
