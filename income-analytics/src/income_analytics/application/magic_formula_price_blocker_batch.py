"""Dry-run batch recovery for price-only Magic Formula universe blockers."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from income_analytics.application.historical_price import gap_analysis
from income_analytics.application.historical_security_identity import (
    EXCHANGE_DIRECTORY_POLICY,
    _class_matches_ticker_isin,
    recover_price_from_exchange_identity,
)
from income_analytics.application.magic_formula_universe import coverage

TERMINAL_STATUSES = (
    "RECOVERED",
    "IDENTITY_CONFIRMED_PRICE_UNAVAILABLE",
    "NO_TRADE_ON_REFERENCE_DATE",
    "NOT_LISTED_ON_REFERENCE_DATE",
    "DELISTED_BEFORE_REFERENCE_DATE",
    "SOURCE_GAP",
    "AMBIGUOUS_IDENTITY",
    "UNRESOLVED",
)


def _directory_security_candidates(current, share_class):
    codes = list(current.get("otherCodes") or [])
    if not codes and current.get("code") and current.get("isin"):
        codes = [{"code": current["code"], "isin": current["isin"]}]
    return [
        item
        for item in codes
        if _class_matches_ticker_isin(item.get("code"), item.get("isin"), share_class)
    ]


def _source_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_batch(snapshot, evidence_directory: Path, cotahist_index, cotahist_manifest):
    """Return a dry-run candidate and one terminal outcome per PRICE-only issuer."""
    manifest = json.loads((evidence_directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest["baseline_snapshot_id"] != snapshot["universe_snapshot_id"]:
        raise ValueError("BEFORE_SNAPSHOT_MISMATCH")
    directory_responses = {r["cvm_code"]: r for r in manifest["responses"]}
    candidate = deepcopy(snapshot)
    outcomes = []
    recovered_ids = []
    eligible = [i for i in snapshot["issuers"] if i["methodology_eligibility"] == "ELIGIBLE"]
    blocker_issuers = [
        i
        for i in eligible
        if not i["market_readiness"]["price_ready"]
        and i["accounting_readiness"]["ready"]
        and i["market_readiness"]["security_ready"]
        and i["market_readiness"]["capital_ready"]
        and i["identity_status"] == "RESOLVED"
    ]
    positions = {i["issuer_id"]: n for n, i in enumerate(candidate["issuers"])}

    for original in blocker_issuers:
        details = {
            "blocker_id": original["issuer_id"],
            "company": original["display_name"],
            "cvm_code": original["cvm_code"],
            "cnpj": original["cnpj"],
            "resolution_attempts": [],
            "candidates_found": [],
            "selected_identity": None,
            "confidence": "LOW",
            "price_lookup_result": None,
            "terminal_status": "UNRESOLVED",
            "reason": None,
        }
        try:
            response = directory_responses.get(original["cvm_code"])
            if not response:
                details["reason"] = "B3_DIRECTORY_RESPONSE_MISSING"
                outcomes.append(details)
                continue
            raw_path = evidence_directory / response["file"]
            raw = raw_path.read_bytes()
            if _source_hash(raw_path) != response["sha256"]:
                details["reason"] = "B3_DIRECTORY_SOURCE_HASH_MISMATCH"
                outcomes.append(details)
                continue
            current = json.loads(raw)
            if (
                not current
                or current.get("cnpj") != original["cnpj"]
                or int(current.get("codeCVM", -1)) != int(original["cvm_code"])
            ):
                details["reason"] = "B3_CVM_CNPJ_IDENTITY_NOT_CONFIRMED"
                outcomes.append(details)
                continue
            staged = deepcopy(original)
            failures = []
            missing = [
                security
                for security in original["securities"]
                if security.get("price_status") != "AVAILABLE" or security.get("price") is None
            ]
            for target in missing:
                attempt = {
                    "raw_identifier": target.get("declared_ticker") or target.get("ticker"),
                    "share_class": target.get("share_class"),
                    "candidates_found": [],
                }
                details["resolution_attempts"].append(attempt)
                if target.get("valid_to") and target["valid_to"] < snapshot["reference_date"]:
                    failures.append(
                        ("DELISTED_BEFORE_REFERENCE_DATE", "SECURITY_VALID_TO_BEFORE_REFERENCE")
                    )
                    continue
                choices = _directory_security_candidates(current, target.get("share_class"))
                attempt["candidates_found"] = deepcopy(choices)
                details["candidates_found"].extend(deepcopy(choices))
                if len(choices) > 1:
                    failures.append(("AMBIGUOUS_IDENTITY", "MULTIPLE_B3_SECURITIES_FOR_CLASS"))
                    continue
                if not choices:
                    failures.append(("UNRESOLVED", "NO_B3_SECURITY_FOR_DECLARED_CLASS"))
                    continue
                choice = choices[0]
                listing = date.fromisoformat(target["valid_from"])
                # The CVM security validity window is class-specific; the B3 directory
                # date is issuer-level and cannot override a later class valid_from.
                if listing > date.fromisoformat(snapshot["reference_date"]):
                    failures.append(
                        ("NOT_LISTED_ON_REFERENCE_DATE", "CLASS_VALID_FROM_AFTER_REFERENCE")
                    )
                    continue
                proof = {
                    "schema_version": EXCHANGE_DIRECTORY_POLICY,
                    "cnpj": original["cnpj"],
                    "cvm_code": original["cvm_code"],
                    "ticker": choice["code"],
                    "isin": choice["isin"],
                    "share_class": target["share_class"],
                    "listing_date": datetime.strptime(current["dateQuotation"], "%d/%m/%Y")
                    .date()
                    .isoformat(),
                    "source_file": response["file"],
                    "source_sha256": response["sha256"],
                    "source_url": response.get("url"),
                    "source_retrieved_at": response.get("retrieved_at"),
                    "historical_ticker": choice["code"],
                    "price_policy_version": "MAGIC_FORMULA_HISTORICAL_PRICE_V1",
                }
                rows = cotahist_index.get(choice["code"], [])
                attempt["selected_identity"] = {
                    "ticker": choice["code"],
                    "isin": choice["isin"],
                    "class": target["share_class"],
                }
                details["selected_identity"] = attempt["selected_identity"]
                if any(
                    row.get("isin") != choice["isin"] for row in rows if row.get("market") == "010"
                ):
                    failures.append(
                        ("AMBIGUOUS_IDENTITY", "HISTORICAL_TICKER_REUSED_OR_ISIN_CONFLICT")
                    )
                    continue
                try:
                    staged = recover_price_from_exchange_identity(
                        staged, proof, current, rows, snapshot["reference_date"]
                    )
                    attempt["price_lookup_result"] = "RESOLVED"
                    attempt["confidence"] = "HIGH"
                    details["confidence"] = "HIGH"
                    details["price_lookup_result"] = "RESOLVED"
                except ValueError as error:
                    reason = str(error)
                    attempt["price_lookup_result"] = reason
                    details["price_lookup_result"] = reason
                    if reason == "LISTING_AFTER_REFERENCE":
                        failures.append(("NOT_LISTED_ON_REFERENCE_DATE", reason))
                    elif reason == "SECURITY_NOT_ACTIVE_AT_REFERENCE_DATE":
                        failures.append(("DELISTED_BEFORE_REFERENCE_DATE", reason))
                    elif reason == "EFFECTIVE_DATE_GAP":
                        failures.append(("NO_TRADE_ON_REFERENCE_DATE", reason))
                    elif reason in {
                        "PRICE_RECORD_NOT_FOUND",
                        "NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY",
                    }:
                        failures.append(("IDENTITY_CONFIRMED_PRICE_UNAVAILABLE", reason))
                    elif reason in {
                        "AMBIGUOUS_REFERENCE_PRICE",
                        "HISTORICAL_ISIN_CONFLICT",
                        "AMBIGUOUS_CURRENT_IDENTITY",
                        "TICKER_ISIN_CLASS_MISMATCH",
                    }:
                        failures.append(("AMBIGUOUS_IDENTITY", reason))
                    else:
                        failures.append(("UNRESOLVED", reason))
            if failures:
                # Nothing is accepted at issuer level when any required class fails.
                statuses = [status for status, _ in failures]
                precedence = [
                    "AMBIGUOUS_IDENTITY",
                    "DELISTED_BEFORE_REFERENCE_DATE",
                    "NOT_LISTED_ON_REFERENCE_DATE",
                    "NO_TRADE_ON_REFERENCE_DATE",
                    "IDENTITY_CONFIRMED_PRICE_UNAVAILABLE",
                    "SOURCE_GAP",
                    "UNRESOLVED",
                ]
                details["terminal_status"] = next(s for s in precedence if s in statuses)
                details["reason"] = ";".join(sorted({reason for _, reason in failures}))
            elif staged["market_readiness"]["price_ready"]:
                candidate["issuers"][positions[original["issuer_id"]]] = staged
                details["terminal_status"] = "RECOVERED"
                details["confidence"] = "HIGH"
                recovered_ids.append(original["issuer_id"])
            else:
                details["terminal_status"] = "UNRESOLVED"
                details["reason"] = "REQUIRED_SECURITY_CLASSES_STILL_UNPRICED"
        except Exception as error:  # A malformed case must not stop the remaining batch.
            details["terminal_status"] = "UNRESOLVED"
            details["reason"] = f"CASE_ERROR:{type(error).__name__}:{error}"
        outcomes.append(details)

    statuses = {
        status: sum(o["terminal_status"] == status for o in outcomes)
        for status in TERMINAL_STATUSES
    }
    if len(outcomes) != len(blocker_issuers) or sum(statuses.values()) != len(blocker_issuers):
        raise AssertionError("BATCH_TERMINAL_STATUS_COUNT_MISMATCH")
    candidate.update(universe_snapshot_id=str(uuid4()))
    candidate["coverage"] = coverage(candidate["issuers"])
    candidate.pop("price_resolution_run", None)
    candidate["identity_recovery_run"] = {
        "policy_version": "MAGIC_FORMULA_PRICE_BLOCKERS_BATCH_RECOVERY_V3",
        "parent_id": snapshot["universe_snapshot_id"],
        "recovered_issuers": recovered_ids,
        "case_results": outcomes,
        "terminal_status_counts": statuses,
        "cotahist_manifest": cotahist_manifest,
        "before_gap_analysis": gap_analysis(snapshot["issuers"]),
        "after_gap_analysis": gap_analysis(candidate["issuers"]),
        "dry_run": True,
        "independent_readback": "REQUIRED",
    }
    return candidate
