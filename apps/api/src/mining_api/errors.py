"""Allowlisted API errors without raw exception text."""

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from uuid import UUID

ERRORS = {
    "INVALID_FILE_TYPE": (415, "Gunakan file Excel .xlsx sesuai template sintetis."),
    "FILE_TOO_LARGE": (413, "Ukuran file melebihi batas 10 MB."),
    "CORRUPT_WORKBOOK": (422, "Workbook tidak valid. Gunakan template .xlsx yang disediakan."),
    "ENCRYPTED_WORKBOOK": (422, "Workbook terenkripsi atau dilindungi tidak didukung."),
    "UNSAFE_WORKBOOK": (422, "Hapus formula, macro, external link, dan data connection dari workbook."),
    "WORKBOOK_LIMIT_EXCEEDED": (422, "Batas workbook: satu sheet, lima kolom, dan 10.000 baris data."),
    "INVALID_FILE_SCHEMA": (422, "Periksa lima kolom, tanggal, angka non-negatif, mapping departemen/kategori, dan duplikat sesuai template."),
    "UPLOAD_NOT_FOUND": (404, "Upload tidak ditemukan."),
    "UPLOAD_INTENT_EXPIRED": (410, "Upload kedaluwarsa. Pilih file dan mulai upload baru."),
    "UPLOAD_NOT_READY": (409, "Upload belum siap atau sudah digunakan. Mulai upload baru."),
    "INVALID_UPLOAD_CAPABILITY": (403, "Izin upload tidak valid atau sudah digunakan."),
    "IDEMPOTENCY_CONFLICT": (409, "Key request sudah dipakai untuk permintaan berbeda."),
    "REPORT_IN_PROGRESS": (409, "Laporan masih diproses. Periksa hasil dengan key yang sama, jangan membuat request baru otomatis."),
    "REPORT_EXPIRED": (410, "Laporan sudah kedaluwarsa. Proses file baru."),
    "INVALID_SESSION": (401, "Sesi tidak valid atau sudah kedaluwarsa."),
    "CSRF_REJECTED": (403, "Permintaan tidak memenuhi validasi CSRF."),
    "UNTRUSTED_PROXY": (403, "Permintaan harus melalui proxy aplikasi."),
    "INVALID_REQUEST": (422, "Format permintaan tidak valid."),
    "NOT_FOUND": (404, "Resource tidak ditemukan."),
    "METHOD_NOT_ALLOWED": (405, "Metode tidak diizinkan."),
    "PROCESSING_FAILURE": (500, "Terjadi kesalahan internal."),
    "SERVICE_UNAVAILABLE": (503, "Layanan sementara tidak tersedia."),
}


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: UUID
    report_id: UUID | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class ApiError(Exception):
    def __init__(self, code: str, report_id: str | None = None):
        self.code = code
        self.report_id = report_id
        super().__init__(code)


def error_response(code: str, request_id: str, report_id: str | None = None) -> JSONResponse:
    status, message = ERRORS[code]
    detail = {"code": code, "message": message, "request_id": request_id}
    if report_id is not None:
        detail["report_id"] = str(UUID(report_id))
    return JSONResponse(
        {"error": detail},
        status_code=status,
        headers={"X-Request-ID": request_id, "Cache-Control": "no-store"},
    )
