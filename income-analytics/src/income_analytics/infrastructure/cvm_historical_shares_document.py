"""Cross-check CVM XML and its official rendered capital page before exposing units."""

import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET
from zipfile import ZipFile


def read_unit_evidence(path):
    with ZipFile(path) as archive:
        metadata = json.loads(archive.read("evidence.json"))
        main_bytes = archive.read(metadata["main_xml_member"])
        descriptor_bytes = archive.read(metadata["descriptor_member"])
        for name, content in (
            (metadata["main_xml_member"], main_bytes),
            (metadata["descriptor_member"], descriptor_bytes),
        ):
            if hashlib.sha256(content).hexdigest() != metadata["member_sha256"][name]:
                raise ValueError("SOURCE_DIGEST_MISMATCH")
        root, descriptor = ET.fromstring(main_bytes), ET.fromstring(descriptor_bytes)
    result = dict(
        status="SOURCE_SCHEMA_ERROR",
        reason_code="MISSING_OR_UNKNOWN_SOURCE_SCHEMA",
        source_reference=metadata["url"]
        + "|"
        + metadata["main_xml_member"]
        + "|DadosDFP/EscalaQtdAcoes",
        acquisition=metadata,
    )
    try:
        company = root.find("DadosEmpresa")
        dfp = root.find("DadosDFP")
        capital = dfp.find("Formulario/DadosEmpresa/ComposicaoCapital")
        scale = dfp.findtext("EscalaQtdAcoes")
        label_matches = re.findall(
            r"Número de Ações\s*\((Mil|Unidades?)\)", metadata["pdf_capital_page"]["text"]
        )
        if len(label_matches) != 1 or scale not in ("1", "2"):
            return result
        label = "Unidade" if label_matches[0] == "Unidades" else label_matches[0]
        reference = datetime.strptime(dfp.findtext("DataReferencia"), "%d/%m/%Y").date().isoformat()
        code = company.findtext("CodigoCvm").zfill(6)
        cnpj = re.sub(r"\D", "", company.findtext("CnpjEmpresa"))
        version = root.findtext("Documento/VersaoDocumento")
        if (
            scale != descriptor.findtext("CodigoEscalaQuantidade")
            or (scale, label) not in (("1", "Unidade"), ("2", "Mil"))
            or reference != descriptor.findtext("DataReferenciaDocumento")[:10]
            or version != descriptor.findtext("NumeroVersaoDocumento")
            or metadata["document_id"] != descriptor.findtext("NumeroSequencialDocumento")
            or cnpj
            != re.sub(r"\D", "", descriptor.findtext("CompanhiaAberta/NumeroCnpjCompanhiaAberta"))
            or code != re.sub(r"\D", "", descriptor.findtext("CompanhiaAberta/CodigoCvm")).zfill(6)
        ):
            result.update(status="REVIEW_REQUIRED", reason_code="DOCUMENT_METADATA_CONFLICT")
            return result
        quantities = {}
        for name, prefix in (
            ("Ordinarias", "QT_ACAO_ORDIN_"),
            ("Preferenciais", "QT_ACAO_PREF_"),
            ("QtdeTotalAcoes", "QT_ACAO_TOTAL_"),
        ):
            quantities[prefix + "CAP_INTEGR"] = capital.findtext("CaptalIntegralizado/" + name)
            quantities[prefix + "TESOURO"] = capital.findtext("Tesouraria/" + name)
        # A second representation from the same filing is cross-evidence, not an
        # independent economic observation. Exact row association is required.
        text = metadata["pdf_capital_page"]["text"]
        expected = [
            quantities[k]
            for k in (
                "QT_ACAO_ORDIN_CAP_INTEGR",
                "QT_ACAO_PREF_CAP_INTEGR",
                "QT_ACAO_TOTAL_CAP_INTEGR",
                "QT_ACAO_ORDIN_TESOURO",
                "QT_ACAO_PREF_TESOURO",
                "QT_ACAO_TOTAL_TESOURO",
            )
        ]
        matches = re.findall(r"(?:Ordinárias|Preferenciais|Total)\s*\n\s*([\d.]+)", text)
        if len(matches) != 6 or [Decimal(v.replace(".", "")) for v in matches] != [
            Decimal(v) for v in expected
        ]:
            result.update(status="REVIEW_REQUIRED", reason_code="PDF_XML_QUANTITY_CONFLICT")
            return result
        result.update(
            status="VERIFIED",
            reason_code=None,
            cnpj=cnpj,
            cvm_code=code,
            reference_date=reference,
            version=version,
            quantity_scale_code=scale,
            unit_label=label,
            quantities=quantities,
        )
    except AttributeError, TypeError, ValueError, InvalidOperation:
        return result
    return result
