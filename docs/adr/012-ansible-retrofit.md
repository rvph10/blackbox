# ADR 012 — Rattrapage Ansible

**Statut :** Accepté
**Date :** 2026-08-28

## Contexte

Le brief initial prévoyait Ansible pour le provisioning des deux machines
(reproductibilité), repris dans [ADR-001](001-monorepo-structure.md)
(`infra/ansible/` dans la structure du repo) et pointé comme risque dans
l'audit externe (dépendance du RTO au niveau d'automatisation). Le dossier
est resté vide (`.gitkeep` seulement) tout au long du déploiement réel
(ADR-002 à ADR-011) : chaque étape a été faite via SSH manuel, documentée
dans des runbooks plutôt qu'automatisée. Dérive non intentionnelle,
constatée après coup plutôt que décidée — rattrapée ici plutôt que
laissée comme dette permanente.

## Périmètre : rattraper l'existant, pas repartir de zéro

Playbook `playbooks/site.yml`, quatre rôles reflétant ce qui a déjà été
construit à la main :
- **base** : paquets système (`mesa-va-drivers`, `vainfo`, `restic`,
  `rclone`), appartenance aux groupes `video`/`render`/`docker`
- **docker** : installation de Docker Engine via le dépôt officiel
  (idempotent — vérifie d'abord si déjà installé, ne relance pas
  l'ajout du dépôt/clé GPG si c'est le cas)
- **deploy** : déploie `docker-compose.yml`, le code du bot et des
  scripts (`gluetun-healthcheck`, `backup`) sur le NucBox, lance
  `docker compose up -d --build`
- **systemd_timers** : déploie et active les timers `gluetun-healthcheck`
  et `blackbox-backup`

**Volontairement hors scope** : les secrets (`.env`, `rclone.conf`). Le
playbook vérifie leur présence et avertit s'ils manquent, mais ne les
génère ni ne les modifie jamais — la création reste une étape manuelle
documentée dans chaque runbook (`setup-*.md`), cohérent avec le principe
déjà établi tout au long du projet (jamais de secret géré par un outil
d'automatisation sans confirmation explicite). Netplan et le montage NFS
du NAS restent également hors scope (déjà configurés, trop sensibles pour
un premier rattrapage).

## Bug bloquant trouvé : incompatibilité `sudo-rs` / Ansible

Toutes les tâches nécessitant les privilèges (`become`) échouaient avec
`Timeout (12s) waiting for privilege escalation prompt`, y compris après
plusieurs pistes explorées sans succès (augmentation du timeout — mauvaise
clé de config, retrait du flag `-n` sur `become_flags`, désactivation du
multiplexage SSH `ControlMaster`/`ControlPersist`).

**Cause réelle** : le NucBox utilise **`sudo-rs`** (réécriture de `sudo`
en Rust, devenue le défaut sur les versions récentes d'Ubuntu) plutôt que
le `sudo` GNU historique. `sudo-rs` affiche un texte supplémentaire avant
de déléguer à PAM (`[sudo: authenticate] Password:` au lieu de
`[sudo] password for kong:`), qui casse la détection du prompt par le
plugin `become` sudo d'Ansible — incompatibilité connue et non résolue au
niveau d'Ansible ([ansible/ansible#85837](https://github.com/ansible/ansible/issues/85837)).

**Corrigé** en réinstallant le paquet `sudo` classique
(`apt install --reinstall sudo`, 1.9.17p2) puis en basculant l'alternative
système vers le binaire GNU (`update-alternatives --set sudo
/usr/bin/sudo.ws` — `sudo-rs` restait actif comme alternative prioritaire
malgré la réinstallation du paquet classique). Après bascule, `become`
fonctionne normalement avec `--ask-become-pass`.

## `ansible.cfg` : réglages non par défaut, documentés dans le fichier

- `roles_path = roles` — nécessaire, sinon Ansible cherche les rôles sous
  `playbooks/roles/` par défaut
- `become_ask_pass` volontairement **absent** : le mot de passe sudo est
  toujours demandé de façon interactive via `--ask-become-pass` en ligne
  de commande, jamais stocké — cohérent avec le refus, tout au long du
  projet, d'automatiser les commandes `sudo` sans confirmation explicite
- `become_flags = -H -S` (sans le `-n` par défaut d'Ansible, qui force
  sudo en mode non-interactif et empêche tout prompt d'apparaître)

## Vérification

- Mode simulation (`--check --diff`) passé en premier, aucune surprise
  détectée avant le run réel
- Run réel exécuté : `changed=1` (uniquement la correction de permissions
  `0775` → `0755` sur deux dossiers créés à la main lors du déploiement
  manuel initial, écart mineur sans conséquence)
- Un deuxième run pour confirmer l'idempotence complète (`changed=0`
  partout) reste à faire — point ouvert, noté plutôt que supposé

## Conséquences

- `infra/ansible/` n'est plus vide : `ansible.cfg`, inventaire, playbook,
  4 rôles
- L'écart avec le brief initial est rattrapé pour tout ce qui a été
  construit jusqu'ici ; tout nouveau chantier futur (Layer 3 du bot, ESP8266,
  routeur/VLAN à la migration fibre) devra passer par ce playbook plutôt
  que par du SSH manuel, pour ne pas recréer le même écart
- Documenté ici plutôt que dans un runbook séparé : ADR suffisant, le
  playbook lui-même sert de référence opérationnelle (commentaires inline)
