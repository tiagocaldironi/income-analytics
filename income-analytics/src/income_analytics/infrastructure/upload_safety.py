"""Bound compressed spreadsheets before XML parsing; no disk extraction."""

from io import BytesIO
from zipfile import BadZipFile, ZipFile


def validate_workbook(payload: bytes):
    if len(payload) > 6 * 1024 * 1024:
        raise ValueError("Planilha excede o limite de 6 MB.")
    try:
        with ZipFile(BytesIO(payload)) as archive:
            entries = archive.infolist()
            if len(entries) > 300 or sum(item.file_size for item in entries) > 32 * 1024 * 1024:
                raise ValueError("Planilha excede o limite de conteúdo descompactado.")
            for item in entries:
                if item.flag_bits & 1 or ".." in item.filename.split("/"):
                    raise ValueError("Planilha inválida.")
                if item.file_size > 16 * 1024 * 1024 or item.file_size > max(
                    1024 * 1024, item.compress_size * 200
                ):
                    raise ValueError("Planilha excede o limite de expansão permitido.")
                if item.filename.endswith((".xml", ".rels")):
                    xml = archive.read(item).upper()
                    if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
                        raise ValueError("Planilha contém XML não permitido.")
    except BadZipFile as error:
        raise ValueError("Arquivo de planilha inválido.") from error
