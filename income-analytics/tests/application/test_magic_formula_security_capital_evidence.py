from datetime import UTC, date, datetime
from decimal import Decimal

from income_analytics.application.magic_formula_security_capital_evidence import (
    CvmFcaSecurityParser,
    FcaSecurityRecord,
    IssuerEvidenceIdentity,
    SecurityCapitalEvidenceAssembler,
    SecurityCapitalEvidenceStatus,
    SecurityClassEvidenceRequest,
)
from income_analytics.infrastructure.cvm_capital_structure import CvmCapitalComposition
from income_analytics.infrastructure.cvm_fundamentals_data import CvmDataset


def _composition() -> CvmCapitalComposition:
    return CvmCapitalComposition(
        "12.345.678/0001-90",
        "Companhia Teste",
        "2025-12-31",
        Decimal("100"),
        Decimal("0"),
        Decimal("2"),
        Decimal("0"),
        "dfp.zip:dfp_cia_aberta_composicao_capital_2025.csv",
    )


def _fca() -> tuple[FcaSecurityRecord, ...]:
    return (
        FcaSecurityRecord(
            "12345678000190",
            date(2025, 12, 31),
            "1",
            "999",
            "TEST3",
            "",
            "Ações Ordinárias",
            date(2020, 1, 1),
            None,
            "fca.zip",
            "fca.zip|fca_cia_aberta_valor_mobiliario_2025.csv|12345678000190|2025-12-31|999|TEST3",
        ),
    )


def _issuer() -> IssuerEvidenceIdentity:
    return IssuerEvidenceIdentity("teste", "12345", "12.345.678/0001-90")


def test_sec_evid_builds_complete_on_component_with_deterministic_references() -> None:
    bundle = SecurityCapitalEvidenceAssembler().build(
        issuer=_issuer(),
        composition=_composition(),
        fca_records=_fca(),
        requests=(SecurityClassEvidenceRequest("teste-on", "TEST3", "ON", "SHARES", Decimal("1")),),
    )

    assert bundle.status is SecurityCapitalEvidenceStatus.RESOLVED
    component = bundle.components[0]
    assert component.issued_shares == Decimal("100")
    assert component.treasury_shares == Decimal("2")
    assert component.outstanding_shares == Decimal("98")
    assert component.normalized_quantity == Decimal("98")
    assert "|ON|OUTSTANDING_SHARES|DERIVED_OUTSTANDING" in component.source_reference
    assert "|ON|ISSUED_SHARES|QT_ACAO_ORDIN_CAP_INTEGR" in component.issued_source_reference
    assert "|ON|TREASURY_SHARES|QT_ACAO_ORDIN_TESOURO" in component.treasury_source_reference
    assert component.fca_source_reference.endswith("|999|TEST3")


def test_sec_evid_requires_explicit_quantity_unit_evidence() -> None:
    bundle = SecurityCapitalEvidenceAssembler().build(
        issuer=_issuer(),
        composition=_composition(),
        fca_records=_fca(),
        requests=(SecurityClassEvidenceRequest("teste-on", "TEST3", "ON", None, None),),
    )

    assert bundle.status is SecurityCapitalEvidenceStatus.REVIEW_REQUIRED
    assert bundle.components == ()
    assert "UNIT_UNRESOLVED:TEST3" in bundle.review_reasons


def test_sec_evid_requires_unique_active_fca_security_identity() -> None:
    duplicate = _fca()[0].__class__(
        **{field: getattr(_fca()[0], field) for field in _fca()[0].__dataclass_fields__}
    )
    bundle = SecurityCapitalEvidenceAssembler().build(
        issuer=_issuer(),
        composition=_composition(),
        fca_records=(_fca()[0], duplicate),
        requests=(SecurityClassEvidenceRequest("teste-on", "TEST3", "ON", "SHARES", Decimal("1")),),
    )

    assert bundle.status is SecurityCapitalEvidenceStatus.REVIEW_REQUIRED
    assert "SECURITY_UNRESOLVED:TEST3" in bundle.review_reasons


def test_sec_evid_parser_keeps_source_record_reference() -> None:
    payload = (
        "CNPJ_Companhia;Data_Referencia;Versao;ID_Documento;Nome_Empresarial;"
        "Valor_Mobiliario;Sigla_Classe_Acao_Preferencial;Classe_Acao_Preferencial;"
        "Codigo_Negociacao;Composicao_BDR_Unit;Mercado;Sigla_Entidade_Administradora;"
        "Entidade_Administradora;Data_Inicio_Negociacao;Data_Fim_Negociacao;Segmento;"
        "Data_Inicio_Listagem;Data_Fim_Listagem\n"
        "12345678000190;2025-12-31;1;999;Teste;Acao Ordinaria;;;TEST3;;;;;2020-01-01;;;\n"
    ).encode("latin-1")
    import io
    from zipfile import ZipFile

    archive = io.BytesIO()
    with ZipFile(archive, "w") as zipped:
        zipped.writestr("fca_cia_aberta_valor_mobiliario_2025.csv", payload)
    records = CvmFcaSecurityParser().parse(
        CvmDataset("FCA", "fca_cia_aberta_2025.zip", datetime.now(UTC), archive.getvalue())
    )

    assert records[0].ticker == "TEST3"
    assert records[0].source_reference.endswith("|999|TEST3")
