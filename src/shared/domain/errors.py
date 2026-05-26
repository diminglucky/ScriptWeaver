"""Cross-service error hierarchy. See v2 plan §3.5."""

from __future__ import annotations


class CreativeError(Exception):
    """Base class for all service errors that should be surfaced to the GUI."""

    code: str = "creative_error"
    http_status: int = 500

    def __init__(self, message: str = "", *, detail: dict | None = None):
        super().__init__(message)
        self.message = message or self.__class__.__name__
        self.detail: dict = detail or {}

    def to_payload(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
        }


class DependencyMissing(CreativeError):
    code = "dependency_missing"
    http_status = 503


class ModelProviderError(CreativeError):
    code = "model_provider_error"
    http_status = 502


class StructuredOutputError(CreativeError):
    code = "structured_output"
    http_status = 422


class RetrievalError(CreativeError):
    code = "retrieval_error"
    http_status = 502


class WorkflowInterrupted(CreativeError):
    code = "workflow_interrupted"
    http_status = 409


class WorkflowCancelled(CreativeError):
    code = "workflow_cancelled"
    http_status = 499


class ProjectSaveError(CreativeError):
    code = "project_save_error"
    http_status = 500


class AuthError(CreativeError):
    code = "auth_error"
    http_status = 401


class NotFound(CreativeError):
    code = "not_found"
    http_status = 404
