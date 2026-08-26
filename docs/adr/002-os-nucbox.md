# ADR 002 — OS du NucBox M6

**Statut :** Accepté
**Date :** 2026-08-26

## Contexte

Le NucBox M6 (Ryzen 5 7640HS, iGPU Radeon 760M RDNA3, 32 Go RAM, 1 To) va être
réinitialisé pour devenir l'hôte Docker (Jellyfin, *arr*, Jellyseerr, Jellystat,
Maintainerr, Postgres, CrowdSec).

Le vrai point d'incertitude du projet, c'est le transcodage matériel VAAPI sur
cette puce : l'audit signale un bug connu sur des puces RDNA3 similaires
(gfx1103/1150). Le support VAAPI dépend du kernel et de Mesa, donc le choix
d'OS n'est pas neutre ici, contrairement à un simple hôte Docker classique.

## Options

- **Debian stable** : prévisible, mais kernel/Mesa figés à la sortie de la
  version stable — risque de faux négatif au test VAAPI sur un iGPU récent.
- **Ubuntu Server LTS + HWE** : kernel et Mesa tenus à jour tout le long du
  cycle LTS sans changer de version majeure. Bien documenté pour Jellyfin+VAAPI.
- **Fedora Server** : support hardware le plus frais, mais cycle de support
  court (~13 mois), donc upgrades de distro fréquents. Pas ce que je veux sur
  un serveur qui doit juste tourner.

## Décision

Ubuntu Server LTS, dernière version disponible au moment de l'install (24.04
minimum), avec le stack HWE activé après coup (pas automatique sur Server,
contrairement à Desktop).

## Conséquences

Les playbooks Ansible cibleront Ubuntu (apt, systemd). Il faut penser à
installer le HWE stack explicitement après le premier boot, sinon on reste sur
le kernel GA. Si le test VAAPI échoue malgré un kernel à jour, au moins ce sera
un résultat fiable — pas un artefact lié à une distro à la traîne côté drivers.
