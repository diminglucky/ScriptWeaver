"""Story overview builders: global overview + section overview.

Extracted from outline_section_generate_mixin.py to reduce file size.
"""

from tkinter import END, messagebox, scrolledtext
import hashlib, logging, os, re, threading
from typing import Optional
import tkinter as tk
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*a, **k): return False

from src.utils.text import sanitize as _sanitize
from src.gui.helpers.story_quality import extract_last_sentence, strip_duplicate_lines
from src.gui.helpers.story_feedback_dialog import show_story_feedback_dialog
from src.gui.mixins.story_modules.story_infra import resolve_deepseek_client_cls as _resolve_deepseek_client_cls

logger = logging.getLogger(__name__)

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
            "悬疑": [
                "家中餐桌",
                "熟悉小区楼道",
                "深夜便利店",
                "旧手机相册",
                "亲友群聊天记录",
                "反复出现的门牌号",
                "被改动过的合照",
            ],
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
            n = max(3, chapter_count)
            return (
                "要求：简洁版。\n"
                "- 「整体故事线」1段（200~350字），完整交代起因、发展、转折、结局；\n"
                f"- 「逐章剧情」{n}条，每条 80~120 字，写清本章具体发生了什么事、人物关系变化和悬念；\n"
                "- 「人物弧线」主角各 1~2 句；\n"
                "- 「高潮与结局」3~4 句。",
                max(1200, 200 * n),
            )
        if detail_level == "rich":
            n = max(6, chapter_count)
            return (
                "要求：详细版。\n"
                "- 「整体故事线」2~3段（400~600字），像小说梗概一样完整叙述从开篇到结局的故事；\n"
                f"- 「逐章剧情」{n}条，每条 150~250 字，必须包含：具体场景描写、核心事件经过、人物对话/冲突细节、关系转折点、章末悬念；\n"
                "- 「人物弧线」每个主要角色 3~4 句，写清性格/立场/关系变化轨迹；\n"
                "- 「高潮与结局」4~6 句，写清最终冲突的具体场景、人物抉择和情感结果。",
                max(2400, 300 * n),
            )
        n = max(4, chapter_count)
        return (
            "要求：标准版。\n"
            "- 「整体故事线」1~2段（300~500字），像讲故事一样完整交代起因、发展、高潮、结局；\n"
            f"- 「逐章剧情」{n}条，每条 100~180 字，必须写清：本章发生了什么具体事件（在哪里、谁做了什么）、人物之间的关键对话或冲突、关系如何变化、章末留下什么悬念；\n"
            "- 「人物弧线」每个主要角色 2~3 句，写清性格和关系的变化方向；\n"
            "- 「高潮与结局」3~5 句，写清最终冲突的具体场景和结果。",
            max(1800, 250 * n),
        )

    @staticmethod
    def _build_section_overview_detail_constraints(detail_level: str) -> tuple[str, int]:
        if detail_level == "brief":
            return (
                "输出“本章场景执行卡”，使用固定标签：\n"
                "【承接点】1句，写清从前文哪一个动作/情绪继续。\n"
                "【本章目标】1句，必须是人物能行动的具体目标。\n"
                "【场景链】3段，每段格式为“场景N：目标/阻力/行动/结果/新问题”。\n"
                "【不可逆代价】1句，写清本章结束后失去什么或局面如何改变。\n"
                "【人物状态变化】1句，写清核心人物从什么状态变成什么状态。\n"
                "【新钩子】1句，提出下一章必须回应的问题。\n"
                "【连续性禁区】1句，列出本章不得违背的人设/时间线/已发生事实。",
                1200,
            )
        if detail_level == "rich":
            return (
                "输出“本章场景执行卡”，使用固定标签：\n"
                "【承接点】2句，写清从前文哪一个动作/情绪/未解问题继续。\n"
                "【本章目标】2句，必须包含外部目标与隐性情感目标。\n"
                "【场景链】5段，每段格式为“场景N：目标/阻力/行动/结果/新问题”，每段必须有地点或动作细节。\n"
                "【反转或失败】2句，写清中段如何打破人物预期。\n"
                "【不可逆代价】2句，写清本章结束后失去什么、暴露什么或关系如何改变。\n"
                "【人物状态变化】2句，写清核心人物的情绪、立场、关系位移。\n"
                "【新钩子】2句，提出下一章必须回应的问题，且必须由本章结果触发。\n"
                "【连续性禁区】2句，列出本章不得违背的人设/时间线/已发生事实。\n"
                "【可落地细节】给出2个可直接写入正文的动作或台词方向。",
                1900,
            )
        return (
            "输出“本章场景执行卡”，使用固定标签：\n"
            "【承接点】1-2句，写清从前文哪一个动作/情绪/未解问题继续。\n"
            "【本章目标】1-2句，必须是人物能行动的具体目标。\n"
            "【场景链】4段，每段格式为“场景N：目标/阻力/行动/结果/新问题”，每段都要产生新信息、阻力或代价。\n"
            "【反转或失败】1句，写清中段如何打破人物预期。\n"
            "【不可逆代价】1-2句，写清本章结束后失去什么、暴露什么或关系如何改变。\n"
            "【人物状态变化】1-2句，写清核心人物的情绪、立场、关系位移。\n"
            "【新钩子】1句，提出下一章必须回应的问题，且必须由本章结果触发。\n"
            "【连续性禁区】1句，列出本章不得违背的人设/时间线/已发生事实。",
            1600,
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
        section_points: Optional[list] = None,
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
            f"【承接点】从前文“{prev_tail}”后的即时动作/情绪继续，不跳时空。\n"
            f"【本章目标】主角围绕“{requirement or '核心需求'}”在《{title}》里做一次可见的高风险尝试。\n"
            f"【场景链】\n"
            f"场景1：目标/把前章余波落到{category or '当前题材'}场景里；阻力/信息不完整；行动/主角主动试探；结果/第一处矛盾显形；新问题/谁在隐瞒关键原因。\n"
            f"场景2：目标/推进“{core_points[0]}”；阻力/对方回避或反制；行动/用动作与对话逼近真相；结果/关系出现裂缝；新问题/主角是否误判。\n"
            f"场景3：目标/推进“{core_points[1]}”；阻力/旧线索被推翻；行动/主角改用更冒险的方法；结果/获得新证据或新敌意；新问题/代价开始落到本人身上。\n"
            f"场景4：目标/推进“{core_points[2]}”；阻力/“{core_points[3]}”带来阻断；行动/主角做出不可回头的选择；结果/局面被改写；新问题/下一章必须处理后果。\n"
            "【反转或失败】中段至少一次让主角的原计划失败，失败原因来自前文线索而不是巧合。\n"
            "【不可逆代价】本章结束后必须失去一种安全感、关系信任、证据优势或选择空间。\n"
            "【人物状态变化】核心人物从克制试探转向正面碰撞，结尾保留带余震的短暂平静。\n"
            "【新钩子】抛出下一章必须回应的问题，且这个问题由本章最后的选择直接触发。\n"
            "【连续性禁区】不改人设、不改规则、不重写已发生事实，所有转折都由前文线索触发。"
        )

    def _strip_html_from_error(self, text: str) -> str:
        """Strip HTML tags from error messages (e.g. 502 Bad Gateway responses)."""
        import re as _re
        cleaned = _re.sub(r"<[^>]+>", " ", str(text or ""))
        cleaned = _re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:200] if cleaned else text[:200]

    def on_generate_story_overview(self) -> None:
        """查看/生成全书总览。已有缓存时直接展示，无缓存时才调用 API 生成。"""
        requirement = self._get_prompt_content()
        if not requirement:
            messagebox.showwarning("提示", "请先输入创作需求/主题")
            return

        category = self.category.get() if hasattr(self, "category") else ""
        outline_text = self.current_outline or ""

        # ---------- 有缓存且未过期 → 直接弹窗查看/编辑，不调 API ----------
        cached = self._get_story_global_overview_text()
        expected_sig = self._build_story_global_overview_signature(
            requirement=requirement, category=category, outline_text=outline_text,
        )
        current_sig = str(getattr(self, "story_global_overview_signature", "") or "").strip()
        is_fresh = bool(cached) and current_sig == expected_sig

        if is_fresh:
            self._show_cached_overview_dialog(
                cached_text=cached,
                requirement=requirement,
                category=category,
                outline_text=outline_text,
                expected_sig=expected_sig,
            )
            return

        # ---------- 无缓存或已过期 → 后台生成再弹窗 ----------
        api_config = self._resolve_generation_api_config("story_generate")
        api_key = _sanitize(api_config.get("key", ""))
        if not api_key:
            messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {api_config.get('provider', '')} 填写后保存")
            return

        selected_model = api_config.get("model", "")
        top_k = self.top_k.get() if hasattr(self, "top_k") else 6
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
                    self._set_story_global_overview_text(overview_text, autosave=True,
                                                         signature=expected_sig)
                self._ui(self.status.set, "全书总览已确认")
                if hasattr(self, "update_header_status"):
                    self._ui(self.update_header_status, "全书总览已确认", "✅")
            except Exception as e:
                raw = _sanitize(str(e)) or e.__class__.__name__
                brief = self._strip_html_from_error(raw)
                self._ui(messagebox.showerror, "错误", f"生成全书总览失败：{brief}")
                self._ui(self.status.set, "全书总览生成失败")
                if hasattr(self, "update_header_status"):
                    self._ui(self.update_header_status, "全书总览失败", "❌")
            finally:
                self._ui(self.set_busy, False)

        threading.Thread(target=task, daemon=True).start()

    def _show_cached_overview_dialog(
        self,
        *,
        cached_text: str,
        requirement: str,
        category: str,
        outline_text: str,
        expected_sig: str,
    ) -> None:
        """直接展示已缓存的总览，支持编辑保存，无需 API 调用。"""

        def _on_dialog_done(action: str, text: str) -> None:
            if action == "accept" and text:
                self._set_story_global_overview_text(text, autosave=True,
                                                     signature=expected_sig)
                if hasattr(self, "status"):
                    self.status.set("全书总览已更新")
                if hasattr(self, "update_header_status"):
                    self.update_header_status("全书总览已更新", "✅")

        action, text = show_story_feedback_dialog(
            self,
            title="全书总览",
            header_text="\U0001f9ed 全书故事情节总览",
            subtitle_text="这是已确认的总览。可直接编辑后保存，或点取消不改动。",
            initial_content=cached_text,
            default_status="当前为已保存版本，可直接编辑。",
            geometry="980x760",
            min_size=(780, 580),
            accept_label="\u2705 保存修改",
            discard_label="\u274c 关闭",
            regen_label=None,
            editor_readonly=False,
            regenerate_fn=None,
        )
        _on_dialog_done(action, text)

    def _is_story_fast_mode(self) -> bool:
        """STORY_FAST_MODE=1 时跳过所有可选步骤（总览/预览/质量评审/记忆提取）。"""
        raw = str(os.getenv("STORY_FAST_MODE", "0") or "0").strip().lower()
        return raw in {"1", "true", "yes", "on"}

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
        signature: Optional[str] = None,
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
        skip_dialog: bool = False,
    ) -> tuple[str, str]:
        """确保存在“已确认全书总览”，用于约束后续写作不跑偏。

        skip_dialog=True 时跳过弹窗自动采用（用于自动批量生成）。
        """
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

        if skip_dialog:
            self._set_story_global_overview_text(
                initial_text,
                autosave=False,
                signature=expected_sig,
            )
            return "accept", initial_text

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
            "你是中文小说策划，请根据目录和创作需求，输出整篇故事情节总览。\n"
            "核心要求：\n"
            "- 像讲故事一样把整个剧情讲清楚，读完后要能知道这本小说从头到尾到底讲了什么；\n"
            "- 每章剧情必须写具体事件（谁在哪里做了什么），不要用“发生了冲突”“关系变化”等笼统表述；\n"
            "- 仅输出情节总览，不写正文，不写规则。\n\n"
            f"{detail_constraints}\n\n"
            f"创作需求：{requirement}\n"
            f"题材：{category}\n"
            f"风格：{style_value or '自动匹配'}\n\n"
            f"目录：\n{outline_clean}\n"
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

        initial_source = str(getattr(self, "_story_global_overview_last_source", "ai") or "ai").strip().lower()
        default_status = "可多次重生成，直到你认可这个全书总览。"
        if initial_source == "fallback":
            default_status = "⚠️ 当前是本地应急草案（网络异常），内容可能偏泛。建议重生成到AI版本后再采用。"

        def _regen(current_text: str, feedback: str) -> str:
            return self._regenerate_story_global_overview_with_feedback(
                client=client,
                requirement=requirement,
                category=category,
                outline_text=outline_text,
                current_text=current_text,
                feedback=feedback,
            )

        return show_story_feedback_dialog(
            self,
            title="全书总览确认",
            header_text="🧭 全书总览（从开篇到结局，后续章节按此推进）",
            subtitle_text="先确认整本故事会怎么发展、怎么收束；可直接改文案或反馈后重生成。",
            initial_content=initial_text,
            default_status=default_status,
            geometry="980x760",
            min_size=(780, 580),
            accept_label="✅ 采用总览",
            discard_label="❌ 取消",
            regen_label="🔄 重生成总览（可多次）",
            editor_readonly=False,
            regenerate_fn=_regen,
        )

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
        skip_dialog: bool = False,
    ) -> tuple[str, str]:
        """先生成章节总览，允许用户反馈改写后再进入正文。

        skip_dialog=True 时跳过弹窗自动采用（用于自动批量生成）。
        """
        if self._is_story_fast_mode():
            return "accept", ""

        # 优先使用预生成的章节蓝图（跳过 API 调用）
        if hasattr(self, "_get_chapter_blueprint_for") and self._is_chapter_blueprints_fresh():
            bp = self._get_chapter_blueprint_for(section_index)
            if bp:
                logger.info("chapter %d using cached blueprint (%d chars), skip overview API",
                            section_index + 1, len(bp))
                return "accept", bp

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

        if skip_dialog:
            return "accept", overview

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
        """生成用于正文写作前确认的章节场景执行卡。"""
        detail_level = self._get_story_overview_detail_level()
        title = str(section.get("title", "") or "").strip()
        event_promise = str(section.get("event_promise", "") or "").strip()
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
        state_contract = ""
        if hasattr(self, "_build_story_state_contract"):
            try:
                state_contract = str(
                    self._build_story_state_contract(section_index, previous_content) or ""
                ).strip()
            except Exception:
                state_contract = ""

        try:
            temp = float(self.temperature.get())
        except Exception:
            temp = 0.7
        temp = max(0.35, min(0.85, temp - 0.08))
        detail_constraints, max_tokens = self._build_section_overview_detail_constraints(detail_level)

        prompt = (
            "你是中文小说策划编辑。请先输出“本章场景执行卡”，供作者确认后再写正文。\n"
            "输出要求：\n"
            "1) 仅输出场景执行卡，不写正文段落，不写纯摘要；\n"
            f"2) {detail_constraints}\n"
            "3) 必须与章节标题、主题需求、前文衔接一致，不得与既有设定冲突；\n"
            "4) 场景链必须按因果推进：上一场结果要制造下一场阻力或新问题；\n"
            "5) 【连续性禁区】必须引用故事状态合同里的事实、关系、时间线或未回收钩子；\n"
            "6) 禁止 Markdown 标题、禁止额外解释。\n\n"
            f"章节位置：第 {section_index+1}/{total_sections} 章\n"
            f"章节标题：{title or '未命名章节'}\n"
            f"本章不可逆事件承诺：{event_promise if event_promise else '无明确承诺，请在总览中补一个会改变后续选择空间的不可逆事件'}\n"
            f"创作需求：{requirement}\n"
            f"题材：{category}\n"
            f"章节要点：\n{points_text}\n\n"
            f"前文收束句：{prev_tail}\n\n"
            f"故事状态合同：\n{state_contract if state_contract else '无'}\n\n"
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
        drafted = (
            drafted.replace("【本章总览】", "")
            .replace("本章总览：", "")
            .replace("【本章场景执行卡】", "")
            .replace("本章场景执行卡：", "")
            .strip()
        )
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
        """根据用户意见重生成章节场景执行卡。"""
        detail_level = self._get_story_overview_detail_level()
        current = str(current_overview or "").strip()
        if not current:
            return current

        user_feedback = str(feedback or "").strip()
        prev_tail = extract_last_sentence(previous_content or "", max_chars=260)
        if not prev_tail:
            prev_tail = "无前文章节，可直接起笔建立场景。"
        state_contract = ""
        if hasattr(self, "_build_story_state_contract"):
            try:
                state_contract = str(
                    self._build_story_state_contract(section_index, previous_content) or ""
                ).strip()
            except Exception:
                state_contract = ""

        try:
            temp = float(self.temperature.get())
        except Exception:
            temp = 0.7
        temp = max(0.35, min(0.9, temp))
        detail_constraints, regen_max_tokens = self._build_section_overview_detail_constraints(detail_level)

        prompt = (
            "你是中文小说策划编辑。请根据用户意见重写“本章场景执行卡”。\n"
            "要求：\n"
            "1) 保持章节主线与设定一致；\n"
            f"2) {detail_constraints}\n"
            "3) 场景链必须按因果推进：上一场结果要制造下一场阻力或新问题；\n"
            "4) 【连续性禁区】必须引用故事状态合同里的事实、关系、时间线或未回收钩子；\n"
            "5) 只输出重写后的场景执行卡，不要解释。\n\n"
            f"章节位置：第 {section_index+1}/{total_sections} 章\n"
            f"章节标题：{section_title}\n"
            f"创作需求：{requirement}\n"
            f"题材：{category}\n"
            f"前文收束句：{prev_tail}\n"
            f"故事状态合同：\n{state_contract if state_contract else '无'}\n"
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
        section_title = str(section.get("title", "") or "未命名章节")

        def _regen(current_text: str, feedback: str) -> str:
            return self._regenerate_section_overview_with_feedback(
                client=client,
                section_index=section_index,
                total_sections=total_sections,
                section_title=section_title,
                requirement=requirement,
                category=category,
                previous_content=previous_content,
                current_overview=current_text,
                feedback=feedback,
            )

        return show_story_feedback_dialog(
            self,
            title=f"章节总览确认 - 第 {section_index + 1}/{total_sections} 章",
            header_text=f"《{section_title}》场景执行卡",
            subtitle_text="先确认场景执行卡，再开始本章正文生成。你可以写意见并反复重生成。",
            initial_content=initial_overview,
            default_status="可反复重生成执行卡，满意后再进入正文。",
            geometry="960x720",
            accept_label="✅ 采用执行卡并开始生成正文",
            discard_label="❌ 取消本章生成",
            regen_label="🔄 重生成执行卡（可多次）",
            editor_readonly=False,
            regenerate_fn=_regen,
        )

    # ── Chapter Blueprint System ─────────────────────────────────

    def _get_chapter_blueprints(self) -> list[dict]:
        """获取已缓存的章节蓝图列表。"""
        bps = getattr(self, "chapter_blueprints", [])
        return bps if isinstance(bps, list) else []

    def _get_chapter_blueprint_for(self, section_index: int) -> str:
        """获取指定章节的蓝图文本。如果蓝图不存在或已过期，返回空字符串。"""
        bps = self._get_chapter_blueprints()
        if section_index < 0 or section_index >= len(bps):
            return ""
        bp = bps[section_index]
        if not isinstance(bp, dict):
            return ""
        return str(bp.get("blueprint", "") or "").strip()

    def _is_chapter_blueprints_fresh(self) -> bool:
        """蓝图是否与当前目录一致（通过签名判断）。"""
        sig = getattr(self, "_chapter_blueprints_outline_sig", "")
        outline = str(getattr(self, "current_outline", "") or "").strip()
        if not sig or not outline:
            return False
        return sig == hashlib.md5(outline.encode()).hexdigest()

    def _invalidate_chapter_blueprints(self) -> None:
        """目录变化时清除蓝图缓存。"""
        self.chapter_blueprints = []
        self._chapter_blueprints_outline_sig = ""

    def generate_all_chapter_blueprints(
        self,
        *,
        client,
        requirement: str,
        category: str,
        outline_text: str,
        sections: list[dict],
    ) -> list[dict]:
        """一次 API 调用，批量生成所有章节的场景执行卡（每章 ~500 字）。

        执行卡用于约束正文生成，包含：
        - 与上一章的即时承接点
        - 本章人物可行动目标
        - 3-5 个因果相连的场景推进节点
        - 中段反转/失败、不可逆代价
        - 人物状态变化、章末新钩子
        - 连续性禁区
        """
        n = len(sections)
        if n == 0:
            return []

        titles_block = "\n".join(
            f"第{i+1}章：{s.get('title', '未命名')}" for i, s in enumerate(sections)
        )

        style_value = ""
        if hasattr(self, "style"):
            try:
                style_value = self.style.get().strip()
            except Exception:
                pass

        global_overview = ""
        if hasattr(self, "_get_story_global_overview_text"):
            try:
                global_overview = str(self._get_story_global_overview_text() or "").strip()
            except Exception:
                pass
        overview_block = (
            f"【全书总览（已确认）】\n{global_overview}\n\n"
            if global_overview else ""
        )

        chars_per_chapter = max(400, min(600, 3500 // n))

        prompt = (
            "你是中文长篇小说的策划总编。请根据目录和创作需求，一次性输出所有章节的**场景执行卡**。\n\n"
            "每章执行卡必须包含以下固定标签（缺一不可）：\n"
            "1. 【承接点】本章开头从上一章哪个动作、情绪、未解问题继续（第1章写如何开篇破题）\n"
            "2. 【本章目标】人物在本章要完成的可见行动目标，不能只是“成长/反思/推进关系”\n"
            "3. 【场景链】3-5个场景，每个场景必须使用“场景N：目标/阻力/行动/结果/新问题”的格式\n"
            "4. 【反转或失败】中段至少一次打破人物预期，失败原因必须来自前文线索或人物选择\n"
            "5. 【不可逆代价】本章结束后失去什么、暴露什么、关系如何改变或选择空间如何收窄\n"
            "6. 【人物状态变化】核心人物的情绪、立场、关系从哪里移动到哪里\n"
            "7. 【新钩子】下一章必须回应的问题，必须由本章结果触发\n"
            "8. 【伏笔线索】本章需要埋下或回收的伏笔（标注：埋伏笔→第N章回收 / 回收→来自第N章）\n"
            "9. 【连续性禁区】本章不得违背的人设、时间线、地点状态、已发生事实\n\n"
            "硬性要求：\n"
            f"- 每章执行卡 {chars_per_chapter}-{chars_per_chapter + 150} 字，必须写具体事件，禁止笼统表述\n"
            "- 场景链之间必须因果相连：上一场结果制造下一场阻力或新问题\n"
            "- 章节之间必须因果相连，后面章节的事件必须在前面有铺垫\n"
            "- 最后一章必须收束所有主线和伏笔\n"
            "- 人物性格/立场的变化必须跨章连续，不能突变\n"
            f"- 用 === 第N章 === 作为分隔符\n\n"
            "输出格式（严格遵循）：\n"
            "=== 第1章 ===\n"
            "【承接点】...\n"
            "【本章目标】...\n"
            "【场景链】\n"
            "场景1：目标/...；阻力/...；行动/...；结果/...；新问题/...\n"
            "场景2：目标/...；阻力/...；行动/...；结果/...；新问题/...\n"
            "场景3：目标/...；阻力/...；行动/...；结果/...；新问题/...\n"
            "【反转或失败】...\n"
            "【不可逆代价】...\n"
            "【人物状态变化】...\n"
            "【新钩子】...\n"
            "【伏笔线索】...\n"
            "【连续性禁区】...\n\n"
            "=== 第2章 ===\n"
            "...\n\n"
            f"{overview_block}"
            f"创作需求：{requirement}\n"
            f"题材：{category}\n"
            f"风格：{style_value or '自动匹配'}\n\n"
            f"目录（共{n}章）：\n{titles_block}\n"
        )

        try:
            temp = float(self.temperature.get())
        except Exception:
            temp = 0.7
        temp = max(0.4, min(0.8, temp - 0.05))

        max_tokens = max(3000, (chars_per_chapter + 200) * n)

        messages = [
            {"role": "system", "content": "你是资深中文长篇小说策划总编，擅长全局规划故事结构、人物弧线和伏笔网络。"},
            {"role": "user", "content": prompt},
        ]

        # 流式生成蓝图，让用户实时看到进度
        result = ""
        _buf = ""
        _last_t = 0.0
        _FLUSH = 0.08
        try:
            import time as _time
            _last_t = _time.time()
            for delta in client.stream(messages, temperature=temp, max_tokens=max_tokens):
                result += delta
                _buf += delta
                now = _time.time()
                if now - _last_t >= _FLUSH or "\n" in delta:
                    try:
                        self._ui(self.output.insert, "end", _buf)
                        self._ui(self.output.see, "end")
                    except Exception:
                        pass
                    _buf = ""
                    _last_t = now
            if _buf:
                try:
                    self._ui(self.output.insert, "end", _buf)
                    self._ui(self.output.see, "end")
                except Exception:
                    pass
        except Exception as exc:
            logger.warning("generate chapter blueprints stream failed: %s", exc)
            if not result.strip():
                # 流式失败，回退到阻塞调用
                try:
                    result = client.chat(messages, temperature=temp, max_tokens=max_tokens)
                except Exception as exc2:
                    logger.warning("generate chapter blueprints fallback failed: %s", exc2)
                    return []

        if not result or not result.strip():
            return []

        # 解析：按 === 第N章 === 分割
        blueprints = self._parse_chapter_blueprints(result.strip(), n)
        if blueprints:
            self.chapter_blueprints = blueprints
            self._chapter_blueprints_outline_sig = hashlib.md5(
                str(outline_text or "").strip().encode()
            ).hexdigest()
        return blueprints

    @staticmethod
    def _parse_chapter_blueprints(raw_text: str, expected_count: int) -> list[dict]:
        """解析 AI 输出的蓝图文本，按章节分割。"""
        import re as _re
        # 按 === 第N章 === 或类似分隔符切割
        parts = _re.split(r"={2,}\s*第\s*(\d+)\s*章\s*={2,}", raw_text)
        # parts: ['前缀', '1', '蓝图1', '2', '蓝图2', ...]
        blueprints: list[dict] = []
        i = 1
        while i < len(parts) - 1:
            try:
                chapter_num = int(parts[i])
            except (ValueError, TypeError):
                i += 2
                continue
            text = parts[i + 1].strip()
            if text:
                blueprints.append({
                    "chapter_index": chapter_num - 1,
                    "blueprint": text,
                })
            i += 2

        # 如果解析不出来（AI 没按格式），按空行切割兜底
        if len(blueprints) < max(1, expected_count // 2):
            chunks = _re.split(r"\n{2,}(?=第\d+章|【场景|章节\d+)", raw_text)
            blueprints = []
            for idx, chunk in enumerate(chunks):
                chunk = chunk.strip()
                if chunk and len(chunk) > 50:
                    blueprints.append({
                        "chapter_index": idx,
                        "blueprint": chunk,
                    })

        return blueprints

    def generate_chapter_blueprints_async(self) -> None:
        """UI 入口：异步生成全部章节蓝图。"""
        outline = str(getattr(self, "current_outline", "") or "").strip()
        sections = getattr(self, "parsed_sections", [])
        if not outline or not sections:
            from tkinter import messagebox
            messagebox.showwarning("提示", "请先生成目录")
            return

        requirement = self._get_prompt_content()
        if not requirement:
            from tkinter import messagebox
            messagebox.showwarning("提示", "请先输入创作需求")
            return

        def task():
            try:
                self._ui(self.set_busy, True)
                self._ui(self.status.set, "正在生成全部章节蓝图...")
                if hasattr(self, "update_header_status"):
                    self._ui(self.update_header_status, "蓝图生成中...", "📋")

                # 记录流式输出前的位置，生成完毕后清除蓝图文本
                pre_pos = self._ui_get(self.output.index, "end-1c") if hasattr(self, "_ui_get") else "end-1c"

                api_config = self._resolve_generation_api_config_safe("story_generate")
                client = self._create_generation_client(api_config)
                category = self._ui_get(self.category.get)

                blueprints = self.generate_all_chapter_blueprints(
                    client=client,
                    requirement=requirement,
                    category=category,
                    outline_text=outline,
                    sections=sections,
                )

                # 清除流式输出的蓝图文本（蓝图已缓存到 self.chapter_blueprints）
                try:
                    self._ui(self.output.delete, pre_pos, "end-1c")
                except Exception:
                    pass

                if blueprints:
                    n = len(blueprints)
                    total_chars = sum(len(bp.get("blueprint", "")) for bp in blueprints)
                    self._ui(self.status.set, f"蓝图已生成（{n}章，共{total_chars}字）")
                    if hasattr(self, "update_header_status"):
                        self._ui(self.update_header_status, f"蓝图就绪（{n}章）", "✅")
                    # 输出简洁汇总（蓝图数据已缓存，无需在输出区占位）
                    summary_lines = [f"📋 蓝图已就绪（{n}章，共{total_chars}字）"]
                    for bp in blueprints:
                        idx = bp.get("chapter_index", 0)
                        bp_text = bp.get("blueprint", "")
                        first_line = bp_text.split("\n")[0][:60] if bp_text else ""
                        summary_lines.append(f"  第{idx+1}章: {first_line}...")
                    self._ui(self.output.insert, "end", "\n".join(summary_lines) + "\n\n")
                    self._ui(self.output.see, "end")
                else:
                    self._ui(self.status.set, "蓝图生成失败，将使用逐章总览")
                    if hasattr(self, "update_header_status"):
                        self._ui(self.update_header_status, "蓝图生成失败", "⚠️")
            except Exception as exc:
                logger.exception("chapter blueprint generation failed")
                self._ui(self.status.set, f"蓝图生成失败：{str(exc)[:60]}")
            finally:
                self._ui(self.set_busy, False)

        threading.Thread(target=task, daemon=True).start()
