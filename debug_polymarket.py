"""
Debug v4: extrae precios reales de los eventos Colombia encontrados.
Event IDs: 34582 (1a vuelta), 34584 (ganador final), 34590 (segunda vuelta?)
"""
import sys
import requests
import json

sys.stdout.reconfigure(encoding='utf-8')

BASE = "https://gamma-api.polymarket.com"

CANDIDATES_KEYWORDS = {
    "Cepeda":          ["cepeda", "ivan cepeda"],
    "De la Espriella": ["espriella", "miguel uribe", "de la espriella"],
    "Valencia":        ["cabal", "maria fernanda cabal", "valencia", "juan carlos"],
}

EVENT_SLUGS = {
    "ganador_final":           "colombia-presidential-election",
    "ganador_primera_vuelta":  "colombia-presidential-election-1st-round-winner",
}

print("=" * 70)
print("PRECIOS EN TIEMPO REAL — COLOMBIA 2026")
print("=" * 70)

all_prices = {}

for market_key, slug in EVENT_SLUGS.items():
    print(f"\n{'=' * 50}")
    print(f"MERCADO: {market_key.upper()} (slug: {slug})")
    print("=" * 50)
    
    r = requests.get(f"{BASE}/events?slug={slug}", timeout=15)
    events = r.json()
    
    if not events:
        print("  ERROR: evento no encontrado")
        continue
    
    event = events[0]
    markets = event.get("markets", [])
    print(f"  Candidatos/mercados totales: {len(markets)}\n")
    
    # Mostrar todos los candidatos con sus precios
    candidate_prices = {}
    for m in markets:
        q = m.get("question", "").lower()
        prices_str = m.get("outcomePrices", '["0","1"]')
        try:
            prices = json.loads(prices_str) if isinstance(prices_str, str) else prices_str
            yes_price = float(prices[0])
        except:
            yes_price = 0.0
        
        # Matchear con candidatos principales
        matched = None
        for cname, keywords in CANDIDATES_KEYWORDS.items():
            if any(kw in q for kw in keywords):
                matched = cname
                break
        
        flag = f" <-- {matched}" if matched else ""
        print(f"  {m.get('question','')[:65]}")
        print(f"    YES price: {yes_price:.3f} ({yes_price:.1%}){flag}")
        
        if matched:
            candidate_prices[matched] = yes_price
    
    all_prices[market_key] = candidate_prices
    print(f"\n  RESUMEN {market_key}:")
    for c, p in candidate_prices.items():
        print(f"    {c:<20} {p:.3%}")

# Mercado extra: segunda vuelta
print("\n" + "=" * 50)
print("MERCADO: Segunda vuelta (alguno gana en 1a?)")
print("=" * 50)
r2 = requests.get(f"{BASE}/events?slug=will-any-presidential-candidate-win-outright-in-the-first-round-of-the-colombias-election", timeout=15)
ev2 = r2.json()
if ev2:
    for m in ev2[0].get("markets", []):
        prices_str = m.get("outcomePrices", '["0","1"]')
        prices = json.loads(prices_str) if isinstance(prices_str, str) else prices_str
        print(f"  Q: {m.get('question','')[:70]}")
        print(f"  YES: {float(prices[0]):.1%}  |  NO: {float(prices[1]):.1%}")

print("\n\n" + "=" * 70)
print("RESUMEN EJECUTIVO PRECIOS LIVE")
print("=" * 70)
print(f"\n{'Mercado':<28} {'Cepeda':>10} {'De la Espriella':>18} {'Valencia':>10}")
print("-" * 70)
for mk, prices in all_prices.items():
    c = prices.get("Cepeda", 0)
    d = prices.get("De la Espriella", 0)
    v = prices.get("Valencia", 0)
    print(f"{mk:<28} {c:>9.1%} {d:>17.1%} {v:>9.1%}")

print("\n(Comparar con encuestas: Cepeda ~44%, Espriella ~33%, Valencia ~22%)")
