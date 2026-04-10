"""UI-less smoke test for end-to-end flows with mocked clients."""

from __future__ import annotations

import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

# Avoid initializing Tk during import (headless environments)
if "tkinter" not in sys.modules:
    tk_mod = types.ModuleType("tkinter")

    # constants
    for name in [
        "BOTH", "LEFT", "RIGHT", "DISABLED", "NORMAL", "END",
        "VERTICAL", "Y", "SUNKEN", "FLAT", "WORD"
    ]:
        setattr(tk_mod, name, name)

    class DummyWidget:
        def __init__(self, *args, **kwargs):
            pass

        def pack(self, *args, **kwargs):
            pass

        def grid(self, *args, **kwargs):
            pass

        def place(self, *args, **kwargs):
            pass

        def config(self, *args, **kwargs):
            pass

        def configure(self, *args, **kwargs):
            pass

        def insert(self, *args, **kwargs):
            pass

        def delete(self, *args, **kwargs):
            pass

        def see(self, *args, **kwargs):
            pass

        def bind(self, *args, **kwargs):
            pass

        def set(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            return ""

        def selection_set(self, *args, **kwargs):
            pass

        def selection_clear(self, *args, **kwargs):
            pass

        def curselection(self, *args, **kwargs):
            return ()

        def event_generate(self, *args, **kwargs):
            pass

        def update(self, *args, **kwargs):
            pass

        def update_idletasks(self, *args, **kwargs):
            pass

        def after(self, *args, **kwargs):
            if len(args) >= 2 and callable(args[1]):
                args[1]()

    tk_mod.Tk = DummyWidget
    tk_mod.Toplevel = DummyWidget
    tk_mod.Frame = DummyWidget
    tk_mod.Label = DummyWidget
    tk_mod.Button = DummyWidget
    tk_mod.Text = DummyWidget
    tk_mod.Scrollbar = DummyWidget
    tk_mod.Menu = DummyWidget
    tk_mod.Canvas = DummyWidget
    tk_mod.Listbox = DummyWidget
    tk_mod.Entry = DummyWidget

    class _Var:
        def __init__(self, value=None):
            self._v = value

        def get(self):
            return self._v

        def set(self, v):
            self._v = v

    tk_mod.StringVar = _Var
    tk_mod.IntVar = _Var
    tk_mod.DoubleVar = _Var
    tk_mod.BooleanVar = _Var

    # submodules: ttk, scrolledtext, messagebox, filedialog
    ttk_mod = types.ModuleType("tkinter.ttk")
    ttk_mod.Notebook = DummyWidget
    ttk_mod.Combobox = DummyWidget
    ttk_mod.Label = DummyWidget
    ttk_mod.Progressbar = DummyWidget

    class DummyStyle:
        def configure(self, *args, **kwargs):
            pass

        def map(self, *args, **kwargs):
            pass

    ttk_mod.Style = DummyStyle
    tk_mod.ttk = ttk_mod

    scrolled_mod = types.ModuleType("tkinter.scrolledtext")
    scrolled_mod.ScrolledText = DummyWidget
    tk_mod.scrolledtext = scrolled_mod

    messagebox_mod = types.ModuleType("tkinter.messagebox")
    messagebox_mod.showwarning = lambda *a, **k: None
    messagebox_mod.showerror = lambda *a, **k: None
    messagebox_mod.showinfo = lambda *a, **k: None
    messagebox_mod.askyesno = lambda *a, **k: True
    tk_mod.messagebox = messagebox_mod

    filedialog_mod = types.ModuleType("tkinter.filedialog")
    filedialog_mod.askopenfilename = lambda *a, **k: ""
    filedialog_mod.asksaveasfilename = lambda *a, **k: ""
    filedialog_mod.askdirectory = lambda *a, **k: ""
    tk_mod.filedialog = filedialog_mod

    sys.modules["tkinter"] = tk_mod
    sys.modules["tkinter.ttk"] = ttk_mod
    sys.modules["tkinter.scrolledtext"] = scrolled_mod
    sys.modules["tkinter.messagebox"] = messagebox_mod
    sys.modules["tkinter.filedialog"] = filedialog_mod

if "PIL.ImageTk" not in sys.modules:
    sys.modules["PIL.ImageTk"] = types.ModuleType("PIL.ImageTk")

# lightweight stubs to avoid heavy model imports
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

from PIL import Image

from src.gui.mixins.ui_mixin import UiMixin
from src.gui.mixins.settings_mixin import SettingsMixin
from src.gui.mixins.story_modules.outline_generator import OutlineGeneratorMixin
from src.gui.mixins.story_modules.story_generator import StoryGeneratorMixin
from src.gui.mixins.image_modules.prompt_ops import PromptOperationsMixin
from src.gui.mixins.image_modules.shot_manager import ShotManagerMixin
from src.gui.mixins.image_modules.image_generator import ImageGeneratorMixin
from src.gui.mixins.image_modules.file_ops import FileOperationsMixin
from src.gui.mixins.image_modules.char_extract import CharacterExtractMixin
from src.gui.mixins.image_modules.char_description import CharacterDescriptionMixin
from src.gui.mixins.image_modules.char_utils import CharacterUtilsMixin
from src.gui.mixins.image_modules.video_ops import VideoPromptMixin
from src.gui.models.character import Character


class SimpleVar:
    def __init__(self, value=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class DummyText:
    def __init__(self, value=""):
        self.value = value
        self.state = "normal"

    def get(self, *_args, **_kwargs):
        return self.value

    def insert(self, _index, text):
        self.value += text

    def delete(self, *_args, **_kwargs):
        self.value = ""

    def see(self, *_args, **_kwargs):
        pass

    def config(self, **kwargs):
        if "state" in kwargs:
            self.state = kwargs["state"]


class DummyEntry:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class DummyListbox:
    def __init__(self):
        self.items = []
        self._selection = ()

    def delete(self, *_args, **_kwargs):
        self.items = []
        self._selection = ()

    def insert(self, _index, text):
        self.items.append(text)

    def get(self, index):
        return self.items[index]

    def selection_set(self, index):
        self._selection = (index,)

    def selection_clear(self, *_args, **_kwargs):
        self._selection = ()

    def curselection(self):
        return self._selection

    def activate(self, *_args, **_kwargs):
        pass

    def event_generate(self, *_args, **_kwargs):
        pass

    def config(self, **_kwargs):
        pass


class DummyButton:
    def configure(self, **_kwargs):
        pass

    def config(self, **_kwargs):
        pass


class DummyCombobox:
    def __init__(self):
        self.values = []
        self._current = -1

    def __setitem__(self, key, value):
        if key == "values":
            self.values = list(value)

    def current(self, index=None):
        if index is None:
            return self._current
        self._current = index


class ImmediateThread:
    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}
        self.daemon = daemon

    def start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)


