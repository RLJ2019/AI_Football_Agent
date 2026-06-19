# V25 Multi-League Value Prediction Engine

## V25.0.9 Premium Reliability & Sharp Market Upgrade

Deze build voegt premiumgroep-hardening toe: luide intrekkingen, jargonvrije Gemini-uitleg, gedeelde workflow-concurrency, atomic notification-state writes, webhook retry/idempotency voor Live Sheet, minder dubbel gestrafte staking, sharp/no-vig fair odds in Telegram en order-invariant logit-attributie.


## V25.0.7 Premium Telegram Operations Upgrade

Professionele multi-league voetbalagent met als uitgangspunt:

> Het model voorspelt. Gemini legt uit.

De agent scant wedstrijden uit meerdere competities, corrigeert bookmaker-odds voor marge, vergelijkt modelkansen met de markt, selecteert alleen value-picks en logt alle voorspellingen voor evaluatie op Brier-score, ROI en Closing Line Value.

## Nieuw in V25.0.7

Deze build voegt premium Telegram-community operations toe bovenop de V25.0.6 model-engine:

- Loud/silent Telegram-notificatiebeleid: dagrapporten en heartbeats stil, echte VALUE PICK-alerts luid.
- Notificatie-state om dubbele alerts te voorkomen bij meerdere scans per dag.
- Status-transities: watchlist naar value pick, value pick update en ingetrokken picks worden apart behandeld.
- Event-driven line-up monitor via `python -m football_agent.scripts.run_lineup_monitor` en een GitHub Actions workflow elke 15 minuten.
- Heartbeat-run via `python -m football_agent.scripts.run_heartbeat` voor stille geruststellende statusupdates.
- Live sheet export naar `output/live_picks_sheet.csv` en optionele `LIVE_SHEET_URL` in Telegram.
- Telegram pick-alerts tonen nu units, min. odds, EV, confidence, datakwaliteit, uncertainty en line-up status.
- Bankroll-discpline blijft defensief: fractional Kelly, stake caps en exposure caps.


## Nieuw in V25.0.5

Deze build verwerkt de nieuwste audit-aanbevelingen:

- ML-voorbereide, competitie-specifieke overlay-gewichten via `learned_model_weights.json`.
- Offline trainingsscript `python -m football_agent.scripts.run_weight_training`.
- Exponential time-decay in het xG-model, zodat recente wedstrijden zwaarder wegen.
- Sharp odds velocity / implied movement als actieve guardrail tegen picks die tegen de scherpe markt in gaan.
- Bootstrapped uncertainty intervals op basis van feature-attributie.
- ValueEngine uitgebreid naar 1X2, Over/Under 2.5 en BTTS-markten.
- API-Football odds-parser uitgebreid voor Over/Under 2.5 en BTTS.
- Prediction log uitgebreid met feature-attributie, marktsoort en sharp movement.

- xG-normalisatie naar xG per 90 minuten via `minutes_played` in match-level teamvorm.
- International-break filter met verhoogde onzekerheid en line-up guardrail.
- Fractional Kelly stake-indicatie met harde caps en uncertainty-discount.
- Candidate recalibration: training schrijft eerst candidate weights + validatierapport, geen blind auto-push.
- Weekly GitHub Actions workflow voor candidate recalibration.
- Backtest-integriteitschecks tegen lookahead bias.
- Markt-specifieke backtest/evaluatie voor 1X2, Over/Under 2.5 en BTTS.

## Competities

- Premier League
- Bundesliga
- Eredivisie
- Ligue 1
- Serie A
- La Liga
- Belgische Pro League
- Champions League
- Europa League
- Conference League

Nationale bekers zijn bewust niet opgenomen in deze build.

## V25.0.9 Premium Staking & Line-up Hygiene

Deze versie voegt defensieve staking, min. odds voor value, watchlist-gerichte line-up monitoring, Telegram discipline en een optionele Google Sheet webhook bridge toe.

Belangrijkste communityregel: VALUE PICK alerts zijn luid; dagrapporten, heartbeats en intrekkingen zijn stil. Unitadvies is altijd in units, nooit in eurobedragen.


## Installatie

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python smoke_test.py
python -m unittest discover -s tests
```

## Secrets / environment variables

```bash
FOOTBALL_DATA_API_KEY=...
API_FOOTBALL_KEY=...
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
LIVE_SHEET_URL=https://...  # optioneel via GitHub vars
```

## Dagelijkse run

```bash
python run_agent.py
```

## Line-up monitor

```bash
python -m football_agent.scripts.run_lineup_monitor
```

Deze run analyseert alleen wedstrijden die exact in de T-65 tot T-45 minuten line-up window vallen. Dagrapporten staan uit; alleen nieuwe/gewijzigde VALUE PICK-alerts of ingetrokken picks worden verstuurd.

## Heartbeat

```bash
python -m football_agent.scripts.run_heartbeat
```

Deze run stuurt alleen een stille statusupdate wanneer er geen value picks zijn. Hiermee voorkom je paniek in een premium Telegramgroep tijdens droge marktdagen.

## Backtest

```bash
python -m football_agent.scripts.run_backtest
```

Verwachte CSV: `output/historical_predictions.csv` met minimaal:

```text
competition_key, selection, actual, odds, model_probability
```

## Gewichten trainen

```bash
python -m football_agent.scripts.run_weight_training
```

Standaard leest dit `output/prediction_log.csv` en schrijft candidate weights naar:

```text
output/candidate_learned_model_weights.json
output/weight_training_report.json
```

Belangrijk: training blijft conservatief en overschrijft productiegewichten niet blind. Promotie naar `learned_model_weights.json` gebeurt alleen bij voldoende sample size en aantoonbare verbetering.

## Belangrijke professionele beperkingen

Deze build is technisch compleet en modulair opgezet, maar de voorspellende kracht hangt volledig af van de kwaliteit van de data. Zonder verse odds, opening/closing odds, line-ups, blessures en teamstats zal de agent streng filteren en meestal `NO_BET` geven. Dat is bewust gedrag.

Voor echte live-value is minimaal nodig:

1. Verse odds met timestamps.
2. Opening en closing odds voor CLV.
3. Sharp/soft bookmakerprofielen.
4. Betrouwbare teamstats/xG.
5. Blessure- en line-updata.
6. Historische backtestdata voor kalibratie.

## Filosofie

Minder picks. Betere picks. Geen schijnzekerheid.


## V25.0.6 Promoted, Thresholds & Game-State Upgrade

Deze build voegt drie professionele live-season correcties toe:

- Bayesian promovendi-Elo: promoted teams starten met een lagere prior (standaard 1435) totdat live resultaten de rating overnemen.
- Competitie- en markt-specifieke EV-thresholds: Premier League/Champions League kunnen scherper zijn, Belgische Pro League/Conference League krijgen een hogere veiligheidsmarge.
- Game-state normalized xG: waar beschikbaar gebruikt het xG-model xG bij gelijke stand of maximaal 1 doelpunt verschil, zodat garbage-time en standvulling minder invloed hebben.

