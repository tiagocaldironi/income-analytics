"""Required-section gate for independent Magic Formula golden evidence."""

from dataclasses import dataclass

from income_analytics.application.magic_formula_contract import golden_contract_errors


@dataclass(frozen=True, slots=True)
class LineageGateResult:
    complete: bool
    missing: tuple[str, ...]
    status: str


class MagicFormulaLineageGate:
    required_sections = ("accounting", "security", "capital", "prices", "expected")

    def evaluate(self, fixture: dict[str, object]) -> LineageGateResult:
        missing = golden_contract_errors(fixture)
        return LineageGateResult(
            complete=not missing,
            missing=missing,
            status="PASS" if not missing else "REVIEW_REQUIRED",
        )
