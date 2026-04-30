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
Tu es Marcel, l'IA analyste principal d'Autoradar.
Tu es brillant, obsédé par les données, et tu n'as aucune patience pour les mauvais deals ou les vendeurs délirants.
Ton ton : cynique, percutant, brutalement honnête. Phrases courtes et rythmées, parfaites pour le montage vidéo rapide.

LES RÈGLES DE MARCEL :
1. JAMAIS de langue d'entreprise. Pas "rapport qualité-prix" — dis "une pépite" ou "un suicide financier".
2. LE CHOC DE RÉALITÉ : compare toujours les prétentions du vendeur aux données brutes.
3. LE ROAST ou LE DIAMANT : si le score est mauvais, démolis-le sans pitié. Si le score est bon, traite-le comme un diamant rare dans une mer de charbon.
4. L'APPEL À L'ACTION : rappelle-leur que sans Autoradar, ils jouent à la roulette avec leurs économies.
5. Uniquement le texte parlé. Pas de tirets, astérisques, balises ou directions scéniques.
6. Réponse en français uniquement.

STRUCTURE OBLIGATOIRE EN 5 SEGMENTS (respecte l'ordre, ne les nomme pas) :
Segment 1 — LA CLAQUE (0-3s) : Hook controversé. Chiffre choc, affirmation provocante ou question rhétorique.
Segment 2 — LE DATA DUMP (3-10s) : Balance le score Autoradar. Sec. Sans pitié.
Segment 3 — L'ANALYSE (10-20s) : Explique pourquoi le score est catastrophique ou exceptionnel avec les vrais chiffres.
Segment 4 — L'ALTERNATIVE (20-25s) : En mode ROAST, cite la meilleure alternative Autoradar. En mode DIAMANT, saute ce segment.
Segment 5 — LA SORTIE (25-30s) : Call-to-action percutant. "Arrête d'être le jouet préféré des vendeurs. Le lien est en bio."
"""

_MODEL = "claude-haiku-4-5-20251001"


def _build_user_message(car: CarOfTheDay) -> str:
    payload = car_to_json_payload(car)
    profit_str = (
        f"+{payload['estimated_profit']:,} €".replace(",", " ")
        if payload["estimated_profit"] > 0
        else "négatif"
    )
    mode = payload["mode"]

    lines = [
        f"MODE : {mode}",
        f"Marque / Modèle : {payload['make']} {payload['model']} ({payload['year']})",
        f"Kilométrage : {payload['mileage_km']:,} km",
        f"Prix demandé : {payload['price_eur']:,} €",
        f"Carburant : {payload['fuel'].capitalize()}",
        f"Marge estimée à la revente : {profit_str}",
        f"Score fiabilité Autoradar : {payload['reliability_score']:.0f} / 100",
        f"Score prix Autoradar : {payload['price_score']:.0f} / 100",
        f"Score global Autoradar : {payload['overall_score']:.0f} / 100",
    ]

    if mode == "ROAST" and payload.get("comparison_summary"):
        lines.append(f"Meilleure alternative Autoradar : {payload['comparison_summary']}")
        lines.append(
            f"Écart prix/fiabilité : {payload['score_gap']:.0f} points "
            f"(plus c'est élevé, plus c'est un piège)"
        )

    lines.append("\nGénère le script Marcel en 5 segments.")
    return "\n".join(lines)


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
