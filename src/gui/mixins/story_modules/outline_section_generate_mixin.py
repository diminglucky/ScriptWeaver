"""Section generation workflows based on parsed outlines."""

from tkinter import END, messagebox, scrolledtext
import hashlib
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
import tkinter as tk
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    def load_dotenv(*args, **kwargs):
        return False

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize
from src.gui.helpers.story_quality import (
    extract_last_sentence,
    should_polish,
    strip_duplicate_lines,
)

logger = logging.getLogger(__name__)

CHAPTER_SEPARATOR = "=" * 50
CHAPTER_HEADER_RE = re.compile(
    r"(?:\n|^)(?P<sep>={20,})\n【第\s*(?P<chapter>\d+)\s*/\s*(?P<total>\d+)\s*章：(?P<title>[^\n】]+)】\n\n",
    re.S,
)
COMPLETED_CHAPTER_BLOCK_RE = re.compile(
    r"(?P<block>\n?={20,}\n【第\s*(?P<chapter>\d+)\s*/\s*(?P<total>\d+)\s*章：(?P<title>[^\n】]+)】\n\n"
    r"(?P<body>.*?)\n\n={20,}\n✅ 第\s*(?P=chapter)\s*章完成！本章字数：(?P<chars>\d+)\s*字\n)",
    re.S,
)


def print(*args, **kwargs):  # type: ignore[override]
    logger.info(" ".join(str(a) for a in args))


def _resolve_deepseek_client_cls():
    """Use aggregator module symbol so tests can monkey-patch one stable path."""
    try:
        from . import outline_generator as outline_generator_module  # local import avoids circular init timing issues

        patched = getattr(outline_generator_module, "DeepSeekClient", None)
        if patched is not None:
            return patched
    except Exception:
        pass
    return DeepSeekClient


