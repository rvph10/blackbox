"""Phrases d'accueil piochées au hasard quand un membre rejoint (ADR-021).

Placeholders : `{mention}` (le nouvel arrivant), `{vibecat}` (emoji animé du
serveur), `{discussions}` (lien vers le salon). Ajouter / retirer des lignes
librement.
"""

import random

VIBECAT = "<a:vibecat:1542947100587860018>"
DISCUSSIONS = "<#1542926642182230076>"

LINES = [
    "Yo {mention}, bienvenue sur Blackbox {vibecat} — ton compte est prêt, "
    "regarde tes MP puis passe dire bonjour dans {discussions}.",
    "{mention} vient de débarquer {vibecat}. Fais comme chez toi — les "
    "identifiants sont dans tes MP.",
    "Nouvelle tête sur Blackbox : {mention} ! Bienvenue. Tout est expliqué "
    "dans le message d'accueil et tes MP.",
    "Bienvenue {mention} {vibecat} La salle de projection t'attend, tes accès "
    "sont en MP.",
    "{mention} a rejoint le club. Popcorn prêt, compte créé, MP envoyés.",
    "Salut {mention} et bienvenue ! Jette un œil à tes MP pour te connecter, "
    "et à {discussions} pour le reste.",
    "On accueille {mention} comme il se doit {vibecat} Bienvenue sur Blackbox "
    "— check tes MP.",
    "{mention} est dans la place. Bienvenue ! Ton compte Jellyfin t'attend "
    "(détails en MP).",
]


def pick(mention: str) -> str:
    return random.choice(LINES).format(
        mention=mention, vibecat=VIBECAT, discussions=DISCUSSIONS
    )
