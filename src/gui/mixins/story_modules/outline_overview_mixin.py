"""Story overview builders: global overview + section overview.

Extracted from outline_section_generate_mixin.py to reduce file size.
"""

from tkinter import END, messagebox, scrolledtext
import hashlib, logging, os, re, threading
import tkinter as tk
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*a, **k): return False

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize
from src.gui.helpers.story_quality import extract_last_sentence, strip_duplicate_lines

logger = logging.getLogger(__name__)

def _resolve_deepseek_client_cls():
    try:
        from . import outline_generator as m
        p = getattr(m, "DeepSeekClient", None)
        if p is not None: return p
    except Exception: pass
    return DeepSeekClient

class OutlineOverviewMixin:
    """Global story overview + section overview."""

    def _extract_outline_titles_for_fallback(self, outline_text: str) -> list[str]:
        titles: list[str] = []
        raw_outline = str(outline_text or "").strip()
        if raw_outline and hasattr(self, "_parse_outline_sections"):
            try:
                sections = self._parse_outline_sections(raw_outline)
            except Exception:
                sections = []
            for sec in sections:
                t = str(sec.get("title", "") or "").strip()
                if t and t not in titles:
                    titles.append(t)
        if not titles and raw_outline:
            for line in raw_outline.splitlines():
                text = str(line or "").strip()
                if not text:
                    continue
                m = re.match(r"^\s*\d+\s*[\.、]\s*(.+)$", text)
                if not m:
                    continue
                t = str(m.group(1) or "").strip()
                if t and t not in titles:
                    titles.append(t)
        return titles[:12]

    @staticmethod
    def _extract_story_role_names(requirement: str) -> tuple[str, str]:
        text = str(requirement or "").strip()
        if not text:
            return "主角", "关键关系人"

        male_patterns = (
            r"(?:男主|男主角|男生|男方)[^。；，,\n]{0,12}(?:叫|名叫|是)\s*([A-Za-z\u4e00-\u9fff]{2,6})",
            r"男主叫\s*([A-Za-z\u4e00-\u9fff]{2,6})",
        )
        female_patterns = (
            r"(?:女主|女主角|女生|女方)[^。；，,\n]{0,12}(?:叫|名叫|是)\s*([A-Za-z\u4e00-\u9fff]{2,6})",
            r"女主叫\s*([A-Za-z\u4e00-\u9fff]{2,6})",
        )

        male = ""
        female = ""
        for pattern in male_patterns:
            m = re.search(pattern, text)
            if m:
                male = str(m.group(1) or "").strip()
                if male:
                    break
        for pattern in female_patterns:
            m = re.search(pattern, text)
            if m:
                female = str(m.group(1) or "").strip()
                if female:
                    break

        if male and female:
            return male, female
        if male and not female:
            return male, "对方"
        if female and not male:
            return "对方", female
        return "主角", "关键关系人"

    @staticmethod
    def _scene_hints_for_category(category: str) -> list[str]:
        key = str(category or "").strip()
        mapping: dict[str, list[str]] = {
            "校园": ["教室", "操场看台", "宿舍走廊", "图书馆", "食堂角落", "实验楼天台", "校门口", "旧礼堂"],
            "职场": ["会议室", "工位区", "电梯间", "茶水间", "客户现场", "地下车库", "公司楼顶", "深夜办公室"],
            "悬疑": ["案发现场", "审讯室", "旧仓库", "雨夜街口", "档案室", "天台边缘", "废弃站台"],
        }
        if key in mapping:
            return mapping[key]
        return ["冲突现场", "公共空间", "私密角落", "高压场景", "对峙地点"]

    @staticmethod
    def _is_story_global_overview_too_generic(text: str) -> bool:
        raw = str(text or "").strip()
        if not raw:
            return True

        generic_phrases = (
            "主角在本章做出关键行动并付出代价",
            "关系/立场出现变化",
            "结尾抛出",
            "明确本章目标与冲突代价",
            "关系变化都由具体事件触发",
        )
        phrase_hits = sum(raw.count(p) for p in generic_phrases)
        if phrase_hits >= 2:
            return True

        numbered = [ln.strip() for ln in raw.splitlines() if re.match(r"^\s*\d+[.、]", ln)]
        if len(numbered) >= 5:
            template_like = 0
            normalized: list[str] = []
            for line in numbered:
                if ("本章" in line and ("结尾" in line or "章末" in line) and ("钩子" in line or "悬念" in line)):
                    template_like += 1
                norm = re.sub(r"《[^》]+》", "《章节》", line)
                norm = re.sub(r"\d+", "N", norm)
                normalized.append(norm)
            if template_like >= max(3, int(len(numbered) * 0.6)):
                return True
            if len(set(normalized)) <= max(2, int(len(normalized) * 0.4)):
                return True
        return False

    def _build_local_story_global_overview_fallback(
        self,
        *,
        requirement: str,
        category: str,
        outline_text: str,
    ) -> str:
        """Build an editable local fallback overview when network calls fail."""
        titles = self._extract_outline_titles_for_fallback(outline_text)
        if not titles:
            titles = [
                "冲突触发",
                "关系试探",
                "真相裂缝",
                "代价升级",
                "抉择对峙",
                "余波收束",
            ]
        lead_name, other_name = self._extract_story_role_names(requirement)
        scene_hints = self._scene_hints_for_category(category)
        chapter_lines: list[str] = []
        rel_from = ["陌生/对立", "戒备", "试探", "误判", "裂痕", "摊牌", "重建/决裂", "新秩序"]
        rel_to = ["戒备", "试探", "误判", "裂痕", "摊牌", "重建/决裂", "新秩序", "余波"]
        action_verbs = ["被迫出手", "主动试探", "被误导后反击", "顶着代价追查", "当众摊牌", "在压力下抉择", "承担后果收束"]
        for idx, title in enumerate(titles, start=1):
            next_title = titles[idx] if idx < len(titles) else "终局收束"
            scene = scene_hints[(idx - 1) % len(scene_hints)]
            verb = action_verbs[min(idx - 1, len(action_verbs) - 1)]
            r_from = rel_from[min(idx - 1, len(rel_from) - 1)]
            r_to = rel_to[min(idx - 1, len(rel_to) - 1)]
            chapter_lines.append(
                f"{idx}. 《{title}》：在{scene}，{lead_name}因“{title}”事件{verb}，{other_name}给出反制，关系由{r_from}转向{r_to}；章末抛出“{next_title}”导火索。"
            )

        act_lines: list[str] = []
        if titles:
            act_lines.append(f"1. 第一幕（开端）：由《{titles[0]}》触发主冲突，确立主角目标与阻力。")
        if len(titles) >= 3:
            act_lines.append(f"2. 第二幕（升级）：从《{titles[1]}》到《{titles[-2]}》持续加压，关系误读与代价同步放大。")
        if len(titles) >= 2:
            act_lines.append(f"3. 第三幕（终局）：在《{titles[-1]}》完成真相揭示与最终抉择，给出情感与命运落点。")

        foreshadow_lines = []
        for idx, title in enumerate(titles[:6], start=1):
            target_idx = min(len(titles), idx + 2)
            target_title = titles[target_idx - 1]
            foreshadow_lines.append(
                f"{idx}. 在《{title}》埋下一个信息点，在《{target_title}》完成解释或反转回收。"
            )

        return (
            "【全书故事总览（从开篇到结局）】\n"
            f"围绕“{requirement or '核心需求'}”，故事在“{category or '既定题材'}”场景中展开。{lead_name}在开篇因一次公开冲突被迫卷入，与{other_name}从相互防备进入高压博弈；中段不断出现误判与代价，双方关系反复拉扯并牵出旧账；终局在关键对峙里揭开核心真相，{lead_name}必须做出不可逆选择，最终以真实代价换来成长或和解。\n\n"
            "【三幕推进】\n"
            f"{chr(10).join(act_lines)}\n\n"
            "【逐章剧情总览】\n"
            f"{chr(10).join(chapter_lines)}\n\n"
            "【人物弧线与关系变化】\n"
            "1. 主角从“防御/逃避”转向“直面/承担”，每章都要体现行为层面的变化。\n"
            "2. 关键关系从试探到对抗再到重建，必须由事件推动，不靠旁白声明。\n"
            "3. 对手角色拥有独立诉求与反制动作，确保冲突真实可感。\n"
            "4. 中段至少发生一次误判导致的关系断裂，终局再完成修复或决裂。\n"
            "5. 结尾关系状态与开篇形成可对照变化，体现代价与成长并存。\n\n"
            "【高潮与结局设计】\n"
            "1. 高潮必须是人物主动选择，不是外力替角色解决问题。\n"
            "2. 结局明确回答“主角最终得到什么、失去什么”。\n"
            "3. 情感落点要回扣开篇命题，避免突然说教式收束。\n\n"
            "【伏笔与回收映射】\n"
            f"{chr(10).join(foreshadow_lines)}\n\n"
            "【写作守则（精简）】\n"
            "1. 每章必须有事件推进、关系变化、信息增量三者之一。\n"
            "2. 场景转换写清因果，不用大段概述跳剧情。\n"
            "3. 情感表达落在动作、对话、细节上，避免口号化抒情。\n"
            "4. 所有反转都要有前置线索，避免突兀改设定。\n"
            "5. 结尾必须回扣开篇核心问题，形成完整闭环。"
        )

    def _get_story_overview_detail_level(self) -> str:
        """Resolve overview detail level from env/mode/runtime."""
        raw = str(os.getenv("STORY_OVERVIEW_DETAIL_LEVEL", "") or "").strip().lower()
        if raw in {"brief", "detailed", "rich"}:
            return raw

        mode = ""
        var = getattr(self, "story_generation_mode", None)
        if hasattr(var, "get"):
            try:
                mode = str(var.get() or "").strip().lower()
            except Exception:
                mode = ""
        if mode == "fast":
            return "brief"
        if mode == "strict":
            return "rich"
        return "detailed"

    @staticmethod
    def _build_global_overview_detail_constraints(detail_level: str, chapter_count: int) -> tuple[str, int]:
        if detail_level == "brief":
            min_rows = max(4, chapter_count)
            return (
                "详细度：简版（强调速度）。\n"
                "- 「全书故事总览（从开篇到结局）」写 1 段（180-280 字），必须包含开端/升级/反转/结局；\n"
                "- 「三幕推进」至少 3 条；\n"
                f"- 「逐章剧情总览」至少 {min_rows} 条，尽量按章节对应；\n"
                "- 每条写明：本章发生什么 + 人物关系变化 + 章节结尾悬念；\n"
                "- 「写作守则（精简）」不超过 4 条，避免大段规则清单。",
                1200,
            )
        if detail_level == "rich":
            min_rows = max(8, chapter_count)
            return (
                "详细度：深度版（强调完整叙事与执行性）。\n"
                "- 「全书故事总览（从开篇到结局）」写 2-4 段（360-700 字），像真正故事梗概，必须看到完整结局；\n"
                "- 「三幕推进」至少 6 条（起势/中段反压/终局决断分开写）；\n"
                f"- 「逐章剧情总览」至少 {min_rows} 条，尽量与章节一一对应；\n"
                "- 每条必须包含：场景锚点 / 本章事件 / 关系变化 / 冲突代价 / 结尾钩子；\n"
                "- 「人物弧线与关系变化」至少 6 条，写清“前态->触发->后态”；\n"
                "- 「高潮与结局设计」至少 3 条，必须说明最终真相、关键抉择、情感落点；\n"
                "- 「伏笔与回收映射」至少 6 条，写明埋点章次与回收章次；\n"
                "- 「写作守则（精简）」最多 6 条，避免输出泛化口号。",
                2600,
            )
        min_rows = max(6, chapter_count)
        return (
            "详细度：详细版（推荐）。\n"
            "- 「全书故事总览（从开篇到结局）」写 2-3 段（260-520 字），完整交代主线走向与结局；\n"
            "- 「三幕推进」至少 4 条；\n"
            f"- 「逐章剧情总览」至少 {min_rows} 条，尽量与章节一一对应；\n"
            "- 每条必须包含：场景锚点 / 本章事件 / 关系变化 / 结尾钩子；\n"
            "- 「人物弧线与关系变化」至少 5 条，写清关系变化方向；\n"
            "- 「高潮与结局设计」至少 2 条，避免结尾悬空；\n"
            "- 「伏笔与回收映射」至少 4 条，避免后文悬空；\n"
            "- 「写作守则（精简）」最多 5 条，使用明确可执行语句。",
            1900,
        )

    @staticmethod
    def _build_section_overview_detail_constraints(detail_level: str) -> tuple[str, int]:
        if detail_level == "brief":
            return (
                "输出 5-7 条短句（每条 18-42 字）。\n"
                "每条聚焦一个动作或冲突，不要空泛总结。",
                1000,
            )
        if detail_level == "rich":
            return (
                "输出 10-14 条短句（每条 24-65 字）。\n"
                "必须覆盖：场景锚点、人物目标、障碍来源、关键动作、对话张力、心理波动、细节意象、结尾钩子。\n"
                "至少给出 2 个“可直接写入正文”的关键句（动作或台词），以保证落地写作。",
                1700,
            )
        return (
            "输出 8-12 条短句（每条 22-55 字）。\n"
            "必须覆盖：开场场景、核心冲突、动作推进、情绪变化、结尾钩子。\n"
            "至少给出 1 个可直接落地的动作句或台词句。",
            1400,
        )

    def _rewrite_story_global_overview_if_too_generic(
        self,
        *,
        client,
        requirement: str,
        category: str,
        outline_text: str,
        current_text: str,
        max_tokens: int,
    ) -> str:
        base = str(current_text or "").strip()
        if not base:
            return ""
        if not self._is_story_global_overview_too_generic(base):
            return base

        prompt = (
            "你是中文小说总编。请把下面“空话偏多”的总览重写成可执行版本。\n"
            "硬性要求：\n"
            "1) 保留结构：全书故事总览/三幕推进/逐章剧情总览/人物弧线与关系变化/高潮与结局设计/伏笔与回收映射/写作守则（精简）；\n"
            "2) 逐章剧情必须写具体事件（谁做了什么、对谁造成什么后果）；\n"
            "3) 禁止套话：\"主角在本章做出关键行动并付出代价\"、\"关系/立场出现变化\"、\"结尾抛出悬念\"；\n"
            "4) 每章至少出现一个可见场景细节（地点/动作/道具之一）；\n"
            "5) 语言直接，不要解释你在做什么。\n\n"
            f"创作需求：{requirement}\n"
            f"题材：{category}\n"
            f"目录：\n{str(outline_text or '').strip() or '（无目录）'}\n\n"
            f"待重写文本：\n{base}\n"
        )
        rewritten, error = self._chat_with_retry_and_token_fallback(
            client=client,
            prompt=prompt,
            temperature=0.45,
            max_tokens=max(700, min(1600, int(max_tokens))),
            stage_label="全书总览去空话重写",
        )
        if error and self._is_connection_like_error(error):
            return base
        rewritten = strip_duplicate_lines(str(rewritten or "").strip())
        if not rewritten:
            return base
        if self._is_story_global_overview_too_generic(rewritten):
            return base
        return rewritten

    def _build_local_section_overview_fallback(
        self,
        *,
        section_title: str,
        requirement: str,
        category: str,
        previous_content: str,
        section_points: list[str] | None = None,
    ) -> str:
        """Build editable section overview fallback for connection failures."""
        prev_tail = extract_last_sentence(previous_content or "", max_chars=120)
        if not prev_tail:
            prev_tail = "前章在情绪与冲突上留有未解张力。"
        points = [str(p).strip() for p in (section_points or []) if str(p).strip()]
        core_points = points[:4]
        while len(core_points) < 4:
            core_points.append("补充本章核心推进动作")
        title = section_title or "未命名章节"
        return (
            f"1. 开场承接前文“{prev_tail}”，在{category or '当前题材'}场域迅速落地《{title}》的第一冲突。\n"
            f"2. 主角本章目标明确化：围绕“{requirement or '核心需求'}”做一次高风险尝试并暴露代价。\n"
            f"3. 关键推进点A：{core_points[0]}，用动作与对话推动，而不是旁白解释。\n"
            f"4. 关键推进点B：{core_points[1]}，制造角色关系的试探或对抗。\n"
            f"5. 关键推进点C：{core_points[2]}，给出新信息或新证据，改变读者预期。\n"
            f"6. 关键推进点D：{core_points[3]}，让人物做出不可逆选择，强化人物弧线。\n"
            "7. 情绪轨迹：从克制试探转向正面碰撞，再落到带余震的短暂平静。\n"
            "8. 细节锚点：至少写入一个空间细节、一个身体动作细节、一个声音或气味细节。\n"
            "9. 结尾钩子：抛出下一章必须回应的问题，且与本章核心冲突直接相关。\n"
            "10. 一致性提醒：本章不改人设、不改规则，所有转折都由前文线索触发。"
        )

    def on_generate_story_overview(self) -> None:
        """生成/编辑全书总览（供后续章节强约束使用）。"""
        requirement = self._get_prompt_content()
        if not requirement:
            messagebox.showwarning("提示", "请先输入创作需求/主题")
            return

        fallback_provider = None
        if hasattr(self, "story_gen_api"):
            fallback_provider = self.story_gen_api.get()
        if not fallback_provider and hasattr(self, "quick_story_api"):
            fallback_provider = self.quick_story_api.get()
        if not fallback_provider and hasattr(self, "api_preset"):
            fallback_provider = self.api_preset.get()

        fallback_model = None
        if hasattr(self, "story_model_var"):
            fallback_model = self.story_model_var.get()
        elif hasattr(self, "model"):
            fallback_model = self.model.get()

        api_config = self._resolve_task_api(
            "story_generate",
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
        )
        selected_api = api_config.get("provider", "")
        api_key = _sanitize(api_config.get("key", ""))
        if not api_key:
            messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
            return

        selected_model = api_config.get("model", "")
        category = self.category.get() if hasattr(self, "category") else ""
        top_k = self.top_k.get() if hasattr(self, "top_k") else 6
        outline_text = self.current_outline or ""
        model_only = bool(self.model_only.get()) if hasattr(self, "model_only") else True
        index_dir_value = self.index_dir.get() if hasattr(self, "index_dir") else ""
        index_exists = bool(index_dir_value) and (Path(index_dir_value) / "kb.index").exists()

        def task():
            try:
                self._ui(self.set_busy, True)
                self._ui(self.status.set, "正在生成全书总览...")
                if hasattr(self, "update_header_status"):
                    self._ui(self.update_header_status, "全书总览生成中...", "🧭")

                contexts: list[str] = []
                if not model_only and index_exists:
                    try:
                        from src.kb.search import KnowledgeBaseSearcher, SearchConfig

                        load_dotenv()
                        searcher = KnowledgeBaseSearcher(
                            SearchConfig(index_dir=Path(index_dir_value), top_k=top_k)
                        )
                        results = searcher.search(requirement, top_k)
                        rag_rows = (
                            self._postprocess_rag_results(results)
                            if hasattr(self, "_postprocess_rag_results")
                            else results
                        )
                        contexts = [c for c, _s, _m in rag_rows]
                    except Exception as e:
                        logger.debug("load overview contexts failed: %s", e)

                client = _resolve_deepseek_client_cls()(
                    api_key=api_key,
                    base_url=_sanitize(api_config.get("base_url", "")),
                    model=selected_model,
                )
                action, overview_text = self._ensure_story_global_overview_before_generation(
                    client=client,
                    requirement=requirement,
                    category=category,
                    contexts=contexts,
                    outline_text=outline_text,
                    force_review=True,
                )
                if action == "discard":
                    self._ui(self.status.set, "已取消更新全书总览")
                    if hasattr(self, "update_header_status"):
                        self._ui(self.update_header_status, "总览未更新", "↩️")
                    return
                if overview_text:
                    self._set_story_global_overview_text(overview_text, autosave=True)
                self._ui(self.status.set, "全书总览已确认")
                if hasattr(self, "update_header_status"):
                    self._ui(self.update_header_status, "全书总览已确认", "✅")
            except Exception as e:
                brief = _sanitize(str(e)) or e.__class__.__name__
                self._ui(messagebox.showerror, "错误", f"生成全书总览失败：{brief}")
                self._ui(self.status.set, "全书总览生成失败")
                if hasattr(self, "update_header_status"):
                    self._ui(self.update_header_status, "全书总览失败", "❌")
            finally:
                self._ui(self.set_busy, False)

        threading.Thread(target=task, daemon=True).start()

    def _is_story_global_overview_enabled(self) -> bool:
        """Whether to enforce a global story overview before正文生成。"""
        val = getattr(self, "story_global_overview_enabled", None)
        if hasattr(val, "get"):
            try:
                return bool(val.get())
            except Exception:
                pass
        raw = str(os.getenv("STORY_GLOBAL_OVERVIEW_ENABLED", "1") or "1").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _get_story_global_overview_text(self) -> str:
        return str(getattr(self, "story_global_overview_text", "") or "").strip()

    def _build_story_global_overview_signature(
        self,
        *,
        requirement: str,
        category: str,
        outline_text: str,
    ) -> str:
        payload = "\n".join(
            [
                str(requirement or "").strip(),
                str(category or "").strip(),
                str(outline_text or "").strip(),
            ]
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

    def _set_story_global_overview_text(
        self,
        text: str,
        *,
        autosave: bool = False,
        signature: str | None = None,
    ) -> None:
        self.story_global_overview_text = str(text or "").strip()
        if signature is not None:
            self.story_global_overview_signature = str(signature or "").strip()
        if autosave and hasattr(self, "_auto_save_story_meta_only"):
            try:
                self._ui(self._auto_save_story_meta_only)
            except Exception:
                pass
        elif autosave and hasattr(self, "_auto_save_to_project"):
            try:
                self._ui(self._auto_save_to_project)
            except Exception:
                pass

    def _ensure_story_global_overview_before_generation(
        self,
        *,
        client,
        requirement: str,
        category: str,
        contexts: list[str],
        outline_text: str,
        force_review: bool = False,
    ) -> tuple[str, str]:
        """确保存在“已确认全书总览”，用于约束后续写作不跑偏。"""
        current = self._get_story_global_overview_text()
        expected_sig = self._build_story_global_overview_signature(
            requirement=requirement,
            category=category,
            outline_text=outline_text,
        )
        current_sig = str(getattr(self, "story_global_overview_signature", "") or "").strip()
        overview_stale = bool(current) and (not current_sig or current_sig != expected_sig)

        if not force_review and not self._is_story_global_overview_enabled():
            return "accept", current
        if current and not force_review and not overview_stale:
            return "accept", current
        if client is None or not hasattr(client, "chat"):
            return "accept", current

        if overview_stale and hasattr(self, "status"):
            try:
                self._ui(self.status.set, "检测到需求/目录变化，正在重新确认全书总览...")
            except Exception:
                pass

        initial_text = current
        if not initial_text or (force_review and overview_stale):
            initial_text = self._generate_story_global_overview_draft(
                client=client,
                requirement=requirement,
                category=category,
                contexts=contexts,
                outline_text=outline_text,
            )
        if not initial_text:
            return "accept", current

        action, overview_text = self._run_modal_ui_call(
            self._show_story_global_overview_dialog,
            client=client,
            requirement=requirement,
            category=category,
            contexts=contexts,
            outline_text=outline_text,
            initial_text=initial_text,
        )
        if action == "accept":
            self._set_story_global_overview_text(
                overview_text,
                autosave=False,
                signature=expected_sig,
            )
        return action, overview_text

    def _generate_story_global_overview_draft(
        self,
        *,
        client,
        requirement: str,
        category: str,
        contexts: list[str],
        outline_text: str,
    ) -> str:
        """生成全书总览草案（故事蓝图）。"""
        detail_level = self._get_story_overview_detail_level()
        style_value = ""
        if hasattr(self, "style"):
            try:
                style_value = str(self.style.get() or "").strip()
            except Exception:
                style_value = ""
        context_rows: list[str] = []
        for idx, ctx in enumerate(contexts or []):
            snippet = str(ctx or "").strip()
            if not snippet:
                continue
            context_rows.append(f"- 资料{idx+1}：{snippet[:280]}")
            if len(context_rows) >= 5:
                break
        contexts_text = "\n".join(context_rows) if context_rows else "- 无"
        outline_clean = str(outline_text or "").strip()
        if not outline_clean:
            outline_clean = "（尚未生成目录，请根据需求自行规划章节推进）"
        chapter_count = 0
        if hasattr(self, "_parse_outline_sections"):
            try:
                chapter_count = len(self._parse_outline_sections(outline_clean))
            except Exception:
                chapter_count = 0
        detail_constraints, max_tokens = self._build_global_overview_detail_constraints(
            detail_level,
            chapter_count,
        )

        try:
            temp = float(self.temperature.get())
        except Exception:
            temp = 0.7
        temp = max(0.35, min(0.85, temp - 0.05))

        prompt = (
            "你是中文长篇小说总编，请输出“整篇小说总览”。\n"
            "输出规范：\n"
            "1) 仅输出总览，不写正文；\n"
            "2) 按以下固定结构输出：\n"
            "【全书故事总览（从开篇到结局）】\n"
            "【三幕推进】\n"
            "【逐章剧情总览】\n"
            "【人物弧线与关系变化】\n"
            "【高潮与结局设计】\n"
            "【伏笔与回收映射】\n"
            "【写作守则（精简）】\n"
            "3) 重点是“整本会发生什么”，不是规则口号；\n"
            "4) 「逐章剧情总览」必须覆盖到结局章节，每条写清：本章事件+关系变化+章节钩子；\n"
            "5) 必须与创作需求、题材、目录一致，不能自相矛盾；\n"
            "6) 避免输出大段“必须/禁止”清单，规则项保持精简。\n\n"
            f"{detail_constraints}\n\n"
            f"创作需求：{requirement}\n"
            f"题材：{category}\n"
            f"风格：{style_value or '自动匹配'}\n\n"
            f"当前目录：\n{outline_clean}\n\n"
            f"参考资料：\n{contexts_text}\n"
        )
        text, error = self._chat_with_retry_and_token_fallback(
            client=client,
            prompt=prompt,
            temperature=temp,
            max_tokens=max_tokens,
            stage_label="全书总览",
        )
        if text:
            cleaned = strip_duplicate_lines(text)
            cleaned = self._rewrite_story_global_overview_if_too_generic(
                client=client,
                requirement=requirement,
                category=category,
                outline_text=outline_text,
                current_text=cleaned,
                max_tokens=max_tokens,
            )
            self._story_global_overview_last_source = "ai"
            return cleaned
        if error and self._is_connection_like_error(error):
            logger.warning("global overview chat failed by connection issue, use local fallback: %s", error)
            self._story_global_overview_last_source = "fallback"
            fallback_text = self._build_local_story_global_overview_fallback(
                requirement=requirement,
                category=category,
                outline_text=outline_text,
            )
            notice = (
                "【⚠️ 当前是本地应急草案（网络异常触发）】\n"
                "该版本用于兜底，细节可能偏泛；建议点击“重生成总览”拿到AI版本后再采用。\n\n"
            )
            return notice + fallback_text
        self._story_global_overview_last_source = "unknown"
        return ""

    def _regenerate_story_global_overview_with_feedback(
        self,
        *,
        client,
        requirement: str,
        category: str,
        outline_text: str,
        current_text: str,
        feedback: str,
    ) -> str:
        """根据用户反馈重写全书总览。"""
        detail_level = self._get_story_overview_detail_level()
        current = str(current_text or "").strip()
        if not current:
            return current
        user_feedback = str(feedback or "").strip()
        chapter_count = 0
        if hasattr(self, "_parse_outline_sections"):
            try:
                chapter_count = len(self._parse_outline_sections(str(outline_text or "").strip()))
            except Exception:
                chapter_count = 0
        detail_constraints, regen_max_tokens = self._build_global_overview_detail_constraints(
            detail_level,
            chapter_count,
        )

        prompt = (
            "你是中文长篇小说总编。请根据“用户反馈”重写整篇小说总览。\n"
            "要求：\n"
            "1) 保留核心主线，但可调整节奏和表达；\n"
            "2) 仍按固定结构输出：全书故事总览（从开篇到结局）/三幕推进/逐章剧情总览/人物弧线与关系变化/高潮与结局设计/伏笔与回收映射/写作守则（精简）；\n"
            "3) 「逐章剧情总览」必须覆盖到结局章节，不可只写原则；\n"
            "4) 仅输出重写后的总览，不要解释。\n\n"
            f"{detail_constraints}\n\n"
            f"创作需求：{requirement}\n"
            f"题材：{category}\n"
            f"目录：\n{str(outline_text or '').strip() or '（无目录）'}\n"
            f"用户反馈：{user_feedback if user_feedback else '请保留主线，给出一个明显不同但更紧凑的新版本。'}\n\n"
            f"当前蓝图：\n{current}\n"
        )
        try:
            temp = float(self.temperature.get())
        except Exception:
            temp = 0.7
        temp = max(0.35, min(0.9, temp))
        rewritten, error = self._chat_with_retry_and_token_fallback(
            client=client,
            prompt=prompt,
            temperature=temp,
            max_tokens=regen_max_tokens,
            stage_label="全书总览重生成",
        )
        if error and self._is_connection_like_error(error):
            logger.warning("regenerate global overview failed by connection issue: %s", error)
            return current
        if not rewritten:
            return current
        rewritten = strip_duplicate_lines(rewritten)
        rewritten = self._rewrite_story_global_overview_if_too_generic(
            client=client,
            requirement=requirement,
            category=category,
            outline_text=outline_text,
            current_text=rewritten,
            max_tokens=regen_max_tokens,
        )
        if rewritten:
            self._story_global_overview_last_source = "ai"
        return rewritten or current

    def _show_story_global_overview_dialog(
        self,
        *,
        client,
        requirement: str,
        category: str,
        contexts: list[str],
        outline_text: str,
        initial_text: str,
    ) -> tuple[str, str]:
        """显示全书总览确认弹窗，支持反复反馈重生成。"""
        _ = contexts
        result = {"action": "discard", "content": str(initial_text or "").strip()}
        dialog = tk.Toplevel(self)
        dialog.title("全书总览确认")
        dialog.geometry("980x760")
        dialog.minsize(780, 580)

        header = tk.Frame(dialog, bg="#f5f5f5")
        header.pack(fill="x", padx=12, pady=(12, 8))
        tk.Label(
            header,
            text="🧭 全书总览（从开篇到结局，后续章节按此推进）",
            bg="#f5f5f5",
            fg="#1f2937",
            font=("", 13, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            header,
            text="先确认整本故事会怎么发展、怎么收束；可直接改文案或反馈后重生成。",
            bg="#f5f5f5",
            fg="#4b5563",
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        editor = scrolledtext.ScrolledText(
            dialog,
            wrap="word",
            font=("", 12),
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief=tk.FLAT,
        )
        editor.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        editor.insert("1.0", result["content"])

        feedback_frame = tk.Frame(dialog, bg="#f5f5f5")
        feedback_frame.pack(fill="x", padx=12, pady=(0, 6))
        tk.Label(
            feedback_frame,
            text="修改意见：",
            bg="#f5f5f5",
            fg="#1f2937",
            font=("", 10, "bold"),
            anchor="w",
        ).pack(anchor="w", pady=(0, 4))
        feedback_box = scrolledtext.ScrolledText(
            feedback_frame,
            wrap="word",
            height=4,
            font=("", 11),
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief=tk.FLAT,
        )
        feedback_box.pack(fill="x")

        initial_source = str(getattr(self, "_story_global_overview_last_source", "ai") or "ai").strip().lower()
        default_status = "可多次重生成，直到你认可这个全书总览。"
        if initial_source == "fallback":
            default_status = "⚠️ 当前是本地应急草案（网络异常），内容可能偏泛。建议重生成到AI版本后再采用。"
        status_var = tk.StringVar(value=default_status)
        tk.Label(
            dialog,
            textvariable=status_var,
            bg="#f5f5f5",
            fg="#4b5563",
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 8))

        action_row = tk.Frame(dialog, bg="#f5f5f5")
        action_row.pack(fill="x", padx=12, pady=(0, 12))
        busy = {"flag": False}
        regen_round = {"count": 0}

        def _set_busy(flag: bool, message: str = "") -> None:
            busy["flag"] = flag
            state = tk.DISABLED if flag else tk.NORMAL
            btn_apply.configure(state=state)
            btn_discard.configure(state=state)
            btn_regen.configure(state=state)
            if message:
                status_var.set(message)

        def _accept():
            if busy["flag"]:
                return
            merged = str(editor.get("1.0", "end-1c") or "").strip()
            if not merged:
                messagebox.showwarning("提示", "总览为空，请先生成或补充后再采用。")
                return
            result["action"] = "accept"
            result["content"] = merged
            dialog.destroy()

        def _discard():
            if busy["flag"]:
                return
            result["action"] = "discard"
            dialog.destroy()

        def _regenerate():
            if busy["flag"]:
                return
            current = str(editor.get("1.0", "end-1c") or "").strip()
            if not current:
                messagebox.showwarning("提示", "当前总览为空，无法重生成。")
                return
            feedback = str(feedback_box.get("1.0", "end-1c") or "").strip()
            _set_busy(
                True,
                "正在根据你的意见重生成全书总览..." if feedback else "正在重生成一个新总览版本...",
            )

            def _worker():
                err = ""
                rewritten = current
                try:
                    rewritten = self._regenerate_story_global_overview_with_feedback(
                        client=client,
                        requirement=requirement,
                        category=category,
                        outline_text=outline_text,
                        current_text=current,
                        feedback=feedback,
                    )
                except Exception as exc:
                    err = _sanitize(str(exc)) or exc.__class__.__name__

                def _finish():
                    _set_busy(False)
                    if err:
                        status_var.set(f"重生成失败：{err}")
                        messagebox.showerror("重生成失败", err)
                        return
                    merged = str(rewritten or "").strip()
                    if not merged:
                        status_var.set("重生成结果为空，已保留原总览。")
                        return
                    regen_round["count"] += 1
                    editor.delete("1.0", "end")
                    editor.insert("1.0", merged)
                    source = str(getattr(self, "_story_global_overview_last_source", "ai") or "ai").strip().lower()
                    if source == "fallback":
                        status_var.set("⚠️ 网络仍不稳定，当前仍是应急草案。建议稍后继续重生成获取AI版本。")
                    else:
                        status_var.set(f"已生成第 {regen_round['count']} 个总览版本，可继续调整或直接采用。")

                dialog.after(0, _finish)

            threading.Thread(target=_worker, daemon=True).start()

        btn_apply = tk.Button(
            action_row,
            text="✅ 采用总览",
            command=_accept,
            bg="#16a34a",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        )
        btn_apply.pack(side="right")
        btn_discard = tk.Button(
            action_row,
            text="❌ 取消",
            command=_discard,
            bg="#6b7280",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        )
        btn_discard.pack(side="right", padx=(0, 10))
        btn_regen = tk.Button(
            action_row,
            text="🔄 重生成总览（可多次）",
            command=_regenerate,
            bg="#2563eb",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        )
        btn_regen.pack(side="right", padx=(0, 10))

        dialog.protocol("WM_DELETE_WINDOW", _discard)
        dialog.transient(self)
        dialog.grab_set()
        self.wait_window(dialog)
        return str(result.get("action", "discard")), str(result.get("content", "") or "").strip()

    def _is_story_overview_before_generate_enabled(self) -> bool:
        """Whether to generate a chapter overview before正文写作。"""
        val = getattr(self, "story_overview_before_generate", None)
        if hasattr(val, "get"):
            try:
                return bool(val.get())
            except Exception:
                pass
        raw = str(os.getenv("STORY_OVERVIEW_BEFORE_GENERATE", "1") or "1").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _prepare_section_overview_before_generation(
        self,
        *,
        client,
        section: dict,
        section_index: int,
        total_sections: int,
        requirement: str,
        contexts: list[str],
        category: str,
        previous_content: str,
    ) -> tuple[str, str]:
        """先生成章节总览，允许用户反馈改写后再进入正文。"""
        if not self._is_story_overview_before_generate_enabled():
            return "accept", ""
        if client is None or not hasattr(client, "chat"):
            return "accept", ""

        try:
            self._ui(self.status.set, f"正在生成第 {section_index+1} 章总览...")
            if hasattr(self, "update_header_status"):
                self._ui(self.update_header_status, f"总览生成中 ({section_index+1}/{total_sections})", "🧭")
        except Exception:
            pass

        try:
            overview = self._generate_section_overview_draft(
                client=client,
                section=section,
                section_index=section_index,
                total_sections=total_sections,
                requirement=requirement,
                contexts=contexts,
                category=category,
                previous_content=previous_content,
            )
        except Exception as exc:
            logger.warning("generate section overview failed: %s", exc)
            return "accept", ""

        if not overview:
            return "accept", ""

        return self._run_modal_ui_call(
            self._show_section_overview_dialog,
            client=client,
            section=section,
            section_index=section_index,
            total_sections=total_sections,
            requirement=requirement,
            contexts=contexts,
            category=category,
            previous_content=previous_content,
            initial_overview=overview,
        )

    def _generate_section_overview_draft(
        self,
        *,
        client,
        section: dict,
        section_index: int,
        total_sections: int,
        requirement: str,
        contexts: list[str],
        category: str,
        previous_content: str,
    ) -> str:
        """生成用于正文写作前确认的章节总览。"""
        detail_level = self._get_story_overview_detail_level()
        title = str(section.get("title", "") or "").strip()
        points = [str(item).strip() for item in (section.get("items") or []) if str(item).strip()]
        points_text = "\n".join(f"- {item}" for item in points[:8]) if points else "- 无明确要点，请围绕章节标题补齐。"
        context_chunks: list[str] = []
        for idx, raw in enumerate(contexts or []):
            snippet = str(raw or "").strip()
            if not snippet:
                continue
            context_chunks.append(f"资料{idx+1}: {snippet[:320]}")
            if len(context_chunks) >= 4:
                break
        context_text = "\n".join(context_chunks) if context_chunks else "无"
        prev_tail = extract_last_sentence(previous_content or "", max_chars=260)
        if not prev_tail:
            prev_tail = "无前文章节，可直接起笔建立场景。"

        try:
            temp = float(self.temperature.get())
        except Exception:
            temp = 0.7
        temp = max(0.35, min(0.85, temp - 0.08))
        detail_constraints, max_tokens = self._build_section_overview_detail_constraints(detail_level)

        prompt = (
            "你是中文小说策划编辑。请先输出“本章总览草案”，供作者确认后再写正文。\n"
            "输出要求：\n"
            "1) 仅输出总览内容，不写正文段落；\n"
            f"2) {detail_constraints}\n"
            "3) 必须与章节标题、主题需求、前文衔接一致，不得与既有设定冲突；\n"
            "4) 禁止 Markdown 标题、禁止额外解释。\n\n"
            f"章节位置：第 {section_index+1}/{total_sections} 章\n"
            f"章节标题：{title or '未命名章节'}\n"
            f"创作需求：{requirement}\n"
            f"题材：{category}\n"
            f"章节要点：\n{points_text}\n\n"
            f"前文收束句：{prev_tail}\n\n"
            f"参考资料摘录：\n{context_text}\n"
        )
        drafted, error = self._chat_with_retry_and_token_fallback(
            client=client,
            prompt=prompt,
            temperature=temp,
            max_tokens=max_tokens,
            stage_label=f"第 {section_index+1} 章总览",
        )
        if error and self._is_connection_like_error(error):
            logger.warning("section overview draft failed by connection issue: %s", error)
            drafted = self._build_local_section_overview_fallback(
                section_title=title,
                requirement=requirement,
                category=category,
                previous_content=previous_content,
                section_points=points,
            )
        if not drafted:
            return ""
        drafted = drafted.replace("【本章总览】", "").replace("本章总览：", "").strip()
        drafted = strip_duplicate_lines(drafted)
        return drafted

    def _regenerate_section_overview_with_feedback(
        self,
        *,
        client,
        section_index: int,
        total_sections: int,
        section_title: str,
        requirement: str,
        category: str,
        previous_content: str,
        current_overview: str,
        feedback: str,
    ) -> str:
        """根据用户意见重生成章节总览。"""
        detail_level = self._get_story_overview_detail_level()
        current = str(current_overview or "").strip()
        if not current:
            return current

        user_feedback = str(feedback or "").strip()
        prev_tail = extract_last_sentence(previous_content or "", max_chars=260)
        if not prev_tail:
            prev_tail = "无前文章节，可直接起笔建立场景。"

        try:
            temp = float(self.temperature.get())
        except Exception:
            temp = 0.7
        temp = max(0.35, min(0.9, temp))
        detail_constraints, regen_max_tokens = self._build_section_overview_detail_constraints(detail_level)

        prompt = (
            "你是中文小说策划编辑。请根据用户意见重写“章节总览草案”。\n"
            "要求：\n"
            "1) 保持章节主线与设定一致；\n"
            f"2) {detail_constraints}\n"
            "3) 只输出重写后的总览，不要解释。\n\n"
            f"章节位置：第 {section_index+1}/{total_sections} 章\n"
            f"章节标题：{section_title}\n"
            f"创作需求：{requirement}\n"
            f"题材：{category}\n"
            f"前文收束句：{prev_tail}\n"
            f"用户意见：{user_feedback if user_feedback else '未提供意见，请给出一个明显不同但同质量的新版本。'}\n\n"
            f"当前总览：\n{current}\n"
        )
        rewritten, error = self._chat_with_retry_and_token_fallback(
            client=client,
            prompt=prompt,
            temperature=temp,
            max_tokens=regen_max_tokens,
            stage_label=f"第 {section_index+1} 章总览重生成",
        )
        if error and self._is_connection_like_error(error):
            logger.warning("section overview regenerate failed by connection issue: %s", error)
            return current
        if not rewritten:
            return current
        rewritten = strip_duplicate_lines(rewritten)
        return rewritten or current

    def _show_section_overview_dialog(
        self,
        *,
        client,
        section: dict,
        section_index: int,
        total_sections: int,
        requirement: str,
        contexts: list[str],
        category: str,
        previous_content: str,
        initial_overview: str,
    ) -> tuple[str, str]:
        """章节总览确认弹窗：可多次反馈改写后再进入正文。"""
        _ = contexts
        result = {"action": "discard", "content": str(initial_overview or "").strip()}

        dialog = tk.Toplevel(self)
        dialog.title(f"章节总览确认 - 第 {section_index + 1}/{total_sections} 章")
        dialog.geometry("960x720")
        dialog.minsize(760, 560)

        header = tk.Frame(dialog, bg="#f5f5f5")
        header.pack(fill="x", padx=12, pady=(12, 8))
        tk.Label(
            header,
            text=f"《{str(section.get('title', '') or '未命名章节')}》总览草案",
            bg="#f5f5f5",
            fg="#1f2937",
            font=("", 13, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            header,
            text="先确认总览，再开始本章正文生成。你可以写意见并反复重生成。",
            bg="#f5f5f5",
            fg="#4b5563",
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        overview_box = scrolledtext.ScrolledText(
            dialog,
            wrap="word",
            height=16,
            font=("", 12),
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief=tk.FLAT,
        )
        overview_box.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        overview_box.insert("1.0", result["content"])

        feedback_frame = tk.Frame(dialog, bg="#f5f5f5")
        feedback_frame.pack(fill="x", padx=12, pady=(0, 6))
        tk.Label(
            feedback_frame,
            text="你的修改意见：",
            bg="#f5f5f5",
            fg="#1f2937",
            font=("", 10, "bold"),
            anchor="w",
        ).pack(anchor="w", pady=(0, 4))
        feedback_box = scrolledtext.ScrolledText(
            feedback_frame,
            wrap="word",
            height=4,
            font=("", 11),
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief=tk.FLAT,
        )
        feedback_box.pack(fill="x")

        status_var = tk.StringVar(value="可反复重生成总览，满意后再进入正文。")
        tk.Label(
            dialog,
            textvariable=status_var,
            bg="#f5f5f5",
            fg="#4b5563",
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 8))

        action_row = tk.Frame(dialog, bg="#f5f5f5")
        action_row.pack(fill="x", padx=12, pady=(0, 12))
        busy = {"flag": False}
        regen_round = {"count": 0}

        def _set_busy(flag: bool, message: str = "") -> None:
            busy["flag"] = flag
            state = tk.DISABLED if flag else tk.NORMAL
            btn_apply.configure(state=state)
            btn_discard.configure(state=state)
            btn_regen.configure(state=state)
            if message:
                status_var.set(message)

        def _accept():
            if busy["flag"]:
                return
            merged = str(overview_box.get("1.0", "end-1c") or "").strip()
            if not merged:
                messagebox.showwarning("提示", "总览为空，请先生成或补充后再采用。")
                return
            result["action"] = "accept"
            result["content"] = merged
            dialog.destroy()

        def _discard():
            if busy["flag"]:
                return
            result["action"] = "discard"
            dialog.destroy()

        def _regenerate():
            if busy["flag"]:
                return
            current_overview = str(overview_box.get("1.0", "end-1c") or "").strip()
            if not current_overview:
                messagebox.showwarning("提示", "当前总览为空，无法重生成。")
                return
            feedback = str(feedback_box.get("1.0", "end-1c") or "").strip()
            _set_busy(
                True,
                "正在根据你的意见重生成总览..." if feedback else "正在重生成一个新版本总览...",
            )

            def _worker():
                err = ""
                new_text = current_overview
                try:
                    new_text = self._regenerate_section_overview_with_feedback(
                        client=client,
                        section_index=section_index,
                        total_sections=total_sections,
                        section_title=str(section.get("title", "") or ""),
                        requirement=requirement,
                        category=category,
                        previous_content=previous_content,
                        current_overview=current_overview,
                        feedback=feedback,
                    )
                except Exception as exc:
                    err = _sanitize(str(exc)) or exc.__class__.__name__

                def _finish():
                    _set_busy(False)
                    if err:
                        status_var.set(f"重生成失败：{err}")
                        messagebox.showerror("重生成失败", err)
                        return
                    merged = str(new_text or "").strip()
                    if not merged:
                        status_var.set("重生成结果为空，已保留原总览。")
                        return
                    regen_round["count"] += 1
                    overview_box.delete("1.0", "end")
                    overview_box.insert("1.0", merged)
                    status_var.set(f"已生成第 {regen_round['count']} 个新总览版本，可继续调整或直接采用。")

                dialog.after(0, _finish)

            threading.Thread(target=_worker, daemon=True).start()

        btn_apply = tk.Button(
            action_row,
            text="✅ 采用总览并开始生成正文",
            command=_accept,
            bg="#16a34a",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        )
        btn_apply.pack(side="right")
        btn_discard = tk.Button(
            action_row,
            text="❌ 取消本章生成",
            command=_discard,
            bg="#6b7280",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        )
        btn_discard.pack(side="right", padx=(0, 10))
        btn_regen = tk.Button(
            action_row,
            text="🔄 重生成总览（可多次）",
            command=_regenerate,
            bg="#2563eb",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        )
        btn_regen.pack(side="right", padx=(0, 10))

        dialog.protocol("WM_DELETE_WINDOW", _discard)
        dialog.transient(self)
        dialog.grab_set()
        self.wait_window(dialog)
        return str(result.get("action", "discard")), str(result.get("content", "") or "").strip()


