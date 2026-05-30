# 🇨🇴 Colombia Predictor

Pipeline de predicción para mercados de predicción políticos colombianos (Kalshi / Polymarket).

## Estructura

```
colombia-predictor/
├── scrapers/           # Recolección de datos
│   ├── polymarket.py   # Precios en tiempo real de Polymarket
│   ├── kalshi.py       # Precios en tiempo real de Kalshi
│   └── polls.py        # Scraper de encuestas (Wikipedia, Infobae)
├── data/               # Datos crudos y procesados
├── models/             # Modelos de predicción
│   ├── features.py     # Feature engineering
│   ├── train.py        # Entrenamiento XGBoost
│   └── calibrate.py    # Calibración de probabilidades
├── analysis/           # Análisis de edge y backtesting
│   ├── edge.py         # Cálculo de edge vs mercado
│   └── kelly.py        # Kelly criterion sizing
└── notebooks/          # Exploración interactiva
    └── colombia_2026.ipynb
```

## Setup rápido

```bash
git clone https://github.com/TU_USUARIO/colombia-predictor.git
cd colombia-predictor
pip install -r requirements.txt
```

## Uso

```bash
# 1. Obtener precios actuales de los mercados
python scrapers/polymarket.py

# 2. Obtener encuestas más recientes
python scrapers/polls.py

# 3. Calcular edge
python analysis/edge.py

# 4. Ver sizing recomendado (Kelly)
python analysis/kelly.py
```

## Mercados activos (Colombia 2026)

| Mercado | Kalshi | Polymarket |
|---------|--------|------------|
| Ganador 1a vuelta | `KXCOLOMBIAPRES` | `colombia-presidential-election-1st-round-winner` |
| Ganador final | `KXCOLOMBIAPRES-26` | `colombia-presidential-election` |
| Turnout | — | `colombia-presidential-election-1st-round-turnout` |

## Candidatos

- **Iván Cepeda** — Pacto Histórico (izquierda)
- **Abelardo de la Espriella** — Independiente (derecha)
- **Paloma Valencia** — Centro Democrático (derecha)

## Disclaimer

Solo para fines educativos. No es asesoría financiera.
