# Runbook — configurer le Wake-on-LAN sur le NucBox M6

Procédure complète pour remettre le WoL en état après une réinstallation.
Contexte et limitation connue : [ADR-004](adr/004-wol-s3-not-s5.md) — **le
réveil ne fonctionne que depuis une veille S3, jamais depuis une extinction
complète S5** sur ce matériel.

## 1. BIOS

| Réglage | Valeur |
|---|---|
| Wake on LAN | Enabled |
| Auto power on | Power On |
| ErP / EuP Ready (deep sleep) | Disabled |

`Wake system from S5` (options Disabled/Fixed Time/Dynamic Time) n'a **rien à
voir** avec le WoL malgré le nom — c'est un réveil programmé par horloge RTC,
sans rapport. Le laisser sur Disabled.

## 2. Identifier la bonne interface

```bash
ip -o link show
```

La carte réseau connectée sur ce modèle est un **Realtek RTL8125 2.5GbE**
(deux ports physiques, même chipset). Noter la MAC de l'interface avec un
câble branché — c'est elle qu'on utilise pour le magic packet.

## 3. Driver : remplacer r8169 par r8125-dkms

Le driver in-kernel `r8169` ne supporte pas correctement le réveil sur cette
puce, même depuis S3. Le driver officiel Realtek est nécessaire :

```bash
sudo apt install -y r8125-dkms
dkms status   # doit lister r8125 installed pour le kernel courant

sudo tee /etc/modprobe.d/blacklist-r8169.conf <<EOF
blacklist r8169
EOF

sudo tee /etc/modprobe.d/r8125.conf <<EOF
options r8125 s5wol=1 s0_magic_packet=1 eee_enable=0 aspm=0 s5_keep_curr_mac=1
EOF

sudo update-initramfs -u
sudo reboot
```

**Piège connu** : le driver `r8125` (hors-arbre) ne fournit pas les mêmes
attributs udev que `r8169`, donc le nommage prévisible de l'interface change
au reboot (ex: `enp3s0` → `eth1`). Fixer le nom par adresse MAC dans netplan
pour ne plus en dépendre :

```yaml
# /etc/netplan/00-installer-config.yaml
network:
  ethernets:
    lan0:
      match:
        macaddress: <mac-de-la-carte>
      set-name: lan0
      accept-ra: true
      dhcp4: true
  version: 2
  wifis: {}
```

```bash
sudo netplan apply
```

## 4. Activer le flag WoL au niveau OS, de façon persistante

```bash
sudo ethtool -s lan0 wol g   # test immédiat

sudo tee /etc/systemd/network/00-wol.link <<EOF
[Match]
MACAddress=<mac-de-la-carte>

[Link]
WakeOnLan=magic
EOF
sudo reboot
sudo ethtool lan0 | grep "Wake-on:"   # doit afficher "g" automatiquement, sans réactivation manuelle
```

## 5. Tester

Le réveil ne fonctionne que depuis une **veille S3**, pas depuis une
extinction complète :

```bash
# sur le NucBox
sudo systemctl suspend

# depuis une autre machine du même réseau (idéalement filaire, pas Wi-Fi —
# certains routeurs ne relaient pas bien le broadcast Wi-Fi↔Ethernet)
wakeonlan -i <broadcast-du-sous-réseau> <mac-de-la-carte>
```

Réveil attendu en quelques secondes.

## Ce qui ne marche pas (testé, écarté)

- `ethtool -s wol g` seul avec le driver `r8169` : insuffisant, ne survit pas
  à une extinction S5
- `s5wol=1` seul (sans `aspm=0`/`eee_enable=0`) sur `r8125` : insuffisant dans
  notre cas
- Un service systemd réaffirmant `wol g` juste avant le shutdown : n'a rien
  changé (le problème n'est pas un souci de timing/ordre au shutdown mais une
  limitation matérielle du réveil depuis S5 sur cette carte mère)
