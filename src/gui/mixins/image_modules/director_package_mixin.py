"""Director package generation helpers extracted from shot manager."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import logging
from tkinter import END, NORMAL, messagebox

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize

from ...helpers.director_script_builder import DirectorScriptBuilder

logger = logging.getLogger(__name__)


def print(*args, **kwargs):  # type: ignore[override]
    logger.info(" ".join(str(a) for a in args))


class DirectorPackageMixin:
    """Generate/parse/apply director package for image workflows."""

    @staticmethod
    def _parse_shot_response(response_text: str) -> list[str]:
        """解析分镜响应文本，提取纯分镜描述列表"""
        shots: list[str] = []
        for line in response_text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            if line[0].isdigit() or line.startswith('•') or line.startswith('-'):
                if '.' in line:
                    shot_text = line.split('.', 1)[1].strip()
                elif line.startswith('•') or line.startswith('-'):
                    shot_text = line[1:].strip()
                else:
                    shot_text = line
                if shot_text:
                    shots.append(shot_text)
        return shots

    @staticmethod
    def _estimate_director_shot_range(story_length: int) -> tuple[int, int]:
        """根据故事长度估算导演脚本的分镜数量范围。"""
        if story_length < 1000:
            return 10, 16
        if story_length < 2500:
            return 16, 24
        if story_length < 4500:
            return 22, 32
        return 28, 40

    def _build_director_package_instruction(self, min_shots: int, max_shots: int) -> str:
        """构建导演脚本包生成提示词。"""
        return (
            "你是电影导演、分镜导演、影视编剧、AI视频提示词工程师。"
            "请把用户提供的故事改写为可执行的导演脚本包。\n\n"
            "输出要求：\n"
            "1. 只能输出一个合法 JSON 对象，不要 Markdown，不要解释。\n"
            "2. 分镜数量必须在指定范围内。\n"
            "3. 人物外貌和服装保持跨镜头一致，除非剧情明确换装。\n"
            "4. director_script_markdown 使用导演脚本写法（可用 INT./EXT. 场景行）。\n"
            "5. veo_prompt 必须偏“运动描述”：动作、镜头运动、节奏、氛围；"
            "尽量避免描述首帧已固定的静态细节，避免引号台词和画面文字。\n\n"
            "6. 每个镜头必须包含 character_states，明确每个角色在该镜头里的身份、动作、情绪、可见外观。\n\n"
            f"分镜数量范围：{min_shots}-{max_shots}\n\n"
            "JSON Schema：\n"
            "{\n"
            "  \"title\": \"故事标题\",\n"
            "  \"logline\": \"一句话梗概\",\n"
            "  \"style_bible\": {\n"
            "    \"genre\": \"类型\",\n"
            "    \"tone\": \"基调\",\n"
            "    \"visual_style\": \"视觉风格\",\n"
            "    \"color_palette\": \"色彩策略\",\n"
            "    \"camera_language\": \"镜头语言\",\n"
            "    \"pacing\": \"节奏\"\n"
            "  },\n"
            "  \"characters\": [\n"
            "    {\n"
            "      \"name\": \"人物名\",\n"
            "      \"role\": \"主角/反派/配角\",\n"
            "      \"goal\": \"人物目标\",\n"
            "      \"arc\": \"人物弧光\",\n"
            "      \"appearance_anchor\": \"稳定外貌锚点\",\n"
            "      \"voice_tone\": \"说话语气\",\n"
            "      \"consistency_notes\": \"一致性规则\"\n"
            "    }\n"
            "  ],\n"
            "  \"scene_beats\": [\n"
            "    {\n"
            "      \"scene_no\": 1,\n"
            "      \"slugline\": \"INT./EXT. 场景 - 时间\",\n"
            "      \"dramatic_purpose\": \"场景目的\",\n"
            "      \"conflict\": \"冲突\",\n"
            "      \"turning_point\": \"转折\",\n"
            "      \"outcome\": \"结果\"\n"
            "    }\n"
            "  ],\n"
            "  \"director_script_markdown\": \"完整导演脚本正文\",\n"
            "  \"shot_list\": [\n"
            "    {\n"
            "      \"shot_no\": 1,\n"
            "      \"scene_no\": 1,\n"
            "      \"shot_type\": \"CU/MS/WS/OTS/POV 等\",\n"
            "      \"camera_movement\": \"固定/推进/拉远/摇镜/跟随/环绕\",\n"
            "      \"duration_sec\": 5,\n"
            "      \"location\": \"地点\",\n"
            "      \"time\": \"时间\",\n"
            "      \"characters\": [\"人物名1\", \"人物名2\"],\n"
            "      \"character_states\": [\n"
            "        {\n"
            "          \"name\": \"人物名\",\n"
            "          \"role\": \"主角/反派/配角\",\n"
            "          \"appearance\": \"本镜头可见外观锚点\",\n"
            "          \"action\": \"该人物在本镜头中的动作\",\n"
            "          \"emotion\": \"该人物在本镜头中的情绪\"\n"
            "        }\n"
            "      ],\n"
            "      \"action\": \"镜头内发生的动作\",\n"
            "      \"dialogue\": \"关键台词，可为空\",\n"
            "      \"sound\": \"环境音/配乐/音效\",\n"
            "      \"transition\": \"切/叠化/淡入淡出/结束\",\n"
            "      \"veo_prompt\": \"给 Veo 的单镜头运动提示词\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )

    def _on_generate_director_package(self) -> None:
        """从故事一键生成人物设定、导演脚本与分镜头。"""
        story_text = self.output.get("1.0", END).strip()
        if not story_text:
            messagebox.showwarning("提示", "请先在“故事”页生成或粘贴正文内容")
            return

        # 导演脚本生成：根据模型路由选择 API
        fallback_provider = None
        if hasattr(self, 'quick_story_api'):
            fallback_provider = self.quick_story_api.get()
        if not fallback_provider and hasattr(self, 'api_preset'):
            fallback_provider = self.api_preset.get()
        fallback_model = None
        if hasattr(self, 'story_model_var'):
            fallback_model = self.story_model_var.get()
        elif hasattr(self, 'model'):
            fallback_model = self.model.get()

        api_config = self._resolve_task_api(
            "director_script_generate",
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
        )
        selected_api = api_config.get("provider", "")
        api_key = _sanitize(api_config.get("key", ""))
        base_url = _sanitize(api_config.get("base_url", ""))
        model = _sanitize(api_config.get("model", ""))

        if not api_key:
            messagebox.showwarning("提示", f"请先在设置页配置 {selected_api} 的 API Key")
            return

        min_shots, max_shots = self._estimate_director_shot_range(len(story_text))
        inst = self._build_director_package_instruction(min_shots, max_shots)

        def task():
            try:
                self.set_busy(True)
                self._ui(
                    self.status.set,
                    f"🎞️ 正在使用 {selected_api} 生成导演脚本包（{min_shots}-{max_shots} 镜）..."
                )
                self._header_status("生成导演脚本包...", "🎞️")

                client = DeepSeekClient(
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                )
                resp = client.chat([
                    {"role": "system", "content": inst},
                    {"role": "user", "content": story_text},
                ], temperature=max(0.4, self.temperature.get() - 0.15))

                try:
                    package = DirectorScriptBuilder.parse_llm_package(resp)
                except Exception:
                    # 兼容模型偏离 JSON 输出时的降级处理。
                    legacy_shots = self._parse_shot_response(resp)
                    if not legacy_shots:
                        raise
                    package = {
                        "title": "未命名导演脚本",
                        "logline": "",
                        "style_bible": {},
                        "characters": [],
                        "scene_beats": [],
                        "director_script_markdown": "",
                        "shot_list": [],
                    }
                    for i, shot_text in enumerate(legacy_shots):
                        parts = [p.strip() for p in shot_text.split("|")]
                        package["shot_list"].append({
                            "shot_no": i + 1,
                            "scene_no": 1,
                            "shot_type": parts[2] if len(parts) > 2 else "中景",
                            "camera_movement": parts[3] if len(parts) > 3 else "固定",
                            "duration_sec": int("".join([c for c in (parts[4] if len(parts) > 4 else "5") if c.isdigit()]) or "5"),
                            "location": parts[0] if len(parts) > 0 else "",
                            "time": "",
                            "characters": [],
                            "character_states": [],
                            "action": parts[1] if len(parts) > 1 else shot_text,
                            "dialogue": "",
                            "sound": parts[6] if len(parts) > 6 else "",
                            "transition": parts[5] if len(parts) > 5 else "切",
                            "veo_prompt": "",
                        })
                if not package.get("shot_list"):
                    raise ValueError("模型未返回有效分镜头清单")

                markdown_path = self._save_director_package_markdown(package)
                self._ui(self._apply_director_package_to_ui, package, markdown_path)
            except Exception as e:
                self._ui(messagebox.showerror, "导演脚本生成失败", str(e))
                self._header_status("导演脚本生成失败", "❌")
            finally:
                self.set_busy(False)

        import threading
        threading.Thread(target=task, daemon=True).start()

    def _apply_director_package_to_ui(self, package: dict, markdown_path: Path | None) -> None:
        """将导演脚本包结果应用到界面。"""
        self._last_director_package = package
        shot_list = package.get("shot_list", []) if isinstance(package, dict) else []
        shot_lines = [DirectorScriptBuilder.shot_to_app_line(shot) for shot in shot_list if isinstance(shot, dict)]
        if not shot_lines:
            messagebox.showwarning("提示", "导演脚本已生成，但未解析到可用分镜")
            return
        self.parsed_shots = shot_lines

        if hasattr(self, "shots_listbox"):
            self.shots_listbox.config(state=NORMAL)
            self.shots_listbox.delete(0, END)
            for i, shot in enumerate(shot_lines):
                display_text = f"{i+1}. {shot[:80]}..." if len(shot) > 80 else f"{i+1}. {shot}"
                self.shots_listbox.insert(END, display_text)
            self.shots_listbox.selection_set(0)
            self.shots_listbox.activate(0)
            self._on_shot_listbox_selected(None)

        roles_text = DirectorScriptBuilder.to_roles_text(package)
        if roles_text and hasattr(self, "img_txt_roles"):
            self.img_txt_roles.delete("1.0", END)
            self.img_txt_roles.insert("1.0", roles_text)

        if hasattr(self, "_update_director_page_with_package"):
            self._update_director_page_with_package(package, shot_lines, markdown_path=markdown_path)

        self._sync_characters_from_director_package(package)

        report = DirectorScriptBuilder.build_quality_report(package)
        character_count = len(package.get("characters", [])) if isinstance(package.get("characters"), list) else 0
        msg = (
            f"✅ 导演脚本包已生成：人物 {character_count} 个，分镜 {len(shot_lines)} 个，"
            f"完整度 {report.get('completeness_percent', 0)}%，问题镜头 {report.get('problem_shots', 0)} 个"
        )
        if markdown_path:
            msg += f"（已保存到 {markdown_path}）"
        self.status.set(msg)
        self._header_status("导演脚本包生成完成", "✅")

    def _sync_characters_from_director_package(self, package: dict) -> None:
        """把导演脚本包中的人物同步到人物列表（用于后续角色图生成）。"""
        try:
            from ...models.character import Character
        except Exception as e:
            print(f"⚠️ 导入人物模型失败，跳过人物同步：{e}")
            return

        if not isinstance(package, dict):
            return
        incoming = package.get("characters", [])
        if not isinstance(incoming, list) or not incoming:
            return
        if not hasattr(self, "character_list"):
            return

        existing_map: dict[str, Character] = {}
        for item in self.character_list:
            if isinstance(item, Character) and item.name:
                existing_map[item.name] = item

        changed = False
        for item in incoming:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue

            role = str(item.get("role", "")).strip()
            goal = str(item.get("goal", "")).strip()
            arc = str(item.get("arc", "")).strip()
            appearance = str(item.get("appearance_anchor", "")).strip()
            voice_tone = str(item.get("voice_tone", "")).strip()
            notes = str(item.get("consistency_notes", "")).strip()

            char = existing_map.get(name)
            if not char:
                char = Character(name=name)
                self.character_list.append(char)
                existing_map[name] = char
                changed = True

            if role and not char.profile.role:
                char.profile.role = role
                changed = True
            if appearance:
                if not char.profile.appearance_hints:
                    char.profile.appearance_hints = appearance
                    changed = True
                if not char.description:
                    char.description = appearance
                    changed = True
            if goal and not char.profile.identity:
                char.profile.identity = goal
                changed = True

            profile_bits = [v for v in [arc, voice_tone, notes] if v]
            if profile_bits:
                merged = "；".join(profile_bits)
                if not char.profile.story_role:
                    char.profile.story_role = merged
                    changed = True
                elif merged not in char.profile.story_role:
                    char.profile.story_role = f"{char.profile.story_role}；{merged}"
                    changed = True

        if changed:
            if hasattr(self, "_save_all_characters_info"):
                self._save_all_characters_info()
            if hasattr(self, "_update_character_listbox"):
                self._update_character_listbox()
            if hasattr(self, "_update_reference_character_list"):
                self._update_reference_character_list()

    def _save_director_package_markdown(self, package: dict) -> Path | None:
        """保存导演脚本包为 Markdown/Fountain 文件。"""
        if not self.current_project:
            return None
        try:
            project_dir = self.current_project.project_dir
            out_dir = project_dir / "director_scripts"
            out_dir.mkdir(parents=True, exist_ok=True)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            md_path = out_dir / f"导演脚本包_{ts}.md"
            md_content = DirectorScriptBuilder.to_markdown(package)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            script_text = str(package.get("director_script_markdown", "")).strip()
            if script_text:
                fountain_path = out_dir / f"导演脚本_{ts}.fountain"
                with open(fountain_path, "w", encoding="utf-8") as f:
                    f.write(script_text + "\n")

            return md_path
        except Exception as e:
            print(f"⚠️ 保存导演脚本包失败：{e}")
            return None
    
