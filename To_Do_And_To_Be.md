# 🇨🇴 Colombia Predictor
## Plan de implementación — Pipeline de predicción para mercados políticos

> Mayo 2026 · Elecciones presidenciales Colombia

**Objetivo:** Construir un pipeline completo de predicción que compare las probabilidades derivadas de encuestas colombianas contra los precios de mercados de predicción internacionales (Kalshi, Polymarket), detecte edge estadístico y genere señales accionables de trading.

---

## 1. Contexto y oportunidad

Las elecciones presidenciales colombianas de 2026 presentan una discrepancia notable entre encuestas locales y mercados internacionales:

| Fuente | Cepeda | De la Espriella | Valencia |
|--------|--------|-----------------|----------|
| CNC / Cambio (24 may) | 33.4% | 30.9% | 12.6% |
| Invamer (22 may) | 44.6% | 31.6% | 14.0% |
| Guarumo / Ecoanalítica (21 may) | 37.1% | 27.5% | 21.7% |
| Atlas Intel (15 may) | 37.0% | 29.0% | 20.0% |
| **── Promedio encuestas ──** | **~38%** | **~28%** | **~19%** |
| Kalshi (precio mercado) | 37% | 63% | 3% |
| Polymarket (precio mercado) | 38% | 61% | 3% |

El gap clave: los mercados internacionales dan 63% a De la Espriella como ganador final, mientras las encuestas presenciales colombianas lo ubican ~28% en primera vuelta. Esto sugiere que los mercados están descontando fuertemente un escenario de segunda vuelta donde De la Espriella derrota a Cepeda.

---

## 2. Arquitectura del pipeline

### 2.1 Estructura del repositorio

```
colombia-predictor/
├── scrapers/           # Recolección de datos
│   ├── polymarket.py   # API pública Polymarket CLOB
│   ├── kalshi.py       # API Kalshi (requiere key)
│   └── polls.py        # Encuestas + promedios ponderados
├── models/             # Modelos de predicción
│   ├── features.py     # Feature engineering (11 features)
│   ├── train.py        # Entrenamiento XGBoost
│   └── calibrate.py    # Calibración Platt scaling
├── analysis/           # Señales de trading
│   ├── edge.py         # Edge = modelo - mercado
│   └── kelly.py        # Kelly criterion sizing
├── data/               # Snapshots JSON / Parquet
├── run.py              # Entry point principal
└── requirements.txt
```

### 2.2 Flujo de datos

1. Scrapers recolectan encuestas y precios de mercado
2. Feature engineering construye vector de 11 features por candidato
3. Modelo genera probabilidad independiente
4. Módulo de edge compara modelo vs mercado
5. Kelly criterion calcula tamaño de posición
6. Resultados se guardan y retroalimentan el modelo

---

## 3. Fases de implementación

### Fase 1 — Setup inmediato (hoy, 2-3 horas)

Objetivo: correr el pipeline básico con datos hardcodeados y obtener las primeras señales.

| Paso | Acción | Comando |
|------|--------|---------|
| 1 | Clonar repo e instalar deps | `git clone ... && pip install -r requirements.txt` |
| 2 | Correr análisis baseline | `python run.py --dry-run` |
| 3 | Actualizar precios en tiempo real | `python run.py --update-prices` |
| 4 | Revisar señales de edge | Ver output en consola / `data/edge_analysis.json` |
| 5 | Subir a GitHub | `git init && git add . && git push` |

### Fase 2 — Modelo de primera vuelta (hoy/mañana)

Objetivo: tener señales antes de que cierren los mercados el 31 de mayo.

- Actualizar `MARKET_PRICES` en `analysis/edge.py` con precios en tiempo real
- Ajustar `MODEL_PROBS` con las encuestas más recientes disponibles
- Correr `python run.py --update-prices` para snapshot de Polymarket
- Revisar señales de `ganador_primera_vuelta`
- Verificar precios en predictionhunt.com y kalshi.com manualmente

**Señales actuales del modelo (baseline encuestas):**

| Mercado | Candidato | Modelo | Mercado | Edge | Señal |
|---------|-----------|--------|---------|------|-------|
| Ganador final | De la Espriella | 42% | 62% | -20% | 🟢 BUY NO |
| Ganador final | Valencia | 20% | 3% | +17% | 🟢 BUY YES |
| Primera vuelta | Cepeda | 49% | 62% | -13% | 🟢 BUY NO |
| Primera vuelta | De la Espriella | 34% | 25% | +9% | 🟡 BUY YES |
| Primera vuelta | Valencia | 18% | 10% | +8% | 🟡 BUY YES |

### Fase 3 — Modelo con datos históricos (semanas 1-2)

Objetivo: entrenar XGBoost con el dataset de Jon-Becker para obtener probabilidades calibradas.

- Descargar dataset Jon-Becker/prediction-market-analysis (36 GB)
- Filtrar mercados políticos latinoamericanos del dataset
- Construir dataset de entrenamiento con `features.py`
- Entrenar modelo XGBoost con validación cruzada
- Calibrar probabilidades con Platt scaling
- Validar con Brier score sobre datos históricos

