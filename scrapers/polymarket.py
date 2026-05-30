"""
scrapers/polymarket.py
Obtiene precios en tiempo real de los mercados de Colombia en Polymarket.
No requiere API key — usa la API pública Gamma (eventos).
"""

import sys
import requests
import json
from datetime import datetime

# Forzar UTF-8 en Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

GAMMA_API = "https://gamma-api.polymarket.com"

# Slugs correctos de los eventos en Polymarket (verificados 30-may-2026)
EVENT_SLUGS = {
    "ganador_final":          "colombia-presidential-election",
    "ganador_primera_vuelta": "colombia-presidential-election-1st-round-winner",
    "segunda_vuelta":         "will-any-presidential-candidate-win-outright-in-the-first-round-of-the-colombias-election",
}

# Keywords para matchear candidatos principales
# (Polymarket usa nombres completos; mapeamos a claves cortas)
CANDIDATE_KEYWORDS = {
    "Cepeda":          ["cepeda"],
    "De la Espriella": ["abelardo de la espriella", "espriella"],
    "Valencia":        ["paloma valencia"],
}


def get_event_markets(slug: str) -> list[dict]:
    """Obtiene los mercados de un evento por su slug."""
    url = f"{GAMMA_API}/events?slug={slug}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        events = r.json()
        if not events:
            print(f"  [WARN] Evento no encontrado: {slug}")
            return []
        return events[0].get("markets", [])
    except Exception as e:
        print(f"  [ERROR] {slug}: {e}")
        return []


def extract_candidate_prices(markets: list[dict]) -> dict:
    """
    Extrae el precio YES de cada candidato principal de la lista de mercados.
    Retorna dict: { "Cepeda": 0.365, "De la Espriella": 0.625, "Valencia": 0.029 }
    """
    prices = {}
    for m in markets:
        question = m.get("question", "").lower()
        prices_raw = m.get("outcomePrices", '["0","1"]')
        try:
            prices_list = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
            yes_price = float(prices_list[0])
        except Exception:
            yes_price = 0.0

        for candidate, keywords in CANDIDATE_KEYWORDS.items():
            if any(kw in question for kw in keywords):
                # Si hay múltiple match (ej. "espriella" en varios), tomar el mayor precio
                if candidate not in prices or yes_price > prices[candidate]:
                    prices[candidate] = round(yes_price, 4)
    return prices


def fetch_all() -> list[dict]:
    """Obtiene precios actuales de todos los mercados de Colombia."""
    results = []
    timestamp = datetime.utcnow().isoformat()

    for market_key, slug in EVENT_SLUGS.items():
        if market_key == "segunda_vuelta":
            # Mercado especial: ¿habrá segunda vuelta?
            markets = get_event_markets(slug)
            if markets:
                m = markets[0]
                prices_raw = m.get("outcomePrices", '["0","1"]')
                try:
                    prices_list = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                    yes_price = float(prices_list[0])
                except Exception:
                    yes_price = 0.0
                row = {
                    "timestamp": timestamp,
                    "market_key": market_key,
                    "market_slug": slug,
                    "outcome": "alguno_gana_en_1a",
                    "yes_price": yes_price,
                    "no_price": round(1 - yes_price, 4),
                    "implied_prob_segunda_vuelta": round(1 - yes_price, 4),
                }
                results.append(row)
                print(f"  Segunda vuelta (NO): {1 - yes_price:.1%} | Gana en 1a (YES): {yes_price:.1%}")
            continue

        print(f"\n  Mercado: {market_key}")
        markets = get_event_markets(slug)
        if not markets:
            continue

        candidate_prices = extract_candidate_prices(markets)

        for candidate, price in candidate_prices.items():
            row = {
                "timestamp": timestamp,
                "market_key": market_key,
                "market_slug": slug,
                "outcome": candidate,
                "implied_prob": price,
            }
            results.append(row)
            print(f"    {candidate:<22} {price:.1%}")

    return results


def save_snapshot(results: list[dict], path: str = "data/polymarket_snapshot.json"):
    """Guarda el snapshot en JSON."""
    import os
    os.makedirs("data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n  Snapshot guardado en {path}")


def get_prices_dict(results: list[dict]) -> dict:
    """
    Convierte lista de resultados a dict anidado compatible con edge.py:
    { "ganador_final": { "Cepeda": { "mid": 0.365 }, ... }, ... }
    """
    prices = {}
    for row in results:
        mk = row["market_key"]
        if mk == "segunda_vuelta":
            continue
        if mk not in prices:
            prices[mk] = {}
        candidate = row["outcome"]
        prices[mk][candidate] = {"mid": row["implied_prob"], "polymarket": row["implied_prob"]}
    return prices


if __name__ == "__main__":
    print("Obteniendo precios de Polymarket — Colombia 2026\n")
    results = fetch_all()
    if results:
        save_snapshot(results)
        print("\n--- Resumen ---")
        prices = get_prices_dict(results)
        for mk, candidates in prices.items():
            print(f"\n{mk}:")
            for c, p in candidates.items():
                print(f"  {c:<22} {p['mid']:.1%}")
