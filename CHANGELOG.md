# Changelog

## [Non publié]

### 2026-08-26

- Squelette du repo (docs/infra/bot), import du brief et de l'audit dans `docs/`
- ADR-001 : structure monorepo
- ADR-002 : OS du NucBox → Ubuntu Server LTS + HWE, surtout pour garder un
  kernel/Mesa à jour avant le test VAAPI
- ADR-003 : RAID1 sur le NAS plutôt que RAID0
- Runbook d'installation OS pour le NucBox (BIOS, HWE, snap Docker à éviter)

### 2026-08-27

- OS Ubuntu Server 26.04 LTS installé sur le NucBox, hostname `nucbox`
- Clé SSH dédiée générée et déployée (`id_nucbox`), alias `ssh nucbox` ajouté
- Wake-on-LAN testé de bout en bout : ne fonctionne pas depuis S5 malgré BIOS
  correct et driver `r8125-dkms` avec tous les paramètres recommandés
  (`s5wol`, `aspm=0`, `eee_enable=0`) — fonctionne de façon fiable depuis S3.
  ADR-004 : on utilisera S3 plutôt que S5 pour l'extinction programmée.
- Runbook WoL complet (BIOS, driver, netplan par MAC, paramètres module)
- Netplan corrigé : `eno1` marqué optionnel (supprime un délai de boot de 2min
  dû à `systemd-networkd-wait-online`), `dhcp4` activé sur l'interface filaire
- ADR-005 (supersède ADR-004) : abandon de l'extinction/veille programmée —
  le NucBox reste allumé 24/7 (redémarrages ponctuels uniquement). WoL
  abandonné entièrement (plus nécessaire), runbook associé archivé. Bot
  Discord hébergé sur le NucBox plutôt que sur un RPi séparé. Plus de RPi
  dans l'archi cible : le seul rôle externe restant (watchdog ping + alerte,
  domaine de panne indépendant du NucBox) sera couvert par un microcontrôleur
  ESP8266 (AZ-Delivery NodeMCU, déjà en stock) en Wi-Fi via ESPHome ; archi
  cible du README mise à jour
- Choix microcontrôleur watchdog ajusté : ESP8266 (AZ-Delivery NodeMCU/D1
  mini déjà possédés) plutôt qu'un ESP32+Ethernet à acheter — compromis
  Wi-Fi documenté dans l'ADR-005. RPi Zero 2 W disponible mais gardé en
  réserve, pas utilisé pour ce rôle
- Brief (`docs/homelab_projet.md`) et audit (`docs/audit_projet.md`)
  réécrits pour un ton documentaire neutre (suppression des emojis de
  sévérité, des tournures trop orales/IA), contenu et conclusions inchangés
- ADR-006 : transcodage matériel VAAPI validé sur le Radeon 760M
  (`mesa-va-drivers` + `vainfo`, utilisateur ajouté aux groupes
  `video`/`render` pour accéder à `/dev/dri/renderD128`). Test réel via
  `ffmpeg` (decode H264 → encode HEVC en VAAPI, ~23x temps réel), pas
  seulement l'énumération de capacités `vainfo`. Risque n°2 du projet levé
- Docker Engine installé sur le NucBox (dépôt officiel apt, pas le snap ;
  utilisateur ajouté au groupe `docker`)
- Premier déploiement applicatif : Jellyfin seul (`infra/docker/prod/`),
  stockage média temporaire en local (SSD) en attendant le NAS,
  `/dev/dri` passé au conteneur avec les GID `video`/`render` de l'hôte via
  `group_add` — accès GPU confirmé à l'intérieur du conteneur, `ffmpeg`
  embarqué détecte les encodeurs/décodeurs VAAPI. Postgres et la suite
  *arr* pas encore ajoutés (périmètre volontairement réduit pour ce
  premier déploiement)
