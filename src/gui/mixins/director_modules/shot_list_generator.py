"""
分镜生成器 - 分段生成版，支持长剧本完整分镜
"""

import tkinter as tk
from tkinter import messagebox, END
import threading
import json
import re
import time  # ★★★ 添加time模块导入 ★★★

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize


class ShotListGeneratorMixin:
    """分镜生成器 Mixin - 支持分段生成"""
    
    def _fix_incomplete_json(self, json_str: str) -> str:
        """修复不完整的JSON字符串"""
        try:
            # 1. 找到最后一个完整的对象
            # 从后往前找最后一个完整的 }
            last_brace = json_str.rfind('}')
            if last_brace == -1:
                return None
            
            # 2. 截取到最后一个完整对象
            truncated = json_str[:last_brace + 1]
            
            # 3. 检查是否需要补充结束符号
            # 计算括号平衡
            open_braces = truncated.count('{')
            close_braces = truncated.count('}')
            open_brackets = truncated.count('[')
            close_brackets = truncated.count(']')
            
            # 补充缺失的括号
            result = truncated
            
            # 如果 shots 数组没有关闭
            if open_brackets > close_brackets:
                # 检查最后是否有未完成的对象
                # 如果最后一个字符不是 } 或 ]，可能需要移除最后一个逗号
                if result.rstrip().endswith(','):
                    result = result.rstrip()[:-1]
                
                # 补充缺失的 ]
                for _ in range(open_brackets - close_brackets):
                    result += ']'
            
            # 如果外层对象没有关闭
            if open_braces > close_braces:
                for _ in range(open_braces - close_braces):
                    result += '}'
            
            # 4. 验证修复后的JSON
            json.loads(result)
            return result
            
        except Exception as e:
            print(f"⚠️ JSON修复失败: {e}")
            
            # 尝试更激进的修复：找到最后一个完整的 shot 对象
            try:
                # 找到所有的 shot 对象起始位置
                shot_pattern = r'"shot_number":\s*\d+'
                matches = list(re.finditer(shot_pattern, json_str))
                
                if len(matches) < 2:
                    return None
                
                # 从倒数第二个 shot 开始截断
                second_last_match = matches[-2]
                truncate_pos = second_last_match.start()
                
                # 回退到这个 shot 的开始 {
                while truncate_pos > 0 and json_str[truncate_pos] != '{':
                    truncate_pos -= 1
                
                # 截取到这里
                result = json_str[:truncate_pos]
                
                # 移除最后的逗号
                result = result.rstrip().rstrip(',')
                
                # 补充结束符号
                result += ']}'
                
                # 验证
                json.loads(result)
                print(f"✅ 使用激进修复策略成功")
                return result
                
            except Exception as e2:
                print(f"⚠️ 激进修复也失败: {e2}")
                return None
    
    def _split_script_by_scenes(self, script_text: str, max_length: int = 1500) -> list:
        """智能分割剧本为多个场景段落"""
        # 按场景标记分割
        scenes = []
        current_scene = []
        current_length = 0
        
        lines = script_text.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # 检测场景分隔符
            is_scene_marker = (
                line_stripped.startswith('【场景') or 
                line_stripped.startswith('场景') or
                line_stripped.startswith('##') or
                '---' in line_stripped
            )
            
            # 如果当前段落太长，或遇到场景标记，就分段
            if is_scene_marker and current_scene and current_length > 500:
                scenes.append('\n'.join(current_scene))
                current_scene = [line]
                current_length = len(line)
            elif current_length + len(line) > max_length and current_scene:
                scenes.append('\n'.join(current_scene))
                current_scene = [line]
                current_length = len(line)
            else:
                current_scene.append(line)
                current_length += len(line)
        
        # 添加最后一段
        if current_scene:
            scenes.append('\n'.join(current_scene))
        
        return scenes if scenes else [script_text]
    
    def _on_script_to_shots(self):
        """生成分镜 - 支持分段生成"""
        
        print("\n" + "=" * 60)
        print("🎬 开始生成完整详细分镜")
        print("=" * 60)
        print(f"[DEBUG] _on_script_to_shots 被调用")
        print(f"[DEBUG] 当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            if not hasattr(self, 'script_text'):
                messagebox.showerror("错误", "未找到剧本文本框")
                return
            
            script_text = self.script_text.get("1.0", END).strip()
            print(f"📜 剧本总长度: {len(script_text)} 字符")
            
            if not script_text:
                messagebox.showwarning("提示", "请先生成剧本")
                return
        except Exception as e:
            messagebox.showerror("错误", f"读取剧本失败: {e}")
            return
        
        try:
            api_key = _sanitize(self.api_key.get()) if hasattr(self, 'api_key') else ""
            base_url = _sanitize(self.base_url.get()) if hasattr(self, 'base_url') else "https://api.deepseek.com"
            model = _sanitize(self.model.get()) if hasattr(self, 'model') else "deepseek-chat"
            
            # ★★★ 详细的API配置调试信息 ★★★
            print(f"[DEBUG] API配置读取:")
            print(f"  - hasattr(self, 'api_key'): {hasattr(self, 'api_key')}")
            if hasattr(self, 'api_key'):
                raw_key = self.api_key.get()
                print(f"  - self.api_key.get() 长度: {len(raw_key) if raw_key else 0}")
                print(f"  - self.api_key.get() 前10字符: {raw_key[:10] if raw_key else '(空)'}")
            print(f"  - api_key (sanitized) 长度: {len(api_key) if api_key else 0}")
            print(f"  - base_url: {base_url}")
            print(f"  - model: {model}")
            
            if not api_key:
                messagebox.showerror("错误", "请先配置 API Key")
                return
        except Exception as e:
            messagebox.showerror("错误", f"读取API配置失败: {e}")
            return
        
        # 智能分段
        scenes = self._split_script_by_scenes(script_text)
        total_scenes_original = len(scenes)
        
        # ★★★ 检查是否只生成部分章节 ★★★
        generation_range = "全部章节"
        if hasattr(self, 'shot_generation_range_var'):
            generation_range = self.shot_generation_range_var.get()
        
        # 根据选择限制生成范围
        if generation_range == "前3段" and total_scenes_original > 3:
            scenes = scenes[:3]
            print(f"⚠️ 仅生成前3段（共 {total_scenes_original} 段）")
        elif generation_range == "前5段" and total_scenes_original > 5:
            scenes = scenes[:5]
            print(f"⚠️ 仅生成前5段（共 {total_scenes_original} 段）")
        elif generation_range == "前10段" and total_scenes_original > 10:
            scenes = scenes[:10]
            print(f"⚠️ 仅生成前10段（共 {total_scenes_original} 段）")
        
        total_scenes = len(scenes)
        
        print(f"📚 剧本已分为 {total_scenes_original} 段，本次生成 {total_scenes} 段")
        for i, scene in enumerate(scenes, 1):
            print(f"  段落 {i}: {len(scene)} 字符")
        
        print(f"[DEBUG] 准备生成分镜，共 {total_scenes} 段")
        if hasattr(self, 'status'):
            self.status.set(f"准备生成 {total_scenes} 段分镜...")
            print(f"[DEBUG] 状态已更新: 准备生成 {total_scenes} 段分镜")
        if hasattr(self, 'header_status_var'):
            self.header_status_var.set(f"准备生成 {total_scenes} 段分镜...")
        if hasattr(self, 'update_header_status'):
            self.update_header_status(f"准备生成 {total_scenes} 段分镜", "分镜")
        
        def task():
            try:
                client = DeepSeekClient(api_key=api_key, base_url=base_url, model=model)
                
                all_shots = []
                shot_counter = 1
                
                # 逐段生成
                for scene_idx, scene_text in enumerate(scenes, 1):
                    print(f"\n{'='*50}")
                    print(f"🎬 生成第 {scene_idx}/{total_scenes} 段")
                    print(f"{'='*50}")
                    
                    # 更新状态（开始生成）
                    def update_start_status(idx=scene_idx, total=total_scenes):
                        status_text = f"🎬 正在生成第 {idx}/{total} 段..."
                        if hasattr(self, 'status'):
                            self.status.set(status_text)
                        print(f"[状态] {status_text}")
                    
                    self.after(0, update_start_status)
                    
                    # 详细提示词
                    system_prompt = """你是奥斯卡金像奖级别的分镜设计大师，专注于创作极其详细的分镜头脚本。

【核心能力】
1. 超细致的视觉描述（每个画面300-500字，可直接作为绘画指令）
2. 人物一致性专家（同一人物外貌、服装100%一致）
3. 故事叙事精准（通过图片序列完整展现故事）
4. 情感传达大师（善用构图、光线、表情传达情感）
5. 镜头语言专家（熟练运用景别、角度变化增强叙事节奏）

【工作标准】
- 人物一致性是第一优先级，绝不能改变同一人物的外貌、发型、服装
- 每个分镜描述要达到800-1200字总量（包含visual_description、character_details、action、emotion、lighting等）
- 描述要具体到可以画出来，避免抽象概念
- ★★★ 每个分镜描述的是一个静态画面（定格瞬间），不是动作过程 ★★★
- ★★★ 相邻分镜必须切换镜头（景别或角度），不能连续使用相同镜头 ★★★
- 确保JSON格式完整正确，从{开始到}结尾
- 只输出JSON，不要任何其他文字

【镜头切换规则】
1. 景别变化：全景 → 中景 → 特写 → 中景 → 全景（形成节奏）
2. 角度变化：平视 → 俯视 → 仰视 → 平视（增强视觉冲击）
3. 避免连续两个分镜使用相同的景别+角度组合
4. 重要情绪时刻用特写，场景转换用全景，对话用中景"""
                    
                    # 上文人物信息（用于保持一致性）
                    character_context = ""
                    if all_shots:
                        last_shot = all_shots[-1]
                        if 'character_details' in last_shot:
                            character_context = f"\n\n【重要】之前已出现的人物，外貌和服装必须完全一致：\n{json.dumps(last_shot['character_details'], ensure_ascii=False, indent=2)}"
                    
                    user_prompt = f"""将以下剧本片段分解为**极其详细**的分镜JSON，每个分镜都要能独立讲述故事片段。

【核心目标】
通过图片序列就能完整理解故事情节，每张图都是故事的关键节点。

【关键要求】
1. ★★★ 每个分镜描述一个静态画面（定格瞬间），就像摄影师按下快门的那一刻 ★★★
2. ★★★ 相邻分镜必须切换镜头（景别或角度不同），形成视觉节奏 ★★★
3. 画面要有明确的视觉焦点，观众一眼就知道看哪里
4. 人物的表情、姿态要能传达情绪，不需要描述动作过程

格式：
{{
  "shots": [
    {{
      "shot_number": {shot_counter},
      "shot_type": "★必须从以下选择，且相邻分镜不能重复：
        - Wide Shot（全景）：展现整体环境和人物位置关系
        - Medium Shot（中景）：腰部以上，适合对话和互动
        - Close-up（特写）：肩部以上，强调表情和情绪
        - Extreme Close-up（大特写）：局部特写，如眼睛、手部
        - Over-the-shoulder（过肩镜头）：从一个人物肩膀看向另一个人物",
      "location": "精确位置：室内/室外+具体地点+方位",
      
      "visual_description": "**静态画面描述（300-500字）- 描述定格瞬间**：
        ★★★ 这是一个静态画面，就像一张照片，描述画面中所有元素的状态 ★★★
        
        - 【画面构图】前景有什么、中景有什么、背景有什么，画面重心在哪里
        - 【人物状态】人物在画面中的位置、姿态、表情（定格状态，不是动作过程）
          例如：\"张三站在窗前，右手扶着窗框，头微微侧向左边，眼神望向窗外\"
          而不是：\"张三走向窗前，伸手推开窗户\"
        - 【空间布局】物品摆放、人物位置关系、距离远近
        - 【光线效果】主光源位置、光线强度、阴影方向、明暗对比、色温
        - 【色彩基调】主色调、辅助色、画面整体色彩情绪
        - 【视觉焦点】观众第一眼会看到什么，引导视线的元素
        - 【情绪氛围】这个画面传达什么情绪（通过构图、光线、表情）
        ⚠️ 描述要具体到可以直接作为绘画指令，重点是\"此刻画面是什么样\"",
      
      "characters": ["人物名"],
      "character_details": {{
        "人物名": {{
          "appearance": "外貌（固定，所有分镜必须一致）：
            - 年龄：XX岁
            - 身高体型：XXXcm，体型特征
            - 脸型：圆脸/方脸/瓜子脸/长脸
            - 眼睛：大小、形状、眼神特点
            - 鼻子：高低、形状
            - 嘴唇：厚薄、颜色
            - 肤色：白皙/健康/古铜等
            - 特殊标记：痣/疤痕/酒窝等",
          
          "hair": "发型（固定）：
            - 长度：长发/中长发/短发/超短发
            - 造型：直发/卷发/波浪/马尾/丸子头等
            - 颜色：黑色/棕色/金色等
            - 刘海：有无、样式
            - 发质：柔顺/蓬松/油亮等",
          
          "clothing": "服装（固定，除非剧情换装）：
            - 上衣：款式、颜色、材质、细节（纽扣/拉链/图案/logo）
            - 下装：款式、颜色、长度
            - 鞋子：类型、颜色、款式
            - 配饰：眼镜/项链/手表/包包/帽子等",
          
          "expression": "此分镜中的表情：
            - 眉毛：皱/扬/平/挑
            - 眼神：锐利/温柔/迷茫/惊恐/专注
            - 嘴角：上扬/下垂/紧抿/微张
            - 整体神态：严肃/放松/紧张/开心/悲伤",
          
          "pose": "此分镜中的人物姿态（静态定格）：
            ★★★ 描述人物在这一瞬间的姿态，不是动作过程 ★★★
            - 身体姿态：站立/坐着/倚靠/蹲着，身体朝向，重心位置
            - 手部位置：左手/右手分别放在哪里，手势是什么
            - 腿部状态：双腿的位置和姿态
            - 头部角度：抬头/低头/转头的具体角度
            - 整体姿态传达的情绪
            例如：\"站在门口，右手扶着门框，左手自然下垂，身体微微前倾，头部转向左侧30度\"
            而不是：\"走向门口，伸手推开门\"",
          
          "emotion": "情绪状态：
            - 主要情绪：喜悦/愤怒/悲伤/恐惧/惊讶/厌恶/平静
            - 强度：轻微/明显/强烈/极度
            - 外化表现：如何通过肢体语言体现"
        }}
      }},
      
      "scene_moment": "**画面瞬间说明（100-150字）**：
        ★★★ 说明这个画面捕捉的是故事中的哪个瞬间 ★★★
        例如：\"这是张三刚听到消息后的反应瞬间，他愣在原地的那一刻\"
        而不是：\"张三听到消息后，慢慢转过身来，走向窗边\"
        
        简要说明：
        - 这个画面在故事中的位置（刚发生了什么/即将发生什么）
        - 为什么选择这个瞬间（情绪高点/转折点/重要信息）",
      
      "dialogue": {{"speaker": "人名", "content": "完整对话内容", "tone": "语气（平静/激动/低沉/颤抖/讽刺/温柔等）"}},
      
      "camera": {{
        "movement": "固定镜头（静态画面用固定镜头）",
        "angle": "★★★ 拍摄角度（必须与上一个分镜不同）：
          - 平视（Eye level）：自然视角，适合日常场景
          - 俯视（High angle）15°/30°/45°：显得人物渺小、脆弱
          - 仰视（Low angle）15°/30°/45°：显得人物高大、有力量
          - 鸟瞰（Bird's eye）：从正上方看，展现空间关系
          - 虫视（Worm's eye）：从地面向上看，极具冲击力",
        "lens": "镜头焦距：广角（16-35mm突出空间感）/标准（50mm自然视角）/长焦（85-135mm突出人物/背景虚化）"
      }},
      
      "duration": "建议时长（XX秒-XX秒）",
      "emotion": "**整体情绪氛围（100-150字）**：这个分镜要传达什么情感，观众应该有什么感受",
      "lighting": "**光线设计（100-150字）**：光源、光线方向、明暗对比、色温、光线对情绪的烘托",
      "transition_to_next": "转场方式：硬切/淡入淡出/叠化/划像/其他",
      
      "story_context": "**这个分镜在故事中的作用（50-100字）**：推动情节/展现冲突/铺垫悬念/情感高潮/等",
      
      "jimeng_prompt": "**图像生成专用提示词（200-300字）- 描述静态画面**：
        ★★★ 精确描述这个定格瞬间的所有视觉元素 ★★★
        格式：[环境]，[光线]，[人物外貌+服装]，[人物姿态+表情]，[构图]，[情绪氛围]。
        
        例如（正确）：'现代办公室内，明亮的日光透过落地窗照入，一位25岁黑色短发戴眼镜的男性，穿白色衬衫黑色西裤，站在落地窗前，右手扶着窗框，左手插在口袋里，头部微微侧向左边，眼神望向窗外，表情若有所思。中景镜头，侧面45度角，背景虚化。沉思氛围。'
        
        而不是：'男性走向窗边，伸手推开窗户，转头看向远方'（这是动作过程）
        
        重点：描述人物在画面中的位置、姿态、表情，而不是动作过程"
    }}
  ]
}}

⚠️ **关键要求**：
1. **人物一致性（最重要）**：同一人物的外貌、发型、服装在所有分镜中必须100%一致，一个细节都不能变
2. **描述详细程度**：每个分镜的总描述字数应达到800-1200字
3. ★★★ **静态画面**：每个分镜描述一个定格瞬间，不是动作过程 ★★★
4. ★★★ **镜头切换**：相邻分镜必须切换景别或角度，形成视觉节奏 ★★★
   - 例如：全景 → 中景 → 特写 → 中景（景别变化）
   - 或者：平视 → 俯视 → 平视（角度变化）
5. **故事完整性**：通过一系列静态画面展现故事的每个转折和情绪变化
6. **可绘制性**：所有描述都要具体到可以作为绘画/生成图像的直接指令
7. **连贯性**：前后分镜要能自然衔接，逻辑流畅{character_context}

剧本片段：
{scene_text}"""
                    
                    # ★★★ 使用流式输出 ★★★
                    print(f"🔄 开始流式生成第 {scene_idx}/{total_scenes} 段...")
                    print(f"[DEBUG] API配置: model={model}, base_url={base_url}")
                    print(f"[DEBUG] system_prompt长度: {len(system_prompt)} 字符")
                    print(f"[DEBUG] user_prompt长度: {len(user_prompt)} 字符")
                    
                    # ★★★ 调用API（流式）- 先不设置max_tokens，让API使用默认值 ★★★
                    print(f"[DEBUG] 准备调用API流式接口...")
                    try:
                        stream_generator = client.stream(
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.6
                            # 不设置max_tokens，使用API默认值
                        )
                        print(f"[DEBUG] API流式生成器已创建")
                    except Exception as e:
                        print(f"[ERROR] 创建流式生成器失败: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                    
                    # ★★★ 收集流式响应并实时显示到UI ★★★
                    response = ""
                    chunk_count = 0
                    last_update_time = 0
                    last_ui_update_length = 0
                    
                    # 实时显示到shots_list
                    def append_to_shots_list(text):
                        """实时追加文本到分镜显示区"""
                        if hasattr(self, 'shots_list'):
                            try:
                                self.shots_list.config(state="normal")
                                self.shots_list.insert("end", text)
                                self.shots_list.see("end")  # 自动滚动到底部
                                self.shots_list.config(state="disabled")
                            except Exception as e:
                                print(f"[ERROR] 更新shots_list失败: {e}")
                    
                    # 在开始生成前，清空显示区（只在第一段时清空）
                    if scene_idx == 1:
                        def clear_shots_list():
                            if hasattr(self, 'shots_list'):
                                self.shots_list.config(state="normal")
                                self.shots_list.delete("1.0", "end")
                                self.shots_list.insert("end", "=" * 100 + "\n")
                                self.shots_list.insert("end", "🎬 正在生成详细分镜...\n")
                                self.shots_list.insert("end", "=" * 100 + "\n\n")
                                self.shots_list.config(state="disabled")
                        
                        self.after(0, clear_shots_list)
                    
                    # 添加段落标题
                    segment_header = f"\n{'='*50}\n📍 第 {scene_idx}/{total_scenes} 段\n{'='*50}\n"
                    self.after(0, lambda: append_to_shots_list(segment_header))
                    
                    for content_chunk in stream_generator:
                        if content_chunk:
                            response += content_chunk
                            chunk_count += 1
                            
                            # ★★★ 实时显示生成的内容到UI ★★★
                            current_time = time.time()
                            if current_time - last_update_time >= 0.3:  # 每0.3秒更新一次
                                # 获取新增的内容
                                new_content = response[last_ui_update_length:]
                                if new_content:
                                    # 实时追加到UI
                                    self.after(0, lambda text=new_content: append_to_shots_list(text))
                                    last_ui_update_length = len(response)
                                
                                # 更新状态栏
                                progress_text = f"🔄 第 {scene_idx}/{total_scenes} 段生成中... ({len(response)} 字符)"
                                def update_status(text=progress_text):
                                    if hasattr(self, 'status'):
                                        self.status.set(text)
                                
                                self.after(0, update_status)
                                last_update_time = current_time
                    
                    # 显示剩余未显示的内容
                    if last_ui_update_length < len(response):
                        final_content = response[last_ui_update_length:]
                        self.after(0, lambda text=final_content: append_to_shots_list(text))
                    
                    print(f"✅ 流式生成完成，总长度: {len(response)} 字符，共 {chunk_count} 个片段")
                    
                    # 添加段落结束标记
                    self.after(0, lambda: append_to_shots_list("\n\n"))
                    
                    # ★★★ 提取JSON（用于内部处理，不显示给用户）★★★
                    json_response = response
                    json_response = re.sub(r'```json\s*', '', json_response)
                    json_response = re.sub(r'```\s*', '', json_response).strip()
                    
                    json_start = json_response.find('{')
                    json_end = json_response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_response = json_response[json_start:json_end]
                    
                    try:
                        shots_data = json.loads(json_response)
                        segment_shots = shots_data.get('shots', [])
                        
                        # 更新分镜编号
                        for shot in segment_shots:
                            shot['shot_number'] = shot_counter
                            shot_counter += 1
                        
                        all_shots.extend(segment_shots)
                        success_msg = f"✅ 第 {scene_idx}/{total_scenes} 段成功，生成 {len(segment_shots)} 个分镜（累计 {len(all_shots)} 个）"
                        print(success_msg)
                        
                        # 更新UI显示
                        def update_success_status(msg=success_msg):
                            if hasattr(self, 'status'):
                                self.status.set(msg)
                        
                        self.after(0, update_success_status)
                        
                    except json.JSONDecodeError as e:
                        print(f"⚠️ 第 {scene_idx} 段JSON解析失败: {e}")
                        print(f"📝 原始响应长度: {len(json_response)} 字符")
                        
                        # ★★★ 增强的JSON修复逻辑 ★★★
                        fixed_response = self._fix_incomplete_json(json_response)
                        
                        if fixed_response:
                            try:
                                shots_data = json.loads(fixed_response)
                                segment_shots = shots_data.get('shots', [])
                                
                                for shot in segment_shots:
                                    shot['shot_number'] = shot_counter
                                    shot_counter += 1
                                
                                all_shots.extend(segment_shots)
                                fix_msg = f"✅ 第 {scene_idx}/{total_scenes} 段已修复，生成 {len(segment_shots)} 个分镜（累计 {len(all_shots)} 个）"
                                print(fix_msg)
                                
                                # 更新UI显示
                                def update_fix_status(msg=fix_msg):
                                    if hasattr(self, 'status'):
                                        self.status.set(msg)
                                
                                self.after(0, update_fix_status)
                            except Exception as fix_error:
                                print(f"❌ 第 {scene_idx} 段修复后仍然失败: {fix_error}")
                                print(f"📄 保存原始响应到日志以供调试...")
                                # 保存到文件用于调试
                                debug_file = f"debug_shot_response_{scene_idx}.txt"
                                with open(debug_file, 'w', encoding='utf-8') as f:
                                    f.write(json_response)
                                print(f"💾 已保存到 {debug_file}")
                                
                                # 在UI显示错误信息
                                error_msg = f"\n⚠️ 第 {scene_idx} 段解析失败，已跳过\n\n"
                                self.after(0, lambda msg=error_msg: append_to_shots_list(msg))
                                continue
                        else:
                            print(f"❌ 第 {scene_idx} 段无法修复，跳过")
                            continue
                
                # ★★★ 全部完成 - 保存数据但不重新显示（因为已经实时显示了）★★★
                print(f"\n[DEBUG] 生成完成检查:")
                print(f"  - all_shots 数量: {len(all_shots) if all_shots else 0}")
                print(f"  - all_shots 类型: {type(all_shots)}")
                
                if all_shots:
                    # 保存分镜数据到self.current_shots
                    self.current_shots = all_shots
                    print(f"[DEBUG] ✅ 已保存 {len(all_shots)} 个分镜到 self.current_shots")
                    print(f"\n{'='*50}")
                    print(f"✅ 全部完成！共生成 {len(all_shots)} 个详细分镜")
                    print(f"{'='*50}")
                    
                    # 在UI显示完成信息
                    range_info = f"（生成范围: {generation_range}）" if generation_range != "全部章节" else ""
                    completion_msg = f"\n\n{'='*100}\n✅ 生成完成！共 {len(all_shots)} 个详细分镜 {range_info}\n{'='*100}\n"
                    
                    def show_completion():
                        if hasattr(self, 'shots_list'):
                            self.shots_list.config(state="normal")
                            self.shots_list.insert("end", completion_msg)
                            self.shots_list.config(state="disabled")
                    
                    self.after(0, show_completion)
                    
                    # 更新状态
                    def update_final_status():
                        final_msg = f"✅ 完整生成 {len(all_shots)} 个详细分镜！"
                        if hasattr(self, 'status'):
                            self.status.set(final_msg)
                        print(f"[最终] {final_msg}")
                    
                    self.after(0, update_final_status)
                    
                    # 自动提取即梦AI提示词、刷新下拉框、保存项目
                    self.after(200, lambda: self._post_generation_tasks(all_shots))
                else:
                    error_msg = "未能生成任何分镜，请检查API配置和剧本内容"
                    print(f"[ERROR] {error_msg}")
                    self.after(0, lambda: messagebox.showerror("错误", error_msg))
                    raise ValueError(error_msg)
                
            except Exception as e:
                print(f"❌ 错误: {e}")
                import traceback
                traceback.print_exc()
                self.after(0, lambda: messagebox.showerror("错误", f"生成失败: {e}"))
                self.after(0, lambda: self.status.set("❌ 生成失败"))
        
        threading.Thread(target=task, daemon=True).start()
    
    def _post_generation_tasks(self, all_shots):
        """生成完成后的后续任务"""
        print("[DEBUG] ========== 执行生成后任务 ==========")
        print(f"[DEBUG] all_shots 数量: {len(all_shots)}")
        print(f"[DEBUG] self.current_shots 数量: {len(self.current_shots) if hasattr(self, 'current_shots') and self.current_shots else 0}")
        
        # 确保 current_shots 已设置
        if not hasattr(self, 'current_shots') or not self.current_shots:
            print("[WARNING] current_shots 未设置或为空，尝试设置")
            self.current_shots = all_shots
        
        print(f"[DEBUG] 确认后 current_shots 数量: {len(self.current_shots)}")
        
        # 提取即梦AI提示词
        if hasattr(self, '_extract_all_jimeng_prompts'):
            try:
                self._extract_all_jimeng_prompts(show_message=False)
                print("[DEBUG] ✅ 即梦AI提示词提取成功")
            except Exception as e:
                print(f"[ERROR] 提取即梦AI提示词失败: {e}")
        else:
            print("[WARNING] 未找到 _extract_all_jimeng_prompts 方法")
        
        # 刷新分镜下拉框（延迟刷新确保UI已更新）
        def delayed_refresh():
            if hasattr(self, '_refresh_shot_combo'):
                try:
                    print(f"[DEBUG] 准备刷新下拉框，current_shots 数量: {len(self.current_shots) if hasattr(self, 'current_shots') and self.current_shots else 0}")
                    self._refresh_shot_combo(silent=True)
                    print("[DEBUG] ✅ 【生成图片】下拉框已刷新")
                except Exception as e:
                    print(f"[ERROR] 刷新下拉框失败: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("[WARNING] 未找到 _refresh_shot_combo 方法")
            
            # 同时刷新预览页面的下拉框
            if hasattr(self, '_refresh_preview_shot_combo'):
                try:
                    self._refresh_preview_shot_combo()
                    print("[DEBUG] ✅ 【预览】下拉框已刷新")
                except Exception as e:
                    print(f"[ERROR] 刷新预览下拉框失败: {e}")
        
        self.after(200, delayed_refresh)
        
        # 保存到项目
        if hasattr(self, '_auto_save_shots_to_project'):
            try:
                self._auto_save_shots_to_project()
                print("[DEBUG] ✅ 分镜已自动保存到项目")
            except Exception as e:
                print(f"[ERROR] 保存分镜失败: {e}")
        else:
            print("[WARNING] 未找到 _auto_save_shots_to_project 方法")
        
        print("[DEBUG] ========== 生成后任务完成 ==========")
        
        # 显示完成提示
        # 获取生成范围信息
        generation_range = "全部章节"
        if hasattr(self, 'shot_generation_range_var'):
            generation_range = self.shot_generation_range_var.get()
        
        range_info = f"\n✓ 生成范围: {generation_range}" if generation_range != "全部章节" else ""
        
        messagebox.showinfo("✅ 完成", 
                           f"成功生成 {len(all_shots)} 个详细分镜！\n\n"
                           f"✓ 分镜已实时显示在【分镜】标签页\n"
                           f"✓ 即梦AI提示词已自动提取\n"
                           f"✓ 已自动保存到项目\n"
                           f"✓ 分镜下拉框已更新"
                           f"{range_info}")
    
    def _show_shots_result(self, shots_data: dict):
        """显示分镜并自动提取即梦AI提示词"""
        print("[DEBUG] ========== 开始显示分镜结果 ==========")
        print(f"[DEBUG] shots_data类型: {type(shots_data)}")
        print(f"[DEBUG] shots_data keys: {shots_data.keys() if isinstance(shots_data, dict) else 'N/A'}")
        
        if 'shots' not in shots_data:
            messagebox.showerror("错误", "分镜数据格式错误")
            return
        
        shots = shots_data['shots']
        self.current_shots = shots
        print(f"[DEBUG] ✅ 保存了 {len(shots)} 个分镜到 self.current_shots")
        
        # ★★★ 强制清空并重新显示分镜 ★★★
        if hasattr(self, 'shots_list'):
            print("[DEBUG] 找到 shots_list，强制清空并更新显示")
            self.shots_list.config(state="normal")
            self.shots_list.delete("1.0", "end")  # 清空所有内容
            
            # ★★★ 友好的格式化显示（添加更多调试信息）★★★
            print(f"[DEBUG] 开始插入 {len(shots)} 个分镜到 shots_list")
            
            for idx, shot in enumerate(shots, 1):
                print(f"[DEBUG] 插入分镜 {idx}/{len(shots)}: shot_number={shot.get('shot_number', idx)}")
                
                self.shots_list.insert("end", "="*100 + "\n")
                self.shots_list.insert("end", f"【分镜 {shot.get('shot_number', idx)}】{shot.get('scene_id', '')} - {shot.get('shot_type', '')}\n")
                self.shots_list.insert("end", "="*100 + "\n\n")
                
                self.shots_list.insert("end", f"📍 位置: {shot.get('location', '')}\n")
                self.shots_list.insert("end", f"👥 人物: {', '.join(shot.get('characters', []))}\n\n")
                
                self.shots_list.insert("end", f"🎨 画面描述:\n{shot.get('visual_description', '')}\n\n")
                self.shots_list.insert("end", f"🎭 动作:\n{shot.get('action', '')}\n\n")
                
                if shot.get('dialogue'):
                    self.shots_list.insert("end", f"💬 对白: {shot.get('dialogue', '')}\n\n")
                
                camera = shot.get('camera', {})
                if camera:
                    self.shots_list.insert("end", f"📷 镜头: {camera.get('movement', '')} | {camera.get('angle', '')} | {camera.get('lens', '')}\n")
                
                self.shots_list.insert("end", f"⏱️  时长: {shot.get('duration', '')} | 过渡: {shot.get('transition_to_next', '')}\n\n")
                
                if shot.get('jimeng_prompt'):
                    self.shots_list.insert("end", f"🖼️  图像提示词:\n{shot.get('jimeng_prompt', '')}\n\n")
                
                if shot.get('notes'):
                    self.shots_list.insert("end", f"📝 备注: {shot.get('notes', '')}\n\n")
                
                self.shots_list.insert("end", "\n")
            
            print(f"[DEBUG] ✅ 完成插入所有分镜")
            self.shots_list.config(state="disabled")
            print(f"[DEBUG] shots_list 已设置为只读")
        elif hasattr(self, 'shots_text'):
            print("[DEBUG] 找到 shots_text（旧变量），更新显示")
            self.shots_text.config(state="normal")
            self.shots_text.delete("1.0", "end")
            
            # 友好的格式化显示
            for idx, shot in enumerate(shots, 1):
                self.shots_text.insert("end", "="*100 + "\n")
                self.shots_text.insert("end", f"【分镜 {shot.get('shot_number', idx)}】{shot.get('scene_id', '')} - {shot.get('shot_type', '')}\n")
                self.shots_text.insert("end", "="*100 + "\n\n")
                
                self.shots_text.insert("end", f"📍 位置: {shot.get('location', '')}\n")
                self.shots_text.insert("end", f"👥 人物: {', '.join(shot.get('characters', []))}\n\n")
                
                self.shots_text.insert("end", f"🎨 画面: {shot.get('visual_description', '')}\n\n")
                self.shots_text.insert("end", f"🎭 动作: {shot.get('action', '')}\n\n")
                
                self.shots_text.insert("end", "\n")
            
            self.shots_text.config(state="disabled")
        else:
            print("[ERROR] 没有找到 shots_list 或 shots_text")
        
        # ★★★ 自动切换到分镜标签页（确保用户能看到）★★★
        if hasattr(self, 'director_content_notebook'):
            print("[DEBUG] 切换到分镜标签页")
            try:
                self.director_content_notebook.select(1)  # 第2个标签（分镜）
                print("[DEBUG] ✅ 已切换到分镜标签页")
            except Exception as e:
                print(f"[DEBUG] ⚠️ 切换标签页失败: {e}")
                # 尝试其他索引
                try:
                    # 可能是第1个标签（索引从0开始）
                    tabs = self.director_content_notebook.tabs()
                    print(f"[DEBUG] 可用标签页: {tabs}")
                    for i, tab in enumerate(tabs):
                        tab_text = self.director_content_notebook.tab(i, "text")
                        print(f"[DEBUG] 标签 {i}: {tab_text}")
                        if "分镜" in tab_text:
                            self.director_content_notebook.select(i)
                            print(f"[DEBUG] ✅ 已切换到分镜标签页（索引 {i}）")
                            break
                except Exception as e2:
                    print(f"[DEBUG] ❌ 无法切换标签页: {e2}")
        
        # ★★★ 自动提取即梦AI提示词（不显示成功提示框，避免重复）★★★
        print("[DEBUG] 开始自动提取即梦AI提示词")
        if hasattr(self, '_extract_all_jimeng_prompts'):
            try:
                # 延迟200ms执行，确保分镜显示完成
                self.after(200, lambda: self._extract_all_jimeng_prompts(show_message=False))
                print("[DEBUG] 即梦AI提示词提取已安排")
            except Exception as e:
                print(f"[ERROR] 提取即梦AI提示词失败: {e}")
        else:
            print("[ERROR] 没有找到 _extract_all_jimeng_prompts 方法")
        
        # 刷新分镜下拉框（静默刷新，不弹提示框）
        if hasattr(self, '_refresh_shot_combo'):
            print("[DEBUG] 刷新【生成图片】下拉框")
            self._refresh_shot_combo(silent=True)
        
        # 刷新预览页面下拉框
        if hasattr(self, '_refresh_preview_shot_combo'):
            print("[DEBUG] 刷新【预览】下拉框")
            self._refresh_preview_shot_combo()
        
        # 自动保存分镜到项目
        print("[DEBUG] 开始自动保存分镜到项目")
        if hasattr(self, '_auto_save_shots_to_project'):
            try:
                self._auto_save_shots_to_project()
                print("[DEBUG] 分镜已自动保存到项目")
            except Exception as e:
                print(f"[ERROR] 保存分镜失败: {e}")
        else:
            print("[ERROR] 没有找到 _auto_save_shots_to_project 方法")
        
        messagebox.showinfo("✅ 完成", 
                           f"成功生成 {len(shots)} 个详细分镜！\n\n"
                           f"✓ 分镜已显示在【分镜】标签页\n"
                           f"✓ 即梦AI提示词已自动提取到【即梦AI提示词】标签页\n"
                           f"✓ 已自动保存到项目\n\n"
                           f"可以直接复制使用！")