class OutlineSectionGenerateMixin:
    """Generate sections and continue writing chapter-by-chapter."""

    def _run_modal_ui_call(self, func, *args, **kwargs):
        """Execute modal UI call with compatibility fallback for tests/stubs."""
        if hasattr(self, "_ui_modal"):
            return self._ui_modal(func, *args, **kwargs)
        if hasattr(self, "_ui"):
            return self._ui(func, *args, **kwargs)
        return func(*args, **kwargs)

    @staticmethod
    def _is_connection_like_error(error_text: str) -> bool:
        text = str(error_text or "").strip().lower()
        if not text:
            return False
        markers = (
            "connection error",
            "connection reset",
            "connection aborted",
            "network error",
            "timed out",
            "timeout",
            "temporarily unavailable",
            "remote protocol",
            "econnreset",
            "broken pipe",
        )
        return any(mark in text for mark in markers)

    @staticmethod
    def _build_token_candidates(max_tokens: int, *, floor: int = 900) -> list[int]:
        upper = max(600, int(max_tokens))
        candidates = [upper, int(upper * 0.78), int(upper * 0.62), floor]
        unique: list[int] = []
        for val in candidates:
            cur = max(600, int(val))
            if cur not in unique:
                unique.append(cur)
        return unique

    def _chat_with_retry_and_token_fallback(
        self,
        *,
        client,
        prompt: str,
        temperature: float,
        max_tokens: int,
        stage_label: str,
    ) -> tuple[str, str]:
        """Call chat with retries and smaller token budgets for unstable gateways."""
        last_error = ""
        token_candidates = self._build_token_candidates(max_tokens)
        for idx, tokens in enumerate(token_candidates):
            try:
                text = client.chat(
                    [{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=tokens,
                ).strip()
                if text:
                    return text, ""
                last_error = "empty response"
            except Exception as exc:
                last_error = _sanitize(str(exc)) or exc.__class__.__name__
                if not self._is_connection_like_error(last_error):
                    raise
            if idx < len(token_candidates) - 1:
                try:
                    if hasattr(self, "status"):
                        self._ui(
                            self.status.set,
                            f"{stage_label}网络波动，自动重试中（{idx+1}/{len(token_candidates)-1}）...",
                        )
                except Exception:
                    pass
                time.sleep(min(1.2, 0.45 * (idx + 1)))
        return "", last_error

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

    def on_generate_section(self) -> None:
        """生成选中的章节"""
        if not self.parsed_sections:
            messagebox.showwarning("提示", "请先生成目录")
            return
        
        query = self._get_prompt_content()
        if not query:
            messagebox.showwarning("提示", "请先输入创作需求/主题")
            return
        try:
            import time
            self._story_creativity_nonce = str(time.time_ns())
        except Exception:
            self._story_creativity_nonce = ""
        
        # 章节生成前置检查：根据模型路由确认 API Key
        fallback_provider = None
        if hasattr(self, 'story_gen_api'):
            fallback_provider = self.story_gen_api.get()
        if not fallback_provider and hasattr(self, 'quick_story_api'):
            fallback_provider = self.quick_story_api.get()
        if not fallback_provider and hasattr(self, 'api_preset'):
            fallback_provider = self.api_preset.get()
        fallback_model = None
        if hasattr(self, 'story_model_var'):
            fallback_model = self.story_model_var.get()
        elif hasattr(self, 'model'):
            fallback_model = self.model.get()
        
        api_config = self._resolve_task_api("story_generate", fallback_provider=fallback_provider, fallback_model=fallback_model)
        if not _sanitize(api_config.get("key", "")):
            messagebox.showwarning("提示", "API Key 为空，请在设置页配置")
            return
        
        # 获取选中的章节索引
        selected_index = self.section_selector.current()
        if selected_index < 0:
            messagebox.showwarning("提示", "请选择要生成的章节")
            return
        
        # 启动生成
        if self.model_only.get():
            self._generate_single_section(query, [], selected_index)
        else:
            # 带知识库检索
            need_build = False
            index_path = Path(self.index_dir.get()) / "kb.index"
            if not index_path.exists():
                if messagebox.askyesno("提示", "未找到索引，是否现在构建？"):
                    need_build = True
                else:
                    return
            
            def task():
                try:
                    self._ui(self.set_busy, True)
                    from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
                    from src.kb.search import KnowledgeBaseSearcher, SearchConfig
                    load_dotenv()
                    if need_build:
                        cfg = IngestConfig(data_root=Path(self._ui_get(self.data_dir.get)), index_dir=Path(self._ui_get(self.index_dir.get)))
                        KnowledgeBaseIngestor(cfg).build()
                    searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self._ui_get(self.index_dir.get)), top_k=self._ui_get(self.top_k.get)))
                    results = searcher.search(query, self._ui_get(self.top_k.get))
                    rag_rows = self._postprocess_rag_results(results) if hasattr(self, "_postprocess_rag_results") else results
                    contexts = [c for c, _s, _m in rag_rows]
                    self._generate_single_section_with_contexts(query, contexts, selected_index)
                except Exception as e:
                    self._report_section_generation_error(selected_index, e)
                finally:
                    self._ui(self.set_busy, False)
            threading.Thread(target=task, daemon=True).start()
    
    
    def on_continue_next_section(self) -> None:
        """继续生成下一章"""
        current_index = self.section_selector.current()
        if current_index < 0:
            messagebox.showwarning("提示", "请先选择当前章节")
            return
        
        next_index = current_index + 1
        if next_index >= len(self.parsed_sections):
            messagebox.showinfo("提示", "已经是最后一章了！")
            return
        
        # 自动选中下一章
        self.section_selector.current(next_index)
        
        # 直接生成
        self.on_generate_section()
    
    def _parallel_post_stream_repairs(
        self,
        *,
        client,
        section_content: str,
        section_title: str,
        section_index: int,
        previous_content: str,
        requirement: str,
        category: str,
    ) -> tuple[str, str, dict | None]:
        """并行执行末尾修复、衔接修复、质量评审，减少串行等待。

        Returns:
            (tail_patch, transition_result, review)
            - tail_patch: 需追加到末尾的文本，空字符串表示无需修复
            - transition_result: 衔接修复后的完整内容，与原文相同表示无需修复
            - review: 质量评审结果字典，None 表示未启用评审
        """
        quality_enabled = self._is_story_quality_review_enabled()

        with ThreadPoolExecutor(max_workers=3) as pool:
            ft_tail: Future[str] = pool.submit(
                self._repair_section_tail_if_needed,
                client, section_title, section_content,
            )
            ft_transition: Future[str] = pool.submit(
                self._repair_section_transition_if_needed,
                client,
                section_index=section_index,
                section_title=section_title,
                previous_content=previous_content,
                section_content=section_content,
            )
            ft_review: Future[dict] | None = None
            if quality_enabled:
                ft_review = pool.submit(
                    self._review_section_quality,
                    client, section_title, section_content,
                    requirement, category,
                )

            tail_patch = ft_tail.result()
            transition_result = ft_transition.result()
            review = ft_review.result() if ft_review is not None else None

        return tail_patch, transition_result, review

    @staticmethod
    def _merge_post_stream_repairs(
        section_content: str,
        tail_patch: str,
        transition_result: str,
    ) -> str:
        """合并并行修复的结果：先应用衔接修复（改开头），再追加末尾修复。"""
        merged = section_content
        if transition_result and transition_result != section_content:
            merged = transition_result
        if tail_patch:
            if not merged.endswith("\n"):
                merged += "\n"
            merged += tail_patch
        return merged

    def _generate_in_sections(self, client, requirement, contexts, sections, target_chars) -> bool:
        """分段生成长文本。返回 True=正常完成，False=中途取消。"""
        total_sections = len(sections)
        target_per_section = int(target_chars / total_sections)
        
        self._ui(self.output.insert, END, f"📖 开始分段生成（共{total_sections}段，目标总字数{target_chars}字）\n\n")
        self._ui(self.output.insert, END, "=" * 50 + "\n\n")
        
        accumulated_content = ""
        style_part = self.style.get().strip()
        category = self.category.get()
        stopped_by_preview = False

        global_action, _global_overview = self._ensure_story_global_overview_before_generation(
            client=client,
            requirement=requirement,
            category=category,
            contexts=contexts,
            outline_text=(getattr(self, "current_outline", "") or ""),
            force_review=False,
        )
        if global_action == "discard":
            self._ui(self.output.insert, END, "⏹️ 已在全书总览阶段取消，本轮分段生成已停止。\n")
            self._ui(self.output.see, END)
            self._ui(self.status.set, "已停止（全书总览未采用）")
            if hasattr(self, 'update_header_status'):
                self._ui(self.update_header_status, "分段生成已停止", "⏹️")
            return False
        
        for idx, section in enumerate(sections):
            overview_action, section_overview_plan = self._prepare_section_overview_before_generation(
                client=client,
                section=section,
                section_index=idx,
                total_sections=total_sections,
                requirement=requirement,
                contexts=contexts,
                category=category,
                previous_content=accumulated_content,
            )
            if overview_action == "discard":
                self._ui(self.output.insert, END, f"⏹️ 已取消第 {idx+1} 段生成（章节总览未采用）。\n")
                self._ui(self.output.see, END)
                self._ui(self.status.set, f"已停止（第 {idx+1} 段总览取消）")
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, "分段生成已停止", "⏹️")
                stopped_by_preview = True
                break

            # 更新状态
            self._ui(self.status.set, f"生成第 {idx+1}/{total_sections} 段: {section['title']}")
            self._ui(self.output.insert, END, f"【正在生成第 {idx+1}/{total_sections} 段】\n\n")
            self._ui(self.output.see, END)
            section_start_pos = self._ui_get(self.output.index, "end-1c") if hasattr(self, "_ui_get") else self.output.index("end-1c")
            # 更新顶部状态栏
            if hasattr(self, 'update_header_status'):
                self._ui(self.update_header_status, f"生成中 ({idx+1}/{total_sections})", "📝")
            
            # 构建本段提示词
            section_prompt = self._build_section_prompt(
                section=section,
                section_index=idx,
                total_sections=total_sections,
                previous_content=accumulated_content,
                requirement=requirement,
                contexts=contexts,
                category=category,
                style_part=style_part,
                target_chars_per_section=target_per_section,
                section_overview_plan=section_overview_plan,
            )
            template = (
                self._get_story_template_profile(requirement=requirement, category=category)
                if hasattr(self, "_get_story_template_profile")
                else {}
            )
            story_system_prompt = template.get(
                "story_system_prompt",
                "你是资深中文叙事作者，擅长结合资料写出有观点、有结构的中文故事。",
            )
            
            # 流式生成本段
            section_content = ""
            for delta in client.stream([
                {"role": "system", "content": story_system_prompt},
                {"role": "user", "content": section_prompt},
            ], temperature=self.temperature.get(), max_tokens=int(target_per_section*2.5)):
                self._ui(self.output.insert, END, delta)
                self._ui(self.output.see, END)
                section_content += delta

            # 并行执行：末尾修复 + 衔接修复 + 质量评审
            original_content = section_content
            tail_patch, transition_result, review = self._parallel_post_stream_repairs(
                client=client,
                section_content=section_content,
                section_title=section.get("title", ""),
                section_index=idx,
                previous_content=accumulated_content,
                requirement=requirement,
                category=category,
            )
            section_content = self._merge_post_stream_repairs(
                section_content, tail_patch, transition_result,
            )
            if section_content != original_content:
                self._ui(self.output.delete, section_start_pos, "end-1c")
                self._ui(self.output.insert, END, section_content)
                self._ui(self.output.see, END)

            # 质量评审结果 → 自动精修
            if review is not None:
                self._update_chapter_quality_report(idx, section.get("title", ""), review)
                min_avg, min_dim = self._get_story_quality_thresholds()
                needs_polish = should_polish(review, min_avg_score=min_avg, min_dimension_score=min_dim)
                if not needs_polish and self._needs_continuity_polish(review, idx):
                    needs_polish = True
                if needs_polish:
                    polished = self._polish_section_text(
                        client,
                        section.get("title", ""),
                        section_content,
                        review,
                        target_per_section,
                        section_index=idx,
                        previous_content=accumulated_content,
                    )
                    if polished and polished != section_content:
                        self._ui(self.output.delete, section_start_pos, "end-1c")
                        self._ui(self.output.insert, END, polished)
                        self._ui(self.output.see, END)
                        section_content = polished

            preview_action = self._preview_generated_section_before_apply(
                client=client,
                section_index=idx,
                total_sections=total_sections,
                section_title=section.get("title", ""),
                section_content=section_content,
                requirement=requirement,
                category=category,
                previous_content=accumulated_content,
            )
            if isinstance(preview_action, tuple):
                action_name, preview_text = preview_action
            else:
                action_name, preview_text = str(preview_action), section_content
            if preview_text and str(preview_text).strip():
                section_content = str(preview_text).strip()
                self._ui(self.output.delete, section_start_pos, "end-1c")
                self._ui(self.output.insert, END, section_content)
                self._ui(self.output.see, END)
            if action_name == "discard":
                self._ui(self.output.delete, section_start_pos, "end-1c")
                self._ui(self.output.insert, END, "⏹️ 已在预览阶段取消，本轮分段生成已停止。\n")
                self._ui(self.output.see, END)
                self._ui(self.status.set, f"已停止（第 {idx+1} 段预览取消）")
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, "分段生成已停止", "⏹️")
                stopped_by_preview = True
                break

            # 记忆账本（用于后续章节连贯）
            memory_entry = self._extract_memory_entry(
                client,
                section_index=idx,
                section_title=section.get("title", ""),
                section_content=section_content,
            )
            self._update_story_memory_ledger(idx, section.get("title", ""), memory_entry)
            if hasattr(self, "_update_story_diagnostics_panel"):
                self._ui(self._update_story_diagnostics_panel)
            
            # 累积内容（用于下一段的上下文）
            accumulated_content += section_content
            
            # 段落分隔
            if idx < total_sections - 1:
                self._ui(self.output.insert, END, "\n\n")
                self._ui(self.output.see, END)
        
        # 完成提示
        if stopped_by_preview:
            return False
        final_length = len(accumulated_content)
        self._ui(self.output.insert, END, f"\n\n" + "=" * 50 + "\n")
        self._ui(self.output.insert, END, f"✅ 生成完成！总字数：{final_length} 字\n")
        self._ui(self.status.set, f"生成完成（{final_length} 字）")
        return True

    
    def _generate_single_section(self, query: str, contexts: list[str], section_index: int) -> None:
        """生成单个章节（无知识库）"""
        def task():
            try:
                self._ui(self.set_busy, True)
                
                # 章节生成：根据模型路由选择 API
                fallback_provider = None
                if hasattr(self, 'story_gen_api'):
                    fallback_provider = self._ui_get(self.story_gen_api.get)
                if not fallback_provider and hasattr(self, 'quick_story_api'):
                    fallback_provider = self._ui_get(self.quick_story_api.get)
                if not fallback_provider and hasattr(self, 'api_preset'):
                    fallback_provider = self._ui_get(self.api_preset.get)
                fallback_model = None
                if hasattr(self, 'story_model_var'):
                    fallback_model = self._ui_get(self.story_model_var.get)
                elif hasattr(self, 'model'):
                    fallback_model = self._ui_get(self.model.get)
                
                api_config = self._ui_get(lambda: self._resolve_task_api("story_generate", fallback_provider=fallback_provider, fallback_model=fallback_model))
                selected_api = api_config.get("provider", "")
                api_key = _sanitize(api_config.get("key", ""))
                if not api_key:
                    self._ui(messagebox.showwarning, "提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
                    return
                
                # 获取用户选择的模型
                selected_model = api_config.get("model", "")
                print(f"🤖 使用模型: {selected_model}")
                
                client = _resolve_deepseek_client_cls()(
                    api_key=api_key,
                    base_url=_sanitize(api_config.get("base_url", "")),
                    model=selected_model,
                )
                self._do_generate_section(client, query, contexts, section_index)
            except Exception as e:
                self._report_section_generation_error(section_index, e)
            finally:
                self._ui(self.set_busy, False)
        threading.Thread(target=task, daemon=True).start()
    
    
    def _generate_single_section_with_contexts(self, query: str, contexts: list[str], section_index: int) -> None:
        """生成单个章节（带知识库）"""
        # 章节生成：根据模型路由选择 API
        fallback_provider = None
        if hasattr(self, 'story_gen_api'):
            fallback_provider = self.story_gen_api.get()
        if not fallback_provider and hasattr(self, 'quick_story_api'):
            fallback_provider = self.quick_story_api.get()
        if not fallback_provider and hasattr(self, 'api_preset'):
            fallback_provider = self.api_preset.get()
        fallback_model = None
        if hasattr(self, 'story_model_var'):
            fallback_model = self.story_model_var.get()
        elif hasattr(self, 'model'):
            fallback_model = self.model.get()
        
        api_config = self._resolve_task_api("story_generate", fallback_provider=fallback_provider, fallback_model=fallback_model)
        selected_api = api_config.get("provider", "")
        api_key = _sanitize(api_config.get("key", ""))
        if not api_key:
            self._ui(messagebox.showwarning, "提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
            return
        
        # 获取用户选择的模型
        selected_model = api_config.get("model", "")
        print(f"🤖 使用模型: {selected_model}")
        
        client = _resolve_deepseek_client_cls()(
            api_key=api_key,
            base_url=_sanitize(api_config.get("base_url", "")),
            model=selected_model,
        )
        self._do_generate_section(client, query, contexts, section_index)
    
    
    def _do_generate_section(
        self,
        client,
        query,
        contexts,
        section_index,
        existing_chapter_policy: str = "ask",
    ):
        """实际执行章节生成的核心逻辑。"""
        section = self.parsed_sections[section_index]
        total_sections = len(self.parsed_sections)
        base_output_text = self._get_output_text_snapshot()

        try:
            global_action, _global_overview = self._ensure_story_global_overview_before_generation(
                client=client,
                requirement=query,
                category=self.category.get(),
                contexts=contexts,
                outline_text=(getattr(self, "current_outline", "") or ""),
                force_review=False,
            )
            if global_action == "discard":
                self._ui(self.status.set, f"已取消第 {section_index+1} 章生成（全书总览未采用）")
                if hasattr(self, "update_header_status"):
                    self._ui(self.update_header_status, f"第 {section_index+1} 章已取消", "↩️")
                return "preview_discard"

            overview_action, section_overview_plan = self._prepare_section_overview_before_generation(
                client=client,
                section=section,
                section_index=section_index,
                total_sections=total_sections,
                requirement=query,
                contexts=contexts,
                category=self.category.get(),
                previous_content=self.generated_content,
            )
            if overview_action == "discard":
                self._ui(self.status.set, f"已取消第 {section_index+1} 章生成（总览未采用）")
                if hasattr(self, "update_header_status"):
                    self._ui(self.update_header_status, f"第 {section_index+1} 章已取消", "↩️")
                return "preview_discard"

            target_per_section, section_prompt, story_system_prompt = self._prepare_section_generation_prompt(
                section=section,
                section_index=section_index,
                total_sections=total_sections,
                query=query,
                contexts=contexts,
                section_overview_plan=section_overview_plan,
            )
            section_start_pos = self._start_section_generation_ui(
                section_index=section_index,
                total_sections=total_sections,
                section_title=section["title"],
            )
            section_content = self._stream_section_content(
                client=client,
                story_system_prompt=story_system_prompt,
                section_prompt=section_prompt,
                target_per_section=target_per_section,
            )

            # 并行执行：末尾修复 + 衔接修复 + 质量评审
            original_content = section_content
            tail_patch, transition_result, review = self._parallel_post_stream_repairs(
                client=client,
                section_content=section_content,
                section_title=section.get("title", ""),
                section_index=section_index,
                previous_content=self.generated_content,
                requirement=query,
                category=self.category.get(),
            )
            section_content = self._merge_post_stream_repairs(
                section_content, tail_patch, transition_result,
            )
            if section_content != original_content:
                self._ui(self.output.delete, section_start_pos, "end-1c")
                self._ui(self.output.insert, END, section_content)
                self._ui(self.output.see, END)

            # 质量评审结果 → 自动精修
            if review is not None:
                min_avg, min_dim = self._get_story_quality_thresholds()
                needs_polish = should_polish(review, min_avg_score=min_avg, min_dimension_score=min_dim)
                if not needs_polish and self._needs_continuity_polish(review, section_index):
                    needs_polish = True
                if needs_polish:
                    polished = self._polish_section_text(
                        client,
                        section.get("title", ""),
                        section_content,
                        review,
                        target_per_section,
                        section_index=section_index,
                        previous_content=self.generated_content,
                    )
                    if polished and polished != section_content:
                        self._ui(self.output.delete, section_start_pos, "end-1c")
                        self._ui(self.output.insert, END, polished)
                        self._ui(self.output.see, END)
                        section_content = polished

            preview_action = self._preview_generated_section_before_apply(
                client=client,
                section_index=section_index,
                total_sections=total_sections,
                section_title=section.get("title", ""),
                section_content=section_content,
                requirement=query,
                category=self.category.get(),
                previous_content=self.generated_content,
            )
            if isinstance(preview_action, tuple):
                action_name, preview_text = preview_action
            else:
                action_name, preview_text = str(preview_action), section_content

            if preview_text and str(preview_text).strip():
                section_content = str(preview_text).strip()

            if action_name == "discard":
                self._overwrite_output_text(base_output_text)
                self.generated_content = self._rebuild_generated_content_from_output(base_output_text)
                self._ui(self.status.set, f"已取消第 {section_index+1} 章入稿（预览后丢弃）")
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, f"第 {section_index+1} 章已丢弃", "↩️")
                return "preview_discard"

            action, final_output_text = self._apply_generated_section_output(
                base_output_text=base_output_text,
                section_index=section_index,
                total_sections=total_sections,
                section_title=section.get("title", ""),
                section_content=section_content,
                existing_chapter_policy=existing_chapter_policy,
            )
            self._overwrite_output_text(final_output_text)
            self.generated_content = self._rebuild_generated_content_from_output(final_output_text)

            if action in {"append", "replace"}:
                if review is not None:
                    self._update_chapter_quality_report(section_index, section.get("title", ""), review)
                memory_entry = self._extract_memory_entry(
                    client,
                    section_index=section_index,
                    section_title=section.get("title", ""),
                    section_content=section_content,
                )
                self._update_story_memory_ledger(section_index, section.get("title", ""), memory_entry)
                if hasattr(self, "_update_story_diagnostics_panel"):
                    self._ui(self._update_story_diagnostics_panel)
                self._ui(self.status.set, f"第 {section_index+1} 章完成（{len(section_content)} 字）")
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, f"第 {section_index+1} 章完成", "✅")
                self._auto_save_to_project()
                return action

            if action == "keep_both":
                self._ui(self.status.set, f"第 {section_index+1} 章候选版本已生成（原章未替换）")
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, f"第 {section_index+1} 章候选已生成", "🧪")
                self._auto_save_to_project()
                return action

            self._ui(self.status.set, f"已保留第 {section_index+1} 章原版本（新版本已丢弃）")
            if hasattr(self, 'update_header_status'):
                self._ui(self.update_header_status, f"第 {section_index+1} 章保留原版本", "↩️")
            return action
        except Exception:
            self._overwrite_output_text(base_output_text)
            raise

    def _prepare_section_generation_prompt(
        self,
        *,
        section,
        section_index: int,
        total_sections: int,
        query: str,
        contexts: list[str],
        section_overview_plan: str = "",
    ) -> tuple[int, str, str]:
        """准备章节生成提示词与系统提示。"""
        target_chars = self.target_chars.get()
        target_per_section = int(target_chars / total_sections)
        self._ensure_generated_content_initialized(query, contexts)

        section_prompt = self._build_section_prompt(
            section=section,
            section_index=section_index,
            total_sections=total_sections,
            previous_content=self.generated_content,
            requirement=query,
            contexts=contexts,
            category=self.category.get(),
            style_part=self.style.get().strip(),
            target_chars_per_section=target_per_section,
            section_overview_plan=section_overview_plan,
        )
        template = (
            self._get_story_template_profile(requirement=query, category=self.category.get())
            if hasattr(self, "_get_story_template_profile")
            else {}
        )
        story_system_prompt = template.get(
            "story_system_prompt",
            "你是资深中文叙事作者，擅长结合资料写出有观点、有结构的中文故事。",
        )
        return target_per_section, section_prompt, story_system_prompt

    def _ensure_generated_content_initialized(self, query: str, contexts: list[str]) -> None:
        """从当前输出里恢复已生成正文，必要时补运行横幅。"""
        current_output = self._get_output_text_snapshot()
        rebuilt = self._rebuild_generated_content_from_output(current_output)
        if rebuilt:
            self.generated_content = rebuilt
        elif "目录" in current_output and "\n\n" in current_output:
            parts = current_output.split("\n\n", 2)
            if len(parts) >= 3:
                self.generated_content = parts[2]
            elif len(parts) == 2:
                self.generated_content = current_output.split(self.current_outline)[-1].strip()
        else:
            self.generated_content = ""

        if not self.generated_content and hasattr(self, "_build_story_run_banner"):
            banner = self._build_story_run_banner(query, self.category.get(), contexts)
            if banner:
                self._ui(self.output.insert, END, banner + "\n\n")

    def _get_output_text_snapshot(self) -> str:
        """安全读取输出区全文。"""
        try:
            return str(self._ui_get(self.output.get, "1.0", END) or "")
        except Exception as exc:
            logger.debug("read output text failed: %s", exc)
            return ""

    def _overwrite_output_text(self, text: str) -> None:
        """用指定文本覆盖输出区，清理半截候选/报错堆栈。"""
        self._ui(self.output.delete, "1.0", END)
        if text:
            self._ui(self.output.insert, "1.0", text)
        self._ui(self.output.see, END)

    def _iter_completed_chapter_blocks(self, text: str) -> list[dict[str, object]]:
        """提取已完成章节块（仅匹配 ✅ 完成标记）。"""
        blocks: list[dict[str, object]] = []
        for match in COMPLETED_CHAPTER_BLOCK_RE.finditer(text or ""):
            blocks.append(
                {
                    "chapter": int(match.group("chapter")),
                    "total": int(match.group("total")),
                    "title": str(match.group("title")).strip(),
                    "start": match.start("block"),
                    "end": match.end("block"),
                    "body": str(match.group("body")).rstrip(),
                    "block": match.group("block"),
                }
            )
        return blocks

    def _iter_chapter_spans(self, text: str) -> list[dict[str, object]]:
        """提取所有章节块范围（含已完成/候选/失败残块）。"""
        raw_text = text or ""
        headers = list(CHAPTER_HEADER_RE.finditer(raw_text))
        spans: list[dict[str, object]] = []
        for idx, header in enumerate(headers):
            start = header.start()
            end = headers[idx + 1].start() if idx + 1 < len(headers) else len(raw_text)
            chapter_no = int(header.group("chapter"))
            block_text = raw_text[start:end]
            spans.append(
                {
                    "chapter": chapter_no,
                    "total": int(header.group("total")),
                    "title": str(header.group("title")).strip(),
                    "start": start,
                    "end": end,
                    "block": block_text,
                    "completed": bool(re.search(rf"✅\s*第\s*{chapter_no}\s*章完成", block_text)),
                    "candidate": bool(re.search(rf"🧪\s*第\s*{chapter_no}\s*章候选版本", block_text)),
                }
            )
        return spans

    def _build_chapter_block_text(
        self,
        *,
        section_index: int,
        total_sections: int,
        section_title: str,
        section_content: str,
        candidate: bool = False,
    ) -> str:
        """组装章节文本块。"""
        chapter_no = section_index + 1
        clean_content = (section_content or "").rstrip()
        footer = (
            f"🧪 第 {chapter_no} 章候选版本（本章字数：{len(clean_content)} 字，原章未替换）\n"
            if candidate
            else f"✅ 第 {chapter_no} 章完成！本章字数：{len(clean_content)} 字\n"
        )
        return (
            f"\n{CHAPTER_SEPARATOR}\n"
            f"【第 {chapter_no}/{total_sections} 章：{section_title}】\n\n"
            f"{clean_content}\n\n"
            f"{CHAPTER_SEPARATOR}\n"
            f"{footer}"
        )

    def _resolve_regeneration_policy(self, section_index: int, section_title: str) -> str:
        """询问用户如何处理重生成结果。"""
        choice = self._run_modal_ui_call(
            messagebox.askyesnocancel,
            "章节重生成",
            (
                f"检测到第 {section_index+1} 章《{section_title}》已存在。\n\n"
                "是：用新版本替换原章节（原位置覆盖）\n"
                "否：保留原章节，并在原位置后追加候选版本\n"
                "取消：保留原章节，丢弃这次新版本"
            ),
        )
        if choice is True:
            return "replace"
        if choice is False:
            return "keep_both"
        return "discard"

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

    def _is_story_preview_before_apply_enabled(self) -> bool:
        """Whether to preview chapter content before final apply/save."""
        val = getattr(self, "story_preview_before_apply", None)
        if hasattr(val, "get"):
            try:
                return bool(val.get())
            except Exception:
                pass
        raw = str(os.getenv("STORY_PREVIEW_BEFORE_APPLY", "1") or "1").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _preview_generated_section_before_apply(
        self,
        *,
        client,
        section_index: int,
        total_sections: int,
        section_title: str,
        section_content: str,
        requirement: str,
        category: str,
        previous_content: str,
    ) -> tuple[str, str]:
        """Show modal preview and return (`accept|discard`, effective content)."""
        if not self._is_story_preview_before_apply_enabled():
            return "accept", str(section_content or "").strip()
        return self._run_modal_ui_call(
            self._show_story_section_preview_dialog,
            client=client,
            section_index=section_index,
            total_sections=total_sections,
            section_title=section_title,
            section_content=section_content,
            requirement=requirement,
            category=category,
            previous_content=previous_content,
        )

    def _regenerate_section_preview_with_feedback(
        self,
        *,
        client,
        section_index: int,
        section_title: str,
        current_content: str,
        feedback: str,
        requirement: str,
        category: str,
        previous_content: str,
    ) -> str:
        """Regenerate chapter preview text from user feedback while keeping continuity."""
        current = str(current_content or "").strip()
        user_feedback = str(feedback or "").strip()
        if not current:
            return current

        try:
            temperature = float(self.temperature.get())
        except Exception:
            temperature = 0.65
        temperature = max(0.35, min(0.9, temperature))

        prev_tail = ""
        transition_context = ""
        memory_context = ""
        try:
            idx = int(section_index)
        except Exception:
            idx = 0
        if idx > 0:
            prev_tail = extract_last_sentence(previous_content or "", max_chars=260)
            if hasattr(self, "_build_section_transition_context"):
                try:
                    transition_context = str(
                        self._build_section_transition_context(section_index, previous_content) or ""
                    ).strip()
                except Exception:
                    transition_context = ""
            if hasattr(self, "_build_story_memory_context"):
                try:
                    memory_context = str(
                        self._build_story_memory_context(section_index, max_items=3) or ""
                    ).strip()
                except Exception:
                    memory_context = ""

        continuity_lines: list[str] = []
        if prev_tail:
            continuity_lines.append(f"- 上章收束句：{prev_tail}")
        if transition_context:
            continuity_lines.append(f"【跨章衔接线索】\n{transition_context}")
        if memory_context:
            continuity_lines.append(
                "【记忆账本】\n"
                f"{memory_context}\n"
                "- 人物关系、事实设定、未回收伏笔必须保持一致。"
            )
        continuity_block = ("\n\n".join(continuity_lines)).strip() if continuity_lines else "无"

        prompt = (
            "你是中文小说编辑。请根据“用户修改意见”重写当前章节预览。\n"
            "要求：\n"
            "1) 必须落实用户意见，允许调整表达与细节；\n"
            "2) 不改变章节主线事件，不新增章节标题；\n"
            "3) 与前文保持连续，不要与既有设定冲突；\n"
            "4) 仅输出重写后的章节正文。\n\n"
            f"章节标题：{section_title}\n"
            f"主题需求：{requirement}\n"
            f"题材：{category}\n"
            "用户修改意见："
            f"{user_feedback if user_feedback else '（未填写意见）请在保持主线和设定一致前提下，换一种节奏与措辞，生成一个明显不同但同质量的新版本。'}\n\n"
            f"连贯性资料：\n{continuity_block}\n\n"
            f"当前预览正文：\n{current}\n"
        )
        max_tokens = max(1200, min(8192, int(len(current) * 2.8)))
        rewritten = client.chat(
            [{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        ).strip()
        if not rewritten:
            return current
        rewritten = re.sub(r"^\s*【?第.*?章[：:】]\s*", "", rewritten).strip()
        rewritten = strip_duplicate_lines(rewritten)
        if len(rewritten) < max(40, int(len(current) * 0.45)):
            return current
        return rewritten

    def _show_story_section_preview_dialog(
        self,
        *,
        client,
        section_index: int,
        total_sections: int,
        section_title: str,
        section_content: str,
        requirement: str,
        category: str,
        previous_content: str,
    ) -> tuple[str, str]:
        """Modal preview dialog that supports feedback-based regeneration."""
        result = {"action": "discard", "content": str(section_content or "").strip()}
        dialog = tk.Toplevel(self)
        dialog.title(f"章节预览 - 第 {section_index + 1}/{total_sections} 章")
        dialog.geometry("1020x780")
        dialog.minsize(760, 560)

        header = tk.Frame(dialog, bg="#f5f5f5")
        header.pack(fill="x", padx=12, pady=(12, 8))
        tk.Label(
            header,
            text=f"《{section_title or '未命名章节'}》预览",
            bg="#f5f5f5",
            fg="#1f2937",
            font=("", 13, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            header,
            text=f"字数：{len((section_content or '').strip())} 字 | 确认后才会入稿保存",
            bg="#f5f5f5",
            fg="#4b5563",
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        tips = tk.Frame(dialog, bg="#f5f5f5")
        tips.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(
            tips,
            text="不满意可反复点“重生成预览”（可不填意见）；填意见会按你的要求改写。确认后后续章节按该版本衔接。",
            bg="#f5f5f5",
            fg="#6b7280",
            anchor="w",
        ).pack(fill="x")

        editor = scrolledtext.ScrolledText(
            dialog,
            wrap="word",
            font=("", 12),
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief=tk.FLAT,
        )
        editor.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        editor.insert("1.0", result["content"])
        editor.configure(state="disabled")

        feedback_frame = tk.Frame(dialog, bg="#f5f5f5")
        feedback_frame.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(
            feedback_frame,
            text="修改意见：",
            bg="#f5f5f5",
            fg="#1f2937",
            anchor="w",
            font=("", 10, "bold"),
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

        status_var = tk.StringVar(value="可多次重生成预览，直到满意后再采用。")
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

        def _set_preview_text(text: str) -> None:
            editor.configure(state="normal")
            editor.delete("1.0", "end")
            editor.insert("1.0", text)
            editor.configure(state="disabled")

        def _set_busy(flag: bool, message: str = "") -> None:
            busy["flag"] = flag
            state = tk.DISABLED if flag else tk.NORMAL
            btn_apply.configure(state=state)
            btn_discard.configure(state=state)
            btn_regen.configure(state=state)
            if message:
                status_var.set(message)

        def _apply():
            if busy["flag"]:
                return
            result["action"] = "accept"
            result["content"] = str(result.get("content", "") or "").strip()
            dialog.destroy()

        def _discard():
            if busy["flag"]:
                return
            result["action"] = "discard"
            dialog.destroy()

        def _regenerate():
            if busy["flag"]:
                return
            feedback = str(feedback_box.get("1.0", "end-1c") or "").strip()
            current_preview = str(result.get("content", "") or "").strip()
            if not current_preview:
                messagebox.showwarning("提示", "当前预览为空，无法重生成。")
                return

            _set_busy(
                True,
                "正在根据你的意见重生成预览..."
                if feedback
                else "正在重生成一个新版本预览...",
            )

            def _worker():
                err = ""
                new_text = current_preview
                try:
                    new_text = self._regenerate_section_preview_with_feedback(
                        client=client,
                        section_index=section_index,
                        section_title=section_title,
                        current_content=current_preview,
                        feedback=feedback,
                        requirement=requirement,
                        category=category,
                        previous_content=previous_content,
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
                        status_var.set("重生成结果为空，已保留原预览。")
                        return
                    regen_round["count"] += 1
                    result["content"] = merged
                    _set_preview_text(merged)
                    status_var.set(f"已生成第 {regen_round['count']} 个新预览版本，可继续重生成或直接采用。")

                dialog.after(0, _finish)

            threading.Thread(target=_worker, daemon=True).start()

        btn_apply = tk.Button(
            action_row,
            text="✅ 采用当前预览并入稿",
            command=_apply,
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
            text="❌ 丢弃本次生成",
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
            text="🔄 重生成预览（可多次）",
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

    def _apply_generated_section_output(
        self,
        *,
        base_output_text: str,
        section_index: int,
        total_sections: int,
        section_title: str,
        section_content: str,
        existing_chapter_policy: str = "ask",
    ) -> tuple[str, str]:
        """合并本次章节到最终输出，支持原位替换/候选保留/丢弃。"""
        chapter_no = section_index + 1
        official_block = self._build_chapter_block_text(
            section_index=section_index,
            total_sections=total_sections,
            section_title=section_title,
            section_content=section_content,
            candidate=False,
        )
        chapter_spans = self._iter_chapter_spans(base_output_text)
        chapter_blocks = [b for b in chapter_spans if int(b["chapter"]) == chapter_no]

        if not chapter_blocks:
            return "append", f"{base_output_text.rstrip()}{official_block}\n"

        policy = (existing_chapter_policy or "ask").strip().lower()
        if policy not in {"replace", "keep_both", "discard"}:
            policy = self._resolve_regeneration_policy(section_index, section_title)

        if policy == "discard":
            return "discard", base_output_text

        if policy == "keep_both":
            candidate_block = self._build_chapter_block_text(
                section_index=section_index,
                total_sections=total_sections,
                section_title=section_title,
                section_content=section_content,
                candidate=True,
            )
            insert_at = int(chapter_blocks[-1]["end"])
            merged = f"{base_output_text[:insert_at]}{candidate_block}{base_output_text[insert_at:]}"
            return "keep_both", merged

        first_start = int(chapter_blocks[0]["start"])
        slices: list[str] = []
        cursor = 0
        for block in chapter_blocks:
            start = int(block["start"])
            end = int(block["end"])
            slices.append(base_output_text[cursor:start])
            cursor = end
        slices.append(base_output_text[cursor:])
        base_without_chapter = "".join(slices)
        merged = f"{base_without_chapter[:first_start]}{official_block}{base_without_chapter[first_start:]}"
        return "replace", merged

    def _rebuild_generated_content_from_output(self, text: str) -> str:
        """从输出中回推章节正文，按章节号拼接（同章取最新完成版）。"""
        blocks = self._iter_completed_chapter_blocks(text)
        if not blocks:
            return ""

        latest_by_chapter: dict[int, str] = {}
        for block in blocks:
            latest_by_chapter[int(block["chapter"])] = str(block["body"])

        return "\n\n".join(
            (latest_by_chapter.get(chapter_no, "").strip())
            for chapter_no in sorted(latest_by_chapter.keys())
            if latest_by_chapter.get(chapter_no, "").strip()
        )

    def _report_section_generation_error(
        self,
        section_index: int,
        error: Exception,
        *,
        prefix: str = "生成出错",
    ) -> None:
        """统一错误提示：不把 traceback 写入正文区。"""
        chapter_no = max(1, int(section_index) + 1)
        brief = _sanitize(str(error)) or error.__class__.__name__
        self._ui(self.output.insert, END, f"\n❌ {prefix}（第 {chapter_no} 章）：{brief}\n")
        self._ui(self.status.set, f"第 {chapter_no} 章生成失败")
        if hasattr(self, "update_header_status"):
            self._ui(self.update_header_status, f"第 {chapter_no} 章生成失败", "❌")
        self._ui(messagebox.showerror, "错误", brief)

    def _start_section_generation_ui(self, *, section_index: int, total_sections: int, section_title: str):
        """刷新章节生成开始时的状态与输出头部。"""
        self._ui(self.status.set, f"生成第 {section_index+1}/{total_sections} 章: {section_title}")
        if hasattr(self, "update_header_status"):
            self._ui(self.update_header_status, f"生成章节 ({section_index+1}/{total_sections})", "📝")
        self._ui(self.output.insert, END, f"\n{'='*50}\n")
        self._ui(self.output.insert, END, f"【第 {section_index+1}/{total_sections} 章：{section_title}】\n\n")
        self._ui(self.output.see, END)
        if hasattr(self, "_ui_get"):
            return self._ui_get(self.output.index, "end-1c")
        return self.output.index("end-1c")

    def _stream_section_content(
        self,
        *,
        client,
        story_system_prompt: str,
        section_prompt: str,
        target_per_section: int,
    ) -> str:
        """流式生成单章正文。"""
        section_content = ""
        max_tokens = max(1200, min(8192, int(target_per_section * 3.2)))
        for delta in client.stream(
            [
                {"role": "system", "content": story_system_prompt},
                {"role": "user", "content": section_prompt},
            ],
            temperature=self.temperature.get(),
            max_tokens=max_tokens,
        ):
            self._ui(self.output.insert, END, delta)
            self._ui(self.output.see, END)
            section_content += delta
        return section_content
    
    
    def _auto_generate_all_sections(self, query, contexts, start_index=0):
        """自动生成所有章节（无知识库）"""
        def task():
            try:
                self._ui(self.set_busy, True)
                
                # 自动生成章节：根据模型路由选择 API
                fallback_provider = None
                if hasattr(self, 'story_gen_api'):
                    fallback_provider = self._ui_get(self.story_gen_api.get)
                if not fallback_provider and hasattr(self, 'quick_story_api'):
                    fallback_provider = self._ui_get(self.quick_story_api.get)
                if not fallback_provider and hasattr(self, 'api_preset'):
                    fallback_provider = self._ui_get(self.api_preset.get)
                fallback_model = None
                if hasattr(self, 'story_model_var'):
                    fallback_model = self._ui_get(self.story_model_var.get)
                elif hasattr(self, 'model'):
                    fallback_model = self._ui_get(self.model.get)
                
                api_config = self._ui_get(lambda: self._resolve_task_api("story_generate", fallback_provider=fallback_provider, fallback_model=fallback_model))
                selected_api = api_config.get("provider", "")
                api_key = _sanitize(api_config.get("key", ""))
                
                if not api_key:
                    self._ui(messagebox.showwarning, "提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
                    return
                
                # 获取用户选择的模型
                selected_model = api_config.get("model", "")
                print(f"🤖 使用模型: {selected_model}")
                
                client = _resolve_deepseek_client_cls()(
                    api_key=api_key,
                    base_url=_sanitize(api_config.get("base_url", "")),
                    model=selected_model,
                )
                
                total_sections = len(self.parsed_sections)
                current_idx = start_index
                for idx in range(start_index, total_sections):
                    current_idx = idx
                    # 更新选择器
                    self._ui(self.section_selector.current, idx)
                    
                    # 生成当前章节
                    result = self._do_generate_section(client, query, contexts, idx, existing_chapter_policy="replace")
                    if result == "preview_discard":
                        self._ui(self.output.insert, END, "\n⏹️ 已在预览阶段取消，自动生成已停止。\n")
                        self._ui(self.output.see, END)
                        self._ui(self.status.set, "自动生成已停止（预览取消）")
                        if hasattr(self, 'update_header_status'):
                            self._ui(self.update_header_status, "自动生成已停止", "⏹️")
                        return
                    
                    # 如果不是最后一章，添加提示
                    if idx < total_sections - 1:
                        self._ui(self.output.insert, END, f"\n\n⏳ 准备生成下一章...\n\n")
                        self._ui(self.output.see, END)
                
                # 全部完成
                self._ui(self.output.insert, END, f"\n\n{'='*50}\n")
                self._ui(self.output.insert, END, f"🎉 全部章节生成完成！共 {total_sections} 章，总字数：{len(self.generated_content)} 字\n")
                self._ui(self.status.set, f"全部完成（{len(self.generated_content)} 字）")
                # 更新顶部状态栏
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, "全部章节完成", "✅")
                self._ui(messagebox.showinfo, "完成", f"所有章节已生成完成！\n\n共 {total_sections} 章，总字数：{len(self.generated_content)} 字")
            except Exception as e:
                self._report_section_generation_error(current_idx, e, prefix="自动生成出错")
                # 更新顶部状态栏
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, "自动生成失败", "❌")
            finally:
                self._ui(self.set_busy, False)
        threading.Thread(target=task, daemon=True).start()
    
    
