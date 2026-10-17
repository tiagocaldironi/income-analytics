"""Frozen validation samples and independent rank QA; no release authorization."""

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from income_analytics.application.magic_formula_contract import (
    ADAPTER_VERSION,
    METHODOLOGY_VERSION,
    digest,
    snapshot_digest,
)

SAMPLE_TYPE = "VALIDATION_SAMPLE"
TIE_POLICY = "DENSE_EY_ROC_AND_SCORE; DISPLAY_SCORE_ASC_ISSUER_UUID_ASC"
INPUT_METRICS = (
    "ebit",
    "enterprise_value",
    "invested_capital",
    "earnings_yield",
    "return_on_capital",
)


class RankingGateBlocked(ValueError):
    def __init__(self, exclusions):
        self.exclusions = tuple(exclusions)
        super().__init__("RANKING_ENGINE_GATE_BLOCKED:" + json.dumps(exclusions))


def load_bound_inputs(repository, bindings, reference_date):
    """Always use exact snapshot IDs, never a newest-snapshot query."""
    inputs, exclusions = [], []
    for binding in bindings:
        issuer_id, sid = binding["issuer_id"], binding["snapshot_id"]
        decision = repository.eligibility(issuer_id, reference_date, snapshot_id=sid)
        reasons = list(decision.reasons)
        if decision.issuer_status != "RESOLVED":
            reasons.append("ISSUER_NOT_RESOLVED")
        if not decision.eligible:
            reasons.append("ISSUER_NOT_RANKING_ELIGIBLE")
        snapshot = repository.read_snapshot(sid)
        if snapshot is None:
            reasons.append("MISSING_VALIDATED_SNAPSHOT")
        else:
            for key, expected, reason in (
                ("id", sid, "SNAPSHOT_ID_MISMATCH"),
                ("issuer_id", issuer_id, "ISSUER_MISMATCH"),
                ("validation_status", "PASS", "SNAPSHOT_NOT_VALIDATED"),
                ("adapter_version", ADAPTER_VERSION, "ADAPTER_VERSION_MISMATCH"),
                ("methodology_version", METHODOLOGY_VERSION, "METHODOLOGY_VERSION_MISMATCH"),
                ("financial_reference_date", reference_date, "REFERENCE_DATE_MISMATCH"),
                ("market_reference_date", reference_date, "REFERENCE_DATE_MISMATCH"),
            ):
                if snapshot.get(key) != expected:
                    reasons.append(reason)
            if decision.snapshot_id != sid or not decision.qa_decision_id:
                reasons.append("MISSING_BOUND_FORMAL_QA")
            amounts = {}
            try:
                metrics = json.loads(snapshot["metrics_json"])
            except (ValueError, KeyError, TypeError):
                metrics = {}
            for key in INPUT_METRICS:
                try:
                    value = Decimal(str(metrics[key]))
                    if not value.is_finite():
                        raise ValueError(key)
                    amounts[key] = value
                    if value <= 0:
                        reasons.append("NON_POSITIVE_" + key.upper())
                except (KeyError, ValueError, InvalidOperation):
                    reasons.append("MISSING_OR_INVALID_" + key.upper())
            if not reasons:
                inputs.append(
                    dict(
                        issuer_id=issuer_id,
                        snapshot_id=sid,
                        qa_id=decision.qa_decision_id,
                        snapshot_digest=snapshot_digest(snapshot),
                        **{k: str(v) for k, v in amounts.items()},
                    )
                )
        if reasons:
            exclusions.append(
                dict(issuer_id=issuer_id, snapshot_id=sid, reason_codes=sorted(set(reasons)))
            )
    if exclusions:
        raise RankingGateBlocked(exclusions)
    return sorted(inputs, key=lambda i: i["issuer_id"])


def freeze_sample(repository, bindings, reference_date):
    if (
        len(bindings) != 5
        or len({b["issuer_id"] for b in bindings}) != 5
        or len({b["snapshot_id"] for b in bindings}) != 5
    ):
        raise RankingGateBlocked([dict(reason_codes=["EXACTLY_FIVE_DISTINCT_ISSUERS_REQUIRED"])])
    inputs = load_bound_inputs(repository, bindings, reference_date)
    return dict(
        sample_id=str(uuid4()),
        universe_type=SAMPLE_TYPE,
        reference_date=reference_date,
        methodology_version=METHODOLOGY_VERSION,
        adapter_version=ADAPTER_VERSION,
        created_at=datetime.now(UTC).isoformat(),
        status="FROZEN",
        tie_policy=TIE_POLICY,
        inputs=inputs,
        inputs_digest=digest(inputs),
    )


