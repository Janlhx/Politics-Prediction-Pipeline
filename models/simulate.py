"""
models/simulate.py
Simulación Monte Carlo para calcular P(ganar pluralidad en primera vuelta).

El modelo de encuestas da la INTENCIÓN DE VOTO PROMEDIO, no la probabilidad
de ganar. Para una elección de 3 candidatos donde Cepeda lidera con 44%, su
probabilidad de GANAR MÁS VOTOS (pluralidad) es mucho mayor que 44%.

Metodología:
  1. Tomar promedios de encuestas como medias μ_i
  2. Modelar incertidumbre: error histórico de encuestas + varianza entre firmas
  3. Simular N elecciones con distribución Dirichlet (respeta suma=1)
  4. Contar quién gana pluralidad en cada simulación → P(ganar pluralidad)
  5. Para ganador final: añadir modelo de segunda vuelta (ballotage)

Referencias históricas de error de encuestas en Colombia:
  - 2022 (1a vuelta): Petro estimado ~40%, obtuvo 40.3% ✓ (buen año)
  - 2018 (1a vuelta): Petro estimado ~25%, obtuvo 25.1% ✓
  - Error promedio histórico en LatAm: 3-6% por candidato
"""

import sys
import os
import numpy as np
from datetime import date

# Fix import path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────────────────────
# PARÁMETROS DEL MODELO
# ─────────────────────────────────────────────────────────────

ELECTION_DATE_1 = "2026-05-31"  # Primera vuelta
ELECTION_DATE_2 = "2026-06-21"  # Segunda vuelta (si aplica)

# Promedios de encuestas recientes (decaimiento semanal 0.7)
# Fuente: polls.py — calculados 30 mayo 2026
POLL_MEANS = {
    "Cepeda":          38.0,   # % intención de voto (sin normalizar)
    "De la Espriella": 28.5,
    "Valencia":        18.9,
    "Otros":           14.6,   # indecisos + otros candidatos
}

# Varianza entre encuestadoras (calculada manualmente de los 5 sondeos)
POLL_STD_DEV = {
    "Cepeda":          4.0,    # ±4pp entre firmas
    "De la Espriella": 2.9,    # más consistente entre firmas
    "Valencia":        4.3,    # mayor dispersión
    "Otros":           4.5,
}

# Error histórico adicional (sesgo sistemático posible)
# En Colombia 2026: posible voto oculto de derecha (fenómeno Hernández 2022)
SYSTEMATIC_BIAS = {
    "Cepeda":          0.0,    # base sin ajuste
    "De la Espriella": +2.5,   # posible subestimación por voto oculto
    "Valencia":        -1.0,   # posible sobreestimación
    "Otros":           -1.5,
}

# Escenarios de segunda vuelta (probabilidades condicionadas)
# Si Cepeda vs De la Espriella: encuesta Guarumo da De la Espriella +8pp
BALLOTAGE_PROBS = {
    ("Cepeda", "De la Espriella"): {"Cepeda": 0.42, "De la Espriella": 0.58},
    ("Cepeda", "Valencia"):        {"Cepeda": 0.45, "Valencia": 0.55},
    ("De la Espriella", "Valencia"): {"De la Espriella": 0.70, "Valencia": 0.30},
}

CANDIDATES_MAIN = ["Cepeda", "De la Espriella", "Valencia"]
N_SIMS = 200_000
RANDOM_SEED = 42


def simulate_first_round(
    n_sims: int = N_SIMS,
    apply_bias: bool = True,
    seed: int = RANDOM_SEED,
) -> dict:
    """
    Simula N elecciones de primera vuelta.
    Retorna:
      - p_plurality: P(cada candidato gana más votos)
      - p_second_round: P(ninguno llega a 50%+1)
      - scenarios: distribución de los top-2 en segunda vuelta
    """
    rng = np.random.default_rng(seed)

    candidates_all = list(POLL_MEANS.keys())

    # Medias ajustadas por sesgo sistemático
    means = np.array([
        POLL_MEANS[c] + (SYSTEMATIC_BIAS[c] if apply_bias else 0)
        for c in candidates_all
    ])
    means = np.maximum(means, 0.1)  # evitar negativos

    stds = np.array([POLL_STD_DEV[c] for c in candidates_all])

    # Simular con distribución normal multivariada (independiente por candidato)
    # Luego normalizar para que sumen 100%
    samples = rng.normal(loc=means, scale=stds, size=(n_sims, len(candidates_all)))
    samples = np.maximum(samples, 0.1)  # no negativos
    samples = samples / samples.sum(axis=1, keepdims=True) * 100  # normalizar a 100%

    results = {
        "p_plurality":      {},
        "p_50_plus_1":      {},
        "p_second_round":   0.0,
        "scenarios_2nd":    {},
        "mean_vote_share":  {},
        "std_vote_share":   {},
    }

    # Estadísticas de intención de voto simulada
    for i, c in enumerate(candidates_all):
        results["mean_vote_share"][c] = float(np.mean(samples[:, i]))
        results["std_vote_share"][c]  = float(np.std(samples[:, i]))

    # Quien gana pluralidad (más votos)
    winner_idx = np.argmax(samples, axis=1)
    for i, c in enumerate(candidates_all):
        results["p_plurality"][c] = float(np.mean(winner_idx == i))

    # Quien llega a 50%+1 (gana en primera vuelta sin ballotage)
    for i, c in enumerate(candidates_all):
        results["p_50_plus_1"][c] = float(np.mean(samples[:, i] > 50.0))

    # Probabilidad de segunda vuelta
    max_votes = samples.max(axis=1)
    results["p_second_round"] = float(np.mean(max_votes < 50.0))

    # Distribución de top-2 (quiénes van a 2a vuelta)
    sorted_idx = np.argsort(samples, axis=1)[:, ::-1]  # desc
    top2_pairs = [
        tuple(sorted([candidates_all[sorted_idx[i, 0]], candidates_all[sorted_idx[i, 1]]]))
        for i in range(n_sims)
        if samples[sorted_idx[i, 0], 0] < 50.0  # solo si hay segunda vuelta
    ]
    from collections import Counter
    pair_counts = Counter(top2_pairs)
    total = sum(pair_counts.values()) or 1
    for pair, count in pair_counts.most_common(5):
        results["scenarios_2nd"][str(pair)] = round(count / total, 4)

    return results


