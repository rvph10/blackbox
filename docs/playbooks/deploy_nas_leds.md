# 💡 deploy_nas_leds.yml

## Objectif

Configure le contrôle automatisé des LEDs du NAS UGREEN DXP2800 via cron :
- **Extinction** : 23:00 (économie énergie + réduction pollution lumineuse)
- **Allumage** : 09:00 (visibilité indicateurs journée)

Utilise le projet communautaire [ugreen_leds_controller](https://github.com/miskcoo/ugreen_leds_controller).

## Prérequis

### Hardware

- UGREEN DXP2800 avec firmware UGOS
- Chipset contrôle LED accessible via i2c

### Système

- Module kernel `i2c-dev` disponible
- Outils build : `gcc`, `make`, `git`

## Actions du Playbook

### 1. Installation Dépendances

```bash
apt install git build-essential i2c-tools
```

### 2. Clonage Repository

Clone depuis GitHub dans `/opt/ugreen_leds_controller/`.

### 3. Compilation

```bash
cd /opt/ugreen_leds_controller
make
```

Génère binaire `led-ugreen` pour contrôle LEDs.

### 4. Chargement Module Kernel i2c-dev

```bash
modprobe i2c-dev
echo "i2c-dev" >> /etc/modules  # Persistant au reboot
```

### 5. Création Scripts Cron

**Script ON** (`/opt/ugreen_leds_controller/leds-on.sh`) :
```bash
#!/bin/bash
/opt/ugreen_leds_controller/led-ugreen disk-leds on
```

**Script OFF** (`/opt/ugreen_leds_controller/leds-off.sh`) :
```bash
#!/bin/bash
/opt/ugreen_leds_controller/led-ugreen disk-leds off
```

Générés depuis templates Jinja2.

### 6. Planification Cron

```cron
0 23 * * * /opt/ugreen_leds_controller/leds-off.sh  # Extinction 23:00
0 9 * * * /opt/ugreen_leds_controller/leds-on.sh    # Allumage 09:00
```

## Commande d'Exécution

```bash
ansible-playbook playbooks/deploy_nas_leds.yml
```

## Vérification

```bash
ssh 192.168.10.5

# Vérifier module i2c-dev chargé
lsmod | grep i2c_dev

# Tester contrôle LED manuel
cd /opt/ugreen_leds_controller
./led-ugreen disk-leds off  # Extinction immédiate
sleep 2
./led-ugreen disk-leds on   # Rallumage

# Vérifier cron
crontab -l | grep leds
```

## Troubleshooting

### Module i2c-dev non chargé

```bash
# Charger manuellement
modprobe i2c-dev

# Vérifier disponibilité
ls /dev/i2c-*
```

### Erreur compilation

```bash
# Réinstaller dépendances
apt update
apt install --reinstall build-essential

# Nettoyer et recompiler
cd /opt/ugreen_leds_controller
make clean
make
```

### LEDs ne répondent pas

```bash
# Vérifier devices i2c
i2cdetect -l
i2cdetect -y 0  # Scanner bus i2c

# Tester avec debug
./led-ugreen disk-leds status
```

## Personnalisation

### Changer Horaires

Éditer template `ansible/templates/nas/leds-off.sh.j2` et `leds-on.sh.j2` pour modifier planification cron.

### Contrôle LED Réseau

```bash
# Allumer LED réseau
./led-ugreen net-leds on

# Mode disco (animation)
./led-ugreen disk-leds blink
```

## Références

- Projet upstream : [https://github.com/miskcoo/ugreen_leds_controller](https://github.com/miskcoo/ugreen_leds_controller)
- Templates : `ansible/templates/nas/leds-*.sh.j2`
- Playbook : `ansible/playbooks/deploy_nas_leds.yml`
