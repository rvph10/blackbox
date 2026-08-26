# ADR 003 — RAID sur le NAS

**Statut :** Accepté
**Date :** 2026-08-26

## Contexte

Le Ugreen DXP2800 (2×4 To) stocke la médiathèque et sert les partages SMB/NFS
au NucBox. Ce choix doit être fait avant de remplir le NAS — changer de niveau
RAID après coup veut dire tout re-télécharger.

## Décision

RAID1 (4 To utiles) plutôt que RAID0 (8 To sans redondance). En RAID0, un
disque qui lâche = toute la médiathèque à refaire, potentiellement des mois de
re-téléchargement pour rien. Le compromis capacité ne vaut pas ce risque.

## Conséquences

4 To utiles seulement. Si la bibliothèque grossit vite, ça deviendra un
goulot d'étranglement — le NAS n'a que 2 baies, pas d'évolution RAID possible
sans tout remplacer. Le jour où ça arrive, la réponse c'est un NAS 4 baies en
RAID5/6, pas un retour en RAID0.

Important à ne pas oublier : RAID1 protège contre une panne disque, pas contre
une suppression accidentelle ou une corruption. Ça ne remplace pas le backup
restic/rclone prévu en phase 3 (configs + dumps Postgres — la médiathèque elle
n'a pas besoin de backup, elle est re-téléchargeable).

Le NAS reste sous UGOS Pro, donc pas de ZFS/snapshots natifs. Un monitoring
SMART basique (script + alerte Discord) reste utile pour repérer une panne
avant qu'elle ne devienne un problème.
