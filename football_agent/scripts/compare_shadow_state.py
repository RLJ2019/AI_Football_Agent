from __future__ import annotations

import csv
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from football_agent.database.connection import DatabaseSettings, SupabaseRestClient
from football_agent.database.repository import DatabaseRepository, pick_identity_from_values


def _local_pick_identities(path: Path, since_utc: str = "") -> tuple[list[str], Dict[str, Dict[str, str]]]:
    if not path.exists():
        return [], {}
    identities: list[str] = []
    rows_by_identity: Dict[str, Dict[str, str]] = {}
    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            created_at = str(row.get("created_at_utc", ""))
            if since_utc and created_at and created_at < since_utc:
                continue
            identity = pick_identity_from_values(
                row.get("fixture_id", ""),
                row.get("market", "1X2"),
                row.get("selection", "NONE"),
                row.get("model_version", "unknown"),
            )
            identities.append(identity)
            rows_by_identity[identity] = row
    return identities, rows_by_identity


def _local_state(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    result: Dict[str, Dict[str, Any]] = {}
    for item in payload.get("picks", {}).values():
        fixture_id = str(item.get("fixture_id", ""))
        selection = str(item.get("selection") or "NONE")
        # V25.0.9 local keys do not persist the market separately. The signature does.
        signature = str(item.get("signature", ""))
        parts = signature.split("|")
        market = parts[2] if len(parts) > 2 and parts[2] else "1X2"
        result[f"{fixture_id}|{market}|{selection}"] = item
    return result


def main() -> None:
    out_dir = Path(os.getenv("LOCAL_OUTPUT_DIR", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    settings = DatabaseSettings.from_env()
    report_path = out_dir / "shadow_parity_report.json"

    if not settings.enabled or not settings.configured:
        report = {
            "status": "SKIPPED",
            "reason": "Database disabled or not configured.",
            "settings": settings.safe_summary(),
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return

    repository = DatabaseRepository(SupabaseRestClient(settings))
    try:
        database_picks = repository.fetch_picks()
        database_state = repository.fetch_notification_state()
    except Exception as exc:
        report = {
            "status": "DATABASE_ERROR",
            "error": str(exc),
            "settings": settings.safe_summary(),
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        if not settings.fail_open:
            raise
        return

    compare_since_utc = os.getenv("SHADOW_COMPARE_SINCE_UTC", "").strip()
    local_ids, _ = _local_pick_identities(out_dir / "prediction_log.csv", compare_since_utc)
    local_counter = Counter(local_ids)
    local_unique = set(local_counter)
    database_ids = [str(row.get("identity_key", "")) for row in database_picks if row.get("identity_key")]
    database_counter = Counter(database_ids)
    database_unique = set(database_counter)

    local_state = _local_state(out_dir / "notification_state.json")
    db_state = {
        f"{row.get('fixture_id')}|{row.get('market')}|{row.get('selection')}": row
        for row in database_state
    }
    common_state_keys = set(local_state) & set(db_state)
    state_mismatches = []
    for key in sorted(common_state_keys):
        local = local_state[key]
        remote = db_state[key]
        if local.get("status") != remote.get("status") or local.get("signature") != remote.get("signature"):
            state_mismatches.append({
                "key": key,
                "local_status": local.get("status"),
                "database_status": remote.get("status"),
                "local_signature": local.get("signature"),
                "database_signature": remote.get("signature"),
            })

    missing = sorted(local_unique - database_unique)
    unexpected = sorted(database_unique - local_unique)
    duplicates_local = sorted(key for key, count in local_counter.items() if count > 1)
    duplicates_database = sorted(key for key, count in database_counter.items() if count > 1)
    matched = len(local_unique & database_unique)
    denominator = max(1, len(local_unique))
    parity = matched / denominator

    report = {
        "status": "PASS" if not missing and not duplicates_database and not state_mismatches else "REVIEW",
        "compare_since_utc": compare_since_utc or None,
        "local_rows": len(local_ids),
        "local_unique_picks": len(local_unique),
        "database_rows": len(database_ids),
        "database_unique_picks": len(database_unique),
        "matched_unique_picks": matched,
        "missing_in_database": missing,
        "unexpected_in_database": unexpected,
        "local_duplicate_identities": duplicates_local,
        "database_duplicate_identities": duplicates_database,
        "local_notification_states": len(local_state),
        "database_notification_states": len(db_state),
        "state_missing_in_database": sorted(set(local_state) - set(db_state)),
        "state_unexpected_in_database": sorted(set(db_state) - set(local_state)),
        "state_mismatches": state_mismatches,
        "shadow_parity": round(parity, 6),
        "shadow_parity_percent": round(parity * 100.0, 2),
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
