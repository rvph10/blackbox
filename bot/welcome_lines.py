"""Phrases d'accueil piochées au hasard quand un membre rejoint (ADR-021).

Placeholders : `{mention}` (le nouvel arrivant), `{vibecat}` (emoji animé du
serveur), `{discussions}` (lien vers le salon). Ajouter / retirer des lignes
librement.
"""

import random

VIBECAT = "<a:vibecat:1542947100587860018>"
DISCUSSIONS = "<#1542926642182230076>"

LINES = [
    "Yo {mention}, bienvenue sur Blackbox {vibecat} — passe dire bonjour "
    "dans {discussions}.",
    "{mention} vient de débarquer {vibecat}. Fais comme chez toi.",
    "Nouvelle tête sur Blackbox : {mention} ! Bienvenue.",
    "Bienvenue {mention} {vibecat} La salle de projection t'attend.",
    "{mention} a rejoint le club. Popcorn prêt.",
    "Salut {mention} et bienvenue ! Jette un œil à {discussions} pour la suite.",
    "On accueille {mention} comme il se doit {vibecat} Bienvenue sur Blackbox.",
    "{mention} est dans la place. Bienvenue !",
]


def pick(mention: str) -> str:
    return random.choice(LINES).format(
        mention=mention, vibecat=VIBECAT, discussions=DISCUSSIONS
    )
