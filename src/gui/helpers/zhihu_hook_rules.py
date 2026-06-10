"""Reusable hook-opening rules for Zhihu-style story prompts."""

from __future__ import annotations


def build_zhihu_hook_opening_rules(*, first_section: bool = True) -> str:
    """Return hard constraints for a high-retention opening."""
    scope = "整篇故事开头/第一章开头" if first_section else "本章开头"
    return (
        f"- {scope}第一句必须直接抛出强钩子，优先使用：反常事实、危险结果、关系爆雷、死亡通知、身份错位、倒计时、不可逆后果、监控/证据异常之一。\n"
        "- 前 150 字禁止写天气、环境铺陈、人物履历、世界观解释、普通日常、作者旁白式总结；必须先让读者看到异常、冲突或代价。\n"
        "- 第一段必须抛出一个具体问题：谁在撒谎、发生了什么不可能的事、主角马上会失去什么、某段关系为什么突然崩掉，至少命中其一。\n"
        "- 前 300 字必须完成“异常出现 -> 主角即时反应 -> 更大的疑问/代价浮出”的节奏，不要把悬念留到几百字之后。\n"
        "- 可以借鉴知乎故事的开场感：像亲历者突然说出一个无法忽视的事实，但不要写成空泛标题党或营销号口吻。\n"
        "- 开头句式参考方向：收到一条不该存在的消息；所有人都否认某个人来过；主角发现自己的身份/记忆/亲密关系有一个致命漏洞；一个倒计时已经开始且无法取消。\n"
        "- 如果开头三句话删掉后不影响理解，说明开头太慢，必须改成直接进入事件现场。"
    )


def build_zhihu_section_opening_rules(*, section_index: int) -> str:
    """Return opening rules tuned for first vs later generated sections."""
    if section_index <= 0:
        return build_zhihu_hook_opening_rules(first_section=True)
    return (
        "- 本章第一句必须承接上章最后一个动作/情绪/发现，并立即给出新的压力、反证、代价或关系变化。\n"
        "- 禁止用“第二天、后来、与此同时、他想起了”这类跳转式软开头，除非上章结尾已经明确需要时间跳跃。\n"
        "- 前 120 字必须同时做到：接住上章悬念、推进一个新动作、制造一个比上章更大的问题。\n"
        "- 不要重新解释前情；读者已经知道的内容只允许通过动作、对话或新证据顺手带出。"
    )
