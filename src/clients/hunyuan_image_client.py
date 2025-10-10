"""腾讯混元文生图客户端

API文档：https://cloud.tencent.com/document/api/1729/108738
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
    """腾讯混元图片生成结果"""
    image: Image.Image
    provider: str = "hunyuan"
    model: str = "hunyuan-turbo"


class HunyuanImageClient:
    """腾讯混元文生图客户端
    
    使用腾讯云API 3.0规范进行调用
    """
    
    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        region: str = "ap-guangzhou",
        timeout_seconds: int = 120
    ):
        """初始化腾讯混元客户端
        
        Args:
            secret_id: 腾讯云SecretId
            secret_key: 腾讯云SecretKey
            region: 地域，默认ap-guangzhou
            timeout_seconds: 超时时间
        """
        if not secret_id or not secret_key:
            raise RuntimeError("需要提供腾讯云SecretId和SecretKey")
        
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.timeout = timeout_seconds
        self.endpoint = "hunyuan.tencentcloudapi.com"
        self.service = "hunyuan"
        self.version = "2023-09-01"
    
    def _sign(self, params: dict, timestamp: int) -> str:
        """生成腾讯云API签名
        
        Args:
            params: 请求参数
            timestamp: 时间戳
            
        Returns:
            签名字符串
        """
        # 1. 拼接规范请求串
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
        
        # 2. 拼接待签名字符串
        algorithm = "TC3-HMAC-SHA256"
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
        
        # 3. 计算签名
        def _hmac_sha256(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
        
        secret_date = _hmac_sha256(("TC3" + self.secret_key).encode("utf-8"), date)
        secret_service = _hmac_sha256(secret_date, self.service)
        secret_signing = _hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        
        # 4. 拼接Authorization
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
        """生成图片
        
        Args:
            prompt: 文本描述（必选）
            negative_prompt: 反向文本描述（可选）
            style: 绘画风格编号（可选，默认201-日系动漫风格）
            resolution: 分辨率（可选，默认1024x1024）
            logo_add: 是否添加标识（1-添加，0-不添加）
            rsp_img_type: 返回图像方式（base64或url）
            
        Returns:
            HunyuanImageResult对象
        """
        # 构建请求参数
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
        
        # 时间戳
        timestamp = int(time.time())
        
        # 生成签名
        authorization = self._sign(params, timestamp)
        
        # 构建请求头
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Host": self.endpoint,
            "X-TC-Action": "TextToImageLite",
            "X-TC-Version": self.version,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Region": self.region
        }
        
        # 发送请求
        url = f"https://{self.endpoint}"
        response = requests.post(
            url,
            headers=headers,
            json=params,
            timeout=self.timeout
        )
        
        # 解析响应
        if response.status_code != 200:
            raise RuntimeError(f"API请求失败: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if "Response" not in result:
            raise RuntimeError(f"API返回格式错误: {result}")
        
        if "Error" in result["Response"]:
            error = result["Response"]["Error"]
            raise RuntimeError(f"API错误: {error.get('Code', 'Unknown')} - {error.get('Message', 'Unknown')}")
        
        # 获取生成的图片
        result_image = result["Response"].get("ResultImage", "")
        
        if rsp_img_type == "base64":
            # Base64解码
            img_bytes = base64.b64decode(result_image)
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
        else:
            # URL方式，需要下载图片
            img_response = requests.get(result_image, timeout=30)
            img = Image.open(BytesIO(img_response.content)).convert("RGB")
        
        return HunyuanImageResult(
            image=img,
            provider="hunyuan",
            model="hunyuan-turbo"
        )


if __name__ == "__main__":
    # 测试代码
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    secret_id = os.getenv("HUNYUAN_SECRET_ID", "")
    secret_key = os.getenv("HUNYUAN_SECRET_KEY", "")
    
    if secret_id and secret_key:
        client = HunyuanImageClient(secret_id, secret_key)
        result = client.generate(
            prompt="雨中, 竹林, 小路",
            resolution="1024x1024",
            rsp_img_type="base64"
        )
        print(f"生成成功，图片大小: {result.image.size}")
        result.image.save("test_hunyuan.png")
    else:
        print("请设置HUNYUAN_SECRET_ID和HUNYUAN_SECRET_KEY环境变量")

