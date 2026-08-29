# Runbook — Tailscale (accès admin distant)

Contexte et choix : [ADR-015](../adr/015-tailscale.md).

Résultat visé : depuis n'importe quel appareil de ton tailnet,
- `ssh kong@nucbox` (via Tailscale SSH, sans clé à distribuer)
- `http://nucbox:8989` / `:7878` / `:9696` / `:6767` / `:8080` / `:5055`
  (dashboards *arr*, qBittorrent, Seerr admin)

sans aucun port ouvert sur la box.

---

## 1. Compte et tailnet

1. Créer un compte sur [tailscale.com](https://tailscale.com) (auth via
   Google avec `rgenu10@gmail.com`, ou GitHub)
2. Installer le client Tailscale sur ta machine de dev et ton téléphone
   (ce sont eux qui joindront le NucBox)

## 2. Clé d'authentification pour le NucBox

Admin console → **Settings → Keys → Generate auth key** :
- **Reusable** : non (une seule machine à enrôler)
- **Ephemeral** : non (le NucBox est un nœud permanent)
- **Expiration** : 90 j (la clé ne sert qu'une fois, à l'enrôlement)
- Tag : optionnel (`tag:server` si tu utilises des ACL taggées)

Copier la clé `tskey-auth-...` (affichée une seule fois).

## 3. Installer + connecter via Ansible (depuis la machine de dev)

```bash
cd infra/ansible
ansible-playbook playbooks/site.yml --ask-become-pass \
  -e tailscale_authkey=tskey-auth-xxxxxxxxxxxx
```

Le rôle `tailscale` :
- ajoute le dépôt apt officiel, installe le paquet, active `tailscaled`
- lance `tailscale up --ssh --hostname=nucbox --auth-key=…` (uniquement si le
  nœud n'est pas déjà connecté ; la clé n'est pas loguée)

Les runs suivants se font **sans** `-e tailscale_authkey=…` : la tâche de
connexion est sautée proprement.

## 4. Réglages admin console (une fois)

Machines → `nucbox` :
- **⋯ → Disable key expiry** — obligatoire pour un serveur, sinon
  déconnexion au bout de ~180 j
- Vérifier que **MagicDNS** est activé (Settings → DNS) pour adresser la
  machine par `nucbox`

**Access Controls** → la politique par défaut n'autorise **pas** Tailscale
SSH. Ajouter un bloc `ssh` :

```jsonc
"ssh": [
  {
    "action": "accept",
    "src":    ["autogroup:member"],
    "dst":    ["autogroup:self"],
    "users":  ["kong", "root"]
  }
]
```

(ajuste `src`/`dst` si tu utilises des tags). Sans ce bloc, `ssh kong@nucbox`
via le tailnet renverra « handshake failed ».

## 5. Vérification

Depuis la machine de dev (connectée au tailnet) :

```bash
tailscale status                 # nucbox doit apparaître, en ligne
ssh kong@nucbox                  # via Tailscale SSH
curl -sI http://nucbox:8989 | head -1   # Sonarr répond
```

Depuis le téléphone en 4G (Tailscale activé) : `http://nucbox:7878`
(Radarr) doit charger.

Sur le NucBox : `tailscale status` liste tes autres appareils.

## 6. Option — joindre le NAS (subnet router)

Les dashboards *arr* tournent sur le NucBox, donc joignables directement.
Le subnet router ne sert que pour l'UI du NAS `dxp` (ou d'autres équipements
LAN sans Tailscale).

```bash
# sous-réseau LAN actuel (changera avec le routeur fibre)
ansible-playbook playbooks/site.yml --ask-become-pass \
  -e tailscale_advertise_routes=192.168.129.0/24
# si le nœud est déjà connecté, appliquer directement sur le NucBox :
ssh kong@nucbox "sudo tailscale set --advertise-routes=192.168.129.0/24"
```

Puis admin console → Machines → `nucbox` → **Edit route settings** →
approuver `192.168.129.0/24`. Les autres appareils accèdent alors au NAS via
son IP LAN à travers le tailnet.

## 7. Changer les réglages plus tard

`tailscale set` modifie un nœud connecté sans réauthentifier :

```bash
ssh kong@nucbox "sudo tailscale set --advertise-routes= "   # retirer les routes
ssh kong@nucbox "sudo tailscale set --ssh=false"            # désactiver Tailscale SSH
```

## 8. Incident

- **`tailscaled` down** : `sudo systemctl restart tailscaled`. L'accès LAN
  (SSH, dashboards) et l'exposition publique Cloudflare ne sont pas affectés.
- **Plus d'accès SSH via tailnet** : passer par le LAN (`ssh nucbox` sur
  l'alias local), vérifier `tailscale status` et les ACL.
- **Retirer complètement** : `sudo tailscale logout` + supprimer le nœud
  dans l'admin console.
