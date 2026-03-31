import sys
import types
import unittest

# --- lightweight stubs to avoid heavy model imports during test discovery ---
if "sentence_transformers" not in sys.modules:
    _st_mod = types.ModuleType("sentence_transformers")

    class _DummySentenceTransformer:
        def __init__(self, *a, **kw):
            pass
        def encode(self, *a, **kw):
            return []

    _st_mod.SentenceTransformer = _DummySentenceTransformer
    sys.modules["sentence_transformers"] = _st_mod

if "faiss" not in sys.modules:
    _faiss_mod = types.ModuleType("faiss")

    class _DummyIndex:
        def __init__(self, *a, **kw):
            pass
        def add(self, *a, **kw):
            pass
        def search(self, *a, **kw):
            return [[0.0]], [[-1]]

    def _noop(*a, **kw):
        return _DummyIndex()

    _faiss_mod.IndexFlatIP = _DummyIndex
    _faiss_mod.read_index = _noop
    _faiss_mod.write_index = _noop
    sys.modules["faiss"] = _faiss_mod

from src.gui.modern_app import ModernApp
from src.gui.mixins.story_modules.ui_builder import StoryUIBuilderMixin


class _DummyStoryPreset(StoryUIBuilderMixin):
    pass


class ProviderNameNormalizationTests(unittest.TestCase):
    def test_story_provider_map_normalization(self):
        data = {
            "鏅鸿氨AI (GLM)": {"base_url": "https://open.bigmodel.cn/api/paas/v4", "models": ["glm-4"], "key": ""},
            "闃块噷閫氫箟 (Qwen)": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "models": ["qwen-max"], "key": ""},
            "鑷畾涔?": {"base_url": "", "models": ["custom-model"], "key": ""},
        }
        normalized = ModernApp._normalize_story_provider_map(data)
        self.assertIn("Zhipu AI (GLM)", normalized)
        self.assertIn("Alibaba Qwen", normalized)
        self.assertIn("Custom", normalized)

    def test_story_provider_custom_alias_by_name(self):
        data = {
            "自定义": {"base_url": "", "models": ["my-model"], "key": ""},
        }
        normalized = ModernApp._normalize_story_provider_map(data)
        self.assertIn("Custom", normalized)

    def test_image_provider_map_normalization(self):
        data = {
            "鑵捐娣峰厓": {"base_url": "", "models": ["hunyuan"], "key": "", "provider": "hunyuan"},
            "纭呭熀娴佸姩 (鍥剧墖)": {"base_url": "https://api.siliconflow.cn/v1", "models": ["flux"], "key": "", "provider": "openai"},
        }
        normalized = ModernApp._normalize_image_provider_map(data)
        self.assertIn("Tencent Hunyuan", normalized)
        self.assertIn("SiliconFlow (Image)", normalized)

    def test_image_provider_custom_alias_by_name(self):
        data = {
            "自定义": {"base_url": "", "models": ["img-model"], "key": "", "provider": "openai"},
        }
        normalized = ModernApp._normalize_image_provider_map(data)
        self.assertIn("Custom", normalized)

    def test_story_ui_alias_normalization(self):
        obj = _DummyStoryPreset()
        obj.api_presets = {
            "Moonshot (鏈堜箣鏆楅潰)": {"base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k", "key": ""},
            "MyCustom": {"base_url": "https://my.proxy/v1", "model": "x", "key": "k"},
        }
        obj._normalize_story_preset_names()
        self.assertIn("Moonshot (Kimi)", obj.api_presets)
        self.assertIn("MyCustom", obj.api_presets)


if __name__ == "__main__":
    unittest.main()
