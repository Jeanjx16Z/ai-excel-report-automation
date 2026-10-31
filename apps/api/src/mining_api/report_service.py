"""Single-process local upload/report service with private objects and safe replay."""

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from hashlib import sha256
import json
import re
import secrets
from threading import RLock
from uuid import UUID, uuid4

from excel_report.management_report import export_management_report, export_management_workbook
from excel_report.models import DataValidationError, InputFileError
from excel_report.reporting import build_structured_output
from excel_report.summarizer import generate_executive_summary

from .core_adapter import analyze_workbook
from .errors import ApiError
from .pdf_renderer import render_pdf
from .presentation import serialize_snapshot
from .storage import ObjectStorage
from .workbook_safety import MAX_UPLOAD_BYTES, inspect_workbook

XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FORMATS = {"pdf": ("application/pdf", "pdf"), "markdown": ("text/markdown; charset=utf-8", "md"),
           "excel": (XLSX_TYPE, "xlsx")}


@dataclass
class Upload:
    id: str
    owner: UUID
    object_key: str
    expected_size: int
    capability_hash: str
    capability_expires: datetime
    expires: datetime
    state: str = "pending"
    active: bool = False


@dataclass
class Job:
    id: str
    owner: UUID
    expires: datetime
    state: str = "processing"
    result: dict | None = None
    error_code: str | None = None
    artifacts: dict = field(default_factory=dict)


@dataclass
class Replay:
    request_hash: str
    job: Job
    expires: datetime


