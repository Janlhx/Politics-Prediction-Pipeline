"""
scrapers/polymarket.py
Obtiene precios en tiempo real de los mercados de Colombia en Polymarket.
No requiere API key — usa la API pública de CLOB.
"""

import requests
import json
from datetime import datetime

MARKETS = {
    "ganador_final": {
        "slug": "colombia-presidential-election",
        "description": "Ganador final (incluyendo segunda vuelta)",
    },
    "ganador_primera_vuelta": {
        "slug": "colombia-presidential-election-1st-round-winner",
        "description": "Ganador primera vuelta (31 mayo)",
    },
    "turnout": {
        "slug": "colombia-presidential-election-1st-round-turnout",
        "description": "Participación primera vuelta",
    },
}

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API  = "https://clob.polymarket.com"


def get_market_by_slug(slug: str) -> dict | None:
    """Busca un mercado por slug en la API Gamma de Polymarket."""
    url = f"{GAMMA_API}/markets?slug={slug}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data[0] if data else None
    except Exception as e:
        print(f"[ERROR] No se pudo obtener mercado '{slug}': {e}")
        return None


def get_prices(condition_id: str) -> dict | None:
    """Obtiene bid/ask para un condition_id desde el CLOB."""
    url = f"{CLOB_API}/book?token_id={condition_id}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        book = r.json()
        bids = book.get("bids", [])
        asks = book.get("asks", [])
        best_bid = float(bids[0]["price"]) if bids else None
        best_ask = float(asks[0]["price"]) if asks else None
        mid = round((best_bid + best_ask) / 2, 4) if best_bid and best_ask else None
        return {"bid": best_bid, "ask": best_ask, "mid": mid}
    except Exception as e:
        print(f"[ERROR] No se pudo obtener precios para {condition_id}: {e}")
        return None


def fetch_all() -> list[dict]:
    """Obtiene precios actuales de todos los mercados de Colombia."""
    results = []
    timestamp = datetime.utcnow().isoformat()

    for key, meta in MARKETS.items():
        print(f"\n📊 {meta['description']}")
        market = get_market_by_slug(meta["slug"])
        if not market:
            continue

        outcomes = market.get("outcomes", [])
        condition_ids = market.get("conditionIds", [])

        for i, outcome in enumerate(outcomes):
            if i >= len(condition_ids):
                break
            prices = get_prices(condition_ids[i])
            if not prices:
                continue

            row = {
                "timestamp": timestamp,
                "market_key": key,
                "market_slug": meta["slug"],
                "outcome": outcome,
                "bid": prices["bid"],
                "ask": prices["ask"],
                "mid": prices["mid"],
                "implied_prob": prices["mid"],
            }
            results.append(row)
            print(f"  {outcome:30s}  mid={prices['mid']:.2%}  bid={prices['bid']}  ask={prices['ask']}")

    return results


def save_snapshot(results: list[dict], path: str = "data/polymarket_snapshot.json"):
    """Guarda el snapshot en JSON."""
    import os
    os.makedirs("data", exist_ok=True)
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Snapshot guardado en {path}")


if __name__ == "__main__":
    print("🔍 Obteniendo precios de Polymarket — Colombia 2026\n")
    results = fetch_all()
    if results:
        save_snapshot(results)
