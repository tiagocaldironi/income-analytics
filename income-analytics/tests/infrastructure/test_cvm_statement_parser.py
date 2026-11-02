"""Synthetic, in-memory coverage of the CVM source-schema boundary."""

import runpy
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from income_analytics.application.cvm_magic_formula_normalization import CvmRawAccount
from income_analytics.infrastructure.cvm_fundamentals_data import (
    CvmDataset,
    CvmSourceSchemaError,
    CvmStatementParser,
)

MEMBER = "dfp_cia_aberta_DRE_con_2025.csv"
HEADER = (
    "CD_CVM",
    "DT_REFER",
    "ORDEM_EXERC",
    "ESCALA_MOEDA",
    "CD_CONTA",
    "DS_CONTA",
    "VL_CONTA",
)


def dataset(csv: str, kind: str = "DFP") -> CvmDataset:
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr(MEMBER, csv.encode("latin-1"))
    return CvmDataset(kind, "synthetic.zip", datetime(2026, 1, 1, tzinfo=UTC), payload.getvalue())


@pytest.mark.parametrize("missing", HEADER)
def test_missing_required_column_raises_source_schema_error(missing: str) -> None:
    csv = ";".join(column for column in HEADER if column != missing) + "\n"
    with pytest.raises(CvmSourceSchemaError) as caught:
        CvmStatementParser().parse(dataset(csv))
    assert caught.value.code == "SOURCE_SCHEMA_ERROR"
    assert str(caught.value) == f"SOURCE_SCHEMA_ERROR: colunas ausentes em {MEMBER}."
    assert isinstance(caught.value, ValueError)


def test_empty_csv_raises_source_schema_error() -> None:
    with pytest.raises(CvmSourceSchemaError, match="SOURCE_SCHEMA_ERROR: colunas ausentes"):
        CvmStatementParser().parse(dataset(""))


@pytest.mark.parametrize(
    "script,entrypoint",
    [
        ("rematerialize_magic_formula_v2.py", "run"),
        ("recover_petrobras_canonical.py", "build_evidence"),
    ],
)
def test_consumers_propagate_schema_error_before_persistence(
    monkeypatch: pytest.MonkeyPatch, script: str, entrypoint: str
) -> None:
    root = Path(__file__).resolve().parents[2]
    consumer = runpy.run_path(str(root / "scripts" / script))[entrypoint]
    invalid = dataset("COLUNA_INCOMPATIVEL\n")
    monkeypatch.setitem(consumer.__globals__, "dataset", lambda *args: invalid)

    def forbidden_repository(*args: object, **kwargs: object) -> None:
        pytest.fail("Invalid schema must stop before repository construction")

    monkeypatch.setitem(
        consumer.__globals__, "SqliteMagicFormulaSnapshotRepository", forbidden_repository
    )
    with pytest.raises(CvmSourceSchemaError) as caught:
        if entrypoint == "run":
            consumer()
        else:
            consumer({}, Path("unused-cvm"), Path("unused-market"))
    assert str(caught.value) == f"SOURCE_SCHEMA_ERROR: colunas ausentes em {MEMBER}."


@pytest.mark.parametrize("kind", ["DFP", "ITR"])
def test_valid_csv_preserves_raw_account_contract(kind: str) -> None:
    csv = ";".join(HEADER) + "\n123;2025-12-31;ÚLTIMO;MIL;3.05;Resultado;123,45\n"
    assert CvmStatementParser().parse(dataset(csv, kind)) == (
        CvmRawAccount(
            "123",
            "123",
            "2025-12-31",
            kind,
            "CONSOLIDATED",
            "DRE",
            "3.05",
            "Resultado",
            Decimal("123.45"),
            "synthetic.zip",
            None,
            "2025-12-31",
            "BRL",
            "MIL",
            None,
        ),
    )
