import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values

from src.gui.helpers.story_creativity import list_story_creativity_modes
from src.gui.helpers.story_generation_modes import list_story_generation_modes
from src.gui.helpers.story_templates import (
    list_story_template_strategies,
    list_story_templates,
)
from src.gui.mixins.settings_mixin import SettingsMixin
from src.gui.mixins.story_modules.ui_builder import StoryUIBuilderMixin


class _Var:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Label:
    def __init__(self):
        self.text = ""

    def config(self, **kwargs):
        if "text" in kwargs:
            self.text = kwargs["text"]


class _Log:
    def __init__(self):
        self.buffer = ""

    def insert(self, _pos, text):
        self.buffer += str(text)

    def see(self, _pos):
        _ = _pos


class _DummySettings(SettingsMixin):
    def _on_settings_provider_change(self, event=None):  # pragma: no cover - test stub
        _ = event

    def _on_settings_img_provider_change(self, event=None):  # pragma: no cover - test stub
        _ = event

    def _sync_img_runtime_from_config(self, provider_name=None):  # pragma: no cover - test stub
        _ = provider_name


class _DummyPromptBuilder(StoryUIBuilderMixin):
    pass


class StoryTemplateHeadlessTests(unittest.TestCase):
    def _build_settings_obj(self):
        obj = _DummySettings()
        template_items = list_story_templates()
        obj.story_template_key_to_label = {item["key"]: item["label"] for item in template_items}
        obj.story_template_label_to_key = {item["label"]: item["key"] for item in template_items}
        obj.story_template_key = _Var("zhihu_realistic")
        obj.story_template_select_var = _Var("都市逆袭爽文")
        obj.story_template_desc_label = _Label()
        strategy_items = list_story_template_strategies()
        obj.story_template_strategy_key_to_label = {
            item["key"]: item["label"] for item in strategy_items
        }
        obj.story_template_strategy_label_to_key = {
            item["label"]: item["key"] for item in strategy_items
        }
        obj.story_template_strategy = _Var("fixed")
        obj.story_template_strategy_select_var = _Var(obj.story_template_strategy_key_to_label["fixed"])
        obj.story_template_strategy_desc_label = _Label()
        creativity_items = list_story_creativity_modes()
        obj.story_creativity_key_to_label = {item["key"]: item["label"] for item in creativity_items}
        obj.story_creativity_label_to_key = {item["label"]: item["key"] for item in creativity_items}
        obj.story_creativity_mode = _Var("blend")
        obj.story_creativity_select_var = _Var(obj.story_creativity_key_to_label["blend"])
        obj.story_creativity_desc_label = _Label()
        generation_mode_items = list_story_generation_modes()
        obj.story_generation_mode_key_to_label = {
            item["key"]: item["label"] for item in generation_mode_items
        }
        obj.story_generation_mode_label_to_key = {
            item["label"]: item["key"] for item in generation_mode_items
        }
        obj.story_generation_mode = _Var("balanced")
        obj.story_generation_mode_select_var = _Var(obj.story_generation_mode_key_to_label["balanced"])
        obj.story_generation_mode_desc_label = _Label()
        obj.settings_log = _Log()
        obj.model_only = _Var(False)
        obj.rag_min_score = _Var(0.12)
        obj.story_quality_review_enabled = _Var(True)
        obj.story_quality_min_avg = _Var(7.4)
        obj.story_quality_min_dim = _Var(6.8)
        obj.story_outline_alignment_strict = _Var(True)
        obj.story_outline_alignment_max_attempts = _Var(2)
        obj.story_global_overview_enabled = _Var(True)
        obj.story_overview_before_generate = _Var(True)
        obj.story_preview_before_apply = _Var(True)
        obj.quick_story_api = _Var("DeepSeek")
        obj.quick_image_api = _Var("OpenAI (DALL-E)")
        obj.api_providers = {"DeepSeek": {}}
        obj.api_presets = {"DeepSeek": {}}
        obj.img_api_providers = {"OpenAI (DALL-E)": {}}
        obj.img_api_presets = {"OpenAI (DALL-E)": {}}
        return obj

    def test_template_selection_persists_to_env_and_updates_desc(self):
        obj = self._build_settings_obj()
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            try:
                obj._on_story_template_changed()
                self.assertEqual(obj.story_template_key.get(), "urban_power")
                self.assertIn("都市逆袭爽文", obj.story_template_desc_label.text)
                env_text = Path(td, ".env").read_text(encoding="utf-8")
                self.assertIn("STORY_TEMPLATE_KEY", env_text)
                self.assertIn("urban_power", env_text)
            finally:
                os.chdir(old_cwd)

    def test_quick_switch_load_applies_template_key_to_ui_vars(self):
        obj = self._build_settings_obj()
        old_story = os.environ.get("STORY_OUTLINE_GEN_API")
        old_image = os.environ.get("IMAGE_GEN_API")
        old_generation_mode = os.environ.get("STORY_GENERATION_MODE")
        old_template = os.environ.get("STORY_TEMPLATE_KEY")
        old_template_strategy = os.environ.get("STORY_TEMPLATE_STRATEGY")
        old_creativity = os.environ.get("STORY_CREATIVITY_MODE")
        old_model_only = os.environ.get("MODEL_ONLY")
        old_rag_min_score = os.environ.get("RAG_MIN_SCORE")
        old_quality_review = os.environ.get("STORY_QUALITY_REVIEW")
        old_quality_min_avg = os.environ.get("STORY_QUALITY_MIN_AVG")
        old_quality_min_dim = os.environ.get("STORY_QUALITY_MIN_DIM")
        old_outline_align_strict = os.environ.get("STORY_OUTLINE_ALIGNMENT_STRICT")
        old_outline_align_attempts = os.environ.get("STORY_OUTLINE_ALIGNMENT_MAX_ATTEMPTS")
        try:
            os.environ["STORY_OUTLINE_GEN_API"] = "DeepSeek"
            os.environ["IMAGE_GEN_API"] = "OpenAI (DALL-E)"
            os.environ["STORY_GENERATION_MODE"] = "strict"
            os.environ["STORY_TEMPLATE_KEY"] = "xianxia_fantasy"
            os.environ["STORY_TEMPLATE_STRATEGY"] = "shuffle"
            os.environ["STORY_CREATIVITY_MODE"] = "wild"
            os.environ["MODEL_ONLY"] = "1"
            os.environ["RAG_MIN_SCORE"] = "0.45"
            os.environ["STORY_QUALITY_REVIEW"] = "0"
            os.environ["STORY_QUALITY_MIN_AVG"] = "8.2"
            os.environ["STORY_QUALITY_MIN_DIM"] = "7.1"
            os.environ["STORY_OUTLINE_ALIGNMENT_STRICT"] = "0"
            os.environ["STORY_OUTLINE_ALIGNMENT_MAX_ATTEMPTS"] = "3"
            obj._load_quick_api_switch()
            self.assertEqual(obj.story_template_key.get(), "xianxia_fantasy")
            self.assertEqual(obj.story_template_select_var.get(), "仙侠玄幻")
            self.assertIn("仙侠玄幻", obj.story_template_desc_label.text)
            self.assertEqual(obj.story_template_strategy.get(), "shuffle")
            self.assertEqual(obj.story_creativity_mode.get(), "wild")
            self.assertEqual(obj.story_generation_mode.get(), "strict")
            self.assertEqual(obj.model_only.get(), True)
            self.assertEqual(obj.rag_min_score.get(), 0.45)
            self.assertEqual(obj.story_quality_review_enabled.get(), True)
            self.assertEqual(obj.story_quality_min_avg.get(), 7.8)
            self.assertEqual(obj.story_quality_min_dim.get(), 7.2)
            self.assertEqual(obj.story_outline_alignment_strict.get(), True)
            self.assertEqual(obj.story_outline_alignment_max_attempts.get(), 4)
            self.assertEqual(obj.story_global_overview_enabled.get(), True)
            self.assertEqual(obj.story_overview_before_generate.get(), True)
            self.assertEqual(obj.story_preview_before_apply.get(), True)
        finally:
            if old_story is None:
                os.environ.pop("STORY_OUTLINE_GEN_API", None)
            else:
                os.environ["STORY_OUTLINE_GEN_API"] = old_story
            if old_image is None:
                os.environ.pop("IMAGE_GEN_API", None)
            else:
                os.environ["IMAGE_GEN_API"] = old_image
            if old_generation_mode is None:
                os.environ.pop("STORY_GENERATION_MODE", None)
            else:
                os.environ["STORY_GENERATION_MODE"] = old_generation_mode
            if old_template is None:
                os.environ.pop("STORY_TEMPLATE_KEY", None)
            else:
                os.environ["STORY_TEMPLATE_KEY"] = old_template
            if old_template_strategy is None:
                os.environ.pop("STORY_TEMPLATE_STRATEGY", None)
            else:
                os.environ["STORY_TEMPLATE_STRATEGY"] = old_template_strategy
            if old_creativity is None:
                os.environ.pop("STORY_CREATIVITY_MODE", None)
            else:
                os.environ["STORY_CREATIVITY_MODE"] = old_creativity
            if old_model_only is None:
                os.environ.pop("MODEL_ONLY", None)
            else:
                os.environ["MODEL_ONLY"] = old_model_only
            if old_rag_min_score is None:
                os.environ.pop("RAG_MIN_SCORE", None)
            else:
                os.environ["RAG_MIN_SCORE"] = old_rag_min_score
            if old_quality_review is None:
                os.environ.pop("STORY_QUALITY_REVIEW", None)
            else:
                os.environ["STORY_QUALITY_REVIEW"] = old_quality_review
            if old_quality_min_avg is None:
                os.environ.pop("STORY_QUALITY_MIN_AVG", None)
            else:
                os.environ["STORY_QUALITY_MIN_AVG"] = old_quality_min_avg
            if old_quality_min_dim is None:
                os.environ.pop("STORY_QUALITY_MIN_DIM", None)
            else:
                os.environ["STORY_QUALITY_MIN_DIM"] = old_quality_min_dim
            if old_outline_align_strict is None:
                os.environ.pop("STORY_OUTLINE_ALIGNMENT_STRICT", None)
            else:
                os.environ["STORY_OUTLINE_ALIGNMENT_STRICT"] = old_outline_align_strict
            if old_outline_align_attempts is None:
                os.environ.pop("STORY_OUTLINE_ALIGNMENT_MAX_ATTEMPTS", None)
            else:
                os.environ["STORY_OUTLINE_ALIGNMENT_MAX_ATTEMPTS"] = old_outline_align_attempts

    @patch("src.gui.mixins.settings_mixin.messagebox.showinfo", return_value=None)
    def test_quick_switch_save_persists_model_only_flag(self, _mock_info):
        obj = self._build_settings_obj()
        obj.model_only.set(True)
        obj.rag_min_score.set(0.35)
        obj.story_template_strategy.set("rotate")
        obj.story_creativity_mode.set("wild")
        obj.story_quality_review_enabled.set(False)
        obj.story_quality_min_avg.set(8.1)
        obj.story_quality_min_dim.set(7.2)
        obj.story_outline_alignment_strict.set(True)
        obj.story_outline_alignment_max_attempts.set(3)
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            try:
                obj._save_quick_api_switch()
                values = dotenv_values(Path(td) / ".env")
                self.assertEqual(str(values.get("MODEL_ONLY")), "1")
                self.assertEqual(str(values.get("RAG_MIN_SCORE")), "0.35")
                self.assertEqual(str(values.get("STORY_TEMPLATE_STRATEGY")), "rotate")
                self.assertEqual(str(values.get("STORY_CREATIVITY_MODE")), "wild")
                self.assertEqual(str(values.get("STORY_QUALITY_REVIEW")), "0")
                self.assertEqual(str(values.get("STORY_QUALITY_MIN_AVG")), "8.1")
                self.assertEqual(str(values.get("STORY_QUALITY_MIN_DIM")), "7.2")
                self.assertEqual(str(values.get("STORY_OUTLINE_ALIGNMENT_STRICT")), "1")
                self.assertEqual(str(values.get("STORY_OUTLINE_ALIGNMENT_MAX_ATTEMPTS")), "3")
                self.assertEqual(str(values.get("STORY_GENERATION_MODE")), "custom")
            finally:
                os.chdir(old_cwd)

    def test_story_generation_mode_change_applies_fast_preset_and_persists(self):
        obj = self._build_settings_obj()
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            try:
                obj.story_generation_mode_select_var.set(obj.story_generation_mode_key_to_label["fast"])
                obj._on_story_generation_mode_changed()
                self.assertEqual(obj.story_generation_mode.get(), "fast")
                self.assertEqual(obj.story_quality_review_enabled.get(), False)
                self.assertEqual(obj.story_global_overview_enabled.get(), False)
                self.assertEqual(obj.story_overview_before_generate.get(), False)
                self.assertEqual(obj.story_preview_before_apply.get(), False)
                self.assertEqual(obj.story_outline_alignment_strict.get(), False)
                self.assertEqual(obj.story_outline_alignment_max_attempts.get(), 1)
                values = dotenv_values(Path(td) / ".env")
                self.assertEqual(str(values.get("STORY_GENERATION_MODE")), "fast")
            finally:
                os.chdir(old_cwd)

    def test_story_generation_mode_infers_custom_after_manual_toggle(self):
        obj = self._build_settings_obj()
        obj.story_generation_mode.set("balanced")
        obj.story_preview_before_apply.set(False)
        payload = obj._collect_story_env_payload()
        self.assertEqual(payload.get("STORY_GENERATION_MODE"), "custom")

    def test_prompt_builder_uses_selected_template_rules(self):
        obj = _DummyPromptBuilder()
        obj.target_chars = _Var(3000)
        obj.style = _Var("快节奏")
        obj.story_template_key = _Var("urban_power")
        outline_prompt = obj._build_outline_prompt("写一个逆袭故事", [], "都市")
        full_prompt = obj._build_prompt("写一个逆袭故事", [], "都市", "")
        section_prompt = obj._build_section_prompt(
            section={"title": "被羞辱后反击", "items": ["被上司打压", "拿出证据反击"]},
            section_index=0,
            total_sections=3,
            previous_content="",
            requirement="写一个逆袭故事",
            contexts=[],
            category="都市",
            style_part="快节奏",
            target_chars_per_section=1000,
            section_overview_plan=(
                "【承接点】从会议室沉默继续。\n"
                "【本章目标】当众证明证据被调包。\n"
                "【场景链】\n"
                "场景1：目标/开口质询；阻力/上司反咬；行动/展示编号；结果/众人动摇；新问题/谁提前换袋。"
            ),
        )
        self.assertIn("当前模版：都市逆袭爽文", outline_prompt)
        self.assertIn("**模版**：都市逆袭爽文", full_prompt)
        self.assertIn("【模版规则】", section_prompt)
        self.assertIn("都市逆袭爽文", section_prompt)
        self.assertIn("【本章剧情合同（硬约束）】", section_prompt)
        self.assertIn("因果推进", section_prompt)
        self.assertIn("【本章场景执行卡（必须逐项兑现）】", section_prompt)
        self.assertIn("正文必须按【场景链】的因果顺序推进", section_prompt)
        self.assertIn("不能写成静态说明", section_prompt)
        self.assertIn("【跨章衔接一致性】", section_prompt)
        self.assertIn("【创新引擎（blend）】", full_prompt)
        self.assertIn("跨模版融合", full_prompt)

    def test_prompt_builder_includes_global_overview_constraints(self):
        obj = _DummyPromptBuilder()
        obj.target_chars = _Var(3000)
        obj.style = _Var("写实")
        obj.story_template_key = _Var("zhihu_realistic")
        obj.story_global_overview_text = (
            "【一句话主线】\n主角在校园与家庭压力下完成自我和解。\n"
            "【章节推进总览】\n冲突递进，最终在毕业前达成和解。"
        )

        full_prompt = obj._build_prompt("写一个校园成长故事", [], "校园", "")
        section_prompt = obj._build_section_prompt(
            section={"title": "冲突起点", "items": ["课堂冲突", "家庭电话"]},
            section_index=0,
            total_sections=4,
            previous_content="",
            requirement="写一个校园成长故事",
            contexts=[],
            category="校园",
            style_part="写实",
            target_chars_per_section=900,
        )

        self.assertIn("【全书总览蓝图（强约束）】", full_prompt)
        self.assertIn("【全书总览蓝图（必须对齐）】", section_prompt)
        self.assertIn("主角在校园与家庭压力下完成自我和解", section_prompt)

    def test_prompt_builder_requirement_alignment_overrides_conflicting_category(self):
        obj = _DummyPromptBuilder()
        obj.target_chars = _Var(3000)
        obj.style = _Var("情感真实")
        obj.story_template_key = _Var("zhihu_realistic")

        requirement = "写一个校园混混的故事，要情感真实"
        outline_prompt = obj._build_outline_prompt(requirement, [], "职场")
        full_prompt = obj._build_prompt(requirement, [], "职场", "")
        banner = obj._build_story_run_banner(requirement, "职场", [])

        self.assertIn("需求对齐锚点", outline_prompt)
        self.assertIn("种类（最终）：校园", outline_prompt)
        self.assertIn("种类（界面）：职场", outline_prompt)
        self.assertIn("种类（最终）**：校园", full_prompt)
        self.assertIn("题材纠偏", banner)

    def test_prompt_builder_requirement_alignment_keeps_selected_when_signals_close(self):
        obj = _DummyPromptBuilder()
        obj.target_chars = _Var(3000)
        obj.style = _Var("写实")
        obj.story_template_key = _Var("zhihu_realistic")

        requirement = "写一个职场人误入校园社团的故事"
        outline_prompt = obj._build_outline_prompt(requirement, [], "职场")
        self.assertIn("种类（最终）：职场", outline_prompt)

    def test_outline_alignment_retry_only_for_critical_or_low_score(self):
        obj = _DummyPromptBuilder()
        obj.target_chars = _Var(3000)
        obj.style = _Var("写实")
        obj.story_template_key = _Var("zhihu_realistic")

        requirement = "校园 混混 情感"
        outline = "1. 校园午时已到\n2. 天台上的交易\n3. 胜利者的孤独"
        report = obj._evaluate_outline_alignment(requirement, "校园", outline)

        self.assertFalse(report["passed"])
        self.assertFalse(report["should_retry"])

    def test_outline_alignment_local_repair_injects_must_tokens(self):
        obj = _DummyPromptBuilder()
        obj.target_chars = _Var(3000)
        obj.style = _Var("写实")
        obj.story_template_key = _Var("zhihu_realistic")

        requirement = "校园 混混 情感"
        bad_outline = "1. 午时已到\n2. 天台上的交易\n3. 胜利者的孤独"
        bad_report = obj._evaluate_outline_alignment(requirement, "校园", bad_outline)
        repaired_outline = obj._repair_outline_for_alignment(requirement, "校园", bad_outline, bad_report)
        repaired_report = obj._evaluate_outline_alignment(requirement, "校园", repaired_outline)

        self.assertTrue(bad_report["should_retry"])
        self.assertNotEqual(repaired_outline, bad_outline)
        self.assertIn("校园", repaired_outline)
        self.assertGreaterEqual(float(repaired_report["score"]), float(bad_report["score"]))
        self.assertIn("校园", repaired_report["anchor_hits"])

    def test_outline_alignment_uses_must_tokens_for_short_hits(self):
        obj = _DummyPromptBuilder()
        obj.target_chars = _Var(3000)
        obj.style = _Var("写实")
        obj.story_template_key = _Var("zhihu_realistic")

        requirement = "写一个校园混混的故事，要情感真实"
        outline = "1. 校园午时已到\n2. 校园天台上的交易\n3. 胜利者的孤独"
        report = obj._evaluate_outline_alignment(requirement, "校园", outline)

        self.assertIn("校园", report["must_tokens"])
        self.assertIn("校园", report["must_hits"])
        self.assertGreaterEqual(float(report["score"]), 0.55)


if __name__ == "__main__":
    unittest.main()