def validate_frozen_sample(repository, sample):
    expected = dict(
        universe_type=SAMPLE_TYPE,
        methodology_version=METHODOLOGY_VERSION,
        adapter_version=ADAPTER_VERSION,
        status="FROZEN",
        tie_policy=TIE_POLICY,
    )
    if any(sample.get(k) != v for k, v in expected.items()):
        raise RankingGateBlocked([dict(reason_codes=["INVALID_FROZEN_SAMPLE_CONTRACT"])])
    bindings = sample["inputs"]
    if len(bindings) != 5 or len({i["issuer_id"] for i in bindings}) != 5:
        raise RankingGateBlocked([dict(reason_codes=["EXACTLY_FIVE_DISTINCT_ISSUERS_REQUIRED"])])
    inputs = load_bound_inputs(repository, bindings, sample["reference_date"])
    if digest(inputs) != sample["inputs_digest"] or inputs != sorted(
        bindings, key=lambda i: i["issuer_id"]
    ):
        raise RankingGateBlocked([dict(reason_codes=["FROZEN_INPUT_OR_QA_CHANGED"])])
    return inputs


def independent_rank_qa(approved_inputs):
    """QA receives only issuer/EY/ROC. Count distinct better values, not production sorting."""
    values = [
        (i["issuer_id"], Decimal(i["earnings_yield"]), Decimal(i["return_on_capital"]))
        for i in approved_inputs
    ]
    result = []
    for issuer, ey, roc in values:
        ey_rank = 1 + len({v[1] for v in values if v[1] > ey})
        roc_rank = 1 + len({v[2] for v in values if v[2] > roc})
        result.append(
            dict(
                issuer_id=issuer,
                earnings_yield=str(ey),
                return_on_capital=str(roc),
                earnings_yield_rank=ey_rank,
                return_on_capital_rank=roc_rank,
                magic_formula_score=ey_rank + roc_rank,
            )
        )
    for row in result:
        row["final_rank"] = 1 + len(
            {
                r["magic_formula_score"]
                for r in result
                if r["magic_formula_score"] < row["magic_formula_score"]
            }
        )
        row["score_tied"] = (
            sum(r["magic_formula_score"] == row["magic_formula_score"] for r in result) > 1
        )
    result.sort(key=lambda r: (r["magic_formula_score"], r["issuer_id"]))
    for position, row in enumerate(result, 1):
        row["final_display_order"] = position
    return result


def compare_independent_qa(inputs, production):
    approved = [
        {k: i[k] for k in ("issuer_id", "earnings_yield", "return_on_capital")} for i in inputs
    ]
    expected = independent_rank_qa(approved)
    actual = [{k: r.get(k) for k in expected[0]} for r in production]
    if actual != expected:
        raise ValueError("INDEPENDENT_RANKING_QA_FAIL")
    return dict(
        status="PASS",
        inputs_digest=digest(approved),
        result_digest=digest(expected),
        compared_fields=list(expected[0]),
        algorithm="COUNT_DISTINCT_BETTER_VALUES",
    )


def ranking_artifact(sample, items, qa):
    return dict(
        ranking_snapshot_id=str(uuid4()),
        sample_id=sample["sample_id"],
        sample_digest=digest(sample),
        universe_type=SAMPLE_TYPE,
        reference_date=sample["reference_date"],
        methodology_version=METHODOLOGY_VERSION,
        adapter_version=ADAPTER_VERSION,
        created_at=datetime.now(UTC).isoformat(),
        status="PASS",
        tie_policy=TIE_POLICY,
        inputs=sample["inputs"],
        items=items,
        independent_qa=qa,
        coverage=dict(
            total_considered=5, resolved=5, eligible=5, ranked=len(items), excluded=0, unresolved=0
        ),
        tool_status="VALIDATION_REQUIRED",
        ranking_status="INACTIVE",
    )
