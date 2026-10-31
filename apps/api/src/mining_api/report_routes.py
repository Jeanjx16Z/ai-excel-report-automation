"""Provider-neutral upload/report contract with an explicitly local upload transport."""

from io import BytesIO
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.responses import FileResponse
from openpyxl import Workbook
from pydantic import BaseModel, ConfigDict, Field

from .dependencies import get_identity, get_session_service
from .errors import ApiError, ErrorEnvelope
from .report_service import XLSX_TYPE
from .repositories import SessionRecord
from .workbook_safety import MAX_UPLOAD_BYTES

router = APIRouter(prefix="/api/v1", responses={
    status: {"model": ErrorEnvelope} for status in (401, 403, 404, 409, 410, 413, 415, 422, 500, 503)
})
Identity = Annotated[SessionRecord, Depends(get_identity)]


def mutation_identity(request: Request) -> SessionRecord:
    service = get_session_service(request)
    identity = get_identity(request)
    service.verify_csrf(identity, request.headers.get("x-csrf-token"))
    return identity


Mutation = Annotated[SessionRecord, Depends(mutation_identity)]


class IntentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(gt=0, strict=True)
    content_type: str
    synthetic_data_ack: Literal[True]


class CompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    upload_id: UUID
    summary_mode: Literal["offline"] = "offline"


@router.get("/template")
def template(identity: Identity):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Synthetic Costs"
    sheet.append(["date", "department", "category", "budget", "actual_cost"])
    sheet.append(["2025-01-01", "Mining Operations", "Diesel Fuel", 1000000, 1200000])
    sheet.append(["2025-01-02", "HSE", "Safety Equipment", 2000000, 1800000])
    sheet.append(["2025-01-03", "Logistics", "Hauling Transportation", 3000000, 3000000])
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    return Response(stream.getvalue(), media_type=XLSX_TYPE,
                    headers={"Content-Disposition": 'attachment; filename="template_synthetic.xlsx"'})


@router.post("/uploads/intents", status_code=201)
def intent(body: IntentRequest, request: Request, identity: Mutation):
    return request.app.state.reports.intent(identity.owner_id, body.size_bytes, body.filename, body.content_type)


@router.put("/uploads/{upload_id}/content")
async def local_content(upload_id: UUID, request: Request, identity: Mutation,
                        capability: Annotated[str | None, Header(alias="X-Upload-Capability")] = None):
    if request.headers.get("content-type", "").split(";")[0] != "application/octet-stream":
        raise ApiError("INVALID_REQUEST")
    service = request.app.state.reports
    upload = service.begin_upload(identity.owner_id, str(upload_id), capability)
    try:
        total = 0
        with service.storage.path(upload.object_key).open("xb") as stream:
            async for chunk in request.stream():
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise ApiError("FILE_TOO_LARGE")
                if total > upload.expected_size:
                    raise ApiError("INVALID_REQUEST")
                stream.write(chunk)
        service.upload_finished(upload, total)
    except BaseException:
        # Include disconnect/cancellation so partial data never becomes ready.
        service.upload_failed(upload)
        raise
    return {"upload_id": upload.id, "state": "uploaded"}


@router.post("/uploads/{upload_id}/complete")
def complete(upload_id: UUID, body: CompleteRequest, request: Request, identity: Mutation):
    return request.app.state.reports.complete(identity.owner_id, str(upload_id))


@router.post("/reports", status_code=201)
def create_report(body: ReportRequest, request: Request, identity: Mutation,
                  key: Annotated[str | None, Header(alias="Idempotency-Key")] = None):
    return request.app.state.reports.create_report(identity.owner_id, str(body.upload_id), key)


@router.get("/reports/{report_id}")
def detail(report_id: UUID, request: Request, identity: Identity):
    return request.app.state.reports.detail(identity.owner_id, str(report_id))


@router.get("/reports/{report_id}/download/{format_name}")
def download(report_id: UUID, format_name: str, request: Request, identity: Identity):
    path, (media_type, extension) = request.app.state.reports.download(identity.owner_id, str(report_id), format_name)
    return FileResponse(path, media_type=media_type, filename=f"laporan_sintetis.{extension}",
                        headers={"Cache-Control": "private, no-store"})
