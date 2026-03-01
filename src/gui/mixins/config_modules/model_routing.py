"""Model routing task definitions for settings UI."""

# (task_key, task_label)
MODEL_ROUTING_TASKS = [
    ("story_outline", "故事大纲生成"),
    ("story_generate", "故事正文生成"),
    ("character_extract", "人物提取"),
    ("character_description", "人物描述生成"),
    ("image_prompt_translate", "图片提示词翻译（前处理）"),
    ("image_prompt_enhance", "图片提示词优化（前处理）"),
    ("image_prompt_from_story", "从故事生成图片提示词（前处理）"),
    ("image_prompt_from_shots", "从分镜生成图片提示词（前处理）"),
    ("director_script_generate", "导演脚本包生成（前处理）"),
    ("image_shot_extract", "分镜提取（前处理）"),
    ("image_shot_to_desc", "分镜转图片描述（前处理）"),
]
