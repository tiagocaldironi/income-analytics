"""Independent complete annual-archive scan for historical-price absence evidence."""

import hashlib
from collections import defaultdict
from datetime import date
from decimal import Decimal
from zipfile import ZipFile


def scan_archive(path, tickers):
    rows = defaultdict(list)
    with ZipFile(path) as archive:
        members = [n for n in archive.namelist() if n.upper().endswith(".TXT")]
        if len(members) != 1:
            raise ValueError("AMBIGUOUS_COTAHIST_MEMBER")
        member = members[0]
        with archive.open(member) as stream:
            for line_number, raw in enumerate(stream, 1):
                if raw[:2] != b"01":
                    continue
                ticker = raw[12:24].decode("latin1").strip()
                if ticker not in tickers:
                    continue
                rows[ticker].append(
                    dict(
                        ticker=ticker,
                        effective_date=date.fromisoformat(raw[2:10].decode()).isoformat(),
                        raw_price=raw[108:121].decode(),
                        price=str(Decimal(raw[108:121].decode()) / Decimal(100)),
                        currency=raw[52:56].decode().strip(),
                        market=raw[24:27].decode(),
                        isin=raw[230:242].decode().strip(),
                        source_reference=f"{path.name}|{member}|line={line_number}",
                    )
                )
    return dict(rows), dict(
        file=path.name,
        member=member,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        scan_complete=True,
        requested_tickers=sorted(tickers),
    )
