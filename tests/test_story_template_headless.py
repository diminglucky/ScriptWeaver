import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values

from src.gui.helpers.story_creativity import list_story_creativity_modes
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
        obj.settings_log = _Log()
        obj.model_only = _Var(False)
        obj.rag_min_score = _Var(0.12)
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
        old_template = os.environ.get("STORY_TEMPLATE_KEY")
        old_template_strategy = os.environ.get("STORY_TEMPLATE_STRATEGY")
        old_creativity = os.environ.get("STORY_CREATIVITY_MODE")
        old_model_only = os.environ.get("MODEL_ONLY")
        old_rag_min_score = os.environ.get("RAG_MIN_SCORE")
        try:
            os.environ["STORY_OUTLINE_GEN_API"] = "DeepSeek"
            os.environ["IMAGE_GEN_API"] = "OpenAI (DALL-E)"
            os.environ["STORY_TEMPLATE_KEY"] = "xianxia_fantasy"
            os.environ["STORY_TEMPLATE_STRATEGY"] = "shuffle"
            os.environ["STORY_CREATIVITY_MODE"] = "wild"
            os.environ["MODEL_ONLY"] = "1"
            os.environ["RAG_MIN_SCORE"] = "0.45"
            obj._load_quick_api_switch()
            self.assertEqual(obj.story_template_key.get(), "xianxia_fantasy")
            self.assertEqual(obj.story_template_select_var.get(), "仙侠玄幻")
            self.assertIn("仙侠玄幻", obj.story_template_desc_label.text)
            self.assertEqual(obj.story_template_strategy.get(), "shuffle")
            self.assertEqual(obj.story_creativity_mode.get(), "wild")
            self.assertEqual(obj.model_only.get(), True)
            self.assertEqual(obj.rag_min_score.get(), 0.45)
        finally:
            if old_story is None:
                os.environ.pop("STORY_OUTLINE_GEN_API", None)
            else:
                os.environ["STORY_OUTLINE_GEN_API"] = old_story
            if old_image is None:
                os.environ.pop("IMAGE_GEN_API", None)
            else:
                os.environ["IMAGE_GEN_API"] = old_image
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

    @patch("src.gui.mixins.settings_mixin.messagebox.showinfo", return_value=None)
    def test_quick_switch_save_persists_model_only_flag(self, _mock_info):
        obj = self._build_settings_obj()
        obj.model_only.set(True)
        obj.rag_min_score.set(0.35)
        obj.story_template_strategy.set("rotate")
        obj.story_creativity_mode.set("wild")
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
            finally:
                os.chdir(old_cwd)

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
        )
        self.assertIn("当前模版：都市逆袭爽文", outline_prompt)
        self.assertIn("**模版**：都市逆袭爽文", full_prompt)
        self.assertIn("【模版规则】", section_prompt)
        self.assertIn("都市逆袭爽文", section_prompt)
        self.assertIn("【创新引擎（blend）】", full_prompt)
        self.assertIn("跨模版融合", full_prompt)


if __name__ == "__main__":
    unittest.main()
