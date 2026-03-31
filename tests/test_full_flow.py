"""Full-flow style tests for core logic (no network, no GUI)."""

from __future__ import annotations

import sys
import types
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# --- lightweight stubs to avoid heavy model imports during tests ---
if "sentence_transformers" not in sys.modules:
    st_mod = types.ModuleType("sentence_transformers")

    class DummySentenceTransformer:
        def __init__(self, *args, **kwargs):
            pass

        def encode(self, *args, **kwargs):
            return []

    st_mod.SentenceTransformer = DummySentenceTransformer
    sys.modules["sentence_transformers"] = st_mod

if "faiss" not in sys.modules:
    faiss_mod = types.ModuleType("faiss")

    class DummyIndex:
        def __init__(self, *args, **kwargs):
            pass

        def add(self, *args, **kwargs):
            pass

        def search(self, *args, **kwargs):
            return [[0.0]], [[-1]]

    def _noop(*args, **kwargs):
        return DummyIndex()

    faiss_mod.IndexFlatIP = DummyIndex
    faiss_mod.read_index = _noop
    faiss_mod.write_index = _noop
    sys.modules["faiss"] = faiss_mod

# --- imports after stubs ---
from src.project_manager import ProjectManager
from src.gui.mixins.settings_mixin import SettingsMixin

from src.gui.mixins.story_modules.outline_generator import OutlineGeneratorMixin
from src.gui.mixins.story_modules.story_generator import StoryGeneratorMixin
from src.gui.mixins.story_modules.ui_builder import StoryUIBuilderMixin
from src.gui.mixins.image_modules.shot_manager import ShotManagerMixin
from src.utils import text as text_utils


class SimpleVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class DummyModelRouting(SettingsMixin):
    def __init__(self):
        self.api_providers = {
            "DeepSeek": {"key": "k1", "base_url": "https://api.deepseek.com/v1", "models": ["deepseek-chat"]},
            "OpenAI": {"key": "k2", "base_url": "https://api.openai.com/v1", "models": ["gpt-4o"]},
        }
        self.api_presets = {
            "DeepSeek": {"key": "k1", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
            "OpenAI": {"key": "k2", "base_url": "https://api.openai.com/v1", "model": "gpt-4o"},
        }
        self.model_routing = {
            "story_outline": {"provider": "OpenAI", "model": "gpt-4o"},
        }
        # prevent _ensure_model_routing_loaded from overwriting in-memory routes
        self._model_routing_loaded = True


class DummyOutline(OutlineGeneratorMixin):
    pass


class DummyStoryUI(StoryUIBuilderMixin):
    def __init__(self):
        self.target_chars = SimpleVar(1800)
        self.style = SimpleVar("写实")


class DummyShot(ShotManagerMixin):
    pass


class TestModelRouting(unittest.TestCase):
    def test_resolve_task_api(self):
        dummy = DummyModelRouting()
        cfg = dummy._resolve_task_api("story_outline")
        self.assertEqual(cfg["provider"], "OpenAI")
        self.assertEqual(cfg["model"], "gpt-4o")
        self.assertEqual(cfg["key"], "k2")

    def test_resolve_with_fallback(self):
        dummy = DummyModelRouting()
        cfg = dummy._resolve_task_api("unknown_task", fallback_provider="DeepSeek", fallback_model="deepseek-chat")
        self.assertEqual(cfg["provider"], "DeepSeek")
        self.assertEqual(cfg["model"], "deepseek-chat")


class TestOutlineParsing(unittest.TestCase):
    def test_parse_outline_sections(self):
        dummy = DummyOutline()
        outline = "1. 开端\n2. 发展\n三、高潮\n四、结局"
        sections = dummy._parse_outline_sections(outline)
        titles = [s["title"] for s in sections]
        self.assertEqual(titles, ["开端", "发展", "高潮", "结局"])


class TestPromptBuilding(unittest.TestCase):
    def test_build_prompt(self):
        dummy = DummyStoryUI()
        prompt = dummy._build_prompt("一个故事", [], "悬疑", "")
        self.assertIn("创作主题/需求", prompt)
        self.assertIn("一个故事", prompt)
        self.assertIn("种类", prompt)
        self.assertIn("悬疑", prompt)


class TestProjectManager(unittest.TestCase):
    def test_project_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm = ProjectManager(workspace=Path(tmp))
            proj = pm.create_project("测试项目")
            proj.save_story("内容", category="测试", requirement="需求", style="风格", target_chars=1000)
            loaded = pm.load_project(proj.project_dir)
            self.assertIn("内容", loaded.load_story())
            projects = pm.list_projects()
            self.assertTrue(any(p["name"] == "测试项目" for p in projects))


class TestShotParsing(unittest.TestCase):
    def test_parse_shot_response(self):
        dummy = DummyShot()
        resp = "1. 场景A | 人物动作\n- 场景B | 动作\n• 场景C | 动作"
        shots = dummy._parse_shot_response(resp)
        self.assertEqual(shots, ["场景A | 人物动作", "场景B | 动作", "场景C | 动作"])


class TestUtils(unittest.TestCase):
    def test_sanitize(self):
        self.assertEqual(text_utils.sanitize("Bearer sk-test"), "sk-test")

    def test_split_by_length(self):
        text = "一句话。" * 30
        chunks = text_utils.split_by_length(text, max_chars=50, overlap=0)
        self.assertTrue(len(chunks) >= 1)


class TestModelCache(unittest.TestCase):
    def test_model_cache(self):
        from src.kb import model_cache

        with patch("src.kb.model_cache.SentenceTransformer") as mock_st:
            mock_st.return_value = object()
            a = model_cache.get_sentence_transformer("fake-model")
            b = model_cache.get_sentence_transformer("fake-model")
            self.assertIs(a, b)


if __name__ == "__main__":
    unittest.main()
