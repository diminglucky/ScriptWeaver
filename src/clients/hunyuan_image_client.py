"""Tencent Hunyuan text-to-image client.

API documentation: https://cloud.tencent.com/document/api/1729/108738
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Optional

import requests
from PIL import Image


@dataclass
class HunyuanImageResult:
    """Tencent Hunyuan image generation result."""

    image: Image.Image
    provider: str = "hunyuan"
    model: str = "hunyuan-turbo"


class HunyuanImageClient:
    """Tencent Hunyuan text-to-image client using the API 3.0 signing flow."""

    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        region: str = "ap-guangzhou",
        timeout_seconds: int = 120,
    ):
        if not secret_id or not secret_key:
            raise RuntimeError("Tencent Cloud SecretId and SecretKey are required")

        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.timeout = timeout_seconds
        self.endpoint = "hunyuan.tencentcloudapi.com"
        self.service = "hunyuan"
        self.version = "2023-09-01"

    def _sign(self, params: dict, timestamp: int) -> str:
        """Create a Tencent Cloud API 3.0 authorization header."""
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = f"content-type:application/json\nhost:{self.endpoint}\n"
        signed_headers = "content-type;host"
        payload = json.dumps(params)
        hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        canonical_request = (
            f"{http_request_method}\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hashed_request_payload}"
        )

        algorithm = "TC3-HMAC-SHA256"
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(
            canonical_request.encode("utf-8")
        ).hexdigest()
        string_to_sign = (
            f"{algorithm}\n{timestamp}\n{credential_scope}\n"
            f"{hashed_canonical_request}"
        )

        def _hmac_sha256(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        secret_date = _hmac_sha256(
            ("TC3" + self.secret_key).encode("utf-8"),
            date,
        )
        secret_service = _hmac_sha256(secret_date, self.service)
        secret_signing = _hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(
            secret_signing,
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return (
            f"{algorithm} "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        style: Optional[str] = "201",
        resolution: str = "1024x1024",
        logo_add: int = 1,
        rsp_img_type: str = "base64",
    ) -> HunyuanImageResult:
        """Generate an image and return the decoded PIL image."""
        params = self._build_generate_params(
            prompt=prompt,
            resolution=resolution,
            logo_add=logo_add,
            rsp_img_type=rsp_img_type,
            negative_prompt=negative_prompt,
            style=style,
        )
        timestamp = int(time.time())
        headers = self._build_generate_headers(params=params, timestamp=timestamp)
        response = self._request_generate(params=params, headers=headers)
        result_image = self._parse_generate_response(response)
        image = self._decode_result_image(
            result_image=result_image,
            rsp_img_type=rsp_img_type,
        )
        return HunyuanImageResult(
            image=image,
            provider="hunyuan",
            model="hunyuan-turbo",
        )

    def _build_generate_params(
        self,
        *,
        prompt: str,
        resolution: str,
        logo_add: int,
        rsp_img_type: str,
        negative_prompt: Optional[str],
        style: Optional[str],
    ) -> dict:
        params = {
            "Prompt": prompt,
            "Resolution": resolution,
            "LogoAdd": logo_add,
            "RspImgType": rsp_img_type,
        }
        if negative_prompt:
            params["NegativePrompt"] = negative_prompt
        if style:
            params["Style"] = style
        return params

    def _build_generate_headers(self, *, params: dict, timestamp: int) -> dict:
        authorization = self._sign(params, timestamp)
        return {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Host": self.endpoint,
            "X-TC-Action": "TextToImageLite",
            "X-TC-Version": self.version,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Region": self.region,
        }

    def _request_generate(self, *, params: dict, headers: dict):
        url = f"https://{self.endpoint}"
        return requests.post(
            url,
            headers=headers,
            json=params,
            timeout=self.timeout,
        )

    def _parse_generate_response(self, response) -> str:
        if response.status_code != 200:
            raise RuntimeError(
                f"API request failed: {response.status_code} - {response.text}"
            )
        result = response.json()
        if "Response" not in result:
            raise RuntimeError(f"Unexpected API response: {result}")
        if "Error" in result["Response"]:
            error = result["Response"]["Error"]
            raise RuntimeError(
                f"API error: {error.get('Code', 'Unknown')} - "
                f"{error.get('Message', 'Unknown')}"
            )
        return result["Response"].get("ResultImage", "")

    def _decode_result_image(
        self,
        *,
        result_image: str,
        rsp_img_type: str,
    ) -> Image.Image:
        if rsp_img_type == "base64":
            img_bytes = base64.b64decode(result_image)
            return Image.open(BytesIO(img_bytes)).convert("RGB")
        img_response = requests.get(result_image, timeout=30)
        return Image.open(BytesIO(img_response.content)).convert("RGB")


if __name__ == "__main__":
    import os

    try:
        from dotenv import load_dotenv
    except Exception:
        def load_dotenv(*args, **kwargs):
            return False

    load_dotenv()

    secret_id = os.getenv("HUNYUAN_SECRET_ID", "")
    secret_key = os.getenv("HUNYUAN_SECRET_KEY", "")

    if secret_id and secret_key:
        client = HunyuanImageClient(secret_id, secret_key)
        result = client.generate(
            prompt="rainy bamboo forest path",
            resolution="1024x1024",
            rsp_img_type="base64",
        )
        print(f"Generation succeeded, image size: {result.image.size}")
        result.image.save("test_hunyuan.png")
    else:
        print("Set HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY first.")
