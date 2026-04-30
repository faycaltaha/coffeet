"""
Stage 2 – Script Generation.

Calls the Anthropic Claude API to generate Marcel's 40-second spoken script.
Uses claude-haiku-4-5 for cost efficiency (~€0.002/script).
"""
from __future__ import annotations

import logging
import os

import anthropic

from .car_selector import CarOfTheDay, car_to_json_payload

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Tu es Marcel, l'IA brutalement honnête et ultra-analytique d'Autoradar.
Écris un script de 40 secondes pour une vidéo verticale au format TikTok/Reels.
Règles strictes :
- Commence par un hook accrocheur sur la voiture (chiffre, fait surprenant, question rhétorique).
- Décompose ensuite le kilométrage, le prix et la fiabilité avec ton œil d'expert.
- Donne ton "Verdict Marcel" final en une phrase percutante.
- Termine par un call-to-action pour s'abonner à Autoradar afin de trouver des deals comme celui-ci.
- Phrases courtes. Ton légèrement sarcastique mais expert. Pas de directions visuelles, uniquement le texte parlé.
- Réponse en français uniquement. Ne mets pas de tirets, astérisques ou balises dans le texte.
"""

_MODEL = "claude-haiku-4-5-20251001"


def _build_user_message(car: CarOfTheDay) -> str:
    payload = car_to_json_payload(car)
    profit_str = (
        f"+{payload['estimated_profit']:,} €".replace(",", " ")
        if payload["estimated_profit"] > 0
        else "inconnu"
    )
    return f"""Voici la voiture du jour :

Marque / Modèle : {payload['make']} {payload['model']} ({payload['year']})
Kilométrage : {payload['mileage_km']:,} km
Prix demandé : {payload['price_eur']:,} €
Carburant : {payload['fuel'].capitalize()}
Marge estimée à la revente : {profit_str}
Score fiabilité Autoradar : {payload['reliability_score']:.0f} / 100
Score prix Autoradar : {payload['price_score']:.0f} / 100
Score global Autoradar : {payload['overall_score']:.0f} / 100

Génère le script Marcel."""


def generate_script(car: CarOfTheDay) -> str:
    """
    Call Claude to generate Marcel's spoken script.

    Returns the raw script text (French, ~200-300 words, no markdown).
    Raises anthropic.APIError on API failures.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_message(car)}],
    )

    script = message.content[0].text.strip()
    logger.info(
        "[script_generator] Script generated (%d chars, %d input tokens, %d output tokens).",
        len(script),
        message.usage.input_tokens,
        message.usage.output_tokens,
    )
    return script
