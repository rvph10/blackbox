# ADR 004 — Réveil réseau : veille S3 plutôt qu'extinction S5

**Statut :** Accepté
**Date :** 2026-08-27

## Contexte

Le brief (§7) prévoyait une extinction complète (S5) du NucBox en dehors des
heures d'usage, avec réveil par Wake-on-LAN déclenché depuis le RPi5. C'était
identifié comme le risque n°1 du projet (§12 du brief, priorité n°1 de l'audit
§17) — support WoL non confirmé sur le NucBox M6.

Test réalisé en conditions réelles, avec la carte réseau connectée
(`lan0`, RTL8125 2.5GbE) :

- BIOS vérifié : `Wake on LAN = Enabled`, `Auto power on = Power On` — corrects
- Driver in-kernel `r8169` remplacé par le driver officiel Realtek `r8125-dkms`
- Paramètres module appliqués : `s5wol=1 s0_magic_packet=1 eee_enable=0 aspm=0
  s5_keep_curr_mac=1`
- Testé en filaire direct (même sous-réseau que l'émetteur) pour écarter tout
  problème de relais broadcast Wi-Fi/Ethernet

Résultat : **le réveil par magic packet ne fonctionne jamais depuis une
extinction complète (S5)**, malgré une config logicielle et BIOS correctes des
deux côtés. En revanche, **le réveil fonctionne de façon fiable et rapide
(~5 secondes) depuis une veille S3** (`systemctl suspend`).

Conclusion : c'est une limitation firmware/matérielle de cette carte mère pour
le réveil réseau depuis S5, pas un problème de configuration côté OS.

## Décision

La logique d'extinction programmée (Phase 4 du brief) utilisera une **veille
S3** plutôt qu'une extinction S5 complète.

## Conséquences

- Économie d'énergie réduite par rapport à un vrai S5 (S3 maintient la RAM
  alimentée et plusieurs rails actifs). Le calcul du brief (§10) estimait déjà
  le gain de l'extinction S5 à ~18€/an, marginal — avec S3 à la place, ce gain
  sera encore plus faible, probablement négligeable. Ça renforce le point déjà
  soulevé par l'audit (§12) : cette fonctionnalité se justifie comme
  démonstration technique (WoL, orchestration, veille programmée), pas comme
  optimisation de coût. À formuler ainsi dans la doc portfolio.
- Le risque n°1 du projet (WoL) est validé et débloque la suite : le bot
  Discord peut être développé sur cette base (`systemctl suspend` /
  `wakeonlan` plutôt que `poweroff`/WoL classique).
- Si une mise à jour BIOS future de GMKtec corrige le réveil depuis S5, on
  pourra reconsidérer cette décision — pas de dépendance dure au choix S3
  ailleurs dans le code (le bot enverra un magic packet dans les deux cas,
  seule la commande d'extinction change : `systemctl suspend` au lieu de
  `systemctl poweroff`).
- Le driver `r8125-dkms` reste en place (remplace `r8169`) : nécessaire pour
  que le WoL fonctionne ne serait-ce que depuis S3 — à garder en tête pour le
  runbook de réinstallation (le driver in-kernel seul ne suffisait pas, même
  pour S3).
