# V25 Multi-League Value Prediction Engine

## V25.1.0 Phase 1 — Shadow Database Infrastructure

Deze build voegt een veilige dual-write database-laag toe zonder de bestaande, werkende V25.0.9-pipeline te vervangen.

> Bestaande CSV/JSON + Telegram blijven leidend. Supabase/PostgreSQL draait uitsluitend als shadow mirror totdat parity aantoonbaar 100% is.

## Wat deze build doet

- Optionele server-side Supabase REST-verbinding.
- Fail-open shadow writes: database-uitval breekt de agent, Telegram of artifacts niet.
- Centrale shadow-tabellen voor fixtures, picks, pick-events, notification-state, odds snapshots en workflow-runs.
- Deterministische `pick_id` en `identity_key`, zodat herhaalde runs geen dubbele picks creëren.
- Append-only event ledger via `pick_events`.
- Lokale auditbestanden:
  - `output/shadow_database_report.json`
  - `output/shadow_database_failures.jsonl` bij fouten
  - `output/shadow_parity_report.json`
- Database-healthcheck en shadow-parity scripts.
- Alle vier workflows ondersteunen dezelfde databaseconfiguratie en dezelfde shared cache-prefix tijdens de migratiefase.
- Telegram blijft centraal via `TELEGRAM_ENABLED` aan/uit te zetten.

## Belangrijk

V25.1.0 Phase 1 verandert niet:

- de modelbeslissing;
- de Value Pick-selectie;
- staking;
- Telegram-deduplicatie;
- de line-upmonitor;
- de huidige CSV/JSON-bron van waarheid.

De database is in deze fase nog **niet** leidend.

## Installatie

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m compileall football_agent -q
python smoke_test.py
python -m unittest discover -s tests
```

## Supabase eenmalig instellen

1. Maak een Supabase-project aan.
2. Open de SQL Editor.
3. Voer volledig uit:

```text
football_agent/database/migrations/001_initial_schema.sql
```

4. Maak in GitHub bij **Settings → Secrets and variables → Actions → Secrets** aan:

```text
SUPABASE_URL
SUPABASE_SECRET_KEY
```

De secret/service-role key is uitsluitend server-side. Plaats hem nooit in Git, een artifact, CSV, Google Sheet of frontend.

5. Maak bij **Variables** aan:

```text
DATABASE_ENABLED=true
DATABASE_SHADOW_MODE=true
DATABASE_FAIL_OPEN=true
DATABASE_TIMEOUT_SECONDS=20
DATABASE_MAX_RETRIES=2
DATABASE_BATCH_SIZE=250
SHADOW_COMPARE_SINCE_UTC=
```

Tijdens de eerste installatie mag `DATABASE_ENABLED=false` blijven. De agent blijft dan exact functioneren zoals V25.0.9.

## Database-healthcheck

Lokaal:

```bash
python -m football_agent.scripts.run_database_healthcheck
```

Of handmatig via de daily workflow met mode:

```text
database_healthcheck
```

Verwachte uitkomst:

```text
reachable: true
message: Supabase REST connection OK.
```

## Shadow parity vergelijken

Na enkele runs:

```bash
python -m football_agent.scripts.compare_shadow_state
```

Of kies in de daily workflow:

```text
compare_shadow
```

De vergelijking controleert:

- unieke lokale picks versus databasepicks;
- ontbrekende of onverwachte records;
- dubbele database-identiteiten;
- notification-state status/signature mismatches;
- shadow parity-percentage.

## Acceptatiecriteria vóór Phase 2

De database mag pas leidend worden na minimaal vijf echte speeldagen met:

```text
100% lokale picks aanwezig in database
0 database-duplicaten
0 ontbrekende statuswijzigingen
0 notification-state mismatches
database-uitval breekt geen agentrun
herhaalde runs creëren geen dubbele records
```

## Dagelijkse run

```bash
python run_agent.py
```

## Line-up monitor

```bash
python -m football_agent.scripts.run_lineup_monitor
```

De monitor gebruikt praktisch een T-65 tot T-45 window. GitHub Actions garandeert geen exact T-55-startmoment.

## Heartbeat

```bash
python -m football_agent.scripts.run_heartbeat
```

## Backtest en weight-training

```bash
python -m football_agent.scripts.run_backtest
python -m football_agent.scripts.run_weight_training
```

## Telegrambeleid

- Dagrapport: stil.
- Heartbeat: stil.
- Value Pick: luid.
- Pick gewijzigd/bevestigd: luid.
- Pick ingetrokken: luid.
- Geen eurobedragen; staking wordt in units weergegeven.

## Volgende fasen

```text
Phase 2: database wordt source of truth voor state en notificaties
Phase 3: polymorfe settlement, closing snapshots en dual-metric CLV
Phase 4: wekelijkse Telegramrapportage en volledige Google Sheet-spiegel
```

## Filosofie

Minder picks. Betere picks. Geen schijnzekerheid. Volledig auditeerbaar.
