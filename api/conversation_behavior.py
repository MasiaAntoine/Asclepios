"""Couche personnalité / comportement conversationnel d'Asclepios.

Cette couche est INDÉPENDANTE du moteur médical (sécurité, outils, données).
Elle produit des instructions de style à injecter dans le prompt système.

Charge sa configuration depuis `data/assistant-personality.md` : ce fichier
est éditable par l'utilisateur (via l'UI, ou même via l'assistant lui-même
grâce au système d'édition validée), sans toucher au code médical.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ExchangeType = Literal["simple", "analyse", "conseil", "rumination", "sensible"]

# ── Configuration ───────────────────────────────────────────────────────────

# Cap pour la personnalité injectée (le fichier .md peut être long, on tronque
# pour laisser de la place au contexte médical dans le budget global).
_MAX_PERSONALITY_CHARS = 12_000


# ── Détection du type d'échange ─────────────────────────────────────────────

_ANALYSE_HINTS = (
    "pourquoi", "analyse", "explique", "explique-moi", "comprends pas",
    "qu'est-ce qui", "comment ça se fait", "que penses-tu", "diagnostic",
    "hypothèse", "biais",
)

_CONSEIL_HINTS = (
    "que faire", "je dois", "je devrais", "conseil", "recommande",
    "meilleur choix", "quelle option", "quoi faire", "faut-il", "à ta place",
    "à ma place",
)

_RUMINATION_HINTS = (
    " minutes", " heures ", "combien de temps", "ça veut dire quoi",
    "elle a vu", "vu mon message", "n'a pas répondu", "elle m'a pas répondu",
    "il a mis", "elle a mis", "il lit pas", "elle lit pas",
)

_SENSIBLE_HINTS = (
    "suicide", "me tuer", "en finir", "je veux mourir", "plus envie de vivre",
    "auto-mutil", "je me fais du mal", "crise de panique", "je vais craquer",
    "j'en peux plus", "au bord", "urgence",
)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def _is_addressed_question(message: str, norm: str) -> bool:
    """Vrai si le message ressemble à une question réellement adressée à l'agent."""
    if "?" in message:
        return True
    # Formes interrogatives adressées ("tu penses", "peux-tu", "explique-moi", ...)
    addressed_markers = (
        "tu penses", "tu crois", "tu peux", "peux-tu", "peux tu",
        "explique-moi", "explique moi", "dis-moi", "dis moi",
        "qu'en penses-tu", "qu en penses tu", "à ton avis", "a ton avis",
    )
    return any(m in norm for m in addressed_markers)


def detect_exchange_type(message: str) -> ExchangeType:
    """Heuristiques légères — ne remplace pas le jugement de l'IA, guide juste le style."""
    if not message.strip():
        return "simple"

    norm = _normalize(message)

    # 1. Sujets sensibles (prioritaires)
    if any(h in norm for h in _SENSIBLE_HINTS):
        return "sensible"

    # 2. Rumination : détails minuscules, chronomètre, lecture des pensées
    if any(h in norm for h in _RUMINATION_HINTS):
        return "rumination"

    addressed = _is_addressed_question(message, norm)

    # 3. Demande de conseil (doit être adressée à l'agent)
    if addressed and any(h in norm for h in _CONSEIL_HINTS):
        return "conseil"

    # 4. Demande d'analyse (doit être adressée à l'agent — sinon c'est un partage
    #    du type "je viens de comprendre pourquoi j'aimais X" → conversation simple)
    if addressed and any(h in norm for h in _ANALYSE_HINTS):
        return "analyse"

    # 5. Message court / réactif → conversation simple
    words = re.findall(r"\S+", message)
    if len(words) <= 25:
        return "simple"

    # 6. Long message non explicitement interrogatif → traitement plutôt analytique
    return "analyse"


# ── Chargement de la personnalité éditable ─────────────────────────────────


def _load_personality_md(data_dir: Path) -> str:
    path = data_dir / "assistant-personality.md"
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if len(text) > _MAX_PERSONALITY_CHARS:
        text = text[: _MAX_PERSONALITY_CHARS - 40].rstrip() + "\n\n[… tronqué …]"
    return text


# ── Instructions ciblées par type d'échange ─────────────────────────────────

