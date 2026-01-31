"""
AI服务 - 角色分析和外貌设计
基于2025最佳实践优化
"""

import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize


@dataclass
class AIConfig:
    api_key: str
    base_url: str = ""
    model: str = ""


class AIService:
    """AI服务"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.client = DeepSeekClient(
            api_key=_sanitize(config.api_key),
            base_url=_sanitize(config.base_url),
            model=_sanitize(config.model),
        )
    
    def chat(self, messages: List[Dict], temperature: float = 0.7) -> str:
        return self.client.chat(messages, temperature=temperature)
    
    def extract_characters(self, story_text: str) -> List[Dict]:
        """从故事中提取角色设定"""
        prompt = f"""你是专业的人物分析师。请从故事中深度分析所有关键人物。

故事：
{story_text}

返回JSON格式：
{{
  "characters": [
    {{
      "name": "名字",
      "role": "主角/配角/反派",
      "gender": "男/女",
      "age_hint": "年龄线索",
      "identity": "身份职业",
      "personality": ["性格1", "性格2"],
      "atmosphere": "整体气质",
      "story_role": "故事作用",
      "appearance_hints": "外貌线索"
    }}
  ]
}}

要求：按重要性排序，最多8人，确保JSON有效"""

        response = self.chat([{"role": "user", "content": prompt}], temperature=0.5)
        
        try:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group()).get("characters", [])
        except:
            pass
        
        return [{"name": line.strip()} for line in response.split('\n') 
                if line.strip() and len(line.strip()) <= 10]
    
    def design_character_appearance(
        self, 
        character_name: str, 
        profile: Dict, 
        story_text: str
    ) -> Dict:
        """
        设计角色外貌 - 优化版
        
        关键改进：
        1. 生成结构化的视觉特征（用于构建一致性DNA）
        2. 生成禁止漂移说明
        3. 生成独特标记提高辨识度
        """
        profile_text = self._build_profile_text(profile)
        
        prompt = f"""你是专业的人物形象设计师。请为"{character_name}"设计独特的外貌形象。

## 角色设定
{profile_text}

## 故事背景
{story_text[:2000]}

## 设计要求
根据角色性格、身份、气质，设计外貌。返回JSON格式：

```json
{{
  "description": "完整外貌描述（200-300字），具体、视觉化",
  "visual_features": {{
    "face_shape": "脸型（方脸/瓜子脸/圆脸/鹅蛋脸）",
    "eye_features": "眼睛特征（剑眉星目/丹凤眼/桃花眼）",
    "nose_features": "鼻子特征（高挺/小巧）",
    "skin_tone": "肤色（白皙/小麦色/古铜色）",
    "body_type": "体型（高大魁梧/修长挺拔/苗条）",
    "hair_style": "发型（利落短发/长发飘逸）",
    "hair_color": "发色（黑色/深棕色）",
    "default_outfit": "默认服装",
    "unique_marks": ["独特标记1（如：右眉角疤痕）", "独特标记2"],
    "do_not_change": ["不能改变的特征1", "不能改变的特征2"]
  }},
  "dna_prompt": "角色DNA提示词（用于AI绘图的核心描述，英文，50-80词）"
}}
```

## 设计原则
1. 外貌与性格匹配（阴险→细长眼/薄唇，温柔→柔和轮廓）
2. 独特标记提高辨识度（疤痕/痣/配饰）
3. 特征要具体，不要模糊
4. dna_prompt是关键，要包含所有核心特征"""

        response = self.chat([{"role": "user", "content": prompt}], temperature=0.8)
        
        try:
            match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if not match:
                match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                json_str = match.group(1) if '```' in response else match.group()
                return json.loads(json_str)
        except:
            pass
        
        return {"description": response.strip(), "visual_features": {}, "dna_prompt": ""}
    
    def _build_profile_text(self, profile: Dict) -> str:
        parts = []
        mappings = [
            ("role", "角色定位"), ("gender", "性别"), ("age_hint", "年龄"),
            ("identity", "身份职业"), ("atmosphere", "整体气质"),
        ]
        for key, label in mappings:
            if profile.get(key):
                parts.append(f"- {label}：{profile[key]}")
        if profile.get("personality"):
            p = profile["personality"]
            parts.append(f"- 性格特点：{', '.join(p) if isinstance(p, list) else p}")
        return "\n".join(parts) if parts else "（请根据故事推断）"
    
    def translate_to_english(self, chinese_prompt: str, style: str = "realistic") -> str:
        """翻译为英文提示词"""
        instruction = f"""Translate to concise English prompt for AI image generation ({style} style).
Keep core visual elements. Max 150 words. Output English only.

Chinese:
{chinese_prompt[:600]}"""
        
        return self.chat([{"role": "user", "content": instruction}], temperature=0.3).strip()


def create_ai_service(api_presets: Dict, selected_api: str) -> Optional[AIService]:
    if selected_api not in api_presets:
        return None
    cfg = api_presets[selected_api]
    if not cfg.get("key"):
        return None
    return AIService(AIConfig(
        api_key=cfg.get("key", ""),
        base_url=cfg.get("base_url", ""),
        model=cfg.get("model", ""),
    ))
