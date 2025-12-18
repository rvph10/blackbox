# 🛡️ Guide de Reconstruction : OPNsense 25.7

Ce document détaille la restauration du routeur virtuel OPNsense.

## 1. Création de la VM (Proxmox)

- **ID :** 100 | **Name :** OPNsense-router.
- **CPU :** Type `Host`.
- **BIOS :** `OVMF (UEFI)`.
- **Désactivation Secure Boot :** Appuyer sur `ESC` au boot de la VM > Device Manager > Secure Boot Configuration > Décocher `Attempt Secure Boot`.

## 2. Interfaces Virtuelles

1. **net0 (LAN) :** Liée à `vmbr0`.
2. **net1 (WAN) :** Liée à `vmbr1` (Le pont physique créé sur l'hôte Proxmox).

## 3. Installation et Assignation

1. Booter sur l'ISO OPNsense et se connecter en `installer` / `opnsense`.
2. Installer en mode **ZFS (Stripe)**.
3. **Assignation au redémarrage (Console) :**
   - **WAN :** `vtnet1` (correspond au `vmbr1` de Proxmox).
   - **LAN :** `vtnet0` (correspond au `vmbr0` de Proxmox).

## 4. Configuration DHCP & DNS (LAN)

> ⚠️ **Important :** Nous utilisons **ISC DHCPv4** et non Dnsmasq pour la gestion des baux, afin de forcer proprement le DNS.

1. **Désactivation Dnsmasq DHCP :**

   - Aller dans _Services > Dnsmasq DNS > Settings_.
   - Décocher **Enable DHCP** (Laisser "Enable Dnsmasq" coché pour le DNS local du routeur).

2. **Configuration ISC DHCP :**
   - Aller dans _Services > ISC DHCPv4 > [LAN]_.
   - **Enable :** ☑️ (Coché).
   - **Range :** `192.168.10.100` à `192.168.10.200`.
   - **DNS servers :** `192.168.10.2` (Force le trafic vers la Tour de Contrôle / AdGuard).
   - **Gateway :** `192.168.10.1` (Le routeur OPNsense).
3. **Validation :**
   - Sauvegarder et appliquer.
   - Les clients doivent être redémarrés pour acquérir le nouveau DNS.

## 5. Configuration WAN (Proximus)

Via l'interface Web (`https://192.168.10.1`) :

1. **Type :** PPPoE.
2. **Username :** `votre_id@PROXIMUS`.
3. **Password :** `votre_mot_de_passe_connexion`.
4. **Physique :** Le câble doit être sur le **Port 1** de la Box Proximus.
