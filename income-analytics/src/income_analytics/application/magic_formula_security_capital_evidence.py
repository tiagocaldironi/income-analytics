"""Independent security and capital evidence for Magic Formula golden cases.

This module deliberately does not calculate market capitalization and does not
promote issuers.  It converts only explicit FCA and DFP capital-composition
records into an auditable bundle.  A caller must supply the security identity
and the quantity-unit evidence; neither is inferred from a company name or a
ticker suffix.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from io import TextIOWrapper
from zipfile import ZipFile

from income_analytics.infrastructure.cvm_capital_structure import CvmCapitalComposition
from income_analytics.infrastructure.cvm_fundamentals_data import CvmDataset


class SecurityCapitalEvidenceStatus(StrEnum):
    RESOLVED = "RESOLVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class IssuerEvidenceIdentity:
    issuer_id: str
    cvm_code: str
    cnpj: str


@dataclass(frozen=True, slots=True)
class FcaSecurityRecord:
    cnpj: str
    reference_date: date
    form_version: str
    form_id: str
    ticker: str
    preferred_share_class: str
    security_type: str
    valid_from: date | None
    valid_to: date | None
    source_file: str
    source_reference: str


@dataclass(frozen=True, slots=True)
class SecurityClassEvidenceRequest:
    """A verified issuer -> FCA security -> DFP capital-class mapping.

    ``share_class`` must be the class in the DFP capital-composition statement
    (currently ``ON`` or ``PN``).  It is intentionally explicit so PN variants
    and units cannot be guessed from a ticker.
    """

    security_id: str
    ticker: str
    share_class: str
    quantity_unit: str | None
    quantity_multiplier: Decimal | None


@dataclass(frozen=True, slots=True)
class ShareClassCapitalEvidence:
    issuer_id: str
    cvm_code: str
    security_id: str
    ticker: str
    share_class: str
    issued_shares: Decimal
    treasury_shares: Decimal
    outstanding_shares: Decimal
    quantity_unit: str
    quantity_multiplier: Decimal
    normalized_quantity: Decimal
    reference_date: date
    source: str
    source_reference: str
    issued_source_reference: str
    treasury_source_reference: str
    outstanding_derivation_rule: str
    fca_source: str
    fca_source_reference: str
    fca_form_id: str
    fca_valid_from: date | None
    fca_valid_to: date | None


@dataclass(frozen=True, slots=True)
class SecurityCapitalEvidenceBundle:
    issuer_id: str
    status: SecurityCapitalEvidenceStatus
    components: tuple[ShareClassCapitalEvidence, ...]
    review_reasons: tuple[str, ...]


class CvmFcaSecurityParser:
    """Parse CVM FCA security records with deterministic raw-record references."""

    filename_fragment = "fca_cia_aberta_valor_mobiliario_"
    required = {
        "CNPJ_Companhia",
        "Data_Referencia",
        "Versao",
        "ID_Documento",
        "Valor_Mobiliario",
        "Sigla_Classe_Acao_Preferencial",
        "Codigo_Negociacao",
        "Data_Inicio_Negociacao",
        "Data_Fim_Negociacao",
    }

    def parse(self, dataset: CvmDataset) -> tuple[FcaSecurityRecord, ...]:
        if dataset.statement_type != "FCA":
            raise ValueError("FCA oficial é obrigatória para a identidade de security.")
        with ZipFile(__import__("io").BytesIO(dataset.payload)) as archive:
            name = next(
                (item for item in archive.namelist() if self.filename_fragment in item.casefold()),
                None,
            )
            if name is None:
                raise ValueError("SOURCE_SCHEMA_ERROR: valor mobiliário FCA ausente.")
            with archive.open(name) as raw:
                reader = csv.DictReader(TextIOWrapper(raw, encoding="latin-1"), delimiter=";")
                if not reader.fieldnames or not self.required.issubset(reader.fieldnames):
                    raise ValueError("SOURCE_SCHEMA_ERROR: colunas FCA ausentes.")
                records: list[FcaSecurityRecord] = []
                for row in reader:
                    ticker = (row["Codigo_Negociacao"] or "").strip().upper()
                    if not ticker:
                        continue
                    reference = self._date(row["Data_Referencia"], "Data_Referencia")
                    form_id = (row["ID_Documento"] or "").strip()
                    record_reference = "|".join(
                        (
                            dataset.source_file,
                            name,
                            row["CNPJ_Companhia"],
                            str(reference),
                            form_id,
                            ticker,
                        )
                    )
                    records.append(
                        FcaSecurityRecord(
                            cnpj=row["CNPJ_Companhia"],
                            reference_date=reference,
                            form_version=(row["Versao"] or "").strip(),
                            form_id=form_id,
                            ticker=ticker,
                            preferred_share_class=(row["Sigla_Classe_Acao_Preferencial"] or "")
                            .strip()
                            .upper(),
                            security_type=(row["Valor_Mobiliario"] or "").strip(),
                            valid_from=self._optional_date(row["Data_Inicio_Negociacao"]),
                            valid_to=self._optional_date(row["Data_Fim_Negociacao"]),
                            source_file=dataset.source_file,
                            source_reference=record_reference,
                        )
                    )
                return tuple(records)

    @staticmethod
    def _date(value: str, field: str) -> date:
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"SOURCE_SCHEMA_ERROR: {field} FCA inválida.") from error

    @classmethod
    def _optional_date(cls, value: str | None) -> date | None:
        return None if not value else cls._date(value, "data FCA")


class SecurityCapitalEvidenceAssembler:
    """Materialize evidence only when raw FCA/DFP identity and units are proven."""

    def build(
        self,
        *,
        issuer: IssuerEvidenceIdentity,
        composition: CvmCapitalComposition | None,
        fca_records: tuple[FcaSecurityRecord, ...],
        requests: tuple[SecurityClassEvidenceRequest, ...],
    ) -> SecurityCapitalEvidenceBundle:
        reasons: list[str] = []
        if composition is None:
            reasons.append("CAPITAL_COMPOSITION_MISSING")
        elif self._digits(composition.cnpj) != self._digits(issuer.cnpj):
            reasons.append("CAPITAL_COMPOSITION_ISSUER_MISMATCH")
        if not requests:
            reasons.append("SECURITY_MAPPING_MISSING")
        if reasons:
            return SecurityCapitalEvidenceBundle(
                issuer.issuer_id, SecurityCapitalEvidenceStatus.REVIEW_REQUIRED, (), tuple(reasons)
            )

        assert composition is not None
        classes = {
            "ON": (composition.ordinary_issued, composition.ordinary_treasury),
            "PN": (composition.preferred_issued, composition.preferred_treasury),
        }
        components: list[ShareClassCapitalEvidence] = []
        seen_classes: set[str] = set()
        for request in requests:
            if request.share_class not in classes:
                reasons.append(f"UNSUPPORTED_SHARE_CLASS:{request.share_class}")
                continue
            if request.share_class in seen_classes:
                reasons.append(f"DUPLICATE_SHARE_CLASS:{request.share_class}")
                continue
            seen_classes.add(request.share_class)
            if (
                not request.quantity_unit
                or request.quantity_multiplier is None
                or request.quantity_multiplier <= 0
            ):
                reasons.append(f"UNIT_UNRESOLVED:{request.ticker}")
                continue
            security = self._single_active_security(
                issuer=issuer,
                ticker=request.ticker,
                reference_date=date.fromisoformat(composition.reference_date),
                fca_records=fca_records,
            )
            if security is None:
                reasons.append(f"SECURITY_UNRESOLVED:{request.ticker}")
                continue
            if not self._security_matches_capital_class(security, request.share_class):
                reasons.append(f"SECURITY_CLASS_UNRESOLVED:{request.ticker}")
                continue
            issued, treasury = classes[request.share_class]
            if issued < 0 or treasury < 0 or treasury > issued:
                reasons.append(f"CAPITAL_QUANTITY_INVALID:{request.share_class}")
                continue
            outstanding = issued - treasury
            components.append(
                ShareClassCapitalEvidence(
                    issuer_id=issuer.issuer_id,
                    cvm_code=issuer.cvm_code,
                    security_id=request.security_id,
                    ticker=request.ticker.upper(),
                    share_class=request.share_class,
                    issued_shares=issued,
                    treasury_shares=treasury,
                    outstanding_shares=outstanding,
                    quantity_unit=request.quantity_unit,
                    quantity_multiplier=request.quantity_multiplier,
                    normalized_quantity=outstanding * request.quantity_multiplier,
                    reference_date=date.fromisoformat(composition.reference_date),
                    source="CVM_DFP_COMPOSICAO_CAPITAL",
                    source_reference=self._capital_reference(
                        composition, request.share_class, "OUTSTANDING_SHARES"
                    ),
                    issued_source_reference=self._capital_reference(
                        composition, request.share_class, "ISSUED_SHARES"
                    ),
                    treasury_source_reference=self._capital_reference(
                        composition, request.share_class, "TREASURY_SHARES"
                    ),
                    outstanding_derivation_rule="OUTSTANDING = ISSUED_SHARES - TREASURY_SHARES",
                    fca_source="CVM_FCA",
                    fca_source_reference=security.source_reference,
                    fca_form_id=security.form_id,
                    fca_valid_from=security.valid_from,
                    fca_valid_to=security.valid_to,
                )
            )

        required_classes = {name for name, values in classes.items() if values[0] > 0}
        if seen_classes != required_classes:
            reasons.append("CAPITAL_CLASS_MAPPING_INCOMPLETE")
        status = (
            SecurityCapitalEvidenceStatus.RESOLVED
            if not reasons
            else SecurityCapitalEvidenceStatus.REVIEW_REQUIRED
        )
        resolved_components = (
            tuple(components) if status is SecurityCapitalEvidenceStatus.RESOLVED else ()
        )
        return SecurityCapitalEvidenceBundle(
            issuer.issuer_id, status, resolved_components, tuple(reasons)
        )

    @classmethod
    def _single_active_security(
        cls,
        *,
        issuer: IssuerEvidenceIdentity,
        ticker: str,
        reference_date: date,
        fca_records: tuple[FcaSecurityRecord, ...],
    ) -> FcaSecurityRecord | None:
        matches = [
            item
            for item in fca_records
            if cls._digits(item.cnpj) == cls._digits(issuer.cnpj)
            and item.ticker == ticker.upper()
            and item.reference_date <= reference_date
            and (item.valid_from is None or item.valid_from <= reference_date)
            and (item.valid_to is None or item.valid_to >= reference_date)
        ]
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _digits(value: str) -> str:
        return "".join(character for character in value if character.isdigit())

    @staticmethod
    def _security_matches_capital_class(security: FcaSecurityRecord, share_class: str) -> bool:
        descriptor = security.security_type.casefold()
        if share_class == "ON":
            return "ordin" in descriptor
        if share_class == "PN":
            return "prefer" in descriptor or security.preferred_share_class.startswith("PN")
        return False

    @staticmethod
    def _capital_reference(
        composition: CvmCapitalComposition, share_class: str, record_type: str
    ) -> str:
        """Stable raw-column locator; distinct for class and issued/treasury semantics."""
        column = {
            ("ON", "ISSUED_SHARES"): "QT_ACAO_ORDIN_CAP_INTEGR",
            ("ON", "TREASURY_SHARES"): "QT_ACAO_ORDIN_TESOURO",
            ("PN", "ISSUED_SHARES"): "QT_ACAO_PREF_CAP_INTEGR",
            ("PN", "TREASURY_SHARES"): "QT_ACAO_PREF_TESOURO",
        }.get((share_class, record_type), "DERIVED_OUTSTANDING")
        return "|".join(
            (
                composition.source_reference,
                composition.cnpj,
                composition.reference_date,
                share_class,
                record_type,
                column,
            )
        )