class DummyDeepSeekClient:
    def __init__(self, *args, **kwargs):
        pass

    def chat(self, messages, **_kwargs):
        text = " ".join(m.get("content", "") for m in messages if isinstance(m, dict))
        if "分镜" in text:
            return "1. 雨夜街道 | 人物匆忙\n2. 路灯下特写 | 神情紧张"
        if "目录" in text or "章节" in text:
            return "1. 开端\n2. 发展\n3. 高潮\n4. 结局"
        if "英文" in text or "翻译" in text:
            return "a cinematic rainy street, dramatic lighting"
        return "好的"

    def stream(self, messages, **_kwargs):
        text = " ".join(m.get("content", "") for m in messages if isinstance(m, dict))
        if "目录" in text or "章节" in text:
            for token in ["1. 开端\n", "2. 发展\n", "3. 高潮\n", "4. 结局"]:
                yield token
            return
        for token in ["故事", "内容", "生成"]:
            yield token


class DummyImageClient:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, prompt, size="512x512", n=1):
        img = Image.new("RGB", (64, 64), color=(200, 200, 200))
        return [SimpleNamespace(image=img, seed=None, provider="openai", model="dummy")]

    def generate_with_reference(self, prompt, reference_image_path, size="512x512"):
        return self.generate(prompt, size=size, n=1)


