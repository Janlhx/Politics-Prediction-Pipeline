"""
run.py — Entry point principal del pipeline Colombia Predictor.
Corre todas las fases en secuencia y muestra el análisis de edge.

Uso:
    python run.py                    # análisis completo
    python run.py --update-prices    # actualiza precios de Polymarket antes de analizar
    python run.py --dry-run          # solo muestra señales, no guarda nada
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


def run_pipeline(update_prices: bool = False, dry_run: bool = False):
    print("\n🇨🇴 COLOMBIA PREDICTOR — Pipeline completo")
    print("=" * 60)

    # FASE 1: Encuestas
    print("\n[1/3] 📊 Cargando encuestas...")
    from scrapers.polls import RECENT_POLLS, print_summary, save_polls
    simple_avg, recency_avg, probs = print_summary(RECENT_POLLS)
    if not dry_run:
        save_polls(RECENT_POLLS)

    # FASE 2 (opcional): Actualizar precios de mercados
    if update_prices:
        print("\n[2/3] 🌐 Actualizando precios de Polymarket...")
        try:
            from scrapers.polymarket import fetch_all, save_snapshot
            results = fetch_all()
            if not dry_run and results:
                save_snapshot(results)
        except Exception as e:
            print(f"  ⚠️  No se pudo actualizar precios: {e}")
            print("  Usando precios hardcodeados...")
    else:
        print("\n[2/3] 💾 Usando precios hardcodeados (pasa --update-prices para actualizar)")

    # FASE 3: Análisis de edge
    print("\n[3/3] 🎯 Calculando edge...")
    from analysis.edge import MARKET_PRICES, MODEL_PROBS, analyze, print_analysis, save_analysis

    all_results = []
    for market_key in MARKET_PRICES:
        results = analyze(market_key, MODEL_PROBS, MARKET_PRICES)
        all_results.extend(results)

    print_analysis(all_results)

    if not dry_run:
        save_analysis(all_results)

    # Resumen ejecutivo
    print("\n" + "=" * 60)
    print("📋 RESUMEN EJECUTIVO")
    print("=" * 60)
    strong_signals = [r for r in all_results if "STRONG" in r["signal"]]
    weak_signals = [r for r in all_results if "WEAK" in r["signal"]]

    if strong_signals:
        print(f"\n🟢 Señales fuertes (edge ≥ 10%):")
        for s in strong_signals:
            print(f"   {s['market']:<25} {s['candidate']:<22} {s['direction']}  edge={s['edge']:+.1%}")
    if weak_signals:
        print(f"\n🟡 Señales débiles (edge 5-10%):")
        for s in weak_signals:
            print(f"   {s['market']:<25} {s['candidate']:<22} {s['direction']}  edge={s['edge']:+.1%}")
    if not strong_signals and not weak_signals:
        print("\n⚪ Sin señales claras con el modelo actual.")

    print("\n⚠️  Disclaimer: Solo para fines educativos. No es asesoría financiera.")
    print("    Verifica siempre los precios en tiempo real antes de cualquier trade.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Colombia Predictor — Pipeline de análisis")
    parser.add_argument("--update-prices", action="store_true", help="Actualiza precios de Polymarket")
    parser.add_argument("--dry-run", action="store_true", help="No guarda archivos")
    args = parser.parse_args()

    run_pipeline(update_prices=args.update_prices, dry_run=args.dry_run)
