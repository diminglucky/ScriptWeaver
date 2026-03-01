"""Director script package parsing and formatting helpers."""

from __future__ import annotations

from collections import Counter
import json
import re
from typing import Any, Dict, List


class DirectorScriptBuilder:
    """Utilities for structured director package generation."""

    SHOT_QUALITY_CHECKPOINTS = (
        "scene",
        "action",
        "duration",
        "characters",
        "character_states",
        "veo_prompt",
    )

    @staticmethod
    def parse_llm_package(response_text: str) -> Dict[str, Any]:
        """Parse model output into normalized director package."""
        if not response_text or not response_text.strip():
            raise ValueError("模型未返回内容")

        cleaned = response_text.strip()
        candidates: List[str] = []

        # Candidate 1: fenced block content.
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if fenced:
            candidates.append(fenced.group(1).strip())

        # Candidate 2: raw full text.
        candidates.append(cleaned)

        # Candidate 3: widest JSON-like object.
        json_like = re.search(r"\{[\s\S]*\}", cleaned)
        if json_like:
            candidates.append(json_like.group(0).strip())

        last_error: Exception | None = None
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                return DirectorScriptBuilder.normalize_package(parsed)
            except Exception as exc:  # pragma: no cover - best effort parser
                last_error = exc
                continue

        raise ValueError(f"导演脚本解析失败: {last_error}")

    @staticmethod
    def normalize_package(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize arbitrary JSON into stable package schema."""
        data = raw if isinstance(raw, dict) else {}

        style_raw = data.get("style_bible", {}) if isinstance(data.get("style_bible"), dict) else {}
        style_bible = {
            "genre": str(style_raw.get("genre", "")).strip(),
            "tone": str(style_raw.get("tone", "")).strip(),
            "visual_style": str(style_raw.get("visual_style", "")).strip(),
            "color_palette": str(style_raw.get("color_palette", "")).strip(),
            "camera_language": str(style_raw.get("camera_language", "")).strip(),
            "pacing": str(style_raw.get("pacing", "")).strip(),
        }

        characters: List[Dict[str, str]] = []
        for item in data.get("characters", []) if isinstance(data.get("characters"), list) else []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            characters.append(
                {
                    "name": name,
                    "role": str(item.get("role", "")).strip(),
                    "goal": str(item.get("goal", "")).strip(),
                    "arc": str(item.get("arc", "")).strip(),
                    "appearance_anchor": str(item.get("appearance_anchor", "")).strip(),
                    "voice_tone": str(item.get("voice_tone", "")).strip(),
                    "consistency_notes": str(item.get("consistency_notes", "")).strip(),
                }
            )

        scene_beats: List[Dict[str, Any]] = []
        for item in data.get("scene_beats", []) if isinstance(data.get("scene_beats"), list) else []:
            if not isinstance(item, dict):
                continue
            scene_no_raw = item.get("scene_no", len(scene_beats) + 1)
            try:
                scene_no = int(scene_no_raw)
            except Exception:
                scene_no = len(scene_beats) + 1
            scene_beats.append(
                {
                    "scene_no": scene_no,
                    "slugline": str(item.get("slugline", "")).strip(),
                    "dramatic_purpose": str(item.get("dramatic_purpose", "")).strip(),
                    "conflict": str(item.get("conflict", "")).strip(),
                    "turning_point": str(item.get("turning_point", "")).strip(),
                    "outcome": str(item.get("outcome", "")).strip(),
                }
            )

        shot_list = DirectorScriptBuilder.normalize_shot_list(data.get("shot_list", []))
        DirectorScriptBuilder._enrich_shot_character_states(shot_list, characters)

        director_script_markdown = str(
            data.get("director_script_markdown", data.get("director_script", ""))
        ).strip()

        package = {
            "title": str(data.get("title", data.get("project_title", "未命名项目"))).strip() or "未命名项目",
            "logline": str(data.get("logline", "")).strip(),
            "style_bible": style_bible,
            "characters": characters,
            "scene_beats": scene_beats,
            "director_script_markdown": director_script_markdown,
            "shot_list": shot_list,
        }
        return package

    @staticmethod
    def normalize_shot_list(shots: Any) -> List[Dict[str, Any]]:
        """Normalize shot list entries to stable fields."""
        result: List[Dict[str, Any]] = []
        for idx, item in enumerate(shots if isinstance(shots, list) else []):
            if not isinstance(item, dict):
                continue

            shot_no_raw = item.get("shot_no", idx + 1)
            scene_no_raw = item.get("scene_no", 1)
            duration_raw = item.get("duration_sec", item.get("duration", 5))

            try:
                shot_no = int(shot_no_raw)
            except Exception:
                shot_no = idx + 1
            try:
                scene_no = int(scene_no_raw)
            except Exception:
                scene_no = 1
            try:
                duration_sec = max(1, int(float(str(duration_raw).replace("秒", "").strip() or "5")))
            except Exception:
                duration_sec = 5

            raw_characters = item.get("characters", [])
            inferred_states: List[Dict[str, str]] = []
            characters: List[str] = []
            if isinstance(raw_characters, str):
                characters = [part.strip() for part in re.split(r"[，,、/|]", raw_characters) if part.strip()]
            elif isinstance(raw_characters, list):
                for c in raw_characters:
                    if isinstance(c, dict):
                        name = str(c.get("name", "")).strip()
                        if not name:
                            continue
                        characters.append(name)
                        inferred_states.append(
                            {
                                "name": name,
                                "role": str(c.get("role", "")).strip(),
                                "appearance": str(c.get("appearance", c.get("appearance_anchor", ""))).strip(),
                                "action": str(c.get("action", "")).strip(),
                                "emotion": str(c.get("emotion", "")).strip(),
                            }
                        )
                    else:
                        name = str(c).strip()
                        if name:
                            characters.append(name)
            else:
                characters = []

            raw_states = item.get("character_states", item.get("characters_detail", []))
            if not raw_states and inferred_states:
                raw_states = inferred_states
            character_states = DirectorScriptBuilder._normalize_character_states(raw_states, characters)

            result.append(
                {
                    "shot_no": shot_no,
                    "scene_no": scene_no,
                    "shot_type": str(item.get("shot_type", item.get("lens", "中景"))).strip() or "中景",
                    "camera_movement": str(item.get("camera_movement", item.get("camera", "固定"))).strip()
                    or "固定",
                    "duration_sec": duration_sec,
                    "location": str(item.get("location", "")).strip(),
                    "time": str(item.get("time", "")).strip(),
                    "characters": characters,
                    "character_states": character_states,
                    "action": str(item.get("action", item.get("description", ""))).strip(),
                    "dialogue": str(item.get("dialogue", "")).strip(),
                    "sound": str(item.get("sound", item.get("audio", ""))).strip(),
                    "transition": str(item.get("transition", "切")).strip() or "切",
                    "veo_prompt": str(item.get("veo_prompt", item.get("video_prompt", ""))).strip(),
                }
            )

        result.sort(key=lambda x: x.get("shot_no", 0))
        return result

    @staticmethod
    def _normalize_character_states(raw_states: Any, shot_characters: List[str]) -> List[Dict[str, str]]:
        """Normalize per-shot character state blocks."""
        states: List[Dict[str, str]] = []

        if isinstance(raw_states, str):
            for name in [part.strip() for part in re.split(r"[，,、/|]", raw_states) if part.strip()]:
                states.append({"name": name, "role": "", "appearance": "", "action": "", "emotion": ""})
        elif isinstance(raw_states, list):
            for item in raw_states:
                if isinstance(item, dict):
                    name = str(item.get("name", item.get("character", ""))).strip()
                    if not name:
                        continue
                    states.append(
                        {
                            "name": name,
                            "role": str(item.get("role", "")).strip(),
                            "appearance": str(item.get("appearance", item.get("appearance_anchor", ""))).strip(),
                            "action": str(item.get("action", "")).strip(),
                            "emotion": str(item.get("emotion", "")).strip(),
                        }
                    )
                else:
                    name = str(item).strip()
                    if name:
                        states.append({"name": name, "role": "", "appearance": "", "action": "", "emotion": ""})

        state_names = {s.get("name", "") for s in states}
        for name in shot_characters:
            if name and name not in state_names:
                states.append({"name": name, "role": "", "appearance": "", "action": "", "emotion": ""})
        return states

    @staticmethod
    def _enrich_shot_character_states(shots: List[Dict[str, Any]], characters: List[Dict[str, str]]) -> None:
        """Backfill role/appearance into shot-level character states from global character cards."""
        char_map: Dict[str, Dict[str, str]] = {}
        for ch in characters:
            if not isinstance(ch, dict):
                continue
            name = str(ch.get("name", "")).strip()
            if not name:
                continue
            char_map[name] = {
                "role": str(ch.get("role", "")).strip(),
                "appearance": str(ch.get("appearance_anchor", "")).strip(),
            }

        for shot in shots:
            states = shot.get("character_states", [])
            if not isinstance(states, list):
                states = []
            normalized_states: List[Dict[str, str]] = []
            seen_names: set[str] = set()

            for st in states:
                if not isinstance(st, dict):
                    continue
                name = str(st.get("name", "")).strip()
                if not name:
                    continue
                role = str(st.get("role", "")).strip() or char_map.get(name, {}).get("role", "")
                appearance = str(st.get("appearance", "")).strip() or char_map.get(name, {}).get("appearance", "")
                normalized_states.append(
                    {
                        "name": name,
                        "role": role,
                        "appearance": appearance,
                        "action": str(st.get("action", "")).strip(),
                        "emotion": str(st.get("emotion", "")).strip(),
                    }
                )
                seen_names.add(name)

            shot_names = shot.get("characters", [])
            if isinstance(shot_names, list):
                for name in shot_names:
                    nm = str(name).strip()
                    if not nm or nm in seen_names:
                        continue
                    normalized_states.append(
                        {
                            "name": nm,
                            "role": char_map.get(nm, {}).get("role", ""),
                            "appearance": char_map.get(nm, {}).get("appearance", ""),
                            "action": "",
                            "emotion": "",
                        }
                    )
                    seen_names.add(nm)

            shot["character_states"] = normalized_states
            if not shot.get("characters"):
                shot["characters"] = [s["name"] for s in normalized_states if s.get("name")]

    @staticmethod
    def build_shot_character_summary(shot: Dict[str, Any]) -> str:
        """Build compact character-role-action summary for one shot."""
        states = shot.get("character_states", [])
        if not isinstance(states, list):
            states = []
        chunks: List[str] = []
        for st in states:
            if not isinstance(st, dict):
                continue
            name = str(st.get("name", "")).strip()
            if not name:
                continue
            role = str(st.get("role", "")).strip()
            action = str(st.get("action", "")).strip()
            emotion = str(st.get("emotion", "")).strip()
            appearance = str(st.get("appearance", "")).strip()

            parts = [name]
            if role:
                parts.append(f"角色={role}")
            if action:
                parts.append(f"动作={action}")
            if emotion:
                parts.append(f"情绪={emotion}")
            if appearance:
                parts.append(f"外观={appearance}")
            chunks.append("（" + "，".join(parts) + "）")
        return "；".join(chunks)

    @staticmethod
    def iter_shots(package: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return normalized shot list from package-like payload."""
        if not isinstance(package, dict):
            return []
        shots = package.get("shot_list", [])
        if not isinstance(shots, list):
            return []
        return [shot for shot in shots if isinstance(shot, dict)]

    @staticmethod
    def extract_shot_characters(shot: Dict[str, Any]) -> List[str]:
        """Extract unique character names from shot-level fields."""
        names: List[str] = []
        states = shot.get("character_states", [])
        if isinstance(states, list):
            for state in states:
                if not isinstance(state, dict):
                    continue
                name = str(state.get("name", "")).strip()
                if name and name not in names:
                    names.append(name)

        raw_names = shot.get("characters", [])
        if isinstance(raw_names, list):
            for raw_name in raw_names:
                name = str(raw_name).strip()
                if name and name not in names:
                    names.append(name)
        return names

    @staticmethod
    def get_shot_quality_issues(shot: Dict[str, Any]) -> List[str]:
        """Build quality issue list for one shot."""
        issues: List[str] = []

        location = str(shot.get("location", "")).strip()
        time = str(shot.get("time", "")).strip()
        if not location and not time:
            issues.append("缺少场景（地点/时间）")

        action = str(shot.get("action", "")).strip()
        if not action:
            issues.append("缺少镜头内容动作")

        duration_raw = shot.get("duration_sec", 0)
        try:
            duration = int(float(str(duration_raw).replace("秒", "").strip() or "0"))
        except Exception:
            duration = 0
        if duration <= 0:
            issues.append("时长无效")

        shot_characters = DirectorScriptBuilder.extract_shot_characters(shot)
        if not shot_characters:
            issues.append("缺少人物")

        states = shot.get("character_states", [])
        normalized_states = states if isinstance(states, list) else []
        if shot_characters and not normalized_states:
            issues.append("缺少人物状态")
        else:
            # Has states but lacks per-character action for every character.
            if normalized_states:
                has_character_action = any(
                    str(state.get("action", "")).strip()
                    for state in normalized_states
                    if isinstance(state, dict)
                )
                if not has_character_action:
                    issues.append("人物状态缺少动作描述")

        veo_prompt = str(shot.get("veo_prompt", "")).strip()
        if not veo_prompt:
            issues.append("缺少Veo提示词")

        return issues

    @staticmethod
    def calculate_shot_completeness(shot: Dict[str, Any]) -> float:
        """Return shot completeness score in range [0, 1]."""
        issues = DirectorScriptBuilder.get_shot_quality_issues(shot)
        checkpoints = len(DirectorScriptBuilder.SHOT_QUALITY_CHECKPOINTS)
        score = max(0.0, (checkpoints - len(issues)) / checkpoints)
        return min(1.0, score)

    @staticmethod
    def build_quality_report(package: Dict[str, Any]) -> Dict[str, Any]:
        """Build aggregated quality stats for director workflow."""
        shots = DirectorScriptBuilder.iter_shots(package)
        shot_reports: List[Dict[str, Any]] = []
        issue_counter: Counter[str] = Counter()

        total_duration = 0
        complete_shots = 0
        score_sum = 0.0

        for idx, shot in enumerate(shots):
            shot_no = shot.get("shot_no", idx + 1)
            issues = DirectorScriptBuilder.get_shot_quality_issues(shot)
            for issue in issues:
                issue_counter[issue] += 1

            score = DirectorScriptBuilder.calculate_shot_completeness(shot)
            score_sum += score
            if not issues:
                complete_shots += 1

            duration_raw = shot.get("duration_sec", 0)
            try:
                duration = max(0, int(float(str(duration_raw).replace("秒", "").strip() or "0")))
            except Exception:
                duration = 0
            total_duration += duration

            shot_reports.append(
                {
                    "shot_no": shot_no,
                    "issues": issues,
                    "score": score,
                    "scene": " ".join(
                        [str(shot.get("location", "")).strip(), str(shot.get("time", "")).strip()]
                    ).strip(),
                }
            )

        total_shots = len(shots)
        completeness_percent = round((complete_shots / total_shots) * 100) if total_shots else 0
        average_score_percent = round((score_sum / total_shots) * 100) if total_shots else 0

        return {
            "total_shots": total_shots,
            "total_characters": len(
                package.get("characters", []) if isinstance(package.get("characters"), list) else []
            ),
            "total_duration_sec": total_duration,
            "average_duration_sec": round(total_duration / total_shots, 1) if total_shots else 0.0,
            "complete_shots": complete_shots,
            "problem_shots": total_shots - complete_shots,
            "completeness_percent": completeness_percent,
            "average_score_percent": average_score_percent,
            "issue_counter": dict(issue_counter),
            "shot_reports": shot_reports,
        }

    @staticmethod
    def to_quality_text(package: Dict[str, Any]) -> str:
        """Render quality report text for UI."""
        report = DirectorScriptBuilder.build_quality_report(package)
        total_shots = report["total_shots"]
        lines = [
            "导演脚本质检报告",
            "",
            f"分镜总数：{total_shots}",
            f"人物总数：{report['total_characters']}",
            f"总时长：{report['total_duration_sec']} 秒",
            f"平均镜头时长：{report['average_duration_sec']} 秒",
            f"完整度：{report['completeness_percent']}%",
            f"问题镜头：{report['problem_shots']}",
            "",
            "高频问题：",
        ]

        issue_counter = report.get("issue_counter", {})
        if isinstance(issue_counter, dict) and issue_counter:
            sorted_items = sorted(issue_counter.items(), key=lambda item: item[1], reverse=True)
            for issue, count in sorted_items[:8]:
                lines.append(f"- {issue}（{count}个镜头）")
        else:
            lines.append("- 未发现明显结构问题")

        lines.append("")
        lines.append("问题镜头清单：")
        shot_reports = report.get("shot_reports", [])
        problem_rows = [
            shot_report
            for shot_report in shot_reports
            if isinstance(shot_report, dict) and shot_report.get("issues")
        ]
        if not problem_rows:
            lines.append("- 全部分镜通过基础质检")
        else:
            for shot_report in problem_rows:
                shot_no = shot_report.get("shot_no", "-")
                issue_text = "；".join(shot_report.get("issues", []))
                lines.append(f"- Shot {shot_no}: {issue_text}")

        return "\n".join(lines).strip()

    @staticmethod
    def format_shot_detail(shot: Dict[str, Any], fallback_index: int = 0) -> str:
        """Render one shot to detailed text for director panel."""
        shot_no = shot.get("shot_no", fallback_index + 1)
        lines = [
            f"Shot {shot_no}",
            f"场景：{str(shot.get('location', '')).strip()} {str(shot.get('time', '')).strip()}".strip(),
            f"镜头：{str(shot.get('shot_type', '')).strip()} / {str(shot.get('camera_movement', '')).strip()}",
            f"时长：{shot.get('duration_sec', '')} 秒",
            "",
            "镜头内容：",
            str(shot.get("action", "")).strip() or "（无）",
        ]

        states = shot.get("character_states", [])
        if isinstance(states, list) and states:
            lines.extend(["", "人物角色信息："])
            for state in states:
                if not isinstance(state, dict):
                    continue
                name = str(state.get("name", "")).strip() or "未知人物"
                role = str(state.get("role", "")).strip()
                action = str(state.get("action", "")).strip()
                emotion = str(state.get("emotion", "")).strip()
                appearance = str(state.get("appearance", "")).strip()
                parts = [name]
                if role:
                    parts.append(f"角色={role}")
                if action:
                    parts.append(f"动作={action}")
                if emotion:
                    parts.append(f"情绪={emotion}")
                if appearance:
                    parts.append(f"外观={appearance}")
                lines.append(" - " + "，".join(parts))
        else:
            lines.extend(["", "人物角色信息：", " - 本镜头未返回人物状态"])

        issues = DirectorScriptBuilder.get_shot_quality_issues(shot)
        if issues:
            lines.extend(["", "质检提示："])
            for issue in issues:
                lines.append(f" - {issue}")

        veo_prompt = str(shot.get("veo_prompt", "")).strip()
        lines.extend(["", "Veo 提示词：", veo_prompt or "（未提供）"])
        return "\n".join(lines).strip()

    @staticmethod
    def shot_to_app_line(shot: Dict[str, Any]) -> str:
        """Convert normalized shot object into app shot string format."""
        scene_parts = [shot.get("location", ""), shot.get("time", "")]
        scene = "，".join([str(p).strip() for p in scene_parts if str(p).strip()]) or "场景未指定"
        core_action = str(shot.get("action", "")).strip() or "人物动作未指定"
        character_summary = DirectorScriptBuilder.build_shot_character_summary(shot)
        if character_summary:
            action = f"人物信息：{character_summary}；镜头内容：{core_action}"
        else:
            action = core_action
        lens = str(shot.get("shot_type", "中景")).strip() or "中景"
        movement = str(shot.get("camera_movement", "固定")).strip() or "固定"
        duration_sec = shot.get("duration_sec", 5)
        try:
            duration = f"{int(duration_sec)}秒"
        except Exception:
            duration = "5秒"
        transition = str(shot.get("transition", "切")).strip() or "切"
        sound = str(shot.get("sound", "")).strip() or "环境音"
        return f"{scene} | {action} | {lens} | {movement} | {duration} | {transition} | {sound}"

    @staticmethod
    def to_roles_text(package: Dict[str, Any]) -> str:
        """Build compact character reference text for image generation pane."""
        rows: List[str] = []
        for ch in package.get("characters", []) if isinstance(package.get("characters"), list) else []:
            if not isinstance(ch, dict):
                continue
            name = str(ch.get("name", "")).strip()
            if not name:
                continue
            role = str(ch.get("role", "")).strip()
            appearance = str(ch.get("appearance_anchor", "")).strip()
            tone = str(ch.get("voice_tone", "")).strip()
            notes = [f"角色:{role}" if role else "", f"外貌锚点:{appearance}" if appearance else "", f"语气:{tone}" if tone else ""]
            notes_text = "；".join([n for n in notes if n])
            rows.append(f"{name}：{notes_text}")
        return "\n".join(rows)

    @staticmethod
    def to_markdown(package: Dict[str, Any]) -> str:
        """Render package into human-readable markdown."""
        style = package.get("style_bible", {}) if isinstance(package.get("style_bible"), dict) else {}
        lines: List[str] = []
        lines.append(f"# 导演脚本包：{package.get('title', '未命名项目')}")
        logline = str(package.get("logline", "")).strip()
        if logline:
            lines.append("")
            lines.append(f"> {logline}")

        lines.append("")
        lines.append("## 风格手册")
        lines.append(f"- 类型：{style.get('genre', '')}")
        lines.append(f"- 基调：{style.get('tone', '')}")
        lines.append(f"- 视觉风格：{style.get('visual_style', '')}")
        lines.append(f"- 色彩策略：{style.get('color_palette', '')}")
        lines.append(f"- 镜头语言：{style.get('camera_language', '')}")
        lines.append(f"- 节奏：{style.get('pacing', '')}")

        lines.append("")
        lines.append("## 人物")
        for ch in package.get("characters", []) if isinstance(package.get("characters"), list) else []:
            if not isinstance(ch, dict):
                continue
            lines.append(f"- {ch.get('name', '')}（{ch.get('role', '')}）")
            anchor = str(ch.get("appearance_anchor", "")).strip()
            if anchor:
                lines.append(f"  外貌锚点：{anchor}")
            goal = str(ch.get("goal", "")).strip()
            if goal:
                lines.append(f"  目标：{goal}")
            arc = str(ch.get("arc", "")).strip()
            if arc:
                lines.append(f"  弧光：{arc}")

        lines.append("")
        lines.append("## 场景节拍")
        for beat in package.get("scene_beats", []) if isinstance(package.get("scene_beats"), list) else []:
            if not isinstance(beat, dict):
                continue
            lines.append(f"- Scene {beat.get('scene_no', '')}: {beat.get('slugline', '')}")
            purpose = str(beat.get("dramatic_purpose", "")).strip()
            conflict = str(beat.get("conflict", "")).strip()
            turn = str(beat.get("turning_point", "")).strip()
            outcome = str(beat.get("outcome", "")).strip()
            if purpose:
                lines.append(f"  目的：{purpose}")
            if conflict:
                lines.append(f"  冲突：{conflict}")
            if turn:
                lines.append(f"  转折：{turn}")
            if outcome:
                lines.append(f"  结果：{outcome}")

        lines.append("")
        lines.append("## 导演脚本")
        script = str(package.get("director_script_markdown", "")).strip()
        lines.append(script if script else "（模型未返回导演脚本正文）")

        lines.append("")
        lines.append("## 分镜头清单")
        for shot in package.get("shot_list", []) if isinstance(package.get("shot_list"), list) else []:
            if not isinstance(shot, dict):
                continue
            lines.append(f"### Shot {shot.get('shot_no', '')}")
            lines.append(f"- 场景：{shot.get('location', '')} {shot.get('time', '')}".strip())
            character_summary = DirectorScriptBuilder.build_shot_character_summary(shot)
            if character_summary:
                lines.append(f"- 人物信息：{character_summary}")
            lines.append(f"- 镜头：{shot.get('shot_type', '')} / {shot.get('camera_movement', '')}")
            lines.append(f"- 时长：{shot.get('duration_sec', '')} 秒")
            lines.append(f"- 动作：{shot.get('action', '')}")
            dialogue = str(shot.get("dialogue", "")).strip()
            if dialogue:
                lines.append(f"- 台词：{dialogue}")
            sound = str(shot.get("sound", "")).strip()
            if sound:
                lines.append(f"- 声音：{sound}")
            veo_prompt = str(shot.get("veo_prompt", "")).strip()
            if veo_prompt:
                lines.append(f"- Veo 提示词：{veo_prompt}")

        return "\n".join(lines).strip() + "\n"
