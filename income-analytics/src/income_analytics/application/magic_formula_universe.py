"""Issuer-level universe policy. Readiness is independent of methodology eligibility."""

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import NAMESPACE_URL, uuid5

from income_analytics.application.cvm_magic_formula_normalization import RULES
from income_analytics.application.magic_formula_contract import canonical_identity, digest
from income_analytics.application.monetary_amount import CurrencyScale, MonetaryScaleNormalizer

UNIVERSE_POLICY_VERSION = "MAGIC_FORMULA_UNIVERSE_CVM_FCA_V1"
FINANCIAL_SECTORS = {
    "Bancos",
    "Seguradoras e Corretoras",
    "Intermediação Financeira",
    "Crédito Imobiliário",
    "Arrendamento Mercantil",
    "Securitização de Recebíveis",
}
NON_FINANCIAL_SECTORS = {
    "Energia Elétrica",
    "Alimentos",
    "Telecomunicações",
    "Serviços Transporte e Logística",
    "Extração Mineral",
    "Comércio (Atacado e Varejo)",
    "Hospedagem e Turismo",
    "Construção Civil, Mat. Constr. e Decoração",
    "Const. Civil, Mat. Const. e Decoração",
    "Saneamento, Serv. Água e Gás",
    "Educação",
    "Máquinas, Equipamentos, Veículos e Peças",
    "Máqs., Equip., Veíc. e Peças",
    "Comunicação e Informática",
    "Serviços médicos",
    "Agricultura (Açúcar, Álcool e Cana)",
    "Brinquedos e Lazer",
    "Farmacêutico e Higiene",
    "Petróleo e Gás",
    "Têxtil e Vestuário",
    "Petroquímicos e Borracha",
    "Papel e Celulose",
    "Bebidas e Fumo",
    "Metalurgia e Siderurgia",
    "Embalagens",
    "Reflorestamento",
}
SHARE_TYPES = {"Ações Ordinárias": "ON", "Ações Preferenciais": "PN", "Units": "UNIT"}


def digits(value):
    return "".join(c for c in str(value) if c.isdigit())


def decimal_or_none(value):
    try:
        result = Decimal(str(value).replace(",", "."))
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def valid_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError, TypeError:
        return None


def discover_candidates(general_rows, security_rows, reference):
    """CVM issuers with B3 exchange equity/units evidence valid at the reference.

    Unknown validity/identity is retained for review, rather than silently included as ready.
    Debt-only and conclusively ended/future listings are outside this source universe.
    """
    grouped, discarded = defaultdict(list), Counter()
    for row in security_rows:
        if (
            row["Valor_Mobiliario"] not in SHARE_TYPES
            or row["Sigla_Entidade_Administradora"] != "B3"
            or row["Mercado"] != "Bolsa"
        ):
            discarded["NOT_B3_EXCHANGE_EQUITY"] += 1
            continue
        if row["Data_Referencia"] and row["Data_Referencia"] > reference:
            discarded["FUTURE_FORM"] += 1
            continue
        start, end = row["Data_Inicio_Negociacao"], row["Data_Fim_Negociacao"]
        if (valid_date(start) and start > reference) or (valid_date(end) and end < reference):
            discarded["OUTSIDE_SECURITY_VALIDITY"] += 1
            continue
        cnpj = digits(row["CNPJ_Companhia"])
        # Missing identity has its own unresolved candidate, never a fabricated company ID.
        key = cnpj if len(cnpj) == 14 else "UNRESOLVED:" + digest(row)
        grouped[key].append(row)
    general = defaultdict(list)
    for row in general_rows:
        if row["Data_Referencia"] and row["Data_Referencia"] <= reference:
            general[digits(row["CNPJ_Companhia"])].append(row)
    result = []
    for key, securities in sorted(grouped.items()):
        rows = general.get(key, [])
        # A version is selected only within a reference date; competing identities stay ambiguous.
        identities = {(r["Codigo_CVM"], digits(r["CNPJ_Companhia"])) for r in rows}
        if rows:
            newest = max((r["Data_Referencia"], int(r["Versao"])) for r in rows)
            rows = [r for r in rows if (r["Data_Referencia"], int(r["Versao"])) == newest]
        result.append(
            dict(
                candidate_key=key,
                general=sorted(rows, key=digest),
                identity_ambiguous=len(identities) != 1,
                raw_securities=sorted(securities, key=digest),
            )
        )
    return result, dict(sorted(discarded.items()))