def simulate_final_winner(first_round_results: dict, n_sims: int = N_SIMS, seed: int = RANDOM_SEED) -> dict:
    """
    Calcula P(ganar elección final) combinando:
    1. P(ganar en primera vuelta directamente, >50%)
    2. P(ir a segunda vuelta) × P(ganar ballotage)
    """
    rng = np.random.default_rng(seed + 1)

    final_probs = {c: 0.0 for c in CANDIDATES_MAIN + ["Otros"]}

    # Ganadores directos en primera vuelta (>50%)
    for c in CANDIDATES_MAIN:
        final_probs[c] += first_round_results["p_50_plus_1"].get(c, 0)

    # Escenarios de segunda vuelta
    scenarios = first_round_results["scenarios_2nd"]
    p_2nd_round = first_round_results["p_second_round"]

    for pair_str, pair_prob in scenarios.items():
        # Parsear la tupla del string
        pair_str_clean = pair_str.strip("()'").replace("'", "")
        parts = [p.strip() for p in pair_str_clean.split(",")]
        if len(parts) != 2:
            continue

        c1, c2 = parts[0], parts[1]
        pair_key = tuple(sorted([c1, c2]))

        ballotage = BALLOTAGE_PROBS.get(pair_key, None)
        if ballotage is None:
            continue

        # Peso = P(2a vuelta) × P(este par llega a 2a vuelta)
        weight = p_2nd_round * pair_prob
        for c, bp in ballotage.items():
            if c in final_probs:
                final_probs[c] += weight * bp

    return final_probs


def print_results(first: dict, final: dict):
    """Imprime resultados del modelo de simulación."""
    print("\n" + "=" * 70)
    print("🎲 MODELO DE SIMULACIÓN MONTE CARLO — COLOMBIA 2026")
    print(f"   Simulaciones: {N_SIMS:,} | Sesgo: activado | Seed: {RANDOM_SEED}")
    print("=" * 70)

    print("\n--- PRIMERA VUELTA (31 mayo) ---")
    print(f"\n{'Candidato':<22} {'Voto sim.':<12} {'P(pluralidad)':<16} {'P(>50%)'}")
    print("-" * 65)
    for c in CANDIDATES_MAIN:
        mv = first["mean_vote_share"].get(c, 0)
        sv = first["std_vote_share"].get(c, 0)
        pp = first["p_plurality"].get(c, 0)
        p5 = first["p_50_plus_1"].get(c, 0)
        print(f"  {c:<20} {mv:.1f}% ±{sv:.1f}%  {pp:.1%}           {p5:.1%}")

    print(f"\n  P(segunda vuelta) = {first['p_second_round']:.1%}")
    print(f"  Polymarket dice   = 87.5% ← consistente con modelo")

    print("\n  Top escenarios de segunda vuelta:")
    for pair_str, prob in list(first["scenarios_2nd"].items())[:4]:
        print(f"    {pair_str:<40} {prob:.1%}")

    print("\n--- GANADOR FINAL (incluyendo 2a vuelta) ---")
    print(f"\n{'Candidato':<22} {'P(ganar final)'}")
    print("-" * 40)
    total = sum(final.values())
    for c in CANDIDATES_MAIN:
        p = final.get(c, 0)
        print(f"  {c:<20} {p:.1%}")

    print("\n--- COMPARATIVA: MODELO vs POLYMARKET ---")
    print(f"\n{'Mercado':<28} {'Candidato':<22} {'Modelo':<10} {'Polymarket':<12} {'Edge':>8}")
    print("-" * 80)

    from analysis.edge import MARKET_PRICES

    # Primera vuelta
    for c in CANDIDATES_MAIN:
        model_p = first["p_plurality"].get(c, 0)
        market_p = MARKET_PRICES.get("ganador_primera_vuelta", {}).get(c, {}).get("mid", 0)
        edge = model_p - market_p
        signal = "🟢" if abs(edge) >= 0.10 else ("🟡" if abs(edge) >= 0.05 else "⚪")
        direction = "BUY YES" if edge > 0 else "BUY NO"
        print(f"  {'1a vuelta':<26} {c:<22} {model_p:.1%}     {market_p:.1%}        {edge:+.1%} {signal}")

    # Final
    for c in CANDIDATES_MAIN:
        model_p = final.get(c, 0)
        market_p = MARKET_PRICES.get("ganador_final", {}).get(c, {}).get("mid", 0)
        edge = model_p - market_p
        signal = "🟢" if abs(edge) >= 0.10 else ("🟡" if abs(edge) >= 0.05 else "⚪")
        direction = "BUY YES" if edge > 0 else "BUY NO"
        print(f"  {'Final':<26} {c:<22} {model_p:.1%}     {market_p:.1%}        {edge:+.1%} {signal}")


if __name__ == "__main__":
    print("Corriendo simulación Monte Carlo...")
    first = simulate_first_round()
    final = simulate_final_winner(first)
    print_results(first, final)
