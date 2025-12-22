# 📺 setup_screen.yml

## Objectif

**PLAYBOOK LEGACY** - Configuration basique de l'écran tactile 3.5".

**Note** : Ce playbook est remplacé par `deploy_kiosk.yml` qui inclut configuration écran + déploiement application dashboard complète.

## État

❌ **DÉPRÉCIÉ** - Utilisé initialement pour tests écran. Remplacé par workflow complet dans `deploy_kiosk.yml`.

## Migration Recommandée

Utiliser à la place :
```bash
ansible-playbook playbooks/deploy_kiosk.yml
```

Qui configure :
- Kernel modules (fb_ili9486, ads7846)
- udev rules
- Application Python dashboard
- Systemd service auto-start

## Références

- Documentation dashboard : `docs/playbooks/deploy_kiosk.md`
- Bootstrap Raspberry Pi : `docs/bootstrap/control-tower.md`