def classify_candidates(candidates, canonical, reference):
    result = []
    for candidate in candidates:
        rows = candidate["general"]
        record = rows[0] if len(rows) == 1 else {}
        sector = record.get("Setor_Atividade")
        base_sector = (sector or "").removeprefix("Emp. Adm. Part. - ")
        if base_sector in FINANCIAL_SECTORS:
            methodology, exclusion, group = "EXCLUDED", "FINANCIAL_SECTOR", "FINANCIAL"
        elif base_sector in NON_FINANCIAL_SECTORS:
            methodology, exclusion, group = "ELIGIBLE", None, "NON_FINANCIAL"
        else:
            methodology, exclusion, group = "REVIEW_REQUIRED", None, "UNDETERMINED"
        identity, issuer_id, code, cnpj = "RESOLVED", None, None, candidate["candidate_key"]
        try:
            if candidate["identity_ambiguous"] or len(rows) != 1:
                raise ValueError("AMBIGUOUS_FCA_IDENTITY")
            code, cnpj = canonical_identity(record["Codigo_CVM"], record["CNPJ_Companhia"])
            matches = [i for i in canonical.values() if i["cvm_code"] == code or i["cnpj"] == cnpj]
            if matches and (
                len(matches) != 1 or (matches[0]["cvm_code"], matches[0]["cnpj"]) != (code, cnpj)
            ):
                raise ValueError("CANONICAL_IDENTITY_CONFLICT")
            issuer_id = (
                matches[0]["issuer_id"]
                if matches
                else str(uuid5(NAMESPACE_URL, f"income-analytics:issuer:cvm:{code}:cnpj:{cnpj}"))
            )
        except ValueError, KeyError:
            identity = "UNRESOLVED"
        result.append(
            dict(
                candidate,
                issuer_id=issuer_id,
                cvm_code=code,
                cnpj=cnpj,
                display_name=record.get("Nome_Empresarial")
                or candidate["raw_securities"][0]["Nome_Empresarial"],
                economic_sector=sector,
                economic_sector_group=group,
                sector_source_reference=record.get("source_reference"),
                methodology_eligibility=methodology,
                exclusion_reason=exclusion,
                identity_status=identity,
                identity_source_reference=record.get("source_reference"),
            )
        )
    # Two distinct CNPJs claiming one CVM code are not two resolved issuers.
    codes = Counter(i["cvm_code"] for i in result if i["cvm_code"])
    for item in result:
        if item["cvm_code"] and codes[item["cvm_code"]] > 1:
            item["identity_status"], item["issuer_id"] = "UNRESOLVED", None
    return result


def accounting_readiness(rows, reference, cnpj, approved):
    exact = [r for r in rows if r["DT_REFER"] == reference]
    missing, ambiguous, evidence = [], [], []
    for rule in RULES:
        for code in rule.account_codes:
            hits = [r for r in exact if r["statement"] == rule.statement and r["CD_CONTA"] == code]
            if not hits:
                missing.append(code)
                continue
            if len(hits) != 1:
                ambiguous.append("DUPLICATE_ACCOUNT:" + code)
                continue
            row = hits[0]
            value = decimal_or_none(row["VL_CONTA"])
            if value is None:
                missing.append(code)
                continue
            end = row.get("DT_FIM_EXERC") or row["DT_REFER"]
            if end != reference or (
                rule.statement == "DRE" and row.get("DT_INI_EXERC") != reference[:4] + "-01-01"
            ):
                ambiguous.append("TEMPORAL_CONFLICT")
            if digits(row["CNPJ_CIA"]) != cnpj:
                ambiguous.append("UNRESOLVED_IDENTITY")
            amount = MonetaryScaleNormalizer().from_cvm(
                raw_value=value,
                currency="BRL" if row.get("MOEDA") == "REAL" else "UNKNOWN",
                source_scale=row["ESCALA_MOEDA"],
                source=row["source_reference"],
            )
            if amount.source_scale == CurrencyScale.UNKNOWN or amount.normalized_value is None:
                ambiguous.append("MONETARY_SCALE_UNRESOLVED")
            evidence.append(
                dict(
                    metric=rule.metric,
                    account_code=code,
                    rule_id=rule.rule_id,
                    source_reference=row["source_reference"],
                    raw_value=row["VL_CONTA"],
                    currency=row.get("MOEDA"),
                    currency_scale=row["ESCALA_MOEDA"],
                )
            )
    reasons = sorted(set(ambiguous + (["NO_ACCOUNTING_DATA"] if missing else [])))
    if not exact and rows:
        reasons.append("TEMPORAL_CONFLICT")
    status = (
        "REVIEW_REQUIRED"
        if ambiguous
        else "DATA_GAP"
        if missing
        else "AVAILABLE"
        if approved
        else "NORMALIZATION_REQUIRED"
    )
    return dict(
        status=status,
        ready=not reasons,
        missing_accounts=missing,
        reason_codes=sorted(set(reasons)),
        evidence=sorted(evidence, key=digest),
    )


