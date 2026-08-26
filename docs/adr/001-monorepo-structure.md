# ADR 001 — Structure monorepo

**Statut :** Accepté
**Date :** 2026-08-26

## Contexte

Le projet a trois briques distinctes : infra (Ansible, Docker Compose), le bot
Discord (Python), et la doc (architecture, ADR, runbooks). Solo dev, un seul
contributeur, projet à double vocation (usage réel + portfolio).

## Décision

Un seul repo Git plutôt qu'un repo par brique.

```
docs/    → brief, audit, ADR, runbooks
infra/   → Ansible + Docker Compose (dev/staging/prod)
bot/     → bot Discord Python
```

Pas de vraie raison de séparer en multi-repo ici : je suis seul, je n'ai pas
besoin d'isoler des cycles de release ou de gérer des permissions par équipe.
Le seul coût du multi-repo (synchro de versions entre dépôts, PR croisées)
n'a pas de contrepartie côté bénéfice à cette échelle.

## Conséquences

Un seul historique à parcourir pour comprendre l'évolution du projet — utile
pour le côté portfolio, quelqu'un qui regarde le repo voit tout au même
endroit. La CI pourra quand même cibler `bot/` seul si besoin (pas obligé de
tout lancer à chaque commit).

Si le projet grossit un jour (plusieurs contributeurs, cycles de release
séparés par brique), on repassera en multi-repo. Pas pertinent maintenant.
