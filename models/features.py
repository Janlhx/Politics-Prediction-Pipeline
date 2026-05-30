"""
models/features.py
Feature engineering para modelo de predicción de mercados políticos.
Diseñado para Colombia 2026, extensible a cualquier elección latam.
"""

import numpy as np
import pandas as pd
from datetime import date, datetime


def days_to_election(election_date: str) -> int:
    """Días restantes hasta la elección."""
    ed = date.fromisoformat(election_date)
    return max(0, (ed - date.today()).days)


def poll_momentum(polls: list[dict], candidate: str, window: int = 14) -> float:
    """
    Momentum: cambio en intención de voto en los últimos `window` días.
    Positivo = subiendo, negativo = bajando.
    """
    df = pd.DataFrame(polls)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values("fecha")
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=window)
    recent = df[df["fecha"] >= cutoff]
    old = df[df["fecha"] < cutoff]
    if recent.empty or old.empty:
        return 0.0
    return float(recent[candidate].mean() - old[candidate].mean())


def poll_variance(polls: list[dict], candidate: str) -> float:
    """Varianza entre encuestadoras — mayor varianza = más incertidumbre."""
    vals = [p.get(candidate, 0) for p in polls]
    return float(np.var(vals)) if vals else 0.0


def market_volume_signal(volume_usd: float) -> float:
    """Normaliza volumen del mercado. Mayor volumen = mercado más informado."""
    return np.log1p(volume_usd) / np.log1p(10_000_000)


def undecided_share(polls: list[dict]) -> float:
    """Porcentaje promedio de indecisos / voto en blanco."""
    vals = [p.get("Otros", 0) for p in polls]
    return float(np.mean(vals)) if vals else 0.0


def right_wing_consolidation(polls: list[dict]) -> float:
    """
    Grado de consolidación del voto de derecha (De la Espriella + Valencia).
    Útil para estimar transferencia de votos en segunda vuelta.
    """
    vals = [p.get("De la Espriella", 0) + p.get("Valencia", 0) for p in polls]
    return float(np.mean(vals)) if vals else 0.0


def build_feature_vector(
    candidate: str,
    polls: list[dict],
    market_price: float,
    election_date: str,
    market_volume: float = 1_000_000,
) -> dict:
    """
    Construye el vector de features para un candidato.
    Retorna dict listo para DataFrame / XGBoost.
    """
    # Intención de voto promedio
    avg_polls = np.mean([p.get(candidate, 0) for p in polls])
    # Normalizar a 0-1
    avg_prob = avg_polls / 100.0

    features = {
        # --- Encuestas ---
        "poll_avg": avg_prob,
        "poll_momentum_14d": poll_momentum(polls, candidate, 14) / 100.0,
        "poll_variance": poll_variance(polls, candidate) / 100.0,

        # --- Mercado ---
        "market_price": market_price,
        "market_edge_raw": avg_prob - market_price,   # diferencia directa
        "market_volume_norm": market_volume_signal(market_volume),

        # --- Contexto electoral ---
        "days_to_election": days_to_election(election_date) / 30.0,  # normalizado a meses
        "undecided_share": undecided_share(polls) / 100.0,
        "right_consolidation": right_wing_consolidation(polls) / 100.0,

        # --- Candidato ---
        "is_incumbent_party": 1 if candidate == "Cepeda" else 0,  # Pacto Histórico en poder
        "is_right_candidate": 1 if candidate in ["De la Espriella", "Valencia"] else 0,
    }
    return features


def build_dataset(all_candidates_data: list[dict]) -> pd.DataFrame:
    """
    Construye dataset completo desde lista de dicts.
    Cada dict debe tener: candidate, polls, market_price, election_date, result (0/1).
    """
    rows = []
    for entry in all_candidates_data:
        features = build_feature_vector(
            candidate=entry["candidate"],
            polls=entry["polls"],
            market_price=entry["market_price"],
            election_date=entry["election_date"],
            market_volume=entry.get("market_volume", 1_000_000),
        )
        features["candidate"] = entry["candidate"]
        features["election_date"] = entry["election_date"]
        features["result"] = entry.get("result", None)  # None = no resuelto aún
        rows.append(features)
    return pd.DataFrame(rows)


# Features que usa el modelo (sin columnas de metadata)
FEATURE_COLS = [
    "poll_avg", "poll_momentum_14d", "poll_variance",
    "market_price", "market_edge_raw", "market_volume_norm",
    "days_to_election", "undecided_share", "right_consolidation",
    "is_incumbent_party", "is_right_candidate",
]


if __name__ == "__main__":
    # Demo: muestra features para Colombia 2026
    from scrapers.polls import RECENT_POLLS, CANDIDATES

    print("🔧 Feature vectors — Colombia 2026\n")

    market_prices = {
        "Cepeda": 0.375,
        "De la Espriella": 0.62,
        "Valencia": 0.031,
    }

    for candidate in CANDIDATES:
        fv = build_feature_vector(
            candidate=candidate,
            polls=RECENT_POLLS,
            market_price=market_prices.get(candidate, 0.1),
            election_date="2026-05-31",
            market_volume=7_397_150,
        )
        print(f"--- {candidate} ---")
        for k, v in fv.items():
            print(f"  {k:<25} {v:.4f}")
        print()
