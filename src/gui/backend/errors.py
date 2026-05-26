"""Translate HTTP error envelopes back into CreativeError subclasses.

See v2 plan §3.5 / §14.1.
"""

from __future__ import annotations

from src.shared.domain.errors import (
    AuthError,
    CreativeError,
    DependencyMissing,
    ModelProviderError,
    NotFound,
    ProjectSaveError,
    RetrievalError,
    StructuredOutputError,
    WorkflowCancelled,
    WorkflowInterrupted,
)

_BY_CODE: dict[str, type[CreativeError]] = {
    "auth_error": AuthError,
    "dependency_missing": DependencyMissing,
    "model_provider_error": ModelProviderError,
    "not_found": NotFound,
    "project_save_error": ProjectSaveError,
    "retrieval_error": RetrievalError,
    "structured_output": StructuredOutputError,
    "workflow_cancelled": WorkflowCancelled,
    "workflow_interrupted": WorkflowInterrupted,
}


def error_from_payload(payload: dict) -> CreativeError:
    err = payload.get("error") if isinstance(payload, dict) else None
    if err is None and isinstance(payload, dict) and "code" in payload:
        err = payload
    if not isinstance(err, dict):
        return CreativeError("unknown error", detail={"raw": payload})
    cls = _BY_CODE.get(err.get("code", ""), CreativeError)
    return cls(err.get("message", ""), detail=err.get("detail") or {})