def market_readiness(item, capital_rows, quotes_by_ticker, reference, approved):
    securities, reasons = [], []
    raw = item["raw_securities"]
    for row in raw:
        ticker = row["Codigo_Negociacao"].strip().upper()
        share_class = SHARE_TYPES[row["Valor_Mobiliario"]]
        valid = bool(
            ticker
            and valid_date(row["Data_Inicio_Negociacao"])
            and valid_date(row["Data_Referencia"])
        )
        if row["Data_Fim_Negociacao"] and not valid_date(row["Data_Fim_Negociacao"]):
            valid = False
        available = [
            q
            for q in quotes_by_ticker.get(ticker, [])
            if q["effective_date"] <= reference
            and 0
            <= (date.fromisoformat(reference) - date.fromisoformat(q["effective_date"])).days
            <= 7
        ]
        if available:
            latest = max(q["effective_date"] for q in available)
            available = [q for q in available if q["effective_date"] == latest]
        quote = available[0] if len(available) == 1 else None
        price = decimal_or_none(quote["price"]) if quote else None
        price_ready = (
            quote is not None and price is not None and price > 0 and quote["currency"] == "R$"
        )
        securities.append(
            dict(
                issuer_id=item["issuer_id"],
                security_id="BR:" + ticker if ticker else None,
                ticker=ticker or None,
                share_class=share_class,
                preferred_class=row["Sigla_Classe_Acao_Preferencial"] or None,
                unit_composition=row["Composicao_BDR_Unit"] or None,
                isin=quote["isin"] if quote else None,
                valid_from=row["Data_Inicio_Negociacao"] or None,
                valid_to=row["Data_Fim_Negociacao"] or None,
                source_reference=row["source_reference"],
                form_id=row["ID_Documento"],
                form_reference=row["Data_Referencia"],
                security_status="RESOLVED" if valid else "SECURITY_UNRESOLVED",
                price_status="AVAILABLE"
                if price_ready
                else "REVIEW_REQUIRED"
                if len(available) > 1
                else "DATA_GAP",
                requested_market_date=reference,
                effective_market_date=quote["effective_date"] if quote else None,
                price=quote["price"] if price_ready else None,
                price_source_reference=quote["source_reference"] if quote else None,
            )
        )
    current = [r for r in capital_rows if r["DT_REFER"] == reference]
    cap = current[0] if len(current) == 1 else None
    classes, quantities = {}, {}
    if cap:
        for share_class, prefix in (("ON", "QT_ACAO_ORDIN_"), ("PN", "QT_ACAO_PREF_")):
            issued, treasury = (
                decimal_or_none(cap[prefix + "CAP_INTEGR"]),
                decimal_or_none(cap[prefix + "TESOURO"]),
            )
            quantities[share_class] = dict(
                issued=cap[prefix + "CAP_INTEGR"] or None, treasury=cap[prefix + "TESOURO"] or None
            )
            if issued is None or treasury is None:
                reasons.append("NO_CAPITAL_DATA")
            elif not 0 <= treasury <= issued:
                reasons.append("INVALID_CAPITAL_DATA")
            elif issued > 0:
                classes[share_class] = (issued, treasury)
    else:
        reasons.append("NO_CAPITAL_DATA" if not current else "AMBIGUOUS_CAPITAL_DATA")
        if not current and capital_rows:
            reasons.append("TEMPORAL_CONFLICT")
    needed = (
        set(classes)
        if classes
        else {s["share_class"] for s in securities if s["share_class"] != "UNIT"}
    )
    selected = []
    security_ready = bool(needed) and all(s["security_status"] == "RESOLVED" for s in securities)
    for share_class in sorted(needed):
        hits = [s for s in securities if s["share_class"] == share_class]
        if len(hits) != 1:
            security_ready = False
        else:
            selected.append(hits[0])
    general = item["general"][0] if len(item["general"]) == 1 else {}
    if (
        general.get("Categoria_Registro_CVM") != "Categoria A"
        or general.get("Situacao_Registro_CVM") != "Ativo"
    ):
        security_ready = False
    for field in ("Data_Situacao_Registro_CVM", "Data_Categoria_Registro_CVM"):
        if general.get(field) and general[field] > reference:
            security_ready = False
            reasons.append("TEMPORAL_CONFLICT")
    if not security_ready:
        reasons.append("NO_VALID_SECURITY")
    # A quoted unit is evidence of a price, even when its class decomposition
    # remains unresolved. It is never used as a substitute for class market cap.
    price_targets = (
        selected
        if security_ready
        else ([s for s in securities if s["share_class"] == "UNIT"] or selected or securities)
    )
    price_ready = bool(price_targets) and all(
        s["price_status"] == "AVAILABLE" for s in price_targets
    )
    if not price_ready:
        reasons.append("NO_REFERENCE_PRICE")
    if any(s["price_status"] == "REVIEW_REQUIRED" for s in price_targets):
        reasons.append("AMBIGUOUS_REFERENCE_PRICE")
    # No universal quantity unit is inferred from DFP magnitudes. Reuse any
    # matching, validated canonical capital evidence, regardless of issuer name.
    unit_ready = bool(classes)
    proofs = approved.get("capital", []) if approved else []
    for share_class, (issued, treasury) in classes.items():
        matches = [
            p
            for p in proofs
            if p["share_class"] == share_class
            and p["reference_date"] == reference
            and p["quantity_unit"] == "UNIT"
            and decimal_or_none(p["quantity_multiplier"]) == 1
            and decimal_or_none(p["issued_shares"]) == issued
            and decimal_or_none(p["treasury_shares"]) == treasury
        ]
        if len(matches) != 1:
            unit_ready = False
    if cap and classes and not unit_ready:
        reasons.append("UNIT_UNRESOLVED")
    capital_ready = (
        cap is not None
        and unit_ready
        and not any(
            r in reasons
            for r in (
                "NO_CAPITAL_DATA",
                "INVALID_CAPITAL_DATA",
                "AMBIGUOUS_CAPITAL_DATA",
                "TEMPORAL_CONFLICT",
            )
        )
    )
    status = (
        "RESOLVABLE"
        if security_ready and capital_ready and price_ready
        else "TEMPORAL_CONFLICT"
        if "TEMPORAL_CONFLICT" in reasons
        else "SECURITY_UNRESOLVED"
        if not security_ready
        else "UNIT_UNRESOLVED"
        if "UNIT_UNRESOLVED" in reasons
        else "INSUFFICIENT_MARKET_DATA"
        if not price_ready
        else "DATA_GAP"
    )
    return dict(
        status=status,
        security_ready=security_ready,
        capital_ready=capital_ready,
        price_ready=price_ready,
        price_readiness_tickers=sorted(s["ticker"] or "" for s in price_targets),
        reason_codes=sorted(set(reasons)),
        securities=sorted(securities, key=digest),
        capital_source_reference=cap["source_reference"] if cap else None,
        raw_capital_quantities=quantities,
        quantity_unit="UNIT" if unit_ready else None,
        unit_evidence_snapshot_id=approved.get("snapshot_id") if unit_ready and approved else None,
    )


