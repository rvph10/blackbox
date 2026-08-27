# ADR 005 — NucBox allumé en permanence, watchdog externe par microcontrôleur

**Statut :** Accepté
**Date :** 2026-08-27
**Supersède :** [ADR-004](004-wol-s3-not-s5.md)

## Contexte

[ADR-004](004-wol-s3-not-s5.md) avait validé le réveil réseau (WoL) comme
débloquant pour la Phase 4 du brief (extinction programmée en dehors des
heures d'usage, réveil par magic packet), avec la limitation que le réveil ne
fonctionne que depuis une veille S3, jamais depuis une extinction complète
S5.

Décision prise depuis : on n'exploitera pas cette logique d'extinction
programmée, et le WoL n'est donc plus nécessaire du tout — même pas comme
utilitaire de réveil manuel, puisque le NucBox ne sera jamais éteint en
usage normal (voir ci-dessous).

Raisons :

- Le gain estimé par le brief (§10) pour l'extinction S5 était déjà marginal
  (~18€/an) ; avec S3 à la place (ADR-004), le gain devenait encore plus
  faible. Ça ne justifiait plus la complexité d'orchestrer une extinction/
  réveil programmés pour un service communautaire où la dispo doit rester
  simple et prévisible.
- Un serveur communautaire (Jellyfin partagé) a intérêt à répondre à tout
  moment sans latence de réveil, même de quelques secondes.

## Décision

- Le NucBox reste **allumé 24/7**. Pas d'extinction ni de mise en veille
  programmée — seulement des redémarrages ponctuels nécessaires (mises à
  jour, maintenance), faits manuellement.
- Le WoL est **abandonné** : plus de driver `r8125` dédié à maintenir pour
  ça, plus de paramétrage BIOS/module spécifique, plus de runbook à suivre.
  Le runbook [setup-wol-nucbox.md](../runbooks/setup-wol-nucbox.md) est
  archivé (marqué obsolète) — gardé pour référence technique uniquement.
- Le bot Discord est hébergé directement sur le NucBox (conteneur Docker),
  pas sur un appareil séparé.
- Le rôle "sentinelle" prévu pour un RPi5 (bot Discord + orchestration WoL +
  watcher seuil) disparaît entièrement : ces fonctions tournent sur le
  NucBox, qui est de toute façon allumé en continu.
- Le seul rôle externe qui reste utile est un **watchdog indépendant** : un
  point de surveillance dans un domaine de panne séparé du NucBox, qui le
  ping et alerte (Discord) s'il ne répond plus — utile si le NucBox plante
  ou perd le réseau, cas où un service tournant dessus ne peut pas
  s'auto-signaler.
- Ce rôle ne justifie plus un RPi (OS complet, carte SD, plus cher, plus
  fragile) : on utilise un **microcontrôleur** à la place — matériel déjà
  possédé : **AZ-Delivery ESP8266 (NodeMCU)**, en Wi-Fi, firmware
  **ESPHome** (composant `wifi` + `http_request` pour ping le NucBox et
  poster sur un webhook Discord en cas d'échec). Pas d'OS à maintenir, boot
  quasi instantané, conso minime.
  Compromis assumé : pas d'Ethernet sur ce chipset, donc dépendance au
  Wi-Fi — si l'AP tombe en même temps que le NucBox (coupure de courant
  générale, par ex.), le watchdog est aveugle aussi. Accepté pour éviter
  d'acheter du matériel neuf pour un gain de fiabilité marginal ; un module
  Ethernet (W5500) pourra être ajouté plus tard si besoin.
  Le RPi Zero 2 (W), également disponible, reste en réserve pour un usage
  futur (ex. Pi-hole) plutôt que pour ce rôle — inutilement lourd (OS
  complet) pour un simple ping/webhook.
- Piste ouverte : coupler ce watchdog à une prise connectée pour permettre
  un power-cycle physique du NucBox à distance en cas de blocage complet.

## Conséquences

- Plus de RPi dans l'archi cible — remplacé par un microcontrôleur ESP8266
  (déjà en stock) pour le seul rôle qui restait (watchdog).
- ADR-004 reste comme trace historique du test WoL (limitation matérielle
  S5 vs S3, driver `r8125` nécessaire), mais est **superseded** : plus
  aucune dépendance active à cette configuration dans le projet.
- Le runbook WoL n'est plus dans le flux opérationnel normal (pas de
  réinstallation OS qui en dépend), il reste juste comme référence en cas
  de retour en arrière futur.
- Choix de la prise connectée pour le power-cycle physique à distance
  reste à confirmer (point ouvert du README).
