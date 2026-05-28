import unittest

from src.gui.helpers.story_quality import (
    extract_first_sentence,
    extract_last_sentence,
    format_memory_context,
    is_redundant_transition_head,
    normalize_memory_entry,
    normalize_sentence_signature,
    parse_memory_entry,
    parse_quality_review,
    should_polish,
    strip_duplicate_lines,
)


class StoryQualityTests(unittest.TestCase):
    def test_parse_quality_review(self):
        raw = (
            '{"scores":{"realism":7.8,"detail":6.4,"coherence":8.1,"naturalness":7.0},'
            '"strengths":["冲突明确"],"issues":["细节偏少"],"key_fix":"补动作细节"}'
        )
        review = parse_quality_review(raw)
        self.assertAlmostEqual(review["scores"]["realism"], 7.8)
        self.assertIn("escalation", review["scores"])
        self.assertIn("hook_density", review["scores"])
        self.assertEqual(review["issues"][0], "细节偏少")
        self.assertTrue(review["avg_score"] > 0)

    def test_should_polish(self):
        review_ok = parse_quality_review(
            '{"scores":{"realism":8.0,"detail":7.2,"coherence":8.1,"naturalness":7.8},"issues":[]}'
        )
        review_bad = parse_quality_review(
            '{"scores":{"realism":7.0,"detail":6.2,"coherence":7.8,"naturalness":7.1},"issues":["细节不足"]}'
        )
        review_flat = parse_quality_review(
            '{"scores":{"realism":8.0,"detail":8.0,"coherence":8.0,"continuity":8.0,'
            '"escalation":5.9,"hook_density":8.0,"naturalness":8.0},"issues":["高潮不足"]}'
        )
        self.assertFalse(should_polish(review_ok, min_avg_score=7.0, min_dimension_score=6.8))
        self.assertTrue(should_polish(review_bad, min_avg_score=7.2, min_dimension_score=6.8))
        self.assertTrue(should_polish(review_flat, min_avg_score=7.0, min_dimension_score=6.8))

    def test_memory_entry_and_format_context(self):
        parsed = parse_memory_entry(
            '{"summary":"主角暴露身份后反制成功","plot_points":["被围攻","反制"],'
            '"relation_changes":["与上司决裂"],"unresolved_hooks":["幕后黑手是谁"],"state_shift":"被动转主动"}'
        )
        entry = normalize_memory_entry(parsed, chapter_index=1, chapter_title="身份暴露")
        text = format_memory_context([entry], max_entries=2)
        self.assertIn("第2章", text)
        self.assertIn("未回收伏笔", text)

    def test_strip_duplicate_lines(self):
        text = "第一句。\n第二句。\n第二句。\n\n第三句。"
        cleaned = strip_duplicate_lines(text)
        self.assertEqual(cleaned.count("第二句。"), 1)

    def test_transition_sentence_extract_and_redundancy(self):
        prev = "他抬手关了灯，走出厕所，冷风一下子扑到脸上。"
        curr = "走出厕所，冷风一下子扑到脸上。他抬眼看见走廊尽头有人影。"
        tail = extract_last_sentence(prev)
        head = extract_first_sentence(curr)
        self.assertTrue(tail)
        self.assertTrue(head)
        self.assertTrue(is_redundant_transition_head(tail, head))

    def test_normalize_sentence_signature(self):
        a = "“走出厕所，冷风一下子扑到脸上。”"
        b = "走出厕所 冷风一下子扑到脸上"
        self.assertEqual(normalize_sentence_signature(a), normalize_sentence_signature(b))


if __name__ == "__main__":
    unittest.main()