def evaluate_readiness(classified, accounts, capitals, quotes, canonical, reference):
    by_code, by_cnpj, by_ticker = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in accounts:
        by_code[row["CD_CVM"].zfill(6)].append(row)
    for row in capitals:
        by_cnpj[digits(row["CNPJ_CIA"])].append(row)
    for row in quotes:
        by_ticker[row["ticker"]].append(row)
    result = []
    for item in classified:
        approved = canonical.get(item["issuer_id"], {}).get("approved")
        accounting = accounting_readiness(
            by_code.get(item["cvm_code"], []), reference, item["cnpj"], approved
        )
        market = market_readiness(
            item, by_cnpj.get(item["cnpj"], []), by_ticker, reference, approved
        )
        reasons = sorted(
            set(
                accounting["reason_codes"]
                + market["reason_codes"]
                + (["UNRESOLVED_IDENTITY"] if item["identity_status"] != "RESOLVED" else [])
            )
        )
        if "UNRESOLVED_IDENTITY" in reasons:
            item = dict(item, identity_status="UNRESOLVED")
        full = (
            item["identity_status"] == "RESOLVED"
            and accounting["ready"]
            and market["security_ready"]
            and market["capital_ready"]
            and market["price_ready"]
        )
        review = any(
            r in reasons
            for r in (
                "UNRESOLVED_IDENTITY",
                "TEMPORAL_CONFLICT",
                "AMBIGUOUS_CAPITAL_DATA",
                "AMBIGUOUS_REFERENCE_PRICE",
            )
        )
        review = review or accounting["status"] == "REVIEW_REQUIRED"
        readiness = "FULL_DATA_READY" if full else "REVIEW_REQUIRED" if review else "DATA_GAP"
        methodology = item["methodology_eligibility"]
        status = (
            "EXCLUDED"
            if methodology == "EXCLUDED"
            else "REVIEW_REQUIRED"
            if methodology == "REVIEW_REQUIRED"
            else "ELIGIBLE"
            if full
            else readiness
        )
        if methodology == "REVIEW_REQUIRED":
            reasons.append("SECTOR_REVIEW_REQUIRED")
        result.append(
            dict(
                **{
                    k: v
                    for k, v in item.items()
                    if k not in ("general", "raw_securities", "identity_ambiguous")
                },
                eligibility_status=status,
                data_readiness_status=readiness,
                data_reason_codes=sorted(set(reasons)),
                accounting_readiness=accounting,
                market_readiness={k: v for k, v in market.items() if k != "securities"},
                securities=market["securities"],
                canonical_status="RESOLVED" if approved else "NOT_RESOLVED",
                canonical_snapshot_id=approved.get("snapshot_id") if approved else None,
                canonical_qa_id=approved.get("qa_id") if approved else None,
                canonical_ranking_eligible=bool(approved and approved.get("ranking_eligible")),
            )
        )
    return sorted(result, key=lambda i: i["candidate_key"])