```bash
python models/train.py --data data/historical_political.parquet
python models/calibrate.py --model models/xgb_v1.pkl
```

### Fase 4 — Automatización y monitoreo (semanas 2-4)

Objetivo: pipeline que corre automáticamente y monitorea cambios de precio.

- Integrar MCP server (JamesANZ/prediction-market-mcp) para precios en tiempo real
- Agregar scraper de Kalshi con autenticación RSA
- Scheduler: correr pipeline cada 30 min con cron o GitHub Actions
- Alertas por email/Telegram cuando edge > 10%
- Dashboard simple con matplotlib para visualizar señales

### Fase 5 — Segunda vuelta (si aplica, 21 junio)

Si ningún candidato supera el 50%+1 el 31 de mayo, hay segunda vuelta el 21 de junio.

- Actualizar `MODEL_PROBS` con resultado de primera vuelta
- Agregar features de segunda vuelta: transferencia de votos Valencia → ¿quién?
- Según encuestas Guarumo: De la Espriella > Cepeda en ballotage
- Monitorear nuevas encuestas post-primera vuelta
- Mercado de ganador final se vuelve más líquido y preciso

---

## 4. Features del modelo

El modelo usa 11 features por candidato, construidos en `models/features.py`:

| Feature | Descripción | Fuente |
|---------|-------------|--------|
| `poll_avg` | Promedio de intención de voto normalizado | Encuestas |
| `poll_momentum_14d` | Cambio en últimos 14 días | Encuestas |
| `poll_variance` | Varianza entre encuestadoras | Encuestas |
| `market_price` | Precio actual del contrato | Kalshi / Polymarket |
| `market_edge_raw` | Diferencia directa modelo - mercado | Calculado |
| `market_volume_norm` | Volumen normalizado (log) | Polymarket API |
| `days_to_election` | Días hasta elección (normalizado) | Calendario |
| `undecided_share` | % indecisos / voto en blanco | Encuestas |
| `right_consolidation` | Suma Espriella + Valencia | Encuestas |
| `is_incumbent_party` | 1 si es candidato del partido en poder | Manual |
| `is_right_candidate` | 1 si es candidato de derecha | Manual |

---

## 5. Repos externos integrados

| Repo | Rol en el pipeline | URL |
|------|--------------------|-----|
| OctagonAI/kalshi-trading-bot-cli | Ejecución de trades + análisis con IA | github.com/OctagonAI/kalshi-trading-bot-cli |
| Jon-Becker/prediction-market-analysis | Dataset histórico 36GB para entrenar modelo | github.com/Jon-Becker/prediction-market-analysis |
| JamesANZ/prediction-market-mcp | Datos en tiempo real sin API key | github.com/JamesANZ/prediction-market-mcp |

---

## 6. Riesgos y consideraciones

### 6.1 Riesgos del modelo

- **Voto oculto de derecha:** encuestas pueden subestimar a De la Espriella (fenómeno Rodolfo Hernández 2022)
- **Indecisos de última hora:** 13-23% según encuestadoras, pueden moverse en cualquier dirección
- **Diferencias metodológicas:** encuestas presenciales vs online vs telefónicas dan resultados distintos
- **Transferencia de votos Valencia** en segunda vuelta: clave pero difícil de modelar

### 6.2 Riesgos operacionales

- **Liquidez:** mercados de Colombia pueden ser thin, especialmente en Kalshi
- **Timing:** mercados pueden cerrar antes de la elección, verificar horarios
- **Precios en tiempo real:** siempre verificar en kalshi.com y polymarket.com antes de cualquier trade

### 6.3 Advertencia

> ⚠️ Este pipeline es una herramienta educativa de análisis cuantitativo. Los mercados de predicción conllevan riesgo de pérdida total del capital. Nunca invertir más de lo que se puede perder. **No es asesoría financiera.**

---

## 7. Referencia rápida de comandos

| Comando | Descripción |
|---------|-------------|
| `python run.py --dry-run` | Análisis completo sin guardar archivos |
| `python run.py --update-prices` | Actualiza precios de Polymarket y analiza |
| `python scrapers/polls.py` | Solo encuestas y promedios |
| `python scrapers/polymarket.py` | Solo precios de Polymarket |
| `python analysis/edge.py` | Solo análisis de edge con precios hardcodeados |
| `python models/features.py` | Ver feature vectors actuales |

**Links útiles:**

- Precios en tiempo real: [predictionhunt.com/odds/colombia-presidential-election](https://predictionhunt.com/odds/colombia-presidential-election)
- Kalshi: [kalshi.com/markets/KXCOLOMBIAPRES](https://kalshi.com/markets/KXCOLOMBIAPRES)
- Polymarket: [polymarket.com/event/colombia-presidential-election](https://polymarket.com/event/colombia-presidential-election)
- Encuestas: [lasillavacia.com](https://lasillavacia.com) (ponderador electoral)
- Resultados oficiales: [registraduria.gov.co](https://registraduria.gov.co)

---

*Colombia Predictor · Mayo 2026 · Solo para fines educativos*