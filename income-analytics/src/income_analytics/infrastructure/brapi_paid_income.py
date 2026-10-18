"""BRAPI adapter for historical paid-income records."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from income_analytics.application.paid_income import (
    IncomeType,
    PaidIncomeEvent,
    PaidIncomeIntegrationStatus,
    PaidIncomeProviderResponse,
)


class BrapiPaidIncomeProvider:
    endpoint = "https://brapi.dev/api/quote/{ticker}"

    def __init__(self, token: str, timeout_seconds: float = 20) -> None:
        self._token = token
        self._timeout_seconds = timeout_seconds

    def get_paid_income(
        self, ticker: str, start_date: date, end_date: date
    ) -> PaidIncomeProviderResponse:
        params = urlencode({"range": "2y", "fundamental": "true", "dividends": "true"})
        url = f"{self.endpoint.format(ticker=ticker.upper())}?{params}"
        try:
            with urlopen(
                Request(
                    url,
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self._token}",
                    },
                ),
                timeout=self._timeout_seconds,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
            items = payload["results"][0]["dividendsData"]["cashDividends"]
            events = tuple(
                event
                for item in items
                if (event := normalize_event(ticker, item))
                and event.payment_date
                and start_date <= event.payment_date <= end_date
            )
            return PaidIncomeProviderResponse(PaidIncomeIntegrationStatus.CONNECTED, events)
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            state = {
                401: PaidIncomeIntegrationStatus.AUTH_ERROR,
                429: PaidIncomeIntegrationStatus.RATE_LIMITED,
            }.get(error.code, PaidIncomeIntegrationStatus.PROVIDER_ERROR)
            if error.code == 403 or (error.code == 400 and "requiredPlan" in body):
                state = PaidIncomeIntegrationStatus.PLAN_NOT_SUPPORTED
            return PaidIncomeProviderResponse(state, detail="BRAPI rejected the request.")
        except URLError, KeyError, IndexError, TypeError, ValueError, InvalidOperation:
            return PaidIncomeProviderResponse(
                PaidIncomeIntegrationStatus.PROVIDER_ERROR, detail="BRAPI payload or network error."
            )


def normalize_event(ticker: str, item: dict[str, object]) -> PaidIncomeEvent | None:
    payment = _date(item.get("paymentDate"))
    amount = _decimal(item.get("rate"))
    if payment is None or amount is None:
        return None
    kind = {
        "DIVIDENDO": IncomeType.DIVIDEND,
        "JCP": IncomeType.JCP,
        "RENDIMENTO": IncomeType.FII_INCOME,
    }.get(str(item.get("label", "")).upper(), IncomeType.OTHER)
    return PaidIncomeEvent(
        ticker.upper(),
        kind,
        amount,
        _date(item.get("lastDatePrior")),
        payment,
        _date(item.get("approvedOn")),
        "BRAPI",
        str(item.get("isinCode")) if item.get("isinCode") else None,
    )


def _date(value: object) -> date | None:
    return date.fromisoformat(str(value)[:10]) if value else None


def _decimal(value: object) -> Decimal | None:
    try:
        return Decimal(str(value)) if value is not None else None
    except InvalidOperation:
        return None
