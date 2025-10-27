"""
故事内容提取工具 - 提取纯净的故事正文
"""

import re
from typing import Optional


class StoryExtractor:
    """故事内容提取器"""
    
    @staticmethod
    def extract_pure_story(full_text: str) -> str:
        """
        提取纯净的故事正文，去除目录、章节标题等结构信息
        
        Args:
            full_text: 完整的故事文本
            
        Returns:
            纯净的故事正文
        """
        if not full_text or not full_text.strip():
            return ""
        
        lines = full_text.split('\n')
        story_lines = []
        
        # 跳过目录部分
        skip_toc = False
        in_story = False
        
        for line in lines:
            stripped = line.strip()
            
            # 跳过空行（保留故事中的空行）
            if not stripped:
                if in_story:
                    story_lines.append(line)
                continue
            
            # 识别并跳过目录
            if re.match(r'^目录[：:]*\s*$', stripped, re.IGNORECASE):
                skip_toc = True
                continue
            
            # 识别目录项（数字序号开头的简短文本）
            if skip_toc:
                # 匹配类似 "1. 校园霸凌日常" 的目录项
                if re.match(r'^\d+[\.、]\s*.{1,30}$', stripped):
                    continue
                # 匹配类似 "第一章 xxx" 的目录项
                if re.match(r'^第[一二三四五六七八九十\d]+[章节篇]\s*.{1,30}$', stripped):
                    continue
                # 匹配 "（共X章，预估字数≈XXXX字）" 格式
                if re.match(r'^[（\(].*共.*[章节篇].*字.*[）\)]$', stripped):
                    continue
                # 如果遇到分隔线，目录结束
                if re.match(r'^[=\-_]{3,}$', stripped):
                    skip_toc = False
                    continue
                # 如果遇到较长的正文段落，说明目录结束
                if len(stripped) > 50 and not re.match(r'^\d+[\.、]', stripped):
                    skip_toc = False
                    in_story = True
            
            # 跳过章节标题（如：【第 1/4 章. 1. 校园霸凌日常】）
            if re.match(r'^【第\s*\d+/\d+\s*章.*】$', stripped):
                continue
            
            # 跳过 "生成目录中..." 这类提示
            if re.match(r'^生成.*中[\.。…]*$', stripped):
                continue
            
            # 跳过 "准备生成下一章..." 这类提示
            if re.match(r'^[📄📝✍️]*\s*准备.*[\.。…]*$', stripped):
                continue
            
            # 跳过 "第 3 章完成！本章字数：1455 字" 这类信息（包括有无空格的情况）
            if re.match(r'^[✓✔☑️]*\s*第\s*\d+\s*章完成[！!]\s*本章字数[：:]\s*\d+\s*字', stripped):
                continue
            
            # 跳过 "准备生成下一章..." 这类信息（包括不同的符号）
            if re.match(r'^[⏳]*\s*准备生成下一章[\.。…]*$', stripped):
                continue
            
            # 跳过 "全部章节生成完成！ 共 X 章，总字数：XXXX 字" 这类总结信息
            if re.match(r'^[⏳🎉]*\s*全部章节生成完成[！!]\s*共\s*\d+\s*章.*总字数[：:]\s*\d+\s*字', stripped):
                continue
            
            # 跳过 "目录（共X章，预估字数≈XXXX字）" 格式
            if re.match(r'^目录\s*[（\(].*共.*[章节篇].*字.*[）\)]', stripped):
                continue
            
            # 跳过纯数字或短标题行（如：1. 校园霸凌日常）
            if re.match(r'^\d+[\.、]\s*.{1,20}$', stripped):
                continue
            
            # 跳过类似 "第X章" 的标题
            if re.match(r'^第[一二三四五六七八九十\d]+[章节篇][\s：:]*.*$', stripped) and len(stripped) < 30:
                continue
            
            # 跳过分隔线
            if re.match(r'^[=\-_]{3,}$', stripped):
                continue
            
            # 跳过纯符号行
            if re.match(r'^[*#\-=_\s]+$', stripped):
                continue
            
            # 保留故事正文
            in_story = True
            story_lines.append(line)
        
        # 合并行并清理
        result = '\n'.join(story_lines)
        
        # 去除开头和结尾的多余空行
        result = result.strip()
        
        # 将多个连续空行压缩为一个空行
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result
    
    @staticmethod
    def extract_title_from_story(full_text: str) -> Optional[str]:
        """
        从故事中提取可能的标题
        
        Args:
            full_text: 完整的故事文本
            
        Returns:
            提取的标题，如果没有则返回None
        """
        if not full_text or not full_text.strip():
            return None
        
        lines = full_text.split('\n')
        
        for line in lines[:10]:  # 只在前10行查找
            stripped = line.strip()
            
            # 跳过空行和目录标识
            if not stripped or stripped in ['目录', '目录：', '目录:']:
                continue
            
            # 跳过目录项
            if re.match(r'^\d+[\.、]', stripped):
                continue
            
            # 跳过章节标题
            if re.match(r'^【第\s*\d+/\d+\s*章.*】$', stripped):
                continue
            
            if re.match(r'^第[一二三四五六七八九十\d]+[章节篇]', stripped):
                continue
            
            # 跳过分隔线
            if re.match(r'^[=\-_]{3,}$', stripped):
                continue
            
            # 如果是较短的行（小于50字），可能是标题
            if 5 < len(stripped) < 50 and not stripped.endswith('。'):
                return stripped
        
        return None
    
    @staticmethod
    def get_story_preview(full_text: str, max_length: int = 200) -> str:
        """
        获取故事预览（前N个字符）
        
        Args:
            full_text: 完整的故事文本
            max_length: 最大长度
            
        Returns:
            预览文本
        """
        pure_story = StoryExtractor.extract_pure_story(full_text)
        
        if not pure_story:
            return ""
        
        if len(pure_story) <= max_length:
            return pure_story
        
        # 截取到最大长度，并尝试在句号处截断
        preview = pure_story[:max_length]
        
        # 找最后一个句号
        last_period = preview.rfind('。')
        if last_period > max_length * 0.5:  # 如果句号位置不是太靠前
            preview = preview[:last_period + 1]
        else:
            preview = preview + '...'
        
        return preview

