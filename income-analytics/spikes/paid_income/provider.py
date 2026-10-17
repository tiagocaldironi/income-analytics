# ruff: noqa: E501
from __future__ import annotations

import json
import os
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import IncomeType, PaidIncomeEvent, ProviderResponse, QueryResult


class PaidIncomeProvider(Protocol):
    def get_paid_income(self, ticker: str, start_date: date, end_date: date) -> ProviderResponse: ...


class BrapiPaidIncomeProvider:
    endpoint = "https://brapi.dev/api/quote/{ticker}"

    def __init__(self, *, token: str | None = None, timeout_seconds: float = 20) -> None:
        self._token = token or os.getenv("BRAPI_TOKEN")
        self._timeout_seconds = timeout_seconds

    def get_paid_income(self, ticker: str, start_date: date, end_date: date) -> ProviderResponse:
        started = time.monotonic()
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        url = f"{self.endpoint.format(ticker=ticker.upper())}?{urlencode({'range': '2y', 'interval': '1d', 'fundamental': 'true', 'dividends': 'true'})}"
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
                status = response.status
            records = payload["results"][0]["dividendsData"]["cashDividends"]
            events = tuple(
                event for item in records
                if (event := normalize_event(ticker, item)) is not None
                and start_date <= event.payment_date <= end_date
            )
            return ProviderResponse(QueryResult.SUCCESS if events else QueryResult.NO_EVENTS, status, _elapsed(started), events)
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            result = {
                401: QueryResult.AUTH_REQUIRED,
                403: QueryResult.PLAN_LIMITATION,
                404: QueryResult.UNSUPPORTED_TICKER,
                429: QueryResult.RATE_LIMIT,
            }.get(error.code, QueryResult.PROVIDER_ERROR)
            if error.code == 400 and "requiredPlan" in body:
                result = QueryResult.PLAN_LIMITATION
            return ProviderResponse(result, error.code, _elapsed(started), detail=body[:500])
        except URLError as error:
            return ProviderResponse(QueryResult.NETWORK_ERROR, None, _elapsed(started), detail=str(error))
        except (KeyError, IndexError, TypeError, ValueError, InvalidOperation) as error:
            return ProviderResponse(QueryResult.INVALID_PAYLOAD, status if 'status' in locals() else None, _elapsed(started), detail=str(error))


def normalize_event(ticker: str, item: dict[str, object]) -> PaidIncomeEvent | None:
    payment = parse_date(item.get("paymentDate"))
    amount = parse_decimal(item.get("rate"))
    if payment is None or amount is None:
        return None
    label = str(item.get("label", "")).upper()
    income_type = {"DIVIDENDO": IncomeType.DIVIDEND, "JCP": IncomeType.JCP, "RENDIMENTO": IncomeType.FII_INCOME}.get(label, IncomeType.OTHER)
    return PaidIncomeEvent(ticker.upper(), income_type, amount, parse_date(item.get("lastDatePrior")), payment, parse_date(item.get("approvedOn")), "brapi", str(item.get("isinCode")) if item.get("isinCode") else None)


def parse_date(value: object) -> date | None:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date() if value else None


def parse_decimal(value: object) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _elapsed(started: float) -> int:
    return round((time.monotonic() - started) * 1000)
