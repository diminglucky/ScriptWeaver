"""CreativeError hierarchy + envelope decoding. See docs/technical_architecture.md.5 / 搂14.1."""

from __future__ import annotations

from src.gui.backend.errors import error_from_payload
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


def test_error_to_payload_shape():
    err = StructuredOutputError("bad json", detail={"attempts": 3})
    payload = err.to_payload()
    assert payload == {
        "code": "structured_output",
        "message": "bad json",
        "detail": {"attempts": 3},
    }


def test_error_codes_have_unique_http_status_for_each_class():
    classes = [
        AuthError,
        DependencyMissing,
        ModelProviderError,
        NotFound,
        ProjectSaveError,
        RetrievalError,
        StructuredOutputError,
        WorkflowCancelled,
        WorkflowInterrupted,
    ]
    codes = {cls.code for cls in classes}
    assert len(codes) == len(classes)


def test_error_from_payload_known_code_returns_subclass():
    payload = {"error": {"code": "retrieval_error", "message": "boom"}}
    back = error_from_payload(payload)
    assert isinstance(back, RetrievalError)
    assert back.message == "boom"


def test_error_from_payload_unknown_code_falls_back_to_creative_error():
    payload = {"error": {"code": "totally_unknown", "message": "x"}}
    back = error_from_payload(payload)
    assert isinstance(back, CreativeError)
    assert not isinstance(back, RetrievalError)


def test_error_from_payload_handles_missing_envelope():
    back = error_from_payload({"weird": "thing"})
    assert isinstance(back, CreativeError)
    assert "raw" in back.detail


def test_error_message_default_falls_back_to_class_name():
    err = AuthError()
    assert err.message == "AuthError"
