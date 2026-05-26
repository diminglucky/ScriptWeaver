from __future__ import annotations

from typing import Any

import httpx

from .errors import error_from_payload


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def request_json(
    method: str,
    url: str,
    *,
    token: str = "",
    json: dict | None = None,
    timeout: float = 30.0,
) -> Any:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.request(method, url, json=json, headers=auth_headers(token))
    if resp.status_code >= 400:
        try:
            payload = resp.json()
        except Exception:
            payload = {"code": "creative_error", "message": resp.text, "detail": {"status_code": resp.status_code}}
        raise error_from_payload(payload)
    if not resp.content:
        return {}
    return resp.json()


async def stream_request(
    method: str,
    url: str,
    *,
    token: str = "",
    timeout: float | None = None,
):
    client = httpx.AsyncClient(timeout=timeout)
    try:
        req = client.build_request(method, url, headers=auth_headers(token))
        resp = await client.send(req, stream=True)
        if resp.status_code >= 400:
            try:
                payload = await resp.aread()
                raise error_from_payload(resp.json() if payload else {})
            finally:
                await client.aclose()
        return resp, client
    except Exception:
        await client.aclose()
        raise
