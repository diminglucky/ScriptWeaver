from types import SimpleNamespace

import pytest

from src.clients.chat_response import extract_chat_content, is_html_page


def test_extract_chat_content_accepts_plain_string():
    assert extract_chat_content("generated text") == "generated text"


def test_extract_chat_content_rejects_html_error_page():
    with pytest.raises(RuntimeError, match="HTML 网页"):
        extract_chat_content("<!doctype html><html><title>API Gateway</title></html>")


def test_is_html_page_only_matches_document_prefix():
    assert is_html_page("\n<html lang='zh-CN'>")
    assert not is_html_page("故事正文中提到了 <html> 标签")


def test_extract_chat_content_accepts_mapping_response():
    response = {"choices": [{"message": {"content": "generated text"}}]}
    assert extract_chat_content(response) == "generated text"


def test_extract_chat_content_accepts_sdk_response_object():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="generated text"))]
    )
    assert extract_chat_content(response) == "generated text"


def test_extract_chat_content_rejects_unknown_response():
    with pytest.raises(RuntimeError, match="AI 返回格式异常"):
        extract_chat_content(object())
