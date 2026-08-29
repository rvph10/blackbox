# ADR 015 — Tailscale pour l'accès admin distant

**Statut :** Accepté
**Date :** 2026-08-29

## Contexte

Depuis [ADR-014](014-cloudflare-tunnel.md), Jellyfin et Seerr sont exposés
publiquement. Tout le reste — SSH, et les dashboards de la suite *arr*
(Prowlarr 9696, Sonarr 8989, Radarr 7878, Bazarr 6767, qBittorrent 8080,
Seerr admin) — n'est joignable qu'en LAN. Administrer le NucBox à distance
signifiait jusqu'ici soit être physiquement sur place, soit ouvrir des ports
(exactement ce que le projet refuse).

Le brief ([homelab_projet.md](../homelab_projet.md) §6) et l'audit
([§6](../audit_projet.md)) prévoient tous deux Tailscale pour l'accès admin,
cantonné à ce rôle (jamais pour exposer un service au public).

## Décisions

### Tailscale SSH activé (`tailscale up --ssh`)

L'accès SSH au NucBox passe par le tailnet, avec authentification et
autorisation gérées par les ACL Tailscale (identité du compte, pas une paire
de clés à distribuer). `sshd` classique reste en écoute et inchangé : le
durcir (restreindre à l'interface tailnet / au LAN) est un pas volontairement
reporté au chantier routeur/VLAN — se verrouiller hors d'une machine distante
sur un changement non testé n'en vaut pas la peine maintenant.

### Installé par Ansible, connecté hors Ansible

Rôle `tailscale` : ajoute le dépôt apt officiel, installe le paquet, active
`tailscaled`. Idempotent (ne refait rien si déjà en place), comme le rôle
`docker`.

La connexion (`tailscale up`) n'a lieu que si le nœud n'est pas déjà
`Running` **et** qu'une clé d'auth est passée en `--extra-vars` :

```
ansible-playbook playbooks/site.yml --ask-become-pass -e tailscale_authkey=tskey-auth-...
```

La clé ne touche ni Git, ni l'inventaire, ni les logs (`no_log: true`) —
même principe que les `.env` (jamais de secret géré par l'automatisation
sans qu'il soit fourni explicitement à l'instant T). Les runs suivants, sans
clé, sautent proprement la tâche.

### Pas de subnet router par défaut

Les dashboards *arr* tournent **sur le NucBox** : une fois le NucBox sur le
tailnet, `http://nucbox:8989` etc. fonctionnent directement, aucun subnet
router nécessaire. L'annonce de route (`--advertise-routes`) n'a d'intérêt
que pour joindre d'autres équipements LAN sans Tailscale (l'UI du NAS `dxp`
surtout). Laissée en option (`tailscale_advertise_routes`, vide par défaut),
à activer au besoin — sachant que le sous-réseau changera avec le routeur
fibre, donc autant ne pas le figer maintenant.

### MagicDNS

Le nœud s'enregistre sous le nom `nucbox`. MagicDNS (activé au niveau du
tailnet) permet de l'adresser par ce nom depuis n'importe quel appareil du
tailnet.

## Points à régler dans l'admin console (manuel, documentés au runbook)

- **Désactiver l'expiration de clé** pour le nœud `nucbox` (sinon
  déconnexion au bout de ~180 j — inacceptable pour un serveur).
- Approuver la route si un subnet router est activé plus tard.

## Conséquences

- `infra/ansible/roles/tailscale/` ; `tailscale` ajouté à `site.yml` (après
  `base`, avant `docker`)
- Runbook [setup-tailscale.md](../runbooks/setup-tailscale.md)
- Nouveau démon sur le NucBox (`tailscaled`). Sortant uniquement, surface
  d'attaque négligeable. S'il tombe : l'accès LAN (SSH, dashboards) n'est pas
  affecté ; l'exposition publique (Cloudflare) non plus — les deux chemins
  sont indépendants.
- Prochaine étape naturelle : durcir `sshd` (tailnet/LAN only) avec le
  chantier routeur/VLAN, une fois la fibre en place.
