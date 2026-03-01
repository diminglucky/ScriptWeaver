from __future__ import annotations

import unittest

from src.gui.helpers.director_script_builder import DirectorScriptBuilder


class DirectorScriptBuilderTests(unittest.TestCase):
    def test_parse_llm_package_from_fenced_json(self):
        response = """```json
{
  "title": "测试故事",
  "logline": "一句话",
  "style_bible": {"genre": "剧情"},
  "characters": [{"name": "陆舟", "role": "主角", "appearance_anchor": "黑框眼镜"}],
  "shot_list": [
    {
      "shot_no": 1,
      "scene_no": 1,
      "shot_type": "MS",
      "camera_movement": "推进",
      "duration_sec": 6,
      "location": "办公室",
      "time": "白天",
      "characters": ["陆舟"],
      "action": "陆舟抬头",
      "sound": "空调声",
      "transition": "切",
      "veo_prompt": "镜头推进，人物抬头，压迫感"
    }
  ]
}
```"""
        parsed = DirectorScriptBuilder.parse_llm_package(response)
        self.assertEqual(parsed["title"], "测试故事")
        self.assertEqual(len(parsed["characters"]), 1)
        self.assertEqual(len(parsed["shot_list"]), 1)
        self.assertEqual(parsed["shot_list"][0]["duration_sec"], 6)
        self.assertEqual(parsed["shot_list"][0]["character_states"][0]["name"], "陆舟")
        self.assertEqual(parsed["shot_list"][0]["character_states"][0]["role"], "主角")

    def test_shot_to_app_line_has_expected_format(self):
        shot = {
            "location": "走廊",
            "time": "夜晚",
            "action": "主角快步离开",
            "shot_type": "CU",
            "camera_movement": "跟随",
            "duration_sec": 5,
            "transition": "切",
            "sound": "脚步声",
        }
        line = DirectorScriptBuilder.shot_to_app_line(shot)
        self.assertIn("走廊，夜晚", line)
        self.assertIn("主角快步离开", line)
        self.assertIn("CU", line)
        self.assertIn("5秒", line)

    def test_shot_to_app_line_includes_character_states(self):
        shot = {
            "location": "会议室",
            "time": "白天",
            "action": "双方对峙",
            "shot_type": "MS",
            "camera_movement": "固定",
            "duration_sec": 6,
            "transition": "切",
            "sound": "空调声",
            "character_states": [
                {"name": "陆舟", "role": "主角", "action": "盯住对方", "emotion": "压抑", "appearance": "黑框眼镜"},
                {"name": "小李", "role": "反派", "action": "挑衅微笑", "emotion": "轻蔑"},
            ],
        }
        line = DirectorScriptBuilder.shot_to_app_line(shot)
        self.assertIn("人物信息", line)
        self.assertIn("陆舟", line)
        self.assertIn("角色=主角", line)
        self.assertIn("镜头内容：双方对峙", line)

    def test_to_roles_text_returns_compact_lines(self):
        pkg = {
            "characters": [
                {"name": "陆舟", "role": "主角", "appearance_anchor": "黑框眼镜", "voice_tone": "克制"},
                {"name": "小李", "role": "反派"},
            ]
        }
        text = DirectorScriptBuilder.to_roles_text(pkg)
        self.assertIn("陆舟", text)
        self.assertIn("黑框眼镜", text)
        self.assertIn("小李", text)

    def test_extract_shot_characters_merges_states_and_characters(self):
        shot = {
            "characters": ["陆舟", "小李"],
            "character_states": [
                {"name": "陆舟", "action": "抬头"},
                {"name": "赵总", "action": "敲桌"},
            ],
        }
        names = DirectorScriptBuilder.extract_shot_characters(shot)
        self.assertEqual(names, ["陆舟", "赵总", "小李"])

    def test_build_quality_report_counts_problem_shots(self):
        pkg = {
            "characters": [{"name": "陆舟"}],
            "shot_list": [
                {
                    "shot_no": 1,
                    "duration_sec": 6,
                    "location": "会议室",
                    "time": "白天",
                    "action": "陆舟起身发言",
                    "characters": ["陆舟"],
                    "character_states": [{"name": "陆舟", "action": "起身发言"}],
                    "veo_prompt": "medium shot, slight push in, calm pacing",
                },
                {
                    "shot_no": 2,
                    "duration_sec": 0,
                    "location": "",
                    "time": "",
                    "action": "",
                    "characters": [],
                    "character_states": [],
                    "veo_prompt": "",
                },
            ],
        }
        report = DirectorScriptBuilder.build_quality_report(pkg)
        self.assertEqual(report["total_shots"], 2)
        self.assertEqual(report["problem_shots"], 1)
        self.assertEqual(report["completeness_percent"], 50)
        self.assertIn("缺少场景（地点/时间）", report["issue_counter"])
        self.assertIn("缺少Veo提示词", report["issue_counter"])

    def test_format_shot_detail_contains_quality_hints(self):
        shot = {
            "shot_no": 3,
            "duration_sec": 0,
            "location": "",
            "time": "",
            "action": "",
            "characters": [],
            "character_states": [],
            "veo_prompt": "",
        }
        detail = DirectorScriptBuilder.format_shot_detail(shot)
        self.assertIn("质检提示", detail)
        self.assertIn("缺少镜头内容动作", detail)
        self.assertIn("Veo 提示词", detail)


if __name__ == "__main__":
    unittest.main()
