"""Character photo generation workflow mixin."""

from __future__ import annotations

from tkinter import DISABLED, END, NORMAL, messagebox

from PIL import Image

from src.clients.image_client import OpenAIImageClient

from ...helpers.character_prompt_builder import CharacterPromptBuilder

import logging

logger = logging.getLogger(__name__)


class _CharacterPhotoAbortError(RuntimeError):
    """Abort current generation flow without generic duplicate error popup."""


class CharacterPhotoGenerationMixin:
    """Generate character photos from selected character data."""

    _ANGLE_NAME_MAP = {
        "front": "正面",
        "side": "侧面",
        "back": "背面",
        "three-quarter": "斜侧",
    }

    _EXPRESSION_NAME_MAP = {
        "neutral": "中性",
        "happy": "开心",
        "sad": "悲伤",
        "angry": "愤怒",
        "surprised": "惊讶",
    }

    _VARIANT_NAME_MAP = {
        "formal": "正装",
        "casual": "休闲",
        "sport": "运动",
        "traditional": "古装",
        "artistic": "艺术",
        "professional": "职业",
    }

    def _on_generate_character_photo(self) -> None:
        """生成选中人物的照片"""
        print("🔔 _on_generate_character_photo 被调用")
        req = self._prepare_character_photo_generation_request()
        if req is None:
            return

        self.char_btn_gen_photo.config(state=DISABLED)
        self.status.set(f"🎨 正在生成\"{req['character_name']}\"的照片 (共{req['total_count']}张)...")
        self._header_status("生成人物照片...", "🎨")

        self._sync_img_runtime_before_generation()

        import threading

        threading.Thread(
            target=lambda: self._run_character_photo_generation(req),
            daemon=True,
        ).start()

    def _prepare_character_photo_generation_request(self):
        """解析并校验人物照片生成请求。"""
        selected = self._get_selected_character_for_photo_generation()
        if selected is None:
            return None
        index, character = selected

        character_name, description, character_dna = self._extract_character_photo_base_info(character)
        print(f"👤 选中人物: {character_name}")
        print(f"📝 描述长度: {len(description) if description else 0}")
        print(f"🧬 角色DNA: {'有' if character_dna else '无'}")

        if not description:
            messagebox.showwarning("提示", "请先设计人物外貌！")
            return None
        if not self.current_project:
            messagebox.showwarning("提示", "请先创建或打开一个项目，人物照片需要保存到项目中！")
            return None
        print(f"📁 当前项目: {self.current_project}")

        style = self.char_img_style.get()
        extra_desc = self.char_txt_extra.get("1.0", END).strip()
        options = self._collect_character_photo_generation_options()

        print(f"🎨 图片风格/类型: {style}")
        print(f"📝 额外描述: {extra_desc}")
        print(f"👁️ 视角: {options['view_angle']}")
        print(f"😊 表情: {options['expression']}")
        print(f"🎯 批量生成角度: {options['batch_generate']}")
        print(f"😊 批量生成表情: {options['batch_expressions']}")
        print(f"👔 服装变体模式: {options['variant_mode']}")
        if options["variant_mode"] != "none":
            print(f"👔 服装变体值: {options['variant_value']}")
        print(f"🎯 一致性级别: {options['consistency_level']}")

        angles_to_generate = self._resolve_character_photo_angles(
            options["batch_generate"],
            options["view_angle"],
        )
        expressions_to_generate = self._resolve_character_photo_expressions(
            options["batch_expressions"],
            options["expression"],
        )

        total_count = len(angles_to_generate) * len(expressions_to_generate)
        print(
            f"📦 总计将生成：{total_count} 张照片 "
            f"({len(angles_to_generate)}角度 × {len(expressions_to_generate)}表情)"
        )

        batch_type = self._resolve_character_photo_batch_type(
            batch_generate=options["batch_generate"],
            batch_expressions=options["batch_expressions"],
            variant_mode=options["variant_mode"],
        )
        print(f"🎯 批量类型: {batch_type}")
        print("🎯 一致性优化: 已启用（medium级别）")

        return {
            "index": index,
            "character_name": character_name,
            "description": description,
            "style": style,
            "extra_desc": extra_desc,
            "angles_to_generate": angles_to_generate,
            "expressions_to_generate": expressions_to_generate,
            "batch_generate": options["batch_generate"],
            "batch_expressions": options["batch_expressions"],
            "variant_mode": options["variant_mode"],
            "variant_value": options["variant_value"],
            "consistency_level": options["consistency_level"],
            "batch_type": batch_type,
            "total_count": total_count,
        }

    def _get_selected_character_for_photo_generation(self):
        """返回当前选中的角色索引和对象。"""
        selection = self.char_listbox.curselection()
        print(f"📋 当前选择: {selection}")
        if not selection:
            print("⚠️ 没有选择人物")
            messagebox.showwarning("提示", "请先从列表中选择一个人物！")
            return None
        index = selection[0]
        return index, self.character_list[index]

    def _extract_character_photo_base_info(self, character):
        """兼容新旧数据结构，提取人物名称/描述/DNA。"""
        from ...models.character import Character

        if isinstance(character, Character):
            return character.name, character.description, (character.dna.core_prompt if character.dna else "")
        return (
            character["name"],
            character.get("description", ""),
            character.get("dna_prompt", ""),
        )

    def _collect_character_photo_generation_options(self) -> dict:
        """读取人物生图选项。"""
        view_angle = self.char_view_angle.get() if hasattr(self, "char_view_angle") else "front"
        expression = self.char_expression.get() if hasattr(self, "char_expression") else "neutral"
        batch_generate = self.char_batch_generate.get() if hasattr(self, "char_batch_generate") else False
        batch_expressions = self.char_batch_expressions.get() if hasattr(self, "char_batch_expressions") else False
        variant_mode = self.char_variant_mode.get() if hasattr(self, "char_variant_mode") else "none"
        variant_preset = self.char_variant_preset.get() if hasattr(self, "char_variant_preset") else "casual"
        variant_custom = self.char_variant_custom.get() if hasattr(self, "char_variant_custom") else ""
        consistency_level = self.char_consistency_level.get() if hasattr(self, "char_consistency_level") else "high"

        if variant_mode == "preset":
            variant_value = variant_preset
        elif variant_mode == "custom":
            variant_value = variant_custom
        else:
            variant_value = ""

        return {
            "view_angle": view_angle,
            "expression": expression,
            "batch_generate": batch_generate,
            "batch_expressions": batch_expressions,
            "variant_mode": variant_mode,
            "variant_value": variant_value,
            "consistency_level": consistency_level,
        }

    def _resolve_character_photo_angles(self, batch_generate: bool, view_angle: str) -> list[tuple[str, str]]:
        """根据模式解析要生成的角度列表。"""
        if batch_generate:
            angles_to_generate = [("front", "正面"), ("side", "侧面"), ("back", "背面")]
            print(f"📦 批量角度模式：将生成 {len(angles_to_generate)} 个角度")
            return angles_to_generate
        angle_name = self._ANGLE_NAME_MAP.get(view_angle, "正面")
        print(f"📸 单一角度：{angle_name}")
        return [(view_angle, angle_name)]

    def _resolve_character_photo_expressions(self, batch_expressions: bool, expression: str) -> list[tuple[str, str]]:
        """根据模式解析要生成的表情列表。"""
        if batch_expressions:
            expressions_to_generate = [
                ("neutral", "中性"),
                ("happy", "开心"),
                ("sad", "悲伤"),
                ("angry", "愤怒"),
                ("surprised", "惊讶"),
            ]
            print(f"😊 批量表情模式：将生成 {len(expressions_to_generate)} 种表情")
            return expressions_to_generate
        expression_name = self._EXPRESSION_NAME_MAP.get(expression, "中性")
        print(f"😊 单一表情：{expression_name}")
        return [(expression, expression_name)]

    @staticmethod
    def _resolve_character_photo_batch_type(*, batch_generate: bool, batch_expressions: bool, variant_mode: str) -> str:
        """计算当前批量类型标签。"""
        if batch_generate and batch_expressions:
            return "angle+expression"
        if batch_generate:
            return "angle"
        if batch_expressions:
            return "expression"
        if variant_mode != "none":
            return "variant"
        return "none"

    def _sync_img_runtime_before_generation(self) -> None:
        """确保运行时图片配置已同步（即使用户未打开设置页）。"""
        if not hasattr(self, "_sync_img_runtime_from_config"):
            return
        try:
            selected_provider = ""
            if hasattr(self, "char_draw_api_var"):
                selected_provider = (self.char_draw_api_var.get() or "").strip()
            self._sync_img_runtime_from_config(selected_provider or None)
        except Exception as e:
            logger.debug("sync img runtime before generation failed: %s", e)

    def _resolve_img_runtime(self):
        """解析当前生图使用的 key/base_url/model，避免空模型发请求。"""
        import os

        key = self.img_api_key.get().strip() if hasattr(self, "img_api_key") else ""
        base_url = self.img_base_url.get().strip() if hasattr(self, "img_base_url") else ""
        model = self.img_model.get().strip() if hasattr(self, "img_model") else ""

        if hasattr(self, "img_api_preset") and hasattr(self, "img_api_presets"):
            preset_name = self.img_api_preset.get().strip()
            if preset_name and preset_name in self.img_api_presets:
                cfg = self.img_api_presets.get(preset_name, {})
                if not model:
                    model = (cfg.get("model") or "").strip()
                if not key:
                    key = (cfg.get("key") or "").strip()
                if not base_url:
                    base_url = (cfg.get("base_url") or "").strip()

        if not model and hasattr(self, "_get_current_img_model"):
            try:
                model = (self._get_current_img_model() or "").strip()
            except Exception as e:
                logger.debug("_get_current_img_model failed: %s", e)

        if not model:
            model = os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3").strip() or "dall-e-3"

        if hasattr(self, "img_model"):
            try:
                self.img_model.set(model)
            except Exception as e:
                logger.debug("set img_model failed: %s", e)

        return key, base_url, model

    @staticmethod
    def _is_safety_block_error(err: Exception) -> bool:
        err_lower = str(err).lower()
        return any(k in err_lower for k in ["blocked", "safety", "policy", "moderation", "content_filter"])

    def _run_character_photo_generation(self, req: dict) -> None:
        generated_photos = []
        character_name = req["character_name"]
        total_count = req["total_count"]

        try:
            print(f"\n{'='*60}\n开始生成人物照片: {character_name}\n{'='*60}")
            print(f"📦 将生成 {total_count} 张照片")

            img_api_type = self.img_api_type.get() if hasattr(self, "img_api_type") else "openai"
            print(f"图片API类型: {img_api_type}")

            current_index = 0
            for angle, angle_name in req["angles_to_generate"]:
                for expr, expr_name in req["expressions_to_generate"]:
                    current_index += 1
                    print(f"\n{'='*50}")
                    print(f"📸 [{current_index}/{total_count}] 正在生成：{angle_name}视图 + {expr_name}表情")
                    print(f"{'='*50}\n")

                    self.after(
                        0,
                        lambda i=current_index, a=angle_name, e=expr_name: self.status.set(
                            f"🎨 [{i}/{total_count}] 正在生成\"{character_name}\"的{a}照片（{e}）..."
                        ),
                    )
                    self._header_status(f"[{current_index}/{total_count}] {angle_name}+{expr_name}...", "🎨")

                    if img_api_type == "hunyuan":
                        img = self._generate_single_photo_hunyuan(req, angle, angle_name, expr, expr_name)
                    else:
                        img = self._generate_single_photo_openai(req, angle, angle_name, expr, expr_name)

                    self.character_last_image = img
                    print(f"✅ [{current_index}/{total_count}] {angle_name}+{expr_name}照片生成成功")

                    filename = self._build_character_photo_filename(
                        character_name=character_name,
                        angle=angle,
                        angle_name=angle_name,
                        expr=expr,
                        expr_name=expr_name,
                        batch_generate=req["batch_generate"],
                        batch_expressions=req["batch_expressions"],
                        variant_mode=req["variant_mode"],
                        variant_value=req["variant_value"],
                    )

                    saved_path = self._auto_save_character_photo_with_name(img, character_name, filename)
                    if saved_path:
                        print(f"💾 已保存: {saved_path}")
                        generated_photos.append(
                            {
                                "angle": angle,
                                "angle_name": angle_name,
                                "expression": expr,
                                "expression_name": expr_name,
                                "path": saved_path,
                                "image": img,
                            }
                        )

            self.after(0, lambda: self._finalize_character_photo_generation(character_name, generated_photos))

        except _CharacterPhotoAbortError:
            # 用户可见错误已在中途提示，不重复弹出
            pass
        except Exception as exc:
            self._handle_character_photo_generation_error(exc)
        finally:
            self._ui(lambda: self.char_btn_gen_photo.config(state=NORMAL))

    def _generate_single_photo_hunyuan(self, req: dict, angle: str, angle_name: str, expr: str, expr_name: str) -> Image.Image:
        """使用腾讯混元生成单张人物照片。"""
        import base64
        from io import BytesIO

        from src.clients.hunyuan_image_client import HunyuanImageClient

        print(f"使用腾讯混元API - {angle_name}视图 + {expr_name}表情")
        secret_id = self.hunyuan_secret_id.get() if hasattr(self, "hunyuan_secret_id") else ""
        secret_key = self.hunyuan_secret_key.get() if hasattr(self, "hunyuan_secret_key") else ""

        if not secret_id or not secret_key:
            print("腾讯混元API密钥未配置")
            self.after(0, lambda: messagebox.showerror("错误", "请先在【设置 → 图片生成 API】配置腾讯混元API密钥"))
            self.after(0, lambda: self.status.set("❌ 未配置API密钥"))
            self._header_status("未配置API", "❌")
            raise _CharacterPhotoAbortError("missing hunyuan key")

        composition = "upper_body" if req["style"] == "证件照" else "full_body"
        full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
            description=req["description"],
            style=req["style"],
            view_angle=angle,
            expression=expr,
            composition=composition,
            extra_details=req["extra_desc"],
            language="zh",
            default_nationality="chinese",
            variant=req["variant_value"],
            variant_mode=req["variant_mode"],
            consistency_level=req["consistency_level"],
            batch_type=req["batch_type"],
        )
        full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, "hunyuan", 256)
        full_prompt = CharacterPromptBuilder.sanitize_for_image_safety(full_prompt, language="zh")

        print(f"📝 腾讯混元提示词 ({angle_name}+{expr_name}): {full_prompt}")
        self._last_character_photo_prompt = full_prompt

        self.after(0, lambda a=angle_name, e=expr_name: self.status.set(f"🚀 正在调用腾讯混元API生成{a}+{e}照片..."))

        client = HunyuanImageClient(secret_id=secret_id, secret_key=secret_key)
        try:
            result = client.generate(prompt=full_prompt, resolution="1024:1024", style="201")
        except Exception as first_err:
            if not self._is_safety_block_error(first_err):
                raise
            retry_prompt = CharacterPromptBuilder.build_retry_prompt(
                description=req["description"],
                style="证件照",
                view_angle="front",
                expression="neutral",
                composition="upper_body",
                language="zh",
            )
            print(f"⚠️ 混元触发策略拦截，使用安全提示词重试：{retry_prompt[:200]}")
            self._last_character_photo_prompt = retry_prompt
            self.after(0, lambda a=angle_name, e=expr_name: self.status.set(f"⚠️ {a}+{e}触发策略拦截，正在安全重试..."))
            result = client.generate(prompt=retry_prompt, resolution="1024:1024", style="201")

        img_base64 = result["ResultImage"]
        img_data = base64.b64decode(img_base64)
        with Image.open(BytesIO(img_data)) as tmp_img:
            return tmp_img.copy()

    def _generate_single_photo_openai(self, req: dict, angle: str, angle_name: str, expr: str, expr_name: str) -> Image.Image:
        """使用 OpenAI 兼容接口生成单张人物照片。"""
        print(f"使用OpenAI或兼容API - {angle_name}视图 + {expr_name}表情")

        api_key, base_url, model = self._resolve_img_runtime()
        base_url = base_url or None
        model_lower = model.lower() if model else ""
        is_gemini_image = "gemini" in model_lower
        self._last_effective_img_model = model

        print(f"API Key存在: {bool(api_key)}, Base URL: {base_url}, Model: {model}")

        if not api_key:
            print("图片API密钥未配置")
            self.after(0, lambda: messagebox.showerror("错误", "请先在【设置 → 图片生成 API】配置API密钥"))
            self.after(0, lambda: self.status.set("❌ 未配置API密钥"))
            self._header_status("未配置API", "❌")
            raise _CharacterPhotoAbortError("missing openai key")

        if is_gemini_image:
            appearance_only = CharacterPromptBuilder.extract_appearance_only(req["description"])
            compact_prompt = (
                f"写实人像照片，成年人，{appearance_only}，{angle_name}视角，{expr_name}表情，"
                "上半身，纯色背景，自然光，高清"
            )
            full_prompt = CharacterPromptBuilder.sanitize_for_image_safety(compact_prompt, language="zh")
            full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, "openai", 320)
        else:
            composition = "upper_body" if req["style"] == "证件照" else "full_body"
            full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
                description=req["description"],
                style=req["style"],
                view_angle=angle,
                expression=expr,
                composition=composition,
                extra_details=req["extra_desc"],
                language="en",
                default_nationality="chinese",
                variant=req["variant_value"],
                variant_mode=req["variant_mode"],
                consistency_level=req["consistency_level"],
                batch_type=req["batch_type"],
            )
            full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, "openai", 1000)
            full_prompt = CharacterPromptBuilder.sanitize_for_image_safety(full_prompt, language="en")

        print(f"📝 OpenAI提示词 ({angle_name}+{expr_name}): {full_prompt[:200]}...")
        self._last_character_photo_prompt = full_prompt

        self.after(0, lambda a=angle_name, e=expr_name: self.status.set(f"🚀 正在调用图片API生成{a}+{e}照片..."))

        print("创建OpenAIImageClient...")
        client = OpenAIImageClient(api_key=api_key, base_url=base_url, model=model)
        print("调用generate方法...")
        try:
            results = client.generate(full_prompt, size="1024x1024")
        except Exception as first_err:
            if not self._is_safety_block_error(first_err):
                raise
            retry_lang = "zh" if is_gemini_image else "en"
            retry_prompt = CharacterPromptBuilder.build_retry_prompt(
                description=req["description"],
                style="证件照" if retry_lang == "zh" else "ID photo",
                view_angle="front",
                expression="neutral",
                composition="upper_body",
                language=retry_lang,
            )
            print(f"⚠️ OpenAI触发策略拦截，使用安全提示词重试：{retry_prompt[:220]}")
            self._last_character_photo_prompt = retry_prompt
            self.after(0, lambda a=angle_name, e=expr_name: self.status.set(f"⚠️ {a}+{e}触发策略拦截，正在安全重试..."))
            results = client.generate(retry_prompt, size="1024x1024")
            print(f"收到结果: {len(results) if results else 0} 张图片")

        if not results:
            raise RuntimeError("API未返回任何图片")
        return results[0].image

    def _build_character_photo_filename(
        self,
        *,
        character_name: str,
        angle: str,
        angle_name: str,
        expr: str,
        expr_name: str,
        batch_generate: bool,
        batch_expressions: bool,
        variant_mode: str,
        variant_value: str,
    ) -> str:
        filename_parts = [character_name]

        if batch_generate or angle != "front":
            filename_parts.append(angle_name)
        if batch_expressions or expr != "neutral":
            filename_parts.append(expr_name)

        if variant_mode == "preset" and variant_value:
            filename_parts.append(self._VARIANT_NAME_MAP.get(variant_value, variant_value))
        elif variant_mode == "custom" and variant_value and not variant_value.startswith("例如"):
            filename_parts.append(variant_value[:10].replace(" ", "_"))

        return "_".join(filename_parts) + ".png"

    def _finalize_character_photo_generation(self, character_name: str, generated_photos: list[dict]) -> None:
        """在主线程更新状态、预览与提示。"""
        project_name = "未知项目"
        if self.current_project:
            project_name = self.current_project.metadata.get("name", "未命名项目")

        if generated_photos:
            last_photo = generated_photos[-1]
            self._update_character_photo_preview(last_photo["image"])

        if len(generated_photos) > 1:
            photo_desc_list = []
            for photo in generated_photos:
                desc_parts = []
                if photo["angle_name"]:
                    desc_parts.append(photo["angle_name"])
                if photo.get("expression_name") and photo["expression_name"] != "中性":
                    desc_parts.append(photo["expression_name"])
                photo_desc_list.append("+".join(desc_parts) if desc_parts else "照片")

            photo_list_str = "、".join(photo_desc_list)
            self.status.set(f"✅ 成功生成{len(generated_photos)}张照片（{photo_list_str}）并保存到项目 [{project_name}]")
            detail_list = "\n".join([f"• {desc}" for desc in photo_desc_list])
            messagebox.showinfo(
                "成功",
                f"已成功生成并保存 {len(generated_photos)} 张照片！\n\n{detail_list}\n\n"
                f"保存位置：项目/characters/{character_name}_xxx.png",
            )
        elif len(generated_photos) == 1:
            photo = generated_photos[0]
            desc_parts = [photo["angle_name"]]
            if photo.get("expression_name") and photo["expression_name"] != "中性":
                desc_parts.append(photo["expression_name"])
            desc = "+".join(desc_parts)
            self.status.set(f"✅ 成功生成并保存\"{character_name}\"的{desc}照片到项目 [{project_name}]")
        else:
            self.status.set("❌ 照片生成失败或未保存")

        self.char_btn_save_photo.config(state=NORMAL)
        self._update_reference_character_list()
        self._header_status("照片生成完成", "✅")

    def _build_character_photo_error_message(self, exc: Exception, raw_reason: str) -> str:
        """构建人物照片生成失败的用户可见错误文本。"""
        error_msg = f"生成照片失败: {raw_reason}"
        err_lower = raw_reason.lower()

        current_model = getattr(self, "_last_effective_img_model", "")
        if not current_model and hasattr(self, "img_model"):
            current_model = self.img_model.get().strip()
        current_base_url = self.img_base_url.get() if hasattr(self, "img_base_url") else ""

        if "no capacity" in err_lower or "capacity available" in err_lower or "capacity" in err_lower:
            return (
                "图片服务当前容量不足（不是提示词违规）。"
                f"\n模型：{current_model or '未知'}"
                f"\nBase URL：{current_base_url or '默认'}"
                f"\n原始原因：{raw_reason[:220]}"
            )
        if "blocked" in err_lower or "safety" in err_lower or "policy" in err_lower:
            return (
                "请求被安全策略拦截（已自动安全重试一次仍失败）。"
                f"\n模型：{current_model or '未知'}"
                f"\nBase URL：{current_base_url or '默认'}"
                f"\n原始原因：{raw_reason[:220]}"
            )
        if "401" in str(exc) or "authentication" in err_lower:
            return "API密钥无效或已过期，请检查配置"
        if "timeout" in err_lower:
            return "API请求超时，请检查网络连接"
        if "rate" in err_lower or "quota" in err_lower:
            return "API配额用尽或请求频率过高"
        return error_msg

    def _handle_character_photo_generation_error(self, exc: Exception) -> None:
        """统一处理人物照片生成异常。"""
        import traceback

        error_detail = traceback.format_exc()
        raw_reason = str(exc).strip()
        print(f"\n{'='*60}\n生成人物照片时发生错误：\n{error_detail}\n{'='*60}\n")

        error_msg = self._build_character_photo_error_message(exc, raw_reason)

        if hasattr(self, "settings_log"):
            def _log_error():
                self.settings_log.insert(END, f"\n❌ 人物照片生成失败: {raw_reason}\n")
                if hasattr(self, "_last_character_photo_prompt"):
                    last_prompt = getattr(self, "_last_character_photo_prompt", "")
                    self.settings_log.insert(END, f"📝 最后提示词: {last_prompt[:320]}\n")
                self.settings_log.see(END)

            self._ui(_log_error)

        self._ui(lambda msg=error_msg: messagebox.showerror("生成失败", msg))
        self._ui(lambda: self.status.set("❌ 生成照片失败"))
        self._header_status("生成失败", "❌")
