"""Character turnaround-sheet generation mixin."""

from tkinter import DISABLED, NORMAL, messagebox
import threading
from typing import Optional

from PIL import Image

from src.clients.image_client import OpenAIImageClient

from ...helpers.character_prompt_builder import CharacterPromptBuilder


class _TurnaroundAbortError(Exception):
    """Raised when turnaround generation is aborted after showing user-facing error."""


class CharacterTurnaroundMixin:
    """Generate turnaround sheets used for character consistency."""
    def _on_generate_turnaround_sheet(self) -> None:
        """生成三视图组合图（正面+侧面+背面在一张图上）
        
        借鉴自 DirectorAI 项目的人物一致性方案：
        生成单张组合图，用于后续图片生成时作为参考，保持人物一致性
        """
        request = self._prepare_turnaround_request()
        if request is None:
            return

        threading.Thread(
            target=lambda: self._run_turnaround_generation_task(request),
            daemon=True,
        ).start()

    def _prepare_turnaround_request(self) -> Optional[dict]:
        """校验输入并组装三视图生成请求。"""
        print("🎯 开始生成三视图组合图")

        selection = self.char_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个人物！")
            return None

        index = selection[0]
        character = self.character_list[index]
        character_name, description = self._extract_character_identity(character)

        if not description:
            messagebox.showwarning("提示", "请先设计人物外貌！")
            return None
        if not self.current_project:
            messagebox.showwarning("提示", "请先创建或打开一个项目！")
            return None

        self.char_btn_turnaround.config(state=DISABLED)
        self.status.set(f"🎯 正在生成\"{character_name}\"的三视图组合图...")
        self._header_status("生成三视图...", "🎯")

        turnaround_prompt = self._build_turnaround_prompt(description)
        turnaround_prompt = CharacterPromptBuilder.sanitize_for_image_safety(turnaround_prompt, language="en")
        style = self.char_img_style.get()
        print(f"📝 三视图提示词: {turnaround_prompt[:200]}...")

        return {
            "character": character,
            "character_name": character_name,
            "description": description,
            "style": style,
            "turnaround_prompt": turnaround_prompt,
        }

    def _extract_character_identity(self, character) -> tuple[str, str]:
        """兼容新旧人物对象结构，返回人物名与描述。"""
        from ...models.character import Character

        if isinstance(character, Character):
            return character.name, character.description
        return character["name"], character.get("description", "")

    def _run_turnaround_generation_task(self, request: dict) -> None:
        """后台执行三视图生成与保存。"""
        try:
            image = self._generate_turnaround_image(request)
            self.character_last_image = image
            save_path = self._save_turnaround_image(request["character_name"], image)
            self._attach_turnaround_to_character(request["character"], save_path)
            self._ui(lambda: self._on_turnaround_generation_success(image, save_path))
        except _TurnaroundAbortError:
            pass
        except Exception as exc:
            import traceback

            error_detail = traceback.format_exc()
            print(f"❌ 生成三视图失败:\n{error_detail}")
            self._ui(lambda: messagebox.showerror("错误", f"生成失败: {str(exc)}"))
            self._ui(lambda: self.status.set("❌ 三视图生成失败"))
        finally:
            self._ui(lambda: self.char_btn_turnaround.config(state=NORMAL))

    def _generate_turnaround_image(self, request: dict) -> Image.Image:
        """根据当前图片提供商生成三视图图片。"""
        img_api_type = self.img_api_type.get() if hasattr(self, "img_api_type") else "openai"
        if img_api_type == "hunyuan":
            return self._generate_turnaround_image_hunyuan(request)
        return self._generate_turnaround_image_openai(request)

    def _generate_turnaround_image_hunyuan(self, request: dict) -> Image.Image:
        """调用腾讯混元生成三视图。"""
        import base64
        from io import BytesIO

        from src.clients.hunyuan_image_client import HunyuanImageClient

        secret_id = self.hunyuan_secret_id.get() if hasattr(self, "hunyuan_secret_id") else ""
        secret_key = self.hunyuan_secret_key.get() if hasattr(self, "hunyuan_secret_key") else ""
        if not secret_id or not secret_key:
            self._ui(lambda: messagebox.showerror("错误", "请先在【设置 → 图片生成 API】配置腾讯混元API密钥"))
            raise _TurnaroundAbortError()

        optimized_prompt = CharacterPromptBuilder.optimize_for_api(request["turnaround_prompt"], "hunyuan", 256)
        optimized_prompt = CharacterPromptBuilder.sanitize_for_image_safety(optimized_prompt, language="zh")
        self._ui(lambda: self.status.set("🚀 正在调用腾讯混元API..."))

        client = HunyuanImageClient(secret_id=secret_id, secret_key=secret_key)
        try:
            result = client.generate(prompt=optimized_prompt, resolution="1024:1024", style="201")
        except Exception as first_err:
            if "blocked" not in str(first_err).lower() and "safety" not in str(first_err).lower():
                raise
            retry_prompt = CharacterPromptBuilder.build_retry_prompt(
                description=request["description"],
                style=request["style"],
                view_angle="front",
                expression="neutral",
                composition="upper_body",
                language="zh",
            )
            result = client.generate(prompt=retry_prompt, resolution="1024:1024", style="201")

        img_base64 = result["ResultImage"]
        img_data = base64.b64decode(img_base64)
        with Image.open(BytesIO(img_data)) as tmp_img:
            return tmp_img.copy()

    def _resolve_openai_turnaround_config(self) -> tuple[str, Optional[str], str]:
        """读取 OpenAI 图片配置并合并预设默认值。"""
        api_key = self.img_api_key.get().strip() if hasattr(self, "img_api_key") else ""
        base_url = self.img_base_url.get().strip() if hasattr(self, "img_base_url") else ""
        model = self.img_model.get().strip() if hasattr(self, "img_model") else ""
        if hasattr(self, "img_api_preset") and hasattr(self, "img_api_presets"):
            preset_name = self.img_api_preset.get().strip()
            if preset_name in self.img_api_presets:
                cfg = self.img_api_presets[preset_name]
                if not model:
                    model = (cfg.get("model") or "").strip()
                if not api_key:
                    api_key = (cfg.get("key") or "").strip()
                if not base_url:
                    base_url = (cfg.get("base_url") or "").strip()

        return api_key, (base_url or None), (model or "dall-e-3")

    def _generate_turnaround_image_openai(self, request: dict) -> Image.Image:
        """调用 OpenAI 兼容图片接口生成三视图。"""
        api_key, base_url, model = self._resolve_openai_turnaround_config()
        if not api_key:
            self._ui(lambda: messagebox.showerror("错误", "请先在【设置 → 图片生成 API】配置API密钥"))
            raise _TurnaroundAbortError()

        self._ui(lambda: self.status.set("🚀 正在调用图片API..."))
        client = OpenAIImageClient(api_key=api_key, base_url=base_url, model=model)
        try:
            results = client.generate(request["turnaround_prompt"], size="1024x1024")
        except Exception as first_err:
            if "blocked" not in str(first_err).lower() and "safety" not in str(first_err).lower():
                raise
            retry_prompt = CharacterPromptBuilder.build_retry_prompt(
                description=request["description"],
                style=request["style"],
                view_angle="front",
                expression="neutral",
                composition="upper_body",
                language="en",
            )
            results = client.generate(retry_prompt, size="1024x1024")

        if not results:
            raise RuntimeError("API未返回任何图片")
        return results[0].image

    def _save_turnaround_image(self, character_name: str, image: Image.Image):
        """保存三视图到当前项目目录。"""
        import re

        characters_dir = self.current_project.project_dir / "characters"
        characters_dir.mkdir(parents=True, exist_ok=True)
        clean_name = re.sub(r"[^\w\s\u4e00-\u9fff-]", "", character_name)
        save_path = characters_dir / f"{clean_name}_三视图.png"
        image.save(str(save_path))
        print(f"✅ 三视图已保存: {save_path}")
        return save_path

    def _attach_turnaround_to_character(self, character, save_path) -> None:
        """将生成结果写回人物数据。"""
        from ...models.character import Character

        if isinstance(character, Character):
            character.turnaround_image = str(save_path)
            if character.dna:
                character.dna.anchor_image = str(save_path)
            return
        character["turnaround_image"] = str(save_path)

    def _on_turnaround_generation_success(self, image: Image.Image, save_path) -> None:
        """主线程更新三视图成功后的 UI。"""
        self._update_character_photo_preview(image)
        self.status.set("✅ 三视图组合图已生成！可用于保持人物一致性")
        self._header_status("三视图完成", "✅")

        messagebox.showinfo(
            "成功",
            f"三视图组合图已生成！\n\n"
            f"📁 保存位置：{save_path}\n\n"
            f"💡 用途：在后续生成分镜图片时，\n"
            f"   可将此图作为参考，保持人物一致性",
        )
        self._update_reference_character_list()
    
    def _build_turnaround_prompt(self, description: str) -> str:
        """构建三视图组合提示词
        
        借鉴自 DirectorAI 的 _buildCombinedViewPrompt 方法
        """
        # 提取核心特征
        base_desc = description if description else "A character"
        
        # 根据图片风格调整提示词
        style = self.char_img_style.get() if hasattr(self, 'char_img_style') else "写实照片"
        
        if "动漫" in style or "漫画" in style:
            style_prefix = "anime style, manga art, 2D animation, cel shaded"
        elif "3D" in style:
            style_prefix = "3D render, highly detailed, professional 3D character"
        elif "国风" in style or "古风" in style or "中国风" in style:
            style_prefix = "Chinese traditional style, ink wash painting style"
        else:
            style_prefix = "realistic portrait, professional photography, high quality"
        
        # 组合三视图提示词
        prompt = f"""Character turnaround reference sheet with three views arranged horizontally:

LEFT PANEL: Front view (character facing camera directly)
CENTER PANEL: Three-quarter view (character at 45 degree angle)  
RIGHT PANEL: Back view (showing character's back)

Character Description: {base_desc}

Style: {style_prefix}
Layout: Three full body shots side by side in ONE single image
Composition: All three poses same size, equal spacing, full body visible
Background: Plain white or light gray background
Quality: High quality, detailed, 4K, consistent appearance across all three views
Pose: Neutral standing pose, arms slightly away from body

IMPORTANT: This is a CHARACTER REFERENCE SHEET for maintaining consistency. 
The same character must appear in all three panels with identical features."""
        
        return prompt
    
    
    
    