_STYLE_HINTS: dict[ExchangeType, str] = {
    "simple": (
        "Type détecté : conversation simple.\n"
        "- Réponds court et naturel.\n"
        "- Ne fais pas d'analyse psychologique non demandée.\n"
        "- Une question de relance minimale suffit si besoin, sinon rien."
    ),
    "analyse": (
        "Type détecté : demande d'analyse.\n"
        "- Sépare faits / interprétations / hypothèses / incertitudes.\n"
        "- Nomme le niveau de confiance de chaque hypothèse.\n"
        "- Ne présente jamais une hypothèse comme un diagnostic."
    ),
    "conseil": (
        "Type détecté : demande de conseil.\n"
        "- Donne une recommandation claire si les infos le permettent.\n"
        "- Explique le pourquoi en 1 ou 2 phrases.\n"
        "- Évite d'aligner 5 options équivalentes ; si une option est meilleure, dis-le."
    ),
    "rumination": (
        "Type détecté : possible rumination / suranalyse.\n"
        "- Ne construis PAS une longue liste d'hypothèses sur un détail (temps de réponse, "
        "un mot, un silence).\n"
        "- Nomme calmement que ce détail ne permet pas de conclure.\n"
        "- Ramène vers ce qui est réellement observable dans la situation globale."
    ),
    "sensible": (
        "Type détecté : sujet potentiellement sensible / crise.\n"
        "- Priorité absolue : sécurité de l'utilisateur.\n"
        "- Reste calme, direct, non-jugeant, pas de disclaimer répétitif.\n"
        "- Si signaux d'urgence : rappelle 3114 (France, écoute suicide 24/7) "
        "et suggère de contacter une personne de confiance ou un professionnel.\n"
        "- Pas d'humour, pas de familiarité forcée."
    ),
}


# ── Interface principale ────────────────────────────────────────────────────


@dataclass(frozen=True)
class BehaviorInstructions:
    exchange_type: ExchangeType
    profile_block: str  # profil complet (à mettre en TÊTE du prompt)
    hint_block: str  # précision contextuelle pour ce message (additive)
    reminder_line: str  # ligne courte à répéter juste avant la génération


class ConversationBehaviorProfile:
    """Produit les instructions de style pour une réponse donnée.

    Ne prend PAS de décision médicale, ne touche PAS aux outils / données :
    c'est le rôle de la couche médicale de `main.py`.
    """

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def build(self, user_message: str) -> BehaviorInstructions:
        exchange = detect_exchange_type(user_message)
        personality_md = _load_personality_md(self._data_dir)
        style_hint = _STYLE_HINTS[exchange]

        if personality_md:
            profile_block = (
                "===== PROFIL COMPORTEMENTAL — À APPLIQUER SYSTÉMATIQUEMENT =====\n"
                "Ces règles définissent TA façon de parler par défaut, à CHAQUE réponse, "
                "sans exception. Elles ne sont pas optionnelles ni situationnelles : c'est "
                "ta personnalité permanente. Seule la sécurité médicale/psychologique peut "
                "les surclasser ponctuellement (cf. règle 16).\n\n"
                f"{personality_md}\n"
                "===== FIN PROFIL COMPORTEMENTAL ====="
            )
        else:
            profile_block = ""

        hint_block = (
            "===== PRÉCISION CONTEXTUELLE POUR CE MESSAGE (additive) =====\n"
            "Ce hint AFFINE le profil comportemental pour ce message précis, il ne le "
            "remplace jamais. Le profil ci-dessus reste appliqué intégralement.\n\n"
            f"{style_hint}\n"
            "===== FIN PRÉCISION CONTEXTUELLE ====="
        )

        reminder = (
            "Applique le PROFIL COMPORTEMENTAL de bout en bout : "
            "empathie sans complaisance, pas de tics thérapeutiques, "
            "structure adaptée (pas de gabarit par défaut), "
            "pas de question de relance systématique, "
            "capacité à ne pas être d'accord et à reconnaître l'incertitude."
        )

        return BehaviorInstructions(
            exchange_type=exchange,
            profile_block=profile_block,
            hint_block=hint_block,
            reminder_line=reminder,
        )
