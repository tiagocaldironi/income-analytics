"""Brapi adapter that normalizes public instrument search results."""

from __future__ import annotations

import json
import os
import unicodedata
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from income_analytics.application.asset_discovery import AssetCandidate, AssetDiscoveryUnavailable
from income_analytics.domain.enums.asset_class import AssetClass


class BrapiAssetDiscoveryProvider:
    base_url = "https://brapi.dev/api/v2/tickers"

    def __init__(self, *, token: str | None = None, timeout_seconds: float = 5) -> None:
        self._token = token or os.getenv("BRAPI_TOKEN")
        self._timeout_seconds = timeout_seconds

    def search(self, query: str, *, limit: int = 8) -> tuple[AssetCandidate, ...]:
        params = urlencode({"search": query.strip(), "limit": limit})
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            request = Request(f"{self.base_url}?{params}", headers=headers)
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, ValueError) as error:
            raise AssetDiscoveryUnavailable("Busca pública indisponível no momento.") from error
        results = payload.get("results", [])
        candidates = (self._candidate(item) for item in results if item.get("symbol"))
        return tuple(candidate for candidate in candidates if candidate is not None)[:limit]

    @staticmethod
    def _candidate(item: dict[str, object]) -> AssetCandidate | None:
        symbol = str(item.get("symbol", "")).strip().upper()
        name = str(item.get("longName") or item.get("name") or "").strip()
        if not symbol or not name:
            return None
        instrument_type = str(item.get("assetType", "")).strip() or None
        subtype = BrapiAssetDiscoveryProvider._normalized_metadata(item.get("subType"))
        asset_type = BrapiAssetDiscoveryProvider._normalized_metadata(item.get("assetType"))
        provider_name = BrapiAssetDiscoveryProvider._normalized_metadata(name)
        asset_class = (
            AssetClass.FII
            if (
                subtype == "fii"
                or "fiagro" in subtype
                or "fiagro" in asset_type
                or "fiagro" in provider_name
                or "figaro imobiliario" in provider_name
                or "direitos creditorios de infraestrutura" in provider_name
            )
            else (
                AssetClass.BRAZILIAN_ETF
                if (
                    "etf" in subtype
                    or "etf" in asset_type
                    or "fundo de indice" in subtype
                    or "fundo de indice" in asset_type
                    or "fundo de indice" in provider_name
                )
                else AssetClass.BRAZILIAN_STOCK
            )
        )
        return AssetCandidate(
            external_id=symbol,
            symbol=symbol,
            name=name,
            instrument_type=instrument_type,
            suggested_asset_class=asset_class,
            country="BR",
            currency_code="BRL",
            sector=str(item.get("sector", "")).strip() or None,
            source="brapi",
        )

    @staticmethod
    def _normalized_metadata(value: object) -> str:
        """Normalize provider metadata only; ticker text is never classified."""
        return (
            unicodedata.normalize("NFKD", str(value or ""))
            .encode("ascii", "ignore")
            .decode()
            .casefold()
            .strip()
        )
