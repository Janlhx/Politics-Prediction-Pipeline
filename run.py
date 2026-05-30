"""
run.py — Entry point principal del pipeline Colombia Predictor.

Uso:
    python run.py                    # análisis completo con simulación
    python run.py --update-prices    # actualiza precios de Polymarket antes de analizar
    python run.py --dry-run          # solo muestra señales, no guarda nada
    python run.py --no-sim           # omite simulación Monte Carlo (más rápido)
"""

import argparse
import sys
import os
import json
from datetime import datetime

# Forzar UTF-8 en Windows (evita UnicodeEncodeError con emojis)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(__file__))


def header(title: str, width: int = 62):
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def run_pipeline(update_prices: bool = False, dry_run: bool = False, run_sim: bool = True):
    start_time = datetime.utcnow()
    print(f"\n🇨🇴 COLOMBIA PREDICTOR — Pipeline completo")
    print(f"   {start_time.strftime('%Y-%m-%d %H:%M UTC')} | dry_run={dry_run} | sim={run_sim}")
    print("=" * 62)

    # ──────────────────────────────────────────────────────────
    # FASE 1: Encuestas
    # ──────────────────────────────────────────────────────────
    header("FASE 1 · Encuestas")
    from scrapers.polls import RECENT_POLLS, print_summary, save_polls
    simple_avg, recency_avg, poll_probs = print_summary(RECENT_POLLS)
    if not dry_run:
        save_polls(RECENT_POLLS)

    # ──────────────────────────────────────────────────────────
    # FASE 2: Precios de mercados
    # ──────────────────────────────────────────────────────────
    if update_prices:
        header("FASE 2 · Actualizando precios de Polymarket (live)")
        try:
            from scrapers.polymarket import fetch_all, save_snapshot, get_prices_dict
            live_results = fetch_all()
            if live_results:
                if not dry_run:
                    save_snapshot(live_results)
                live_prices = get_prices_dict(live_results)
            else:
                live_prices = None
                print("  ⚠️  No se obtuvieron precios, usando hardcodeados")
        except Exception as e:
            print(f"  ⚠️  Error: {e}")
            live_prices = None
    else:
        header("FASE 2 · Precios hardcodeados (usa --update-prices para actualizar)")
        live_prices = None

    # ──────────────────────────────────────────────────────────
    # FASE 3: Análisis de edge (modelo baseline de encuestas)
    # ──────────────────────────────────────────────────────────
    header("FASE 3 · Análisis de Edge (baseline encuestas)")
    from analysis.edge import MARKET_PRICES, MODEL_PROBS, analyze, print_analysis, save_analysis

    # Si tenemos precios live, usarlos en lugar de los hardcodeados
    market_prices_to_use = live_prices if live_prices else MARKET_PRICES

    all_results = []
    for market_key in MODEL_PROBS:
        mkey = "ganador_primera_vuelta" if "primera" in market_key else "ganador_final"
        if mkey in market_prices_to_use:
            results = analyze(mkey, MODEL_PROBS, market_prices_to_use)
            # Evitar duplicados
            existing_markets = {r["market"] for r in all_results}
            for r in results:
                if r["market"] not in existing_markets:
                    all_results.append(r)
                    existing_markets.add(r["market"])

    # Si no hubo match, usar el método original
    if not all_results:
        for market_key in MARKET_PRICES:
            results = analyze(market_key, MODEL_PROBS, MARKET_PRICES)
            all_results.extend(results)

    print_analysis(all_results)
    if not dry_run:
        save_analysis(all_results)

    # ──────────────────────────────────────────────────────────
    # FASE 4: Simulación Monte Carlo
    # ──────────────────────────────────────────────────────────
    sim_first = None
    sim_final = None

    if run_sim:
        header("FASE 4 · Simulación Monte Carlo (200k elecciones)")
        try:
            from models.simulate import simulate_first_round, simulate_final_winner, print_results as print_sim
            print("  Corriendo simulación...")
            sim_first = simulate_first_round()
            sim_final = simulate_final_winner(sim_first)
            print_sim(sim_first, sim_final)
        except Exception as e:
            print(f"  ⚠️  Error en simulación: {e}")
            import traceback; traceback.print_exc()

    # ──────────────────────────────────────────────────────────
    # RESUMEN EJECUTIVO CONSOLIDADO
    # ──────────────────────────────────────────────────────────
    header("RESUMEN EJECUTIVO CONSOLIDADO", 62)

    from analysis.edge import MARKET_PRICES as MP

    prices_ref = market_prices_to_use if market_prices_to_use else MP

    candidates = ["Cepeda", "De la Espriella", "Valencia"]

    print(f"\n{'─'*62}")
    print(f"  📅 Elección: 31 mayo 2026 | Análisis: {start_time.strftime('%d/%m %H:%M UTC')}")
    print(f"{'─'*62}")

    # Tabla unificada
    print(f"\n  {'MERCADO / CANDIDATO':<30} {'MOD.SIM':>8} {'POLY':>8} {'EDGE':>8} {'SEÑAL'}")
    print(f"  {'─'*58}")

    markets_display = [
        ("ganador_primera_vuelta", "1a VUELTA · Ganar pluralidad"),
        ("ganador_final",          "GANADOR FINAL · Con 2a vuelta"),
    ]

    all_signals = []

    for mkey, mlabel in markets_display:
        print(f"\n  📌 {mlabel}")
        for c in candidates:
            # Precio de mercado
            mkt_price = prices_ref.get(mkey, {}).get(c, {}).get("mid", None)
            if mkt_price is None:
                continue

            # Probabilidad del modelo (simulación si disponible, si no baseline)
            if sim_first and mkey == "ganador_primera_vuelta":
                model_p = sim_first["p_plurality"].get(c, 0)
            elif sim_final and mkey == "ganador_final":
                model_p = sim_final.get(c, 0)
            else:
                model_key = "primera_vuelta" if "primera" in mkey else "ganador_final"
                model_p = MODEL_PROBS.get(model_key, {}).get(c, 0)

            edge = model_p - mkt_price
            abs_edge = abs(edge)
            direction = "BUY YES" if edge > 0 else "BUY NO"

            if abs_edge >= 0.10:
                signal_icon = "🟢 STRONG"
            elif abs_edge >= 0.05:
                signal_icon = "🟡 WEAK"
            else:
                signal_icon = "⚪ skip"

            print(f"    {c:<28} {model_p:>7.1%} {mkt_price:>7.1%} {edge:>+8.1%}  {signal_icon} {direction}")

            if abs_edge >= 0.05:
                all_signals.append({
                    "market": mkey,
                    "candidate": c,
                    "model": model_p,
                    "market_price": mkt_price,
                    "edge": edge,
                    "direction": direction,
                    "signal": signal_icon,
                })

    # Señales accionables ordenadas por edge absoluto
    print(f"\n{'─'*62}")
    print("  🚨 SEÑALES ACCIONABLES (ordenadas por edge absoluto):")
    print(f"{'─'*62}")

    strong = sorted([s for s in all_signals if "STRONG" in s["signal"]], key=lambda x: abs(x["edge"]), reverse=True)
    weak   = sorted([s for s in all_signals if "WEAK"   in s["signal"]], key=lambda x: abs(x["edge"]), reverse=True)

    if strong:
        print(f"\n  🟢 Señales FUERTES (edge ≥ 10%):")
        for s in strong:
            mkt_label = "1a vuelta" if "primera" in s["market"] else "Final    "
            print(f"     {mkt_label} · {s['candidate']:<22}  {s['direction']:<10}  edge={s['edge']:+.1%}")

    if weak:
        print(f"\n  🟡 Señales DÉBILES (edge 5-10%):")
        for s in weak:
            mkt_label = "1a vuelta" if "primera" in s["market"] else "Final    "
            print(f"     {mkt_label} · {s['candidate']:<22}  {s['direction']:<10}  edge={s['edge']:+.1%}")

    if not strong and not weak:
        print("\n  ⚪ Sin señales claras.")

    # Contexto clave
    print(f"\n{'─'*62}")
    print("  📎 CONTEXTO CLAVE:")
    print("     • P(segunda vuelta) modelo: ~99% | Polymarket: 87.5%")
    print("     • Escenario casi seguro: Cepeda vs De la Espriella en 2a vuelta")
    print("     • En ballotage: encuestas Guarumo dan De la Espriella +8pp")
    print("     • Voto oculto de derecha: +2.5pp ajuste en simulación")
    print(f"{'─'*62}")
    print("\n  ⚠️  No es asesoría financiera. Verificar precios antes de operar.\n")

    # Guardar reporte completo
    if not dry_run and sim_first:
        report = {
            "timestamp": start_time.isoformat(),
            "polls": {
                "simple_avg": simple_avg,
                "recency_avg": recency_avg,
                "probabilities": poll_probs,
            },
            "simulation": {
                "p_plurality": sim_first["p_plurality"],
                "p_50_plus_1": sim_first["p_50_plus_1"],
                "p_second_round": sim_first["p_second_round"],
                "scenarios_2nd": sim_first["scenarios_2nd"],
                "mean_vote_share": sim_first["mean_vote_share"],
            },
            "final_winner_probs": sim_final,
            "signals": all_signals,
        }
        os.makedirs("data", exist_ok=True)
        with open("data/full_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print("  ✅ Reporte completo guardado en data/full_report.json\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Colombia Predictor — Pipeline de análisis")
    parser.add_argument("--update-prices", action="store_true", help="Actualiza precios de Polymarket")
    parser.add_argument("--dry-run",       action="store_true", help="No guarda archivos")
    parser.add_argument("--no-sim",        action="store_true", help="Omite simulación Monte Carlo")
    args = parser.parse_args()

    run_pipeline(
        update_prices=args.update_prices,
        dry_run=args.dry_run,
        run_sim=not args.no_sim,
    )