def coverage(issuers):
    eligible = [i for i in issuers if i["methodology_eligibility"] == "ELIGIBLE"]
    funnel = dict(TOTAL_CANDIDATE_ISSUERS=len(issuers), METHODOLOGY_ELIGIBLE=len(eligible))
    stages = (
        ("IDENTITY_RESOLVED", lambda i: i["identity_status"] == "RESOLVED"),
        ("ACCOUNTING_READY", lambda i: i["accounting_readiness"]["ready"]),
        ("SECURITY_READY", lambda i: i["market_readiness"]["security_ready"]),
        ("CAPITAL_READY", lambda i: i["market_readiness"]["capital_ready"]),
        ("MARKET_PRICE_READY", lambda i: i["market_readiness"]["price_ready"]),
        ("FULL_DATA_READY", lambda i: i["data_readiness_status"] == "FULL_DATA_READY"),
    )
    remaining, independent = eligible, {}
    for name, predicate in stages:
        independent[name] = sum(predicate(i) for i in eligible)
        remaining = [i for i in remaining if predicate(i)]
        funnel[name] = len(remaining)
    primary = Counter(i["eligibility_status"] for i in issuers)
    methodology = Counter(i["methodology_eligibility"] for i in issuers)
    reasons = Counter(r for i in eligible for r in set(i["data_reason_codes"]))
    primary_gap = Counter(
        (i["data_reason_codes"][0] if i["data_reason_codes"] else "NONE")
        for i in eligible
        if i["data_readiness_status"] != "FULL_DATA_READY"
    )
    metrics = {}
    for name, numerator, denominator in (
        ("methodology_coverage", len(eligible), len(issuers)),
        *((k.lower() + "_coverage", value, len(eligible)) for k, value in independent.items()),
    ):
        metrics[name] = dict(
            numerator=numerator,
            denominator=denominator,
            percent=str(Decimal(100) * numerator / denominator) if denominator else None,
        )
    return dict(
        funnel=funnel,
        independent_dimensions=independent,
        metrics=metrics,
        methodology_distribution=dict(sorted(methodology.items())),
        primary_status_distribution=dict(sorted(primary.items())),
        methodology_exclusion_reasons=dict(
            sorted(Counter(i["exclusion_reason"] for i in issuers if i["exclusion_reason"]).items())
        ),
        data_gap_reason_incidence=dict(sorted(reasons.items())),
        primary_gap_reasons=dict(sorted(primary_gap.items())),
        top_3_data_gaps=[
            dict(reason_code=k, issuers=v)
            for k, v in sorted(reasons.items(), key=lambda x: (-x[1], x[0]))[:3]
        ],
    )
