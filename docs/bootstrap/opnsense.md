# 🛡️ Guide de Reconstruction : OPNsense 25.7

Ce document détaille la restauration du routeur virtuel OPNsense.

## 1. Création de la VM (Proxmox)
* **ID :** 100 | **Name :** OPNsense-router.
* **CPU :** Type `Host`.
* **BIOS :** `OVMF (UEFI)`.
* **Désactivation Secure Boot :** Appuyer sur `ESC` au boot de la VM > Device Manager > Secure Boot Configuration > Décocher `Attempt Secure Boot`.

## 2. Interfaces Virtuelles
1. **net0 (LAN) :** Liée à `vmbr0`.
2. **net1 (WAN) :** Liée à `vmbr1` (Le pont physique créé sur l'hôte Proxmox).

## 3. Installation et Assignation
1. Booter sur l'ISO OPNsense et se connecter en `installer` / `opnsense`.
2. Installer en mode **ZFS (Stripe)**.
3. **Assignation au redémarrage (Console) :**
    * **WAN :** `vtnet1` (correspond au `vmbr1` de Proxmox).
    * **LAN :** `vtnet0` (correspond au `vmbr0` de Proxmox).

## 4. Configuration IP LAN
1. Choisir l'option `2) Set interface IP address`.
2. Configurer le LAN sur **`192.168.10.1/24`**.
3. Activer le serveur DHCP (Plage : `192.168.10.100` à `192.168.10.200`).

## 5. Configuration WAN (Proximus)
Via l'interface Web (`https://192.168.10.1`) :
1. **Type :** PPPoE.
2. **Username :** `votre_id@PROXIMUS`.
3. **Password :** `votre_mot_de_passe_connexion`.
4. **Physique :** Le câble doit être sur le **Port 1** de la Box Proximus.
