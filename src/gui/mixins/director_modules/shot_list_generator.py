"""
分镜生成器 - 分段生成版，支持长剧本完整分镜
"""

import tkinter as tk
from tkinter import messagebox, END
import threading
import json
import re

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize


class ShotListGeneratorMixin:
    """分镜生成器 Mixin - 支持分段生成"""
    
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
        
        print("=" * 60)
        print("🎬 开始生成完整详细分镜")
        print("=" * 60)
        
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
            
            if not api_key:
                messagebox.showerror("错误", "请先配置 API Key")
                return
        except Exception as e:
            messagebox.showerror("错误", f"读取API配置失败: {e}")
            return
        
        # 智能分段
        scenes = self._split_script_by_scenes(script_text)
        total_scenes = len(scenes)
        
        print(f"📚 剧本已分为 {total_scenes} 段")
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
                    
                    self.after(0, lambda idx=scene_idx, total=total_scenes: 
                              self.status.set(f"🎬 正在生成第 {idx}/{total} 段..."))
                    
                    # 详细提示词
                    system_prompt = """你是奥斯卡金像奖级别的分镜设计大师，专注于创作极其详细的分镜头脚本。

【核心能力】
1. 超细致的视觉描述（每个画面300-500字，可直接作为绘画指令）
2. 人物一致性专家（同一人物外貌、服装100%一致）
3. 故事叙事精准（通过图片序列完整展现故事）
4. 情感传达大师（善用构图、光线、表情传达情感）

【工作标准】
- 人物一致性是第一优先级，绝不能改变同一人物的外貌、发型、服装
- 每个分镜描述要达到800-1200字总量（包含visual_description、character_details、action、emotion、lighting等）
- 描述要具体到可以画出来，避免抽象概念
- 确保JSON格式完整正确，从{开始到}结尾
- 只输出JSON，不要任何其他文字"""
                    
                    # 上文人物信息（用于保持一致性）
                    character_context = ""
                    if all_shots:
                        last_shot = all_shots[-1]
                        if 'character_details' in last_shot:
                            character_context = f"\n\n【重要】之前已出现的人物，外貌和服装必须完全一致：\n{json.dumps(last_shot['character_details'], ensure_ascii=False, indent=2)}"
                    
                    user_prompt = f"""将以下剧本片段分解为**极其详细**的分镜JSON，每个分镜都要能独立讲述故事片段。

【核心目标】
通过图片序列就能完整理解故事情节，每张图都是故事的关键节点。

格式：
{{
  "shots": [
    {{
      "shot_number": {shot_counter},
      "shot_type": "Wide Shot（全景）/Medium Shot（中景）/Close-up（特写）/Extreme Close-up（大特写）",
      "location": "精确位置：室内/室外+具体地点+方位",
      
      "visual_description": "**画面详细描述（300-500字）**：
        - 【画面构图】前景有什么、中景有什么、背景有什么，画面重心在哪里
        - 【空间布局】物品摆放、人物位置关系、距离远近
        - 【光线效果】主光源位置、光线强度、阴影方向、明暗对比、色温
        - 【色彩基调】主色调、辅助色、画面整体色彩情绪
        - 【视觉焦点】观众第一眼会看到什么，引导视线的元素
        - 【环境氛围】给人的整体感受（温馨/压抑/紧张/轻松等）
        ⚠️ 描述要具体到可以直接作为绘画指令",
      
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
          
          "action": "此分镜中的具体动作（细致描述）：
            - 身体姿态：站/坐/走/跑/躺，身体朝向
            - 手部动作：左手/右手分别在做什么
            - 腿部动作：移动状态、重心
            - 头部动作：抬头/低头/转头，角度
            - 动作幅度：大/中/小
            - 动作速度：快/慢/突然/缓慢
            ⚠️ 要能想象出定格画面",
          
          "emotion": "情绪状态：
            - 主要情绪：喜悦/愤怒/悲伤/恐惧/惊讶/厌恶/平静
            - 强度：轻微/明显/强烈/极度
            - 外化表现：如何通过肢体语言体现"
        }}
      }},
      
      "action": "**主要动作叙述（200-300字）**：
        详细描述这个分镜中正在发生什么，动作的前因后果，人物之间的互动细节。
        要能让读者脑海中浮现动态画面。",
      
      "dialogue": {{"speaker": "人名", "content": "完整对话内容", "tone": "语气（平静/激动/低沉/颤抖/讽刺/温柔等）"}},
      
      "camera": {{
        "movement": "运镜方式：固定镜头/推进（Push in）/拉远（Pull back）/横摇（Pan）/纵摇（Tilt）/跟随（Follow）/环绕（Orbit）",
        "angle": "拍摄角度：平视（Eye level）/俯视（High angle）15°/30°/45°/仰视（Low angle）15°/30°/45°/鸟瞰（Bird's eye）/虫视（Worm's eye）",
        "lens": "镜头焦距：广角（16-35mm突出空间感）/标准（50mm自然视角）/长焦（85-135mm突出人物/背景虚化）"
      }},
      
      "duration": "建议时长（XX秒-XX秒）",
      "emotion": "**整体情绪氛围（100-150字）**：这个分镜要传达什么情感，观众应该有什么感受",
      "lighting": "**光线设计（100-150字）**：光源、光线方向、明暗对比、色温、光线对情绪的烘托",
      "transition_to_next": "转场方式：硬切/淡入淡出/叠化/划像/其他",
      
      "story_context": "**这个分镜在故事中的作用（50-100字）**：推动情节/展现冲突/铺垫悬念/情感高潮/等",
      
      "jimeng_prompt": "**图像生成专用提示词（200-300字）**：
        精确描述画面的所有视觉元素，语言简洁清晰，适合直接输入AI图像生成。
        格式：[环境]，[光线]，[人物外貌+服装]，[人物动作+表情]，[构图]，[情绪氛围]。
        例如：'现代办公室内，明亮的日光透过落地窗照入，一位25岁黑色短发戴眼镜的男性，穿白色衬衫黑色西裤，坐在办公桌前专注看电脑，表情严肃，手指敲击键盘。中景镜头，侧面45度角，背景虚化。专业商务氛围。'"
    }}
  ]
}}

⚠️ **关键要求**：
1. **人物一致性（最重要）**：同一人物的外貌、发型、服装在所有分镜中必须100%一致，一个细节都不能变
2. **描述详细程度**：每个分镜的总描述字数应达到800-1200字
3. **故事完整性**：分镜要细致到足以展现故事的每个转折和情绪变化
4. **可绘制性**：所有描述都要具体到可以作为绘画/生成图像的直接指令
5. **连贯性**：前后分镜要能自然衔接，逻辑流畅{character_context}

剧本片段：
{scene_text}"""
                    
                    # 调用API
                    response = client.chat([
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ], temperature=0.6)
                    
                    print(f"✅ API响应长度: {len(response)} 字符")
                    
                    # 提取JSON
                    response = re.sub(r'```json\s*', '', response)
                    response = re.sub(r'```\s*', '', response).strip()
                    
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        response = response[json_start:json_end]
                    
                    try:
                        shots_data = json.loads(response)
                        segment_shots = shots_data.get('shots', [])
                        
                        # 更新分镜编号
                        for shot in segment_shots:
                            shot['shot_number'] = shot_counter
                            shot_counter += 1
                        
                        all_shots.extend(segment_shots)
                        print(f"✅ 第 {scene_idx} 段成功，生成 {len(segment_shots)} 个分镜")
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ 第 {scene_idx} 段JSON解析失败: {e}")
                        # 尝试修复
                        try:
                            fixed = response[:response.rfind(',')]
                            if not fixed.endswith(']'):
                                fixed += ']'
                            if not fixed.endswith('}'):
                                fixed += '}'
                            shots_data = json.loads(fixed)
                            segment_shots = shots_data.get('shots', [])
                            
                            for shot in segment_shots:
                                shot['shot_number'] = shot_counter
                                shot_counter += 1
                            
                            all_shots.extend(segment_shots)
                            print(f"✅ 第 {scene_idx} 段已修复，生成 {len(segment_shots)} 个分镜")
                        except:
                            print(f"❌ 第 {scene_idx} 段无法修复，跳过")
                            continue
                
                # 全部完成
                if all_shots:
                    final_data = {"shots": all_shots}
                    print(f"\n{'='*50}")
                    print(f"✅ 全部完成！共生成 {len(all_shots)} 个详细分镜")
                    print(f"{'='*50}")
                    
                    self.after(0, self._show_shots_result, final_data)
                    self.after(0, lambda: self.status.set(f"✅ 完整生成 {len(all_shots)} 个详细分镜！"))
                    
                    # 自动生成即梦AI提示词
                    self.after(0, lambda: self._generate_jimeng_prompts_for_all_shots(all_shots))
                else:
                    raise ValueError("未能生成任何分镜")
                
            except Exception as e:
                print(f"❌ 错误: {e}")
                import traceback
                traceback.print_exc()
                self.after(0, lambda: messagebox.showerror("错误", f"生成失败: {e}"))
                self.after(0, lambda: self.status.set("❌ 生成失败"))
        
        threading.Thread(target=task, daemon=True).start()
    
    def _show_shots_result(self, shots_data: dict):
        """显示分镜并自动提取即梦AI提示词"""
        print("[DEBUG] 开始显示分镜结果")
        
        if 'shots' not in shots_data:
            messagebox.showerror("错误", "分镜数据格式错误")
            return
        
        shots = shots_data['shots']
        self.current_shots = shots
        print(f"[DEBUG] 保存了 {len(shots)} 个分镜到 self.current_shots")
        
        # 显示友好格式的分镜（不是JSON）
        if hasattr(self, 'shots_list'):
            print("[DEBUG] 找到 shots_list，更新显示（友好格式）")
            self.shots_list.config(state="normal")
            self.shots_list.delete("1.0", "end")
            
            # 友好的格式化显示
            for idx, shot in enumerate(shots, 1):
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
                
                if shot.get('notes'):
                    self.shots_list.insert("end", f"📝 备注: {shot.get('notes', '')}\n\n")
                
                self.shots_list.insert("end", "\n")
            
            self.shots_list.config(state="disabled")
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
        
        # 自动切换到分镜标签页
        if hasattr(self, 'director_content_notebook'):
            print("[DEBUG] 切换到分镜标签页")
            self.director_content_notebook.select(1)  # 第2个标签（分镜）
        
        # 自动提取即梦AI提示词（不显示成功提示框，避免重复）
        print("[DEBUG] 开始自动提取即梦AI提示词")
        if hasattr(self, '_extract_all_jimeng_prompts'):
            try:
                self._extract_all_jimeng_prompts(show_message=False)
                print("[DEBUG] 即梦AI提示词提取成功")
            except Exception as e:
                print(f"[ERROR] 提取即梦AI提示词失败: {e}")
        else:
            print("[ERROR] 没有找到 _extract_all_jimeng_prompts 方法")
        
        # 刷新分镜下拉框（静默刷新，不弹提示框）
        if hasattr(self, '_refresh_shot_combo'):
            print("[DEBUG] 刷新分镜下拉框")
            self._refresh_shot_combo(silent=True)
        
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
