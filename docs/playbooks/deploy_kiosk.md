# 🖥️ deploy_kiosk.yml

## Objectif

Déploie le dashboard tactile Python sur le Raspberry Pi 5 avec écran 3.5" capacitif. Application Python custom affichant :
- Météo (Open-Meteo API)
- Statistiques réseau (OPNsense API)
- État des services (port probes)
- Statut backups (JSON depuis NAS)
- Statistiques système (CPU, RAM, température)

## Prérequis

### Matériel

- Raspberry Pi 5
- Écran tactile 3.5" (ILI9486 display driver)
- Touch controller ADS7846

###Variables Vault Nécessaires

| Variable | Description |
|----------|-------------|
| `vault_opnsense_api_key` | Clé API OPNsense |
| `vault_opnsense_api_secret` | Secret API OPNsense |
| `vault_gateway_ip` | IP OPNsense (192.168.10.1) |
| `vault_cargo_ip` | IP NAS (192.168.10.5) |

## Actions du Playbook

### 1. Installation Dépendances Python

```bash
python3-pil        # PIL/Pillow (traitement images)
python3-evdev      # Lecture événements tactiles
python3-psutil     # Statistiques système
python3-rpi-gpio   # Contrôle GPIO (backlight)
```

### 2. Configuration Kernel Modules

Modules chargés au boot via `/etc/modules` :
- `fb_ili9486` : Driver LCD ILI9486
- `ads7846` : Driver touchscreen ADS7846

### 3. udev Rules

Fichier `/etc/udev/rules.d/99-ads7846.rules` :
```
SUBSYSTEM=="input", ATTRS{name}=="*ADS7846*", MODE="0666"
```

Permet accès touch input sans sudo.

### 4. Déploiement Application Python

Copie modules depuis `ansible/templates/rpi/dashboard/` :
- `main.py` : Point d'entrée
- `config.py` : Configuration (généré depuis template .j2)
- `display.py` : Contrôle framebuffer + backlight
- `input.py` : Gestion bouton GPIO + touch
- `monitor.py` : Collecte données (threads)
- `renderer.py` : Rendu graphique PIL (350 lignes)
- `hardware.py` : Abstraction GPIO avec fallback

Destination : `/opt/kiosk/`

### 5. Systemd Service

`/etc/systemd/system/kiosk-dashboard.service` :
```ini
[Unit]
Description=Homelab Dashboard Kiosk
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/kiosk
ExecStart=/usr/bin/python3 /opt/kiosk/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Auto-start au boot avec restart automatique.

## Commande d'Exécution

```bash
ansible-playbook playbooks/deploy_kiosk.yml
```

## Fonctionnalités Dashboard

### Pages (Navigation Tactile)

1. **Page 1 : Vue d'ensemble**
   - Météo actuelle + prévisions
   - CPU / RAM / Température
   - Heure système

2. **Page 2 : Réseau**
   - WAN throughput (download/upload)
   - Latency
   - IP publique

3. **Page 3 : Services**
   - État services (vert = up, rouge = down)
   - Dernière vérification

4. **Page Alert** (automatique si service down)
   - Liste services en erreur
   - Retour auto après résolution

### Animations Configurables

```python
# Dans config.py.j2
ANIMATION_TYPE = "slide"  # slide, fade, minimal
ANIMATION_DURATION = 0.3  # secondes
```

### Auto Off/On

- Extinction écran : 00:00 (minuit)
- Allumage écran : 09:00 (matin)
- Override manuel : bouton GPIO

## Vérification

```bash
# Service actif
ssh control-tower.blackbox.homes
systemctl status kiosk-dashboard

# Logs
journalctl -u kiosk-dashboard -f

# Test manuel
cd /opt/kiosk
python3 main.py
```

## Troubleshooting

### Écran reste noir

```bash
# Vérifier modules kernel
lsmod | grep fb_ili9486
lsmod | grep ads7846

# Charger manuellement
sudo modprobe fb_ili9486
sudo modprobe ads7846

# Vérifier framebuffer
ls /dev/fb*  # Devrait montrer /dev/fb0 et /dev/fb1
```

### Touch non fonctionnel

```bash
# Lister devices input
ls /dev/input/event*
evtest /dev/input/event0  # Tester chaque event

# Vérifier permissions
ls -la /dev/input/event* | grep ADS
```

### Erreur API OPNsense

```bash
# Tester API manuellement
curl -k -u "{{ vault_opnsense_api_key }}:{{ vault_opnsense_api_secret }}" \
  https://192.168.10.1/api/diagnostics/interface/getInterfaceStatistics
```

## Références

- Code source : `ansible/templates/rpi/dashboard/`
- Configuration : `docs/bootstrap/control-tower.md`
- Playbook : `ansible/playbooks/deploy_kiosk.yml`
