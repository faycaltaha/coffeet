"""
Stage 2 – Script Generation.

Calls the Anthropic Claude API to generate Marcel's 40-second spoken script.
Uses claude-haiku-4-5 for cost efficiency (~€0.002/script).
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import date

import anthropic

from .car_selector import CarOfTheDay, car_to_json_payload

logger = logging.getLogger(__name__)

# ── Marcel signature pool ──────────────────────────────────────────────────────
# Each video ends with one phrase from the matching mode pool, picked by a
# deterministic daily hash — consistent within a day, varied across days.
# ROAST phrases are brutal warnings; DIAMOND phrases are triumphant / exclusive.
MARCEL_SIGNATURES: dict[str, list[str]] = {
    "ROAST": [
        "Ne venez pas pleurer quand elle vous lâchera sur l'autoroute. Moi, j'ai fait mon job. C'est Autoradar.",
        "Le vendeur sourit, mais mes chiffres font la gueule. La vérité est ailleurs. Bienvenue sur Autoradar.",
        "Verdict : une ruine sur quatre roues. Votre portefeuille mérite mieux que ça. Signé Autoradar.",
        "La data n'a pas d'états d'âme, contrairement à votre garagiste. Vous êtes prévenus. C'est Autoradar.",
        "Acheter ça, c'est du suicide financier. Arrêtez de deviner, commencez à calculer. Autoradar.",
        "J'analyse, je juge, je condamne. Ne soyez pas la prochaine victime. Autoradar.",
    ],
    "DIAMOND": [
        "Une perle rare dans un océan de ferraille. La machine a parlé. C'est Autoradar.",
        "Pendant que vous hésitez, mon algorithme a déjà validé. Le deal est là. Autoradar.",
        "La chance, c'est pour les amateurs. La précision, c'est pour vous. Signé Autoradar.",
        "J'ai scanné, j'ai trouvé, vous n'avez plus qu'à cliquer. Trop facile. Autoradar.",
        "Mon processeur ne valide presque jamais. Mais là, c'est du lourd. Certifié Autoradar.",
        "L'affaire du siècle n'attend pas les retardataires. Je l'ai trouvée, à vous de jouer. Autoradar.",
    ],
}


def pick_signature(car: CarOfTheDay, today: date | None = None) -> str:
    """
    Return the Marcel signature catchphrase for this car and day.

    Uses MD5(car.title + ISO date) so the same pipeline run always returns the
    same phrase, while varying day to day for community-building variety.
    Unknown mode values fall back to the ROAST pool.
    """
    pool = MARCEL_SIGNATURES.get(car.mode, MARCEL_SIGNATURES["ROAST"])
    seed = f"{car.title}:{(today or date.today()).isoformat()}"
    index = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(pool)
    return pool[index]


# ── Prompts ────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Tu es Marcel, l'IA analyste principal d'Autoradar.
Tu es brillant, obsédé par les données, et tu n'as aucune patience pour les mauvais deals ou les vendeurs délirants.
Ton ton : cynique, percutant, brutalement honnête. Phrases courtes et rythmées, parfaites pour le montage vidéo rapide.

LES RÈGLES DE MARCEL :
1. JAMAIS de langue d'entreprise. Pas "rapport qualité-prix" — dis "une pépite" ou "un suicide financier".
2. LE CHOC DE RÉALITÉ : compare toujours les prétentions du vendeur aux données brutes.
3. LE ROAST ou LE DIAMANT : si le score est mauvais, démolis-le sans pitié. Si le score est bon, traite-le comme un diamant rare dans une mer de charbon.
4. L'APPEL À L'ACTION : rappelle-leur que sans Autoradar, ils jouent à la roulette avec leurs économies.
5. LA SIGNATURE : le message contient une SIGNATURE FINALE. Tu dois clore le Segment 5 par cette phrase exacte, mot pour mot.
6. Uniquement le texte parlé. Pas de tirets, astérisques, balises ou directions scéniques.
7. Réponse en français uniquement.

STRUCTURE OBLIGATOIRE EN 5 SEGMENTS (respecte l'ordre, ne les nomme pas) :
Segment 1 — LA CLAQUE (0-3s) : Hook controversé. Chiffre choc, affirmation provocante ou question rhétorique.
Segment 2 — LE DATA DUMP (3-10s) : Balance le score Autoradar. Sec. Sans pitié.
Segment 3 — L'ANALYSE (10-20s) : Explique pourquoi le score est catastrophique ou exceptionnel avec les vrais chiffres.
Segment 4 — L'ALTERNATIVE (20-25s) : En mode ROAST, cite la meilleure alternative Autoradar. En mode DIAMANT, saute ce segment.
Segment 5 — LA SORTIE (25-30s) : Call-to-action. Lien en bio. Termine obligatoirement par la SIGNATURE FINALE fournie.
"""

_MODEL = "claude-haiku-4-5-20251001"


def _build_user_message(car: CarOfTheDay, signature: str) -> str:
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

    lines.append(f'\nSIGNATURE FINALE OBLIGATOIRE : "{signature}"')
    lines.append("Génère le script Marcel en 5 segments.")
    return "\n".join(lines)


def generate_script(car: CarOfTheDay) -> str:
    """
    Call Claude to generate Marcel's spoken script.

    Returns the raw script text (French, ~200-300 words, no markdown).
    The script ends with the daily signature phrase from MARCEL_SIGNATURES.
    Raises anthropic.APIError on API failures.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

    signature = pick_signature(car)
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_message(car, signature)}],
    )

    script = message.content[0].text.strip()
    logger.info(
        "[script_generator] Script generated (mode=%s, signature=%r, %d chars, "
        "%d in / %d out tokens).",
        car.mode, signature, len(script),
        message.usage.input_tokens, message.usage.output_tokens,
    )
    return script
