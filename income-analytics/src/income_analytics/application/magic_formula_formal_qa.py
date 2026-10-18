"""Dimensional QA recovered from golden evidence and exact snapshot read-back.

No production metrics or expected values are written or recalculated here.
Derived identities are checked using only the independent golden inputs.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation

from income_analytics.application.magic_formula_contract import (
    DIMENSIONS,
    FINANCIAL_METRICS,
    DimensionDecision,
    ValidationStatus,
    golden_contract_errors,
)


def evaluate_formal_qa(
    fixture: dict, snapshot: dict, *, readback_matches: bool
) -> tuple[DimensionDecision, ...]:
    decisions = []
    contract_errors = golden_contract_errors(fixture)
    try:
        metrics = json.loads(snapshot["metrics_json"])
        lineage = json.loads(snapshot["lineage_json"])
        expected = fixture["expected"]
        components = [s for entry in lineage for s in entry.get("market_cap_components", [])]
    except (KeyError, TypeError, ValueError):
        return tuple(
            (
                DimensionDecision(d, ValidationStatus.REVIEW_REQUIRED, ("MALFORMED_ARTIFACT",))
                for d in DIMENSIONS
            )
        )

    def check(dimension, operation):
        if contract_errors:
            decisions.append(
                DimensionDecision(dimension, ValidationStatus.REVIEW_REQUIRED, contract_errors)
            )
            return
        try:
            evidence = operation()
            decisions.append(DimensionDecision(dimension, ValidationStatus.PASS, tuple(evidence)))
        except (KeyError, TypeError, ValueError, InvalidOperation, ZeroDivisionError) as exc:
            decisions.append(
                DimensionDecision(
                    dimension, ValidationStatus.REVIEW_REQUIRED, (f"MISSING_EVIDENCE:{exc}",)
                )
            )
        except AssertionError as exc:
            decisions.append(
                DimensionDecision(dimension, ValidationStatus.FAIL, (f"EVIDENCE_MISMATCH:{exc}",))
            )

    def present(record, *keys):
        for key in keys:
            if record.get(key) is None or record[key] == "":
                raise ValueError(key)

    def number(value):
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError("NONFINITE_AMOUNT")
        return result

    def equal(a, b, label):
        if not number(a) == number(b):
            raise AssertionError(label)

    def accounting():
        references = []
        required = FINANCIAL_METRICS[:7]
        for metric in required:
            group = fixture["accounting"][metric]
            present(group, "rule_id", "components", "normalized_expected_value")
            if not group["components"]:
                raise ValueError(metric)
            total = Decimal(0)
            seen = set()
            for c in group["components"]:
                present(
                    c,
                    "account_code",
                    "account_description",
                    "period_end",
                    "statement_scope",
                    "raw_value",
                    "currency_scale",
                    "normalization_multiplier",
                    "normalized_expected_value",
                    "source_reference",
                )
                if not c["account_code"] not in seen:
                    raise AssertionError("DUPLICATE_ACCOUNT")
                seen.add(c["account_code"])
                if not c["statement_scope"] == "CONSOLIDATED":
                    raise AssertionError("ACCOUNTING_SCOPE")
                if not c["period_end"] == fixture["reference_date"]:
                    raise AssertionError("ACCOUNTING_PERIOD")
                if not c["reference_date"] == fixture["reference_date"]:
                    raise AssertionError("ACCOUNTING_REFERENCE")
                if not c["currency"] == "BRL":
                    raise AssertionError("ACCOUNTING_CURRENCY")
                multipliers = {"UNIT": 1, "THOUSAND": 1000, "MILLION": 1000000}
                equal(c["normalization_multiplier"], multipliers[c["currency_scale"]], "SCALE")
                equal(
                    number(c["raw_value"]) * number(c["normalization_multiplier"]),
                    c["normalized_expected_value"],
                    "MONETARY_NORMALIZATION",
                )
                if metric == "ebit":
                    present(c, "period_start")
                    if not c["period_start"] == fixture["reference_date"][:4] + "-01-01":
                        raise AssertionError("EBIT_PERIOD")
                if fixture["issuer"]["cvm_code"] not in c["source_reference"].split("|"):
                    raise AssertionError("CVM_LOCATOR")
                total += number(c["normalized_expected_value"])
                references.append(c["source_reference"])
            equal(total, group["normalized_expected_value"], metric)
            equal(total, expected[metric], metric)
            equal(metrics[metric], expected[metric], metric)
        return references

    def securities():
        evidence = fixture["security"]
        capital = fixture["capital"]["securities"]
        if not len(evidence) == len(capital) > 0:
            raise AssertionError("SECURITY_COUNT")
        if not len({s["ticker"] for s in evidence}) == len(evidence):
            raise AssertionError("DUPLICATE_SECURITY")
        refs = []
        for s in evidence:
            present(
                s,
                "ticker",
                "share_class",
                "cnpj",
                "fca_form_id",
                "fca_source_reference",
                "valid_from",
                "security_id",
                "issuer_id",
            )
            if not s["issuer_id"] == fixture["issuer"]["issuer_id"]:
                raise AssertionError("SECURITY_ISSUER")
            if not s["cnpj"] == fixture["issuer"]["cnpj"]:
                raise AssertionError("SECURITY_CNPJ")
            parts = s["fca_source_reference"].split("|")
            if not len(parts) == 6:
                raise AssertionError("FCA_LOCATOR")
            if not "".join((c for c in parts[2] if c.isdigit())) == s["cnpj"]:
                raise AssertionError("FCA_CNPJ")
            if not (parts[4] == s["fca_form_id"] and parts[5] == s["ticker"]):
                raise AssertionError("FCA_FORM_TICKER")
            if not date.fromisoformat(parts[3]) <= date.fromisoformat(fixture["reference_date"]):
                raise AssertionError("EVIDENCE_MISMATCH")
            if not s["valid_from"] <= fixture["reference_date"]:
                raise AssertionError("SECURITY_VALID_FROM")
            if not (s.get("valid_to") is None or s["valid_to"] >= fixture["reference_date"]):
                raise AssertionError("EVIDENCE_MISMATCH")
            matches = [c for c in capital if c["security_id"] == s["security_id"]]
            if not len(matches) == 1:
                raise AssertionError("SECURITY_CAPITAL_MAPPING")
            for key in ("ticker", "share_class", "fca_source_reference", "valid_from", "valid_to"):
                if not matches[0].get(key) == s.get(key):
                    raise AssertionError(key)
            refs.append(s["fca_source_reference"])
        return refs

    def capital():
        refs = []
        caps = fixture["capital"]["securities"]
        if not len(caps) == len(components) > 0:
            raise AssertionError("CAPITAL_COMPONENT_COUNT")
        if not len({c["share_class"] for c in caps}) == len(caps):
            raise AssertionError("DUPLICATE_CLASS")
        for c in caps:
            present(
                c,
                "issued_source_reference",
                "treasury_source_reference",
                "outstanding_derivation_rule",
                "quantity_unit",
                "quantity_multiplier",
            )
            if not c["issuer_id"] == fixture["issuer"]["issuer_id"]:
                raise AssertionError("CAPITAL_ISSUER")
            if not c["reference_date"] == fixture["reference_date"]:
                raise AssertionError("CAPITAL_REFERENCE")
            if not c["quantity_unit"] == "UNIT":
                raise AssertionError("UNPROVEN_QUANTITY_UNIT")
            equal(c["quantity_multiplier"], 1, "QUANTITY_MULTIPLIER")
            if (
                not c["outstanding_derivation_rule"]
                == "OUTSTANDING = ISSUED_SHARES - TREASURY_SHARES"
            ):
                raise AssertionError("EVIDENCE_MISMATCH")
            issued, treasury = (
                number(c["issued_or_integralized_shares"]),
                number(c["treasury_shares"]),
            )
            if not 0 <= treasury <= issued:
                raise AssertionError("CAPITAL_QUANTITIES")
            equal(issued - treasury, c["outstanding_shares"], "OUTSTANDING")
            equal(c["normalized_quantity"], issued - treasury, "NORMALIZED_QUANTITY")
            if "ISSUED_SHARES" not in c["issued_source_reference"]:
                raise AssertionError("ISSUED_LOCATOR")
            if "TREASURY_SHARES" not in c["treasury_source_reference"]:
                raise AssertionError("TREASURY_LOCATOR")
            matches = [x for x in components if x["security_id"] == c["security_id"]]
            if not len(matches) == 1:
                raise AssertionError("CAPITAL_SNAPSHOT_MAPPING")
            actual = matches[0]
            for key in (
                "issued_source_reference",
                "treasury_source_reference",
                "share_class",
                "fca_source_reference",
                "reference_date",
                "quantity_unit",
            ):
                if not actual[key] == c[key]:
                    raise AssertionError(key)
            for source, target in (
                ("issued_shares", "issued_or_integralized_shares"),
                ("treasury_shares", "treasury_shares"),
                ("normalized_quantity", "normalized_quantity"),
            ):
                equal(actual[source], c[target], source)
            refs.extend((c["issued_source_reference"], c["treasury_source_reference"]))
        return refs

    def market():
        refs = []
        prices = fixture["prices"]
        if not len(prices) == len(components) > 0:
            raise AssertionError("PRICE_COUNT")
        if not len({p["ticker"] for p in prices}) == len(prices):
            raise AssertionError("DUPLICATE_PRICE")
        for p in prices:
            present(p, "record_reference", "source_file", "price", "effective_date")
            parts = p["record_reference"].split("|")
            if not (len(parts) == 6 and parts[0] == p["source_file"]):
                raise AssertionError("COTAHIST_LOCATOR")
            if not (parts[0].endswith(".ZIP") and parts[1].endswith(".TXT")):
                raise AssertionError("EVIDENCE_MISMATCH")
            if not int(parts[2].removeprefix("line=")) > 0:
                raise AssertionError("EVIDENCE_MISMATCH")
            if not parts[3] == "date=" + p["effective_date"].replace("-", ""):
                raise AssertionError("EVIDENCE_MISMATCH")
            if not parts[4] == "ticker=" + p["ticker"]:
                raise AssertionError("EVIDENCE_MISMATCH")
            equal(parts[5].removeprefix("close="), p["price"], "PRICE_LOCATOR")
            if not p["requested_reference_date"] == fixture["reference"]["market_reference_date"]:
                raise AssertionError("EVIDENCE_MISMATCH")
            gap = (
                date.fromisoformat(p["requested_reference_date"])
                - date.fromisoformat(p["effective_date"])
            ).days
            if not (0 <= gap <= 7 and number(p["price"]) > 0 and (p["currency"] == "BRL")):
                raise AssertionError("EVIDENCE_MISMATCH")
            matches = [c for c in components if c["ticker"] == p["ticker"]]
            if not len(matches) == 1:
                raise AssertionError("EVIDENCE_MISMATCH")
            actual = matches[0]
            if not actual["price_record_reference"] == p["record_reference"]:
                raise AssertionError("EVIDENCE_MISMATCH")
            if not actual["price_effective_date"] == p["effective_date"]:
                raise AssertionError("EVIDENCE_MISMATCH")
            equal(actual["price"], p["price"], "SNAPSHOT_PRICE")
            refs.append(p["record_reference"])
        return refs

    def market_cap():
        prices = {p["ticker"]: number(p["price"]) for p in fixture["prices"]}
        for c in fixture["capital"]["securities"]:
            matches = [x for x in components if x["security_id"] == c["security_id"]]
            if len(matches) != 1:
                raise AssertionError("CLASS_MARKET_CAP_MAPPING")
            actual = matches[0]
            partial = number(c["normalized_quantity"]) * prices[c["ticker"]]
            equal(
                number(actual["normalized_quantity"]) * number(actual["price"]),
                partial,
                "CLASS_MARKET_CAP",
            )
            # Earlier V2 artifacts did not store an explicit partial. When present,
            # it must agree even if errors in two classes cancel in the issuer total.
            if "partial_market_cap" in actual:
                equal(actual["partial_market_cap"], partial, "CLASS_MARKET_CAP")
        total = sum(
            (
                number(c["normalized_quantity"]) * prices[c["ticker"]]
                for c in fixture["capital"]["securities"]
            ),
            Decimal(0),
        )
        equal(total, expected["market_cap"], "EXPECTED_MARKET_CAP")
        equal(metrics["market_cap"], expected["market_cap"], "SNAPSHOT_MARKET_CAP")
        return ("SUM(normalized_quantity * official_close)",)

    def derived():
        e = {k: number(v) for k, v in expected.items()}
        identities = {
            "financial_debt_total": e["financial_debt_short_term"] + e["financial_debt_long_term"],
            "net_debt": e["financial_debt_total"] - e["cash_and_equivalents"],
            "net_working_capital": e["operating_current_assets"]
            - e["operating_current_liabilities"],
            "invested_capital": e["net_working_capital"] + e["net_fixed_assets"],
            "enterprise_value": e["market_cap"] + e["net_debt"],
            "earnings_yield": e["ebit"] / e["enterprise_value"],
            "return_on_capital": e["ebit"] / e["invested_capital"],
        }
        for key, value in identities.items():
            equal(value, e[key], key)
            if key != "financial_debt_total":
                equal(metrics[key], e[key], key)
        return tuple(identities)

    def accounting_lineage():
        refs = []
        for metric, group in fixture["accounting"].items():
            for c in group["components"]:
                hits = [
                    x
                    for x in lineage
                    if x.get("metric") == metric and x.get("account_code") == c["account_code"]
                ]
                if not len(hits) == 1:
                    raise AssertionError("LINEAGE_COMPONENT_COUNT")
                actual = hits[0]
                for source, target in (
                    ("account_description", "account_description"),
                    ("raw_value", "raw_value"),
                    ("source_reference", "source_reference"),
                    ("period_start", "period_start"),
                    ("period_end", "period_end"),
                    ("statement_scope", "statement_scope"),
                    ("currency_scale", "currency_scale"),
                    ("currency", "currency"),
                ):
                    if not actual[source] == c[target]:
                        raise AssertionError(source)
                equal(actual["multiplier"], c["normalization_multiplier"], "MULTIPLIER")
                equal(actual["normalized_value"], c["normalized_expected_value"], "COMPONENT")
                if not actual["rule_id"] == group["rule_id"]:
                    raise AssertionError("RULE_ID")
                refs.append(c["source_reference"])
        return refs

    def readback():
        if not readback_matches:
            raise AssertionError("SNAPSHOT_CHANGED_BETWEEN_SESSIONS")
        if not "validation_status" not in metrics:
            raise AssertionError("DUPLICATE_VALIDATION_STATUS")
        if not snapshot["issuer_id"] == fixture["issuer"]["issuer_id"]:
            raise AssertionError("SNAPSHOT_ISSUER")
        if not snapshot["financial_reference_date"] == fixture["reference_date"]:
            raise AssertionError("EVIDENCE_MISMATCH")
        if not snapshot["market_reference_date"] == fixture["reference"]["market_reference_date"]:
            raise AssertionError("EVIDENCE_MISMATCH")
        if not snapshot["adapter_version"] == fixture["reference"]["adapter_version"]:
            raise AssertionError("EVIDENCE_MISMATCH")
        if not snapshot["methodology_version"] == fixture["methodology_version"]:
            raise AssertionError("EVIDENCE_MISMATCH")
        return ("CLOSED_AND_REOPENED:" + snapshot["id"],)

    for dimension, operation in zip(
        DIMENSIONS,
        (
            accounting,
            securities,
            capital,
            market,
            market_cap,
            derived,
            accounting_lineage,
            readback,
        ),
        strict=True,
    ):
        check(dimension, operation)
    return tuple(decisions)
