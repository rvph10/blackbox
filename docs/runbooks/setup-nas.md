# Runbook — configuration du NAS (dxp, Ugreen DXP2800)

## 1. Identité et reset

- Nom d'appareil : `dxp`
- IP locale : `192.168.129.180` (à réserver par MAC sur le routeur —
  `6c:1f:f7:7a:3a:5f` — tant qu'on reste sur ce routeur ; tout sera
  reconfiguré de toute façon à la migration fibre, voir §5 ci-dessous)
- OS : UGOS Pro (d'origine, pas remplacé — le NAS reste "stockage pur",
  voir §5 du brief)

Le RAID1 sur les deux disques 4 To existait déjà d'une installation
précédente (`md1`, `sda2`+`sdb2`, sain — `[UU]`), pas besoin de le
recréer. Un cache SSD NVMe (LVM cache, `md2`) est également en place,
bonus non prévu au départ.

## 2. Nettoyage de l'installation précédente

L'installation précédente sur ce NAS contenait des restes d'un autre
projet homelab (Grafana, Loki, Prometheus, Home Assistant, Jellyfin,
Jellyseerr, Overseerr, AdGuard, dumps Proxmox...) — aucun conteneur actif
au moment du nettoyage (`sudo docker ps -a` vide). Contenu vidé sans
supprimer les dossiers partagés eux-mêmes (pour ne pas casser leur
enregistrement côté UGOS) :

```bash
for d in appdata proxmox-backups docker backups-configs media photos; do
  sudo find /volume1/$d -mindepth 1 -delete
done
```

Les dossiers système préfixés `@` (`@docker`, `@appstore`, etc.) et
`UserFolder` n'ont pas été touchés.

## 3. Partage NFS

- **Control Panel → File Services → NFS** : activé
- Dossier partagé `media` (sur le volume RAID1) → règle NFS :
  - Client : `192.168.129.175` (IP du NucBox)
  - Droits : lecture/écriture
- Export vérifié côté NucBox : `showmount -e 192.168.129.180` →
  `/volume1/media 192.168.129.175`

Structure sous `media/` : `movies/`, `tvshows/`.

## 4. Montage côté NucBox

`/etc/fstab` :

```
192.168.129.180:/volume1/media /mnt/nas-media nfs _netdev,noauto,x-systemd.automount,x-systemd.idle-timeout=600,timeo=30,retrans=2,nofail 0 0
```

`noauto,x-systemd.automount,nofail` : le montage se fait à la demande
(premier accès) plutôt qu'au boot, et ne bloque jamais le démarrage si le
NAS est injoignable — même logique que le correctif déjà appliqué sur
l'interface réseau `eno1` (voir CHANGELOG 2026-08-27).

Jellyfin (`infra/docker/prod/`) pointe dessus via `MEDIA_PATH=/mnt/nas-media`
dans `.env` — les chemins internes au conteneur (`/media/movies`,
`/media/tvshows`) n'ont pas changé, donc les bibliothèques Jellyfin n'ont
pas eu besoin d'être reconfigurées, seul le montage source côté hôte a
changé.

## 5. Limite connue : IP en dur

L'IP du NAS (règle NFS) et celle du NucBox (entrée `fstab`, alias SSH
local) sont codées en dur. Ça tient tant qu'on reste sur le routeur
actuel (via réservation DHCP par MAC). **À reconfigurer entièrement à
l'installation du routeur dédié pour la fibre** (prévue le 15/09,
[§5 de l'audit](../audit_projet.md)) — nouveau sous-réseau probable, point
de rupture de toute façon. Pas d'action avant cette date.
