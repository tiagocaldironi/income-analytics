from datetime import date
from pathlib import Path

from spikes.paid_income.models import QueryResult
from spikes.paid_income_b3_cvm.provider import CvmFiiMonthlyProvider


def test_cvm_monthly_parser_reads_yield_but_not_paid_income_event(tmp_path) -> None:
    year = tmp_path / "2026"
    year.mkdir()
    (year / "inf_mensal_fii_complemento_2026.csv").write_text(
        "CNPJ_Fundo_Classe;Data_Referencia;Percentual_Dividend_Yield_Mes;Percentual_Amortizacao_Cotas_Mes\n"
        "26.614.291/0001-00;2026-07-01;0.01354704;0\n",
        encoding="utf-8",
    )
    provider = CvmFiiMonthlyProvider(tmp_path)

    evidence = provider.monthly_evidence("GGRC11", date(2026, 1, 1), date(2026, 12, 31))
    response = provider.get_paid_income("GGRC11", date(2026, 1, 1), date(2026, 12, 31))

    assert len(evidence) == 1
    assert str(evidence[0].dividend_yield_month) == "0.01354704"
    assert response.result is QueryResult.INVALID_PAYLOAD
    assert response.events == ()
    assert "data de pagamento" in response.detail


def test_cvm_monthly_parser_returns_no_evidence_for_stock() -> None:
    provider = CvmFiiMonthlyProvider(Path("."))

    assert provider.monthly_evidence("PETR4", date(2026, 1, 1), date(2026, 12, 31)) == ()
