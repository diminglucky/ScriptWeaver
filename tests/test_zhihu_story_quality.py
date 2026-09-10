from __future__ import annotations

import unittest

from src.gui.helpers.zhihu_story_quality import (
    inspect_zhihu_story_shape,
    merge_local_quality_report,
)


class ZhihuStoryQualityTests(unittest.TestCase):
    def test_evidence_led_story_passes_shape_gate(self):
        text = (
            "凌晨两点十七分，我的手机收到一条来自自家门锁的开门记录。\n\n"
            "我翻出门锁 App，核对了时间和设备编号，又调出楼道监控。\n\n"
            "监控里的人穿着我的外套。我决定报警，把录像和记录交给警察。\n\n"
            "警察走后，我再次打开门锁，屏幕上仍显示两点十七分。"
        )
        report = inspect_zhihu_story_shape(text, require_opening=True, require_ending=True)

        self.assertTrue(report["passed"])
        self.assertEqual(report["issues"], [])

    def test_atmosphere_only_story_is_flagged(self):
        text = "\n\n".join(["我感到恐怖和不安，空气里满是诡异的气息。"] * 5)
        report = inspect_zhihu_story_shape(text, require_opening=True)

        self.assertFalse(report["passed"])
        self.assertTrue(any("证据" in issue for issue in report["issues"]))
        self.assertTrue(any("验证" in issue for issue in report["issues"]))
        self.assertIn("detail", report["deductions"])

    def test_merge_local_report_preserves_model_feedback_and_lowers_scores(self):
        review = {
            "scores": {"detail": 8.0, "coherence": 8.0},
            "avg_score": 8.0,
            "issues": ["模型指出节奏偏慢"],
            "key_fix": "",
        }
        local = {
            "passed": False,
            "gate_failures": ["opening_evidence"],
            "deductions": {"detail": 1.2, "coherence": 0.8},
            "issues": ["开头缺少可验证的生活证据或具体时间点"],
        }

        merged = merge_local_quality_report(review, local)

        self.assertEqual(merged["scores"]["detail"], 6.8)
        self.assertEqual(merged["scores"]["coherence"], 7.2)
        self.assertEqual(len(merged["issues"]), 2)
        self.assertEqual(merged["key_fix"], "开头缺少可验证的生活证据或具体时间点"[:20])
        self.assertFalse(merged["quality_gate_passed"])

    def test_local_signal_does_not_override_ai_score(self):
        merged = merge_local_quality_report(
            {"scores": {"detail": 9.8, "hook_density": 9.8}, "issues": []},
            {
                "passed": False,
                "gate_failures": ["opening_evidence"],
                "deductions": {},
                "issues": ["开头缺少可验证的生活证据或具体时间点"],
            },
        )

        self.assertEqual(merged["scores"]["detail"], 9.8)
        self.assertEqual(merged["scores"]["hook_density"], 9.8)
        self.assertFalse(merged["quality_gate_passed"])


if __name__ == "__main__":
    unittest.main()
