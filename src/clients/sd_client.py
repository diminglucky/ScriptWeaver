"""
Stable Diffusion API客户端
支持本地部署的SD WebUI API
"""

import requests
import base64
from io import BytesIO
from PIL import Image
from typing import Optional, Dict, Any
import os


class StableDiffusionClient:
    """Stable Diffusion WebUI API 客户端"""
    
    def __init__(self, base_url: str = None):
        """
        初始化SD客户端
        
        Args:
            base_url: SD WebUI API地址，例如 http://localhost:7860
        """
        self.base_url = base_url or os.getenv("SD_BASE_URL", "http://localhost:7860")
        self.timeout = 300  # 5分钟超时
    
    def txt2img(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        sampler_name: str = "Euler a",
        seed: int = -1,
        batch_size: int = 1,
        **kwargs
    ) -> Optional[list[Image.Image]]:
        """
        文生图
        
        Args:
            prompt: 正面提示词
            negative_prompt: 负面提示词
            width: 图片宽度
            height: 图片高度
            steps: 采样步数
            cfg_scale: CFG系数
            sampler_name: 采样器名称
            seed: 随机种子 (-1为随机)
            batch_size: 批次大小
            **kwargs: 其他参数
            
        Returns:
            生成的图片列表，失败返回None
        """
        url = f"{self.base_url}/sdapi/v1/txt2img"
        
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler_name": sampler_name,
            "seed": seed,
            "batch_size": batch_size,
            **kwargs
        }
        
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            images = []
            
            # 解析返回的base64图片
            for img_data in result.get("images", []):
                img_bytes = base64.b64decode(img_data)
                img = Image.open(BytesIO(img_bytes))
                images.append(img)
            
            return images if images else None
            
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"无法连接到SD服务器: {self.base_url}")
        except requests.exceptions.Timeout:
            raise TimeoutError(f"请求超时（{self.timeout}秒）")
        except Exception as e:
            raise RuntimeError(f"SD API错误: {str(e)}")
    
    def img2img(
        self,
        init_image: Image.Image,
        prompt: str,
        negative_prompt: str = "",
        denoising_strength: float = 0.75,
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        sampler_name: str = "Euler a",
        seed: int = -1,
        **kwargs
    ) -> Optional[list[Image.Image]]:
        """
        图生图
        
        Args:
            init_image: 初始图片
            prompt: 正面提示词
            negative_prompt: 负面提示词
            denoising_strength: 重绘幅度 (0-1)
            width: 图片宽度
            height: 图片高度
            steps: 采样步数
            cfg_scale: CFG系数
            sampler_name: 采样器名称
            seed: 随机种子
            **kwargs: 其他参数
            
        Returns:
            生成的图片列表，失败返回None
        """
        url = f"{self.base_url}/sdapi/v1/img2img"
        
        # 将PIL图片转为base64
        buffered = BytesIO()
        init_image.save(buffered, format="PNG")
        init_image_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        payload = {
            "init_images": [init_image_base64],
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "denoising_strength": denoising_strength,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler_name": sampler_name,
            "seed": seed,
            **kwargs
        }
        
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            images = []
            
            for img_data in result.get("images", []):
                img_bytes = base64.b64decode(img_data)
                img = Image.open(BytesIO(img_bytes))
                images.append(img)
            
            return images if images else None
            
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"无法连接到SD服务器: {self.base_url}")
        except requests.exceptions.Timeout:
            raise TimeoutError(f"请求超时（{self.timeout}秒）")
        except Exception as e:
            raise RuntimeError(f"SD API错误: {str(e)}")
    
    def get_samplers(self) -> list[str]:
        """获取可用的采样器列表"""
        url = f"{self.base_url}/sdapi/v1/samplers"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            samplers = response.json()
            return [s["name"] for s in samplers]
        except:
            # 返回常用采样器列表作为后备
            return [
                "Euler a", "Euler", "LMS", "Heun", "DPM2", "DPM2 a",
                "DPM++ 2S a", "DPM++ 2M", "DPM++ SDE", "DPM fast",
                "DPM adaptive", "LMS Karras", "DPM2 Karras", "DPM2 a Karras",
                "DPM++ 2S a Karras", "DPM++ 2M Karras", "DPM++ SDE Karras",
                "DDIM", "PLMS"
            ]
    
    def get_models(self) -> list[str]:
        """获取可用的模型列表"""
        url = f"{self.base_url}/sdapi/v1/sd-models"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            models = response.json()
            return [m["model_name"] for m in models]
        except:
            return []
    
    def get_current_model(self) -> Optional[str]:
        """获取当前使用的模型"""
        url = f"{self.base_url}/sdapi/v1/options"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            options = response.json()
            return options.get("sd_model_checkpoint")
        except:
            return None
    
    def set_model(self, model_name: str) -> bool:
        """切换模型"""
        url = f"{self.base_url}/sdapi/v1/options"
        try:
            response = requests.post(
                url,
                json={"sd_model_checkpoint": model_name},
                timeout=60
            )
            response.raise_for_status()
            return True
        except:
            return False
    
    def test_connection(self) -> tuple[bool, str]:
        """测试连接"""
        try:
            url = f"{self.base_url}/sdapi/v1/sd-models"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            models = response.json()
            return True, f"连接成功！找到{len(models)}个模型"
        except requests.exceptions.ConnectionError:
            return False, f"无法连接到 {self.base_url}"
        except requests.exceptions.Timeout:
            return False, "连接超时"
        except Exception as e:
            return False, f"错误: {str(e)}"

