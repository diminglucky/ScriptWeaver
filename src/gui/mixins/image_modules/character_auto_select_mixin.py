"""Auto-select reference characters from shot text."""

from __future__ import annotations

import logging
import re
from tkinter import END

logger = logging.getLogger(__name__)


class ShotCharacterAutoSelectMixin:
    """Detect and select matching reference characters for current shot."""

    def _auto_select_characters_from_shot(self, shot_text: str, description: str = "") -> None:
        """智能识别分镜中的人物并自动选中（支持名字、别名、特征匹配）"""
        try:
            print(f"\n{'='*60}")
            print("🤖 开始智能识别人物")
            print(f"{'='*60}")

            if not hasattr(self, "ref_character_listbox"):
                return
            self.ref_character_listbox.selection_clear(0, END)

            available_characters = self._collect_available_reference_characters()
            if not available_characters:
                print("⚠️ 没有已生成照片的人物")
                return

            print(f"📋 可用人物数量：{len(available_characters)}")
            for char in available_characters:
                desc_preview = char["description"][:50] + "..." if len(char["description"]) > 50 else char["description"]
                print(f"   - {char['name']}: {desc_preview}")

            search_text = f"{shot_text} {description}"
            print(f"\n📝 搜索文本长度：{len(search_text)} 字")
            print(f"📝 搜索文本前300字：{search_text[:300]}...")

            mentioned_characters = self._detect_characters_from_text(available_characters, search_text)
            if not mentioned_characters:
                print("💡 未在分镜中识别到已生成照片的人物")
                print("   提示：可能是人物描述与分镜描述差异较大")
                print(f"{'='*60}\n")
                return

            selected_count = self._apply_detected_character_selection(mentioned_characters)
            char_names = "、".join(mentioned_characters)
            self._ui(self.status.set, f"✅ 已自动选择参考人物：{char_names}")
            print(f"🎭 智能识别并选中 {selected_count} 个人物：{char_names}")
            print(f"{'='*60}\n")
        except Exception as exc:
            print(f"⚠️ 自动选择参考人物时出错：{str(exc)}")
            import traceback

            traceback.print_exc()

    def _collect_available_reference_characters(self) -> list[dict[str, str]]:
        """Collect characters with available reference photos."""
        if not hasattr(self, "character_list") or not self.character_list:
            print("⚠️ 人物列表为空")
            return []

        try:
            from ...models.character import Character
        except Exception as exc:
            logger.debug("import Character model failed, fallback to dict mode: %s", exc)
            Character = None

        available_characters: list[dict[str, str]] = []
        for char in self.character_list:
            if Character and isinstance(char, Character):
                photo_path = char.primary_photo
                name = char.name
                description = char.description or ""
            else:
                photo_path = char.get("photo_path") if isinstance(char, dict) else ""
                name = char.get("name", "") if isinstance(char, dict) else ""
                description = char.get("description", "") if isinstance(char, dict) else ""

            if photo_path:
                available_characters.append({"name": name, "description": description})
        return available_characters

    def _detect_characters_from_text(
        self,
        available_characters: list[dict[str, str]],
        search_text: str,
    ) -> list[str]:
        """Detect mentioned characters by name + feature cues."""
        mentioned_characters: list[str] = []
        for char in available_characters:
            char_name = char["name"]
            char_desc = char["description"]
            matched_reasons = []

            if char_name and char_name in search_text:
                matched_reasons.append("名字匹配")

            identity_keywords = self._extract_identity_keywords(char_desc)
            for keyword in identity_keywords:
                if keyword in search_text:
                    matched_reasons.append(f"身份特征'{keyword}'匹配")
                    break

            age_match = re.search(r"(\d{1,2})\s*岁", char_desc)
            if age_match:
                age = age_match.group(1)
                if f"{age}岁" in search_text:
                    matched_reasons.append(f"年龄'{age}岁'匹配")

            appearance_keywords = self._extract_appearance_keywords(char_desc, search_text)
            if appearance_keywords:
                matched_reasons.append(f"外貌特征{appearance_keywords}匹配")

            clothing_keywords = self._extract_clothing_keywords(char_desc, search_text)
            if clothing_keywords:
                matched_reasons.append(f"服装特征{clothing_keywords}匹配")

            if matched_reasons:
                mentioned_characters.append(char_name)
                print(f"✅ 识别到人物【{char_name}】：{' | '.join(matched_reasons)}")
        return mentioned_characters

    @staticmethod
    def _extract_identity_keywords(char_desc: str) -> list[str]:
        """Extract identity/role keywords from character description."""
        keywords = [
            "主角",
            "我",
            "实习生",
            "护士",
            "医生",
            "老人",
            "阿姨",
            "大妈",
            "女孩",
            "男孩",
            "年轻人",
            "中年",
            "老年",
            "小孩",
            "孩子",
            "病人",
            "患者",
            "家属",
            "访客",
            "保安",
            "清洁工",
            "教师",
            "学生",
            "司机",
            "服务员",
            "经理",
            "老板",
        ]
        return [keyword for keyword in keywords if keyword in char_desc]

    @staticmethod
    def _extract_appearance_keywords(char_desc: str, search_text: str) -> list[str]:
        """Extract appearance cue matches."""
        keywords = [
            "短发",
            "长发",
            "齐肩",
            "卷发",
            "直发",
            "马尾",
            "辫子",
            "黑发",
            "白发",
            "金发",
            "棕发",
            "红发",
            "眼镜",
            "胡须",
            "瘦",
            "胖",
            "高",
            "矮",
        ]
        return [keyword for keyword in keywords if keyword in char_desc and keyword in search_text]

    @staticmethod
    def _extract_clothing_keywords(char_desc: str, search_text: str) -> list[str]:
        """Extract clothing cue matches."""
        keywords = ["白大褂", "护士服", "制服", "西装", "衬衫", "T恤", "裙子", "裤子"]
        return [keyword for keyword in keywords if keyword in char_desc and keyword in search_text]

    def _apply_detected_character_selection(self, mentioned_characters: list[str]) -> int:
        """Select detected characters in reference listbox."""
        selected_count = 0
        for idx in range(self.ref_character_listbox.size()):
            item_text = self.ref_character_listbox.get(idx)
            if item_text.startswith(("✅ ", "🧬 ")):
                char_name = item_text[2:].strip()
                if char_name in mentioned_characters:
                    self.ref_character_listbox.selection_set(idx)
                    selected_count += 1
                    print(f"🎯 在列表第{idx}行选中：{char_name}")
        return selected_count
