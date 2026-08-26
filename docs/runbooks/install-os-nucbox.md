# Runbook — installer l'OS sur le NucBox M6

Procédure pour une install initiale ou une réinstallation complète du NucBox
(panne disque, remise à zéro). Décision liée : [ADR-002](adr/002-os-nucbox.md).

## Image et support

Dernière Ubuntu Server LTS depuis ubuntu.com/download/server (24.04 au moment
où j'écris ceci — vérifier qu'il n'y a pas une LTS plus récente, cycle de 2 ans
en avril). Vérifier le SHA256 avant de flasher sur clé USB.

## BIOS, avant de lancer l'installeur

| Réglage | Valeur | Pourquoi |
|---|---|---|
| Wake-on-LAN / Power On by PCIE-LAN | Activé | Nécessaire pour le test WoL, souvent off par défaut |
| ErP / EuP Ready (deep sleep) | Désactivé | Sinon coupe le WoL en extinction complète (S5), même WoL activé |
| Power On after AC Loss | Power On / Last State | Redémarre seul après coupure de courant |
| Secure Boot | Activé, ne pas toucher | amdgpu (driver open-source) fonctionne très bien avec |

## Dans l'installeur (Subiquity)

- Partitionnement : disque entier + LVM (défaut) — laisse de la marge si un
  second SSD en miroir est ajouté plus tard (pas encore tranché).
- Cocher OpenSSH Server, importer la clé publique GitHub si dispo.
- Ne PAS cocher le Docker snap proposé par l'installeur. Le snap a un modèle de
  confinement différent de Docker CE (apt) — problématique avec les bind mounts
  hors home dir (les volumes média). Docker sera installé proprement via
  Ansible ensuite.
- Ubuntu Pro : décliner pour l'instant.
- Hostname clair et stable (utilisé dans l'inventaire Ansible après).
- Timezone Europe/Brussels.

## Après le premier boot

```bash
sudo apt update && sudo apt full-upgrade -y

# stack HWE — important pour le support VAAPI RDNA3, cf ADR-002
sudo apt install --install-recommends linux-generic-hwe-<version> mesa-va-drivers
sudo reboot
uname -r   # vérifier que le kernel a changé

# pare-feu minimal tant que le routeur dédié n'est pas branché
sudo ufw allow ssh
sudo ufw enable

# maj sécu auto, sans reboot automatique (pas envie qu'un stream se coupe la nuit)
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
# vérifier dans /etc/apt/apt.conf.d/50unattended-upgrades :
#   Unattended-Upgrade::Automatic-Reboot "false";
```

## À noter pour la suite

- Adresse MAC (`ip link show`) — nécessaire pour le paquet magique WoL.
- IP actuelle (DHCP pour l'instant, à fixer une fois le routeur dédié en place).
- Version de kernel après activation HWE.

Étape suivante : test Wake-on-LAN, puis test VAAPI (`vainfo` + session
Jellyfin réelle).
