"""
analysis/edge.py
Compara probabilidades del modelo (encuestas) vs precios del mercado.
Calcula edge, oportunidades de arbitraje y recomendaciones.
"""

import json
import os
from datetime import datetime

# Precios actuales de mercados (actualizados manualmente o via scrapers)
# Fuente: predictionhunt.com / Kalshi / Polymarket — 30 mayo 2026
MARKET_PRICES = {
    # Mercado: ganador final (incluye segunda vuelta)
    "ganador_final": {
        "Cepeda": {
            "kalshi": 0.37,
            "polymarket": 0.38,
            "mid": 0.375,
        },
        "De la Espriella": {
            "kalshi": 0.63,
            "polymarket": 0.61,
            "mid": 0.62,
        },
        "Valencia": {
            "kalshi": 0.03,
            "polymarket": 0.032,
            "mid": 0.031,
        },
    },
    # Mercado: ganador primera vuelta (31 mayo)
    "ganador_primera_vuelta": {
        "Cepeda": {
            "polymarket": 0.62,   # referencia aproximada
            "mid": 0.62,
        },
        "De la Espriella": {
            "polymarket": 0.25,
            "mid": 0.25,
        },
        "Valencia": {
            "polymarket": 0.10,
            "mid": 0.10,
        },
    },
}

# Probabilidades del modelo (de polls.py, promedio reciente)
MODEL_PROBS = {
    "primera_vuelta": {
        "Cepeda": 0.4860,       # ~49% encuestas normalizadas
        "De la Espriella": 0.3370,
        "Valencia": 0.1770,
    },
    # Para ganador final, ajustamos por escenarios de segunda vuelta
    # Guarumo: en 2a vuelta, De la Espriella > Cepeda y Valencia > Cepeda
    # → Cepeda tiene menor chance en final que en 1a vuelta
    "ganador_final": {
        "Cepeda": 0.38,         # baja porque pierde en segunda vuelta según encuestas
        "De la Espriella": 0.42,
        "Valencia": 0.20,
    },
}

CANDIDATES = ["Cepeda", "De la Espriella", "Valencia"]
MIN_EDGE = 0.05  # edge mínimo para considerar una posición (5 puntos)


def calculate_edge(model_prob: float, market_price: float) -> float:
    """Edge = diferencia entre probabilidad del modelo y precio del mercado."""
    return round(model_prob - market_price, 4)


def kelly_fraction(prob: float, market_price: float) -> float:
    """
    Kelly criterion para contratos binarios (pagan $1 o $0).
    f* = (p - q) / (b * p - q)  simplificado para odds implícitos.

    En mercados de predicción:
      b = (1 - market_price) / market_price  (odds del contrato YES)
      p = probabilidad del modelo
      q = 1 - p
    """
    if market_price <= 0 or market_price >= 1:
        return 0.0
    b = (1 - market_price) / market_price
    p = prob
    q = 1 - p
    f = (b * p - q) / b
    return max(0.0, round(f, 4))


def analyze(market_key: str, model_probs: dict, market_prices: dict) -> list[dict]:
    """Analiza oportunidades para un mercado dado."""
    results = []
    prices = market_prices.get(market_key, {})
    model = model_probs.get(market_key.replace("ganador_primera_vuelta", "primera_vuelta").replace("ganador_final", "ganador_final"), {})

    # Fallback key mapping
    if not model:
        if "primera" in market_key:
            model = model_probs.get("primera_vuelta", {})
        else:
            model = model_probs.get("ganador_final", {})

    for candidate in CANDIDATES:
        if candidate not in prices or candidate not in model:
            continue

        mp = model[candidate]
        mkt = prices[candidate].get("mid", 0)
        edge = calculate_edge(mp, mkt)
        kf = kelly_fraction(mp, mkt) * 0.5   # half-Kelly por defecto

        direction = "BUY YES" if edge > 0 else "BUY NO"
        abs_edge = abs(edge)

        row = {
            "market": market_key,
            "candidate": candidate,
            "model_prob": mp,
            "market_price": mkt,
            "edge": edge,
            "abs_edge": abs_edge,
            "direction": direction if abs_edge >= MIN_EDGE else "SKIP",
            "half_kelly": kf if edge > 0 else kelly_fraction(1 - mp, 1 - mkt) * 0.5,
            "signal": "🟢 STRONG" if abs_edge >= 0.10 else ("🟡 WEAK" if abs_edge >= MIN_EDGE else "⚪ NO EDGE"),
        }
        results.append(row)

    return results


def print_analysis(results: list[dict]):
    """Imprime análisis de edge formateado."""
    print("=" * 70)
    print("🎯 ANÁLISIS DE EDGE — COLOMBIA 2026")
    print(f"   Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    current_market = None
    for r in results:
        if r["market"] != current_market:
            current_market = r["market"]
            label = "🗳️  GANADOR FINAL" if "final" in current_market else "1⃣  PRIMERA VUELTA"
            print(f"\n{label}")
            print(f"  {'Candidato':<22} {'Modelo':>8} {'Mercado':>8} {'Edge':>8} {'Dirección':<12} {'Kelly':>7} {'Señal'}")
            print("  " + "-" * 68)

        print(
            f"  {r['candidate']:<22} "
            f"{r['model_prob']:>7.1%} "
            f"{r['market_price']:>7.1%} "
            f"{r['edge']:>+7.1%}  "
            f"{r['direction']:<12} "
            f"{r['half_kelly']:>6.1%}  "
            f"{r['signal']}"
        )

    print("\n--- Notas ---")
    print("• Edge = modelo - mercado. Positivo → mercado subestima al candidato.")
    print("• Half-Kelly: fracción del bankroll a arriesgar (conservador).")
    print("• Encuestas presenciales colombianas consistentemente dan más a Cepeda.")
    print("• Mercados internacionales sesgan hacia De la Espriella (voto oculto?)")
    print("• Segunda vuelta clave: encuestas dan a De la Espriella > Cepeda en ballotage.")
    print("• ⚠️  No es asesoría financiera. Usa --dry-run primero.")


def save_analysis(results: list[dict], path: str = "data/edge_analysis.json"):
    os.makedirs("data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": datetime.utcnow().isoformat(), "results": results}, f, indent=2)
    print(f"\n✅ Análisis guardado en {path}")


if __name__ == "__main__":
    all_results = []
    for market_key in MARKET_PRICES:
        results = analyze(market_key, MODEL_PROBS, MARKET_PRICES)
        all_results.extend(results)

    print_analysis(all_results)
    save_analysis(all_results)