class DummyAIService:
    def extract_characters(self, story_text):
        return [
            {
                "name": "李雷",
                "role": "主角",
                "gender": "男",
                "age_hint": "青年",
                "identity": "工程师",
                "personality": ["冷静"],
                "atmosphere": "沉稳",
                "story_role": "主线",
                "appearance_hints": "短发",
            }
        ]

    def design_character_appearance(self, character_name, profile, story_text):
        return {
            "description": f"{character_name} 外貌描述",
            "visual_features": {
                "face_shape": "椭圆形",
                "eye_features": "深邃",
                "nose_features": "挺直",
                "skin_tone": "自然",
                "body_type": "匀称",
                "hair_style": "短发",
                "hair_color": "黑色",
                "default_outfit": "黑色外套",
                "unique_marks": ["左眉痣"],
                "do_not_change": ["左眉痣"],
            },
            "dna_prompt": f"{character_name} DNA 核心描述",
        }


class FlowApp(
    UiMixin,
    SettingsMixin,
    OutlineGeneratorMixin,
    StoryGeneratorMixin,
    PromptOperationsMixin,
    ShotManagerMixin,
    ImageGeneratorMixin,
    FileOperationsMixin,
    CharacterExtractMixin,
    CharacterDescriptionMixin,
    CharacterUtilsMixin,
    VideoPromptMixin,
):
    def __init__(self):
        # basic vars
        self.status = SimpleVar("就绪")
        self.model_only = SimpleVar(True)
        self.temperature = SimpleVar(0.7)
        self.top_k = SimpleVar(6)
        self.target_chars = SimpleVar(1200)
        self.category = SimpleVar("悬疑")
        self.style = SimpleVar("紧张")
        self.current_outline = None
        self.parsed_sections = []
        self.generated_content = ""

        self.story_model_var = SimpleVar("dummy-model")
        self.char_model_var = SimpleVar("dummy-model")
        self.model = SimpleVar("dummy-model")
        self.api_preset = SimpleVar("Dummy")
        self.quick_story_api = SimpleVar("Dummy")
        self.outline_gen_api = SimpleVar("Dummy")
        self.story_gen_api = SimpleVar("Dummy")

        self.api_presets = {
            "Dummy": {"key": "k", "base_url": "https://api.example.com/v1", "model": "dummy-model"}
        }
        self.api_providers = {
            "Dummy": {"key": "k", "base_url": "https://api.example.com/v1", "models": ["dummy-model"]}
        }
        self.model_routing = {}
        self._model_routing_loaded = True

        # story UI
        self.prompt_text = DummyText("写一个故事")
        self.output = DummyText("")
        self.section_selector = DummyCombobox()
        self.btn_generate_section = DummyButton()
        self.btn_continue_next = DummyButton()
        self.btn_auto_generate = DummyButton()

        # image UI
        self.img_txt_prompt_cn = DummyText("一个雨夜街道的场景")
        self.img_txt_prompt = DummyText("")
        self.img_txt_roles = DummyText("")
        self.img_entry_scene = DummyEntry("")
        self.img_type = SimpleVar("写实照片")
        self.img_size = SimpleVar("512x512")
        self.img_api_preset = SimpleVar("Default")
        self.img_api_presets = {"Default": {"provider": "openai"}}
        self.img_api_type = SimpleVar("openai")
        self.img_api_key = SimpleVar("key")
        self.img_base_url = SimpleVar("https://api.example.com/v1")
        self.img_model = SimpleVar("gpt-image-1")
        self.img_ref_path = SimpleVar("")
        self.img_last_image = None

        # lists
        self.shots_listbox = DummyListbox()
        self.ref_character_listbox = DummyListbox()
        self.char_listbox = DummyListbox()
        self.character_list = []

        # character UI
        self.char_txt_desc = DummyText("")
        self.char_btn_extract = DummyButton()
        self.char_btn_refresh = DummyButton()
        self.char_btn_gen_desc = DummyButton()
        self.char_btn_copy_desc = DummyButton()
        self.char_btn_gen_photo = DummyButton()
        self.char_btn_turnaround = DummyButton()
        self.char_btn_view_gallery = DummyButton()
        self.char_btn_generate_sheet = DummyButton()

        # image buttons
        self.img_btn_gen = DummyButton()
        self.img_btn_save = DummyButton()
        self.btn_enhance_prompt = DummyButton()

        # project
        self.current_project = None

    def after(self, _ms, func):
        func()

    def update_idletasks(self):
        pass

    def _ui(self, func, *args, **kwargs):
        """In tests, execute UI calls immediately (no thread deferral)."""
        return func(*args, **kwargs)

    def _ui_get(self, func, *args, **kwargs):
        """In tests, execute getter calls immediately."""
        return func(*args, **kwargs)

    def set_busy(self, busy: bool):
        self._is_busy = busy

    def update_header_status(self, *_args, **_kwargs):
        pass

    def _get_prompt_content(self):
        return self.prompt_text.get("1.0", "end-1c").strip()

    def _update_img_preview(self):
        # skip real canvas rendering in tests
        pass

    def _estimate_chars(self, outline: str) -> int:
        return max(0, len(outline))

    def _build_prompt(self, requirement, contexts, category, outline=""):
        return f"{requirement}\n{category}\n{outline}"

    def _build_outline_prompt(self, requirement, contexts, category):
        return f"{requirement}\n{category}"


