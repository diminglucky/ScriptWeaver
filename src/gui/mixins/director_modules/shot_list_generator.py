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
                    system_prompt = """你是专业分镜师。输出完整详细的JSON格式分镜脚本。
人物外貌、服装在所有分镜中必须保持一致。
只输出JSON，从{开始到}结尾。"""
                    
                    # 上文人物信息（用于保持一致性）
                    character_context = ""
                    if all_shots:
                        last_shot = all_shots[-1]
                        if 'character_details' in last_shot:
                            character_context = f"\n\n【重要】之前已出现的人物，外貌和服装必须完全一致：\n{json.dumps(last_shot['character_details'], ensure_ascii=False, indent=2)}"
                    
                    user_prompt = f"""将以下剧本片段分解为详细分镜JSON。

格式：
{{
  "shots": [
    {{
      "shot_number": {shot_counter},
      "shot_type": "Wide Shot/Medium Shot/Close-up",
      "location": "详细位置",
      "visual_description": "详细画面描述200-300字：前景、中景、背景、人物位置、光线、色调、构图",
      "characters": ["人物名"],
      "character_details": {{
        "人物名": {{
          "appearance": "外貌（固定）：年龄、体型、脸型、五官",
          "hair": "发型（固定）：长度、造型、颜色",
          "clothing": "服装（固定）：上衣、下装、鞋子、配饰",
          "expression": "表情：眉眼、嘴角、神态",
          "action": "动作：具体在做什么",
          "emotion": "情绪：类型+强度"
        }}
      }},
      "action": "主要动作描述150-200字：谁做什么，动作细节",
      "dialogue": {{"speaker": "人名", "content": "对话", "tone": "语气"}},
      "camera": {{
        "movement": "运镜：固定/推进/拉远/横摇/跟随",
        "angle": "角度：平视/俯视/仰视",
        "lens": "镜头：广角/标准/长焦"
      }},
      "duration": "建议时长",
      "emotion": "整体情绪氛围80字",
      "lighting": "光线设计80字",
      "transition_to_next": "转场方式",
      "jimeng_prompt": "即梦AI提示词150-200字：简洁清晰的场景描述+人物动作+镜头运动，适合直接输入即梦AI生成视频"
    }}
  ]
}}

要求：
1. 人物外貌、发型、服装在所有分镜中保持完全一致
2. 描述详细，每个分镜200-400字
3. 完整覆盖该段所有场景和动作
4. 确保JSON格式完整正确
5. **jimeng_prompt必须生成**：简洁清晰、适合视频生成的提示词，包含：
   - 场景环境（简洁）
   - 人物外貌和动作（关键特征）
   - 镜头运动（如：镜头缓缓推进/固定镜头/跟随拍摄）
   - 情绪氛围
   示例："教室内，阳光透过窗户，一个穿蓝色校服的男生坐在课桌前，低头写作业，表情专注。镜头从侧面缓缓推进。"{character_context}

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