class ReportService:
    def __init__(self, storage: ObjectStorage, clock, retention_seconds=3600):
        self.storage = storage
        self.clock = clock
        self.retention_seconds = retention_seconds
        self.uploads: dict[str, Upload] = {}
        self.jobs: dict[str, Job] = {}
        self.replays: dict[tuple[UUID, str], Replay] = {}
        self.pending_cleanup: set[str] = set()
        self.lock = RLock()

    def discard(self, key):
        try:
            self.storage.delete(key)
            self.pending_cleanup.discard(key)
        except OSError:
            # Retry opportunistically; no false claim of background execution.
            self.pending_cleanup.add(key)

    def cleanup(self):
        with self.lock:
            now = self.clock()
            for key in tuple(self.pending_cleanup):
                self.discard(key)
            for identifier, upload in tuple(self.uploads.items()):
                if upload.expires <= now and not upload.active and upload.state not in {"writing", "validating"}:
                    self.discard(upload.object_key)
                    del self.uploads[identifier]
            for identifier, job in tuple(self.jobs.items()):
                if job.expires <= now and job.state != "processing":
                    for key in job.artifacts.values():
                        self.discard(key)
                    del self.jobs[identifier]
            self.replays = {key: replay for key, replay in self.replays.items() if replay.expires > now}

    def intent(self, owner, size, filename, content_type):
        self.cleanup()
        if not filename.lower().endswith(".xlsx") or content_type != XLSX_TYPE:
            raise ApiError("INVALID_FILE_TYPE")
        if size > MAX_UPLOAD_BYTES:
            raise ApiError("FILE_TOO_LARGE")
        with self.lock:
            if len(self.uploads) >= 50 or len(self.jobs) >= 50:
                raise ApiError("SERVICE_UNAVAILABLE")
            identifier, capability = str(uuid4()), secrets.token_urlsafe(32)
            now = self.clock()
            upload = Upload(identifier, owner, self.storage.allocate(".xlsx"), size,
                            sha256(capability.encode()).hexdigest(), now + timedelta(seconds=120),
                            now + timedelta(seconds=300))
            self.uploads[identifier] = upload
        return {"upload_id": identifier, "state": "pending", "upload_instruction": {
            "method": "PUT", "target": f"/api/v1/uploads/{identifier}/content",
            "headers": {"X-Upload-Capability": capability, "Content-Type": "application/octet-stream"},
            "expires_at": upload.capability_expires.isoformat(), "max_size_bytes": MAX_UPLOAD_BYTES,
            "content_type": "application/octet-stream",
        }}

    def owned_upload(self, owner, identifier):
        upload = self.uploads.get(identifier)
        if not upload or upload.owner != owner:
            raise ApiError("UPLOAD_NOT_FOUND")
        if upload.expires <= self.clock():
            self.discard(upload.object_key)
            upload.state = "expired"
            raise ApiError("UPLOAD_INTENT_EXPIRED")
        return upload

    def begin_upload(self, owner, identifier, capability):
        with self.lock:
            upload = self.owned_upload(owner, identifier)
            if upload.capability_expires <= self.clock():
                self.discard(upload.object_key)
                upload.state = "expired"
                raise ApiError("UPLOAD_INTENT_EXPIRED")
            if (upload.state != "pending" or not capability or len(capability) != 43 or not secrets.compare_digest(
                upload.capability_hash, sha256(capability.encode()).hexdigest()
            )):
                raise ApiError("INVALID_UPLOAD_CAPABILITY")
            upload.state = "writing"
            upload.capability_hash = ""
            return upload

    def upload_failed(self, upload):
        with self.lock:
            upload.state = "rejected"
            self.discard(upload.object_key)

    def upload_finished(self, upload, size):
        with self.lock:
            if size != upload.expected_size:
                self.upload_failed(upload)
                raise ApiError("INVALID_REQUEST")
            self.owned_upload(upload.owner, upload.id)
            upload.state = "uploaded"

    def complete(self, owner, identifier):
        with self.lock:
            upload = self.owned_upload(owner, identifier)
            if upload.state == "ready":
                return {"upload_id": identifier, "state": "ready"}
            if upload.state != "uploaded":
                raise ApiError("UPLOAD_NOT_READY")
            if sum(item.state == "validating" for item in self.uploads.values()) >= 2:
                raise ApiError("SERVICE_UNAVAILABLE")
            upload.state = "validating"
        try:
            inspect_workbook(self.storage.path(upload.object_key))
        except Exception:
            self.upload_failed(upload)
            raise
        with self.lock:
            upload.state = "ready"
        return {"upload_id": identifier, "state": "ready"}

    def create_report(self, owner, upload_id, idempotency_key):
        if not re.fullmatch(r"[A-Za-z0-9._:-]{16,128}", idempotency_key or ""):
            raise ApiError("INVALID_REQUEST")
        self.cleanup()
        key = (owner, sha256(idempotency_key.encode()).hexdigest())
        request_hash = sha256(json.dumps({"upload_id": upload_id, "summary_mode": "offline"}, sort_keys=True).encode()).hexdigest()
        with self.lock:
            replay = self.replays.get(key)
            if replay:
                if replay.request_hash != request_hash:
                    raise ApiError("IDEMPOTENCY_CONFLICT")
                if replay.job.state == "processing":
                    raise ApiError("REPORT_IN_PROGRESS", replay.job.id)
                if replay.job.state == "failed":
                    raise ApiError(replay.job.error_code, replay.job.id)
                return deepcopy(replay.job.result)
            upload = self.owned_upload(owner, upload_id)
            if upload.state != "ready":
                raise ApiError("UPLOAD_NOT_READY")
            if len(self.jobs) >= 50:
                raise ApiError("SERVICE_UNAVAILABLE")
            if sum(item.state == "processing" for item in self.jobs.values()) >= 2:
                raise ApiError("SERVICE_UNAVAILABLE")
            job = Job(str(uuid4()), owner, self.clock() + timedelta(seconds=self.retention_seconds))
            upload.state = "consumed"
            upload.active = True
            self.jobs[job.id] = job
            self.replays[key] = Replay(request_hash, job, job.expires)
        allocated = []
        try:
            payload = build_structured_output(analyze_workbook(self.storage.path(upload.object_key)))
            summary = generate_executive_summary(payload, mode="offline")
            result = {"report_id": job.id, "state": "completed", "summary_source": "offline",
                      "created_at": self.clock().isoformat(), "expires_at": job.expires.isoformat(),
                      **serialize_snapshot(payload), "summary": asdict(summary)}
            for format_name in FORMATS:
                object_key = self.storage.allocate("." + FORMATS[format_name][1])
                allocated.append(object_key)
                destination = self.storage.path(object_key)
                if format_name == "pdf":
                    render_pdf(result, destination)
                elif format_name == "markdown":
                    export_management_report(payload, summary, destination)
                else:
                    export_management_workbook(payload, summary, destination)
                job.artifacts[format_name] = object_key
            result["artifacts"] = [{"format": name, "available": True,
                "download_path": f"/api/v1/reports/{job.id}/download/{name}"} for name in FORMATS]
            with self.lock:
                job.result, job.state = result, "completed"
            return deepcopy(result)
        except Exception as error:
            code = "INVALID_FILE_SCHEMA" if isinstance(error, (DataValidationError, InputFileError)) else (
                error.code if isinstance(error, ApiError) else "PROCESSING_FAILURE")
            with self.lock:
                job.state, job.error_code = "failed", code
                job.artifacts.clear()
                for object_key in allocated:
                    self.discard(object_key)
            raise ApiError(code, job.id) from None
        finally:
            upload.active = False
            self.discard(upload.object_key)

    def owned_job(self, owner, identifier):
        job = self.jobs.get(identifier)
        if not job or job.owner != owner:
            raise ApiError("NOT_FOUND")
        if job.expires <= self.clock():
            for key in job.artifacts.values():
                self.discard(key)
            raise ApiError("REPORT_EXPIRED")
        return job

    def detail(self, owner, identifier):
        with self.lock:
            job = self.owned_job(owner, identifier)
            if job.state == "completed":
                return deepcopy(job.result)
            return {"report_id": job.id, "state": job.state, "safe_error": job.error_code}

    def download(self, owner, identifier, format_name):
        with self.lock:
            job = self.owned_job(owner, identifier)
            if format_name not in FORMATS or job.state != "completed":
                raise ApiError("NOT_FOUND")
            return self.storage.path(job.artifacts[format_name]), FORMATS[format_name]
