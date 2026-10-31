"""Bounded OOXML inspection before any Pandas/openpyxl parsing."""

from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree

from .errors import ApiError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_MEMBERS = 128
MAX_UNCOMPRESSED_BYTES = 40 * 1024 * 1024
MAX_MEMBER_BYTES = 20 * 1024 * 1024
MAX_ROWS = 10000


def inspect_workbook(path: Path) -> None:
    try:
        if path.stat().st_size > MAX_UPLOAD_BYTES:
            raise ApiError("FILE_TOO_LARGE")
        signature = path.open("rb")
        with signature:
            first = signature.read(8)
        if first.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
            raise ApiError("ENCRYPTED_WORKBOOK")
        if not first.startswith(b"PK\x03\x04"):
            raise ApiError("CORRUPT_WORKBOOK")
        with ZipFile(path) as archive:
            members = archive.infolist()
            names = [item.filename for item in members]
            if (len(members) > MAX_MEMBERS or len(names) != len(set(names))
                    or sum(item.file_size for item in members) > MAX_UNCOMPRESSED_BYTES):
                raise ApiError("WORKBOOK_LIMIT_EXCEEDED")
            sheets = []
            for member in members:
                name = member.filename
                lower = name.lower()
                if member.flag_bits & 1:
                    raise ApiError("ENCRYPTED_WORKBOOK")
                if (member.file_size > MAX_MEMBER_BYTES or member.file_size > max(member.compress_size, 1) * 200
                        or name.startswith("/") or "\\" in name or ".." in name.split("/")):
                    raise ApiError("WORKBOOK_LIMIT_EXCEEDED")
                if any(term in lower for term in ("vbaproject", "macrosheets/", "externallinks/", "connections.xml", "querytables/", "embeddings/", "activex/")):
                    raise ApiError("UNSAFE_WORKBOOK")
                if lower.endswith((".xml", ".rels")):
                    data = archive.read(member)
                    # Local OOXML contract accepts UTF-8 XML only; reject encodings that could
                    # hide a DTD/entity declaration from the pre-parse guard.
                    data.decode("utf-8-sig")
                    if b"\x00" in data:
                        raise ApiError("UNSAFE_WORKBOOK")
                    if b"<!doctype" in data.lower() or b"<!entity" in data.lower():
                        raise ApiError("UNSAFE_WORKBOOK")
                    if lower == "[content_types].xml" and any(
                        term in data.lower() for term in (b"macro", b"vba", b"activex")
                    ):
                        raise ApiError("UNSAFE_WORKBOOK")
                    xml = ElementTree.fromstring(data)
                    for node in xml.iter():
                        local = node.tag.rsplit("}", 1)[-1]
                        if (local in {"workbookProtection", "sheetProtection"}
                                and any(value.lower() not in {"0", "false", ""} for value in node.attrib.values())):
                            raise ApiError("ENCRYPTED_WORKBOOK")
                        if (local in {"f", "externalReference", "connection"}
                                or node.attrib.get("TargetMode", "").lower() == "external"):
                            raise ApiError("UNSAFE_WORKBOOK")
                    if re.fullmatch(r"xl/worksheets/[^/]+\.xml", lower):
                        sheets.append(xml)
            if not {"[Content_Types].xml", "xl/workbook.xml"}.issubset(names):
                raise ApiError("CORRUPT_WORKBOOK")
            if len(sheets) != 1:
                raise ApiError("WORKBOOK_LIMIT_EXCEEDED")
            rows = [node for node in sheets[0].iter() if node.tag.rsplit("}", 1)[-1] == "row"]
            if len(rows) > MAX_ROWS + 1:
                raise ApiError("WORKBOOK_LIMIT_EXCEEDED")
            previous_row = 0
            for row in rows:
                row_number = int(row.attrib.get("r", "0"))
                if row_number <= previous_row or row_number > MAX_ROWS + 1 or len(row) > 5:
                    raise ApiError("WORKBOOK_LIMIT_EXCEEDED")
                previous_row = row_number
                columns = set()
                for cell in row:
                    reference = cell.attrib.get("r", "")
                    if not re.fullmatch(r"[A-E][1-9][0-9]{0,4}", reference):
                        raise ApiError("WORKBOOK_LIMIT_EXCEEDED")
                    if int(reference[1:]) > MAX_ROWS + 1:
                        raise ApiError("WORKBOOK_LIMIT_EXCEEDED")
                    if int(reference[1:]) != row_number or reference[0] in columns:
                        raise ApiError("CORRUPT_WORKBOOK")
                    columns.add(reference[0])
            for dimension in sheets[0].iter():
                if dimension.tag.rsplit("}", 1)[-1] == "dimension":
                    for ref in dimension.attrib.get("ref", "").split(":"):
                        if not re.fullmatch(r"[A-E][1-9][0-9]{0,4}", ref) or int(re.sub(r"^[A-Z]+", "", ref)) > MAX_ROWS + 1:
                            raise ApiError("WORKBOOK_LIMIT_EXCEEDED")
    except ApiError:
        raise
    except (BadZipFile, ElementTree.ParseError, OSError, ValueError, RuntimeError, NotImplementedError):
        raise ApiError("CORRUPT_WORKBOOK") from None
