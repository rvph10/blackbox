# 🏗️ Guide de Reconstruction : Proxmox VE 9.1

Ce document explique comment reconstruire l'hôte Proxmox sur le **GMKtec NucBox M6** en cas de sinistre total.

## 1. Préparation Matérielle
* [cite_start]**Clé USB :** Créée avec Ventoy contenant l'ISO de Proxmox VE 9.1[cite: 1].
* **BIOS/UEFI :** * `SVM Mode` (Virtualisation AMD) : **Enabled**.
    * `IOMMU` : **Enabled**.
    * `Secure Boot` : **Disabled**.

## 2. Installation de l'OS
1. Booter sur la clé USB et choisir l'installateur graphique.
2. **Management Interface :** Choisir `nic0` (`enp1s0`).
3. **Hostname :** `pve.blackbox.homes`.
4. **IP Statique :** `192.168.10.10/24`.
5. **Gateway :** `192.168.10.1` (IP du futur routeur OPNsense).

## 3. Configuration Post-Install (Manuelle)
Le script automatique peut échouer sur la v9.1, effectuer ces étapes via le Shell :

### A. Dépôts (Repositories)
Désactiver le dépôt Enterprise et ajouter le No-Subscription :
```bash
# Désactiver Enterprise
sed -i "s/^deb/#deb/g" /etc/apt/sources.list.d/pve-enterprise.list

# Ajouter No-Subscription (Debian 13 Trixie)
echo "deb [http://download.proxmox.com/debian/pve](http://download.proxmox.com/debian/pve) trixie pve-no-subscription" > /etc/apt/sources.list.d/pve-no-subscription.list
```

### B. Activation de l'IOMMU
```bash
# Editer GRUB
# Ajouter 'amd_iommu=on' à GRUB_CMDLINE_LINUX_DEFAULT
nano /etc/default/grub
update-grub
```

## 4. Configuration Réseau (Bridge WAN)
Pour éviter les problèmes de pilotes Realtek 2.5G dans OPNsense :
1. Aller dans **System > Network**.
2. **vmbr0 (LAN) :** Déjà créé sur `nic0`.
3. **Créer vmbr1 (WAN) :**
    * Type : `Linux Bridge`.
    * Ports : `nic1` (`enp...` inutilisé).
    * Commentaire : `WAN-Physique`.
    * **Ne pas mettre d'IP**.
4. Cliquer sur **Apply Configuration**.