class TestFullFlowSmoke(unittest.TestCase):
    def test_full_flow_smoke(self):
        app = FlowApp()

        with patch("threading.Thread", ImmediateThread), \
             patch("tkinter.messagebox.showwarning", lambda *a, **k: None), \
             patch("tkinter.messagebox.showerror", lambda *a, **k: None), \
             patch("tkinter.messagebox.showinfo", lambda *a, **k: None), \
             patch("tkinter.messagebox.askyesno", lambda *a, **k: True):

            with patch("src.gui.mixins.story_modules.outline_generator.DeepSeekClient", DummyDeepSeekClient):
                app.on_generate_outline()
            self.assertGreater(len(app.parsed_sections), 0)

            with patch("src.gui.mixins.story_modules.story_generator.DeepSeekClient", DummyDeepSeekClient):
                app.on_generate()
            self.assertIn("故事", app.output.value)

            with patch("src.gui.mixins.image_modules.char_extract.create_ai_service", lambda *a, **k: DummyAIService()):
                app._on_extract_characters()
            self.assertTrue(app.character_list)

            # select first character and generate description
            app.char_listbox.selection_set(0)
            with patch("src.gui.mixins.image_modules.char_description.create_ai_service", lambda *a, **k: DummyAIService()):
                app._on_generate_character_description()
            self.assertTrue(app.char_txt_desc.value)

            with patch("src.gui.mixins.image_modules.shot_manager.DeepSeekClient", DummyDeepSeekClient):
                app._on_img_extract_shots(mode="brief")
            self.assertTrue(app.parsed_shots)

            with patch("src.gui.mixins.image_modules.prompt_ops.DeepSeekClient", DummyDeepSeekClient):
                app._on_img_build_prompt()
            self.assertTrue(app.img_txt_prompt.value)

            with patch("src.gui.mixins.image_modules.image_generator.DeepSeekClient", DummyDeepSeekClient), \
                 patch("src.gui.mixins.image_modules.image_generator.OpenAIImageClient", DummyImageClient):
                app._on_img_generate()
            self.assertIsNotNone(app.img_last_image)


if __name__ == "__main__":
    unittest.main()
