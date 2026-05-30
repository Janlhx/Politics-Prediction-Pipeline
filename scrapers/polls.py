"""
scrapers/polls.py
Recolecta datos de encuestas electorales colombianas 2026.
Fuentes: datos hardcodeados de encuestas públicas recientes + Wikipedia.
"""

import sys
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# Forzar UTF-8 en Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Encuestas recientes hardcodeadas (fuente: medios colombianos, mayo 2026)
# Formato: { "firma": str, "fecha": str, "muestra": int, candidato: float }
RECENT_POLLS = [
    {
        "firma": "CNC / Cambio",
        "fecha": "2026-05-24",
        "muestra": 1200,
        "Cepeda": 33.4,
        "De la Espriella": 30.9,
        "Valencia": 12.6,
        "Otros": 23.1,
        "url": "https://www.infobae.com/colombia/2026/05/24/ivan-cepeda-y-de-la-espriella-lideran-la-intencion-de-voto"
    },
    {
        "firma": "Invamer",
        "fecha": "2026-05-22",
        "muestra": 1600,
        "Cepeda": 44.6,
        "De la Espriella": 31.6,
        "Valencia": 14.0,
        "Otros": 9.8,
        "url": "https://es.wikipedia.org/wiki/Anexo:Sondeos_de_intenci%C3%B3n_de_voto_para_las_elecciones_presidenciales_de_Colombia_de_2026"
    },
    {
        "firma": "Guarumo / Ecoanalítica",
        "fecha": "2026-05-21",
        "muestra": 3787,
        "Cepeda": 37.1,
        "De la Espriella": 27.5,
        "Valencia": 21.7,
        "Otros": 13.7,
        "url": "https://www.eltiempo.com/politica/elecciones-colombia-2026/encuesta-guarumo"
    },
    {
        "firma": "Atlas Intel",
        "fecha": "2026-05-15",
        "muestra": 2000,
        "Cepeda": 37.0,
        "De la Espriella": 29.0,
        "Valencia": 20.0,
        "Otros": 14.0,
        "url": "https://es.wikipedia.org/wiki/Anexo:Sondeos"
    },
    {
        "firma": "Guarumo / El Tiempo",
        "fecha": "2026-04-30",
        "muestra": 3500,
        "Cepeda": 38.0,
        "De la Espriella": 23.9,
        "Valencia": 22.8,
        "Otros": 15.3,
        "url": "https://www.eltiempo.com"
    },
]

CANDIDATES = ["Cepeda", "De la Espriella", "Valencia"]


def poll_average(polls: list[dict], weights: dict | None = None) -> dict:
    """
    Calcula promedio ponderado de encuestas.
    Por defecto pondera por tamaño de muestra.
    """
    totals = {c: 0.0 for c in CANDIDATES}
    total_weight = 0.0

    for poll in polls:
        w = weights.get(poll["firma"], poll.get("muestra", 1000)) if weights else poll.get("muestra", 1000)
        for c in CANDIDATES:
            totals[c] += poll.get(c, 0) * w
        total_weight += w

    return {c: round(totals[c] / total_weight, 2) for c in CANDIDATES}


def recency_weighted_average(polls: list[dict], decay: float = 0.7) -> dict:
    """
    Pondera encuestas más recientes con mayor peso.
    decay=0.7 significa que cada semana de diferencia reduce el peso 30%.
    """
    from datetime import date

    today = date.today()
    weights = {}
    for poll in polls:
        poll_date = date.fromisoformat(poll["fecha"])
        days_ago = (today - poll_date).days
        weeks_ago = days_ago / 7
        weights[poll["firma"]] = (decay ** weeks_ago) * poll.get("muestra", 1000)

    return poll_average(polls, weights)


def to_probabilities(averages: dict) -> dict:
    """Normaliza las intenciones de voto a probabilidades que suman 1."""
    total = sum(averages.values())
    return {c: round(v / total, 4) for c, v in averages.items()}


def print_summary(polls: list[dict]):
    """Imprime resumen de encuestas y promedios."""
    print("=" * 60)
    print("📊 ENCUESTAS COLOMBIA 2026 — PRIMERA VUELTA")
    print("=" * 60)

    print(f"\n{'Firma':<25} {'Fecha':<12} {'Cepeda':>8} {'Espriella':>10} {'Valencia':>9}")
    print("-" * 65)
    for p in polls:
        print(f"{p['firma']:<25} {p['fecha']:<12} {p['Cepeda']:>7.1f}% {p['De la Espriella']:>9.1f}% {p['Valencia']:>8.1f}%")

    print("\n--- Promedios ---")
    simple_avg = poll_average(polls)
    recency_avg = recency_weighted_average(polls)

    print(f"\nPromedio simple (ponderado por muestra):")
    for c, v in simple_avg.items():
        print(f"  {c:<20} {v:.1f}%")

    print(f"\nPromedio reciente (decay semanal 0.7):")
    for c, v in recency_avg.items():
        print(f"  {c:<20} {v:.1f}%")

    print(f"\nProbabilidades normalizadas (modelo baseline):")
    probs = to_probabilities(recency_avg)
    for c, v in probs.items():
        print(f"  {c:<20} {v:.2%}")

    return simple_avg, recency_avg, probs


def save_polls(polls: list[dict], path: str = "data/polls.json"):
    """Guarda encuestas en JSON."""
    import os
    os.makedirs("data", exist_ok=True)
    payload = {
        "updated": datetime.utcnow().isoformat(),
        "polls": polls,
        "averages": {
            "simple": poll_average(polls),
            "recency_weighted": recency_weighted_average(polls),
            "probabilities": to_probabilities(recency_weighted_average(polls)),
        }
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Encuestas guardadas en {path}")
    return payload


if __name__ == "__main__":
    simple_avg, recency_avg, probs = print_summary(RECENT_POLLS)
    save_polls(RECENT_POLLS)
