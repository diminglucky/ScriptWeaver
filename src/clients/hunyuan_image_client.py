"""鑵捐娣峰厓鏂囩敓鍥惧鎴风

API鏂囨。锛歨ttps://cloud.tencent.com/document/api/1729/108738
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
from urllib.parse import urlencode

import requests
from PIL import Image


@dataclass
class HunyuanImageResult:
    """鑵捐娣峰厓鍥剧墖鐢熸垚缁撴灉"""
    image: Image.Image
    provider: str = "hunyuan"
    model: str = "hunyuan-turbo"


class HunyuanImageClient:
    """鑵捐娣峰厓鏂囩敓鍥惧鎴风
    
    浣跨敤鑵捐浜慉PI 3.0瑙勮寖杩涜璋冪敤
    """
    
    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        region: str = "ap-guangzhou",
        timeout_seconds: int = 120
    ):
        """鍒濆鍖栬吘璁贩鍏冨鎴风
        
        Args:
            secret_id: 鑵捐浜慡ecretId
            secret_key: 鑵捐浜慡ecretKey
            region: 鍦板煙锛岄粯璁p-guangzhou
            timeout_seconds: 瓒呮椂鏃堕棿
        """
        if not secret_id or not secret_key:
            raise RuntimeError("闇€瑕佹彁渚涜吘璁簯SecretId鍜孲ecretKey")
        
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.timeout = timeout_seconds
        self.endpoint = "hunyuan.tencentcloudapi.com"
        self.service = "hunyuan"
        self.version = "2023-09-01"
    
    def _sign(self, params: dict, timestamp: int) -> str:
        """鐢熸垚鑵捐浜慉PI绛惧悕
        
        Args:
            params: 璇锋眰鍙傛暟
            timestamp: 鏃堕棿鎴?
            
        Returns:
            绛惧悕瀛楃涓?
        """
        # 1. 鎷兼帴瑙勮寖璇锋眰涓?
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
        
        # 2. 鎷兼帴寰呯鍚嶅瓧绗︿覆
        algorithm = "TC3-HMAC-SHA256"
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
        
        # 3. 璁＄畻绛惧悕
        def _hmac_sha256(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
        
        secret_date = _hmac_sha256(("TC3" + self.secret_key).encode("utf-8"), date)
        secret_service = _hmac_sha256(secret_date, self.service)
        secret_signing = _hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        
        # 4. 鎷兼帴Authorization
        authorization = (
            f"{algorithm} "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        
        return authorization
    
    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        style: Optional[str] = "201",
        resolution: str = "1024x1024",
        logo_add: int = 1,
        rsp_img_type: str = "base64"
    ) -> HunyuanImageResult:
        """鐢熸垚鍥剧墖
        
        Args:
            prompt: 鏂囨湰鎻忚堪锛堝繀閫夛級
            negative_prompt: 鍙嶅悜鏂囨湰鎻忚堪锛堝彲閫夛級
            style: 缁樼敾椋庢牸缂栧彿锛堝彲閫夛紝榛樿201-鏃ョ郴鍔ㄦ极椋庢牸锛?
            resolution: 鍒嗚鲸鐜囷紙鍙€夛紝榛樿1024x1024锛?
            logo_add: 鏄惁娣诲姞鏍囪瘑锛?-娣诲姞锛?-涓嶆坊鍔狅級
            rsp_img_type: 杩斿洖鍥惧儚鏂瑰紡锛坆ase64鎴杣rl锛?
            
        Returns:
            HunyuanImageResult瀵硅薄
        """
        # 鏋勫缓璇锋眰鍙傛暟
        params = {
            "Prompt": prompt,
            "Resolution": resolution,
            "LogoAdd": logo_add,
            "RspImgType": rsp_img_type
        }
        
        if negative_prompt:
            params["NegativePrompt"] = negative_prompt
        
        if style:
            params["Style"] = style
        
        # 鏃堕棿鎴?
        timestamp = int(time.time())
        
        # 鐢熸垚绛惧悕
        authorization = self._sign(params, timestamp)
        
        # 鏋勫缓璇锋眰澶?
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Host": self.endpoint,
            "X-TC-Action": "TextToImageLite",
            "X-TC-Version": self.version,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Region": self.region
        }
        
        # 鍙戦€佽姹?
        url = f"https://{self.endpoint}"
        response = requests.post(
            url,
            headers=headers,
            json=params,
            timeout=self.timeout
        )
        
        # 瑙ｆ瀽鍝嶅簲
        if response.status_code != 200:
            raise RuntimeError(f"API璇锋眰澶辫触: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if "Response" not in result:
            raise RuntimeError(f"API杩斿洖鏍煎紡閿欒: {result}")
        
        if "Error" in result["Response"]:
            error = result["Response"]["Error"]
            raise RuntimeError(f"API閿欒: {error.get('Code', 'Unknown')} - {error.get('Message', 'Unknown')}")
        
        # 鑾峰彇鐢熸垚鐨勫浘鐗?
        result_image = result["Response"].get("ResultImage", "")
        
        if rsp_img_type == "base64":
            # Base64瑙ｇ爜
            img_bytes = base64.b64decode(result_image)
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
        else:
            # URL鏂瑰紡锛岄渶瑕佷笅杞藉浘鐗?
            img_response = requests.get(result_image, timeout=30)
            img = Image.open(BytesIO(img_response.content)).convert("RGB")
        
        return HunyuanImageResult(
            image=img,
            provider="hunyuan",
            model="hunyuan-turbo"
        )


if __name__ == "__main__":
    # 娴嬭瘯浠ｇ爜
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
            rsp_img_type="base64"
        )
        print(f"Generation succeeded, image size: {result.image.size}")
        result.image.save("test_hunyuan.png")
    else:
        print("Set HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY first.")

