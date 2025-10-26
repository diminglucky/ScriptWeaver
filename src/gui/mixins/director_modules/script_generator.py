"""
剧本生成器 - 将故事转换为详细的电影剧本

专业功能：
- 完整故事转换
- 详细场景描述
- 人物外貌服装固定
- 动作分解细致
- 连贯性保证
"""

import tkinter as tk
from tkinter import messagebox, END
import threading

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize


class ScriptGeneratorMixin:
    """剧本生成器 Mixin - 专业级故事到剧本转换"""
    
    def _on_story_to_script(self):
        """生成剧本 - 从故事文本转换为专业电影剧本"""
        
        print("=" * 60)
        print("📝 开始生成剧本")
        print("=" * 60)
        
        try:
            # 获取故事内容
            if not hasattr(self, 'output'):
                messagebox.showerror("错误", "未找到故事文本框\n请确保在「故事生成」页面生成了故事")
                print("❌ 错误：未找到 self.output")
                return
            
            story_text = self.output.get("1.0", END).strip()
            print(f"📖 故事文本长度: {len(story_text)} 字符")
            
            if not story_text:
                messagebox.showwarning("提示", "请先在「故事生成」页面生成或粘贴故事内容")
                print("⚠️ 警告：故事文本为空")
                return
        except Exception as e:
            messagebox.showerror("错误", f"读取故事失败: {str(e)}")
            print(f"❌ 异常：{e}")
            import traceback
            traceback.print_exc()
            return
        
        # 获取API配置
        try:
            api_key = _sanitize(self.api_key.get()) if hasattr(self, 'api_key') else ""
            base_url = _sanitize(self.base_url.get()) if hasattr(self, 'base_url') else "https://api.deepseek.com"
            model = _sanitize(self.model.get()) if hasattr(self, 'model') else "deepseek-chat"
            
            print(f"🔑 API配置:")
            print(f"  - API Key: {'已设置' if api_key else '未设置'}")
            print(f"  - Base URL: {base_url}")
            print(f"  - Model: {model}")
            
            if not api_key:
                messagebox.showerror("错误", "请先在「故事生成-配置」页面配置 API Key")
                print("❌ 错误：API Key 未设置")
                return
        except Exception as e:
            messagebox.showerror("错误", f"读取API配置失败: {str(e)}")
            print(f"❌ 异常：{e}")
            import traceback
            traceback.print_exc()
            return
        
        # 更新状态
        print("[DEBUG] 准备更新状态...")
        if hasattr(self, 'status'):
            print(f"[DEBUG] 找到status变量: {self.status}")
            self.status.set("正在将故事转换为专业剧本...")
            print("[DEBUG] 状态已更新")
        else:
            print("[DEBUG] 没有找到status变量！")
        
        # 同时更新header状态（如果有）
        if hasattr(self, 'header_status_var'):
            print("[DEBUG] 找到header_status_var")
            self.header_status_var.set("生成剧本中...")
        
        if hasattr(self, 'update_header_status'):
            print("[DEBUG] 调用update_header_status")
            self.update_header_status("生成剧本中...", "编写")
        
        def task():
            try:
                client = DeepSeekClient(api_key=api_key, base_url=base_url, model=model)
                
                # 🎬 专业级剧本生成提示词
                system_prompt = """你是奥斯卡级别的电影编剧，曾为《肖申克的救赎》《盗梦空间》《阿凡达》等大片编写剧本。你擅长：
1. 将故事完整转换为极具画面感的详细剧本
2. 保持人物外貌、服装的一致性描述
3. 动作分解细致，每个细节都可视化
4. 场景过渡自然流畅，连贯性强
5. 对话真实，符合人物性格"""

                user_prompt = f"""请将以下故事**完整、详细、连贯**地转换为专业电影剧本。

【核心要求】
1. **完整性**：故事中的所有情节、人物、对话都要体现，不能遗漏任何内容
2. **连贯性**：场景过渡自然流畅，时间线清晰，因果关系明确
3. **详细性**：环境、人物、动作、情绪都要具体描述，可直接指导拍摄
4. **一致性**：人物外貌、服装在整个剧本中必须保持一致

【剧本格式】

═══════════════════════════════════════
【场景X】INT/EXT - 具体地点 - 时间段
═══════════════════════════════════════

【环境描述】（200-300字）
- 空间布局：房间大小、结构、家具摆放、重点道具位置
- 光线氛围：主光源位置、光线强度、明暗分布、色温（冷/暖）
- 视觉细节：墙面装饰、地面材质、窗外景色、远近景物
- 环境音效：背景声音（如风声、车声、音乐）
- 情绪基调：整体氛围感受（温馨/压抑/紧张/轻松等）

【人物登场】
人物1：[姓名]
  - 外貌特征（固定）：年龄段、身高体型、脸型（圆/方/瓜子）、五官特点（眼睛大小、鼻梁高低、嘴唇薄厚）
  - 发型发色（固定）：长度（长发/短发/中长发）、造型（直发/卷发/马尾辫）、颜色（黑色/棕色/其他）
  - 服装造型（固定）：
    * 上衣：款式（衬衫/T恤/外套）、颜色、材质、细节（纽扣/拉链/图案）
    * 下装：款式（裤子/裙子）、颜色、长度
    * 鞋子：类型（运动鞋/皮鞋/高跟鞋）、颜色
    * 配饰：眼镜、项链、手表、包包等
  - 初始状态：进入场景时的表情、姿态、位置、正在做什么

人物2：[姓名]
  （同上格式，确保首次出现时描述详细，后续场景保持一致）

【剧情展开】（按时间顺序，动作细致分解）

[时间点 00:00] 场景建立
动作：镜头如何展现环境，观众首先看到什么
描述：用具体的视觉语言描述画面

[时间点 00:05] [人物名]的动作
动作：[人物]具体做什么
  - 身体动作：站/坐/走，移动方向，动作幅度
  - 手部动作：拿/放/指/握，左右手分别做什么
  - 面部表情：眉毛（皱/扬）、眼神（锐利/柔和）、嘴角（上扬/下垂）
  - 姿态细节：身体朝向、重心、肢体语言
对话：（如有）"对话内容"
  - 语气：平静/激动/低沉/颤抖/讽刺等
  - 音量：耳语/正常/提高/喊叫
  - 节奏：快速/缓慢/停顿
情绪：[人物]的内心情绪
  - 主情绪：焦虑/喜悦/恐惧/愤怒/悲伤等
  - 强度：轻微/明显/强烈/爆发
  - 变化：情绪如何发展

[时间点 00:10] [人物名]的反应
动作：另一人物对前面动作/对话的反应
（继续按时间顺序展开，确保：）
- 每个动作都有明确的时间点
- 动作之间的因果关系清晰
- 对话和动作配合自然
- 情绪发展有逻辑性

[时间点 XX:XX] 场景高潮
（剧情冲突点，情绪最强烈的时刻）

[时间点 YY:YY] 场景结尾
（为下一场景做铺垫）

【镜头建议】
- 主镜头：Wide Shot（全景）/Medium Shot（中景）/Close-up（特写）
- 拍摄角度：平视/俯视15°/俯视45°/仰视15°/仰视45°
- 镜头运动：固定/推进/拉远/横摇/纵摇/跟随/环绕
- 重点捕捉：需要特写的细节（如：手部动作、眼神交流、道具特写）
- 拍摄要点：光线运用、景深控制、构图方式

【场景结尾】
- 持续时长：建议XX秒 - XX秒
- 转场方式：切（硬切）/淡入淡出/叠化/划像/其他特效
- 下一场景：简要说明下一场景的时间、地点，确保连贯

═══════════════════════════════════════

【剧本编写规范】

1. **人物一致性**（极其重要）
   - 同一人物的外貌、发型、服装在整个剧本中**必须完全一致**
   - 首次登场时要详细描述，后续场景直接引用："[人物名]穿着场景1中的蓝色衬衫和黑色西裤"
   - 如果换装，必须明确说明原因和时间点（如："回到家后，换上了灰色家居服"）

2. **动作可视化**
   - 避免抽象描述，如"他很生气" ❌
   - 使用具体动作，如"他猛地握紧拳头，眉头紧皱，眼睛瞪大盯着对方" ✅
   - 每个动作都要能在脑海中形成清晰画面

3. **对话自然**
   - 符合人物性格、年龄、身份
   - 有潜台词，不是简单的信息传递
   - 配合动作、表情，增强真实感

4. **场景完整**
   - 每个场景都有明确的开始、发展、高潮、结尾
   - 场景之间的过渡要自然，时间和空间关系要清晰
   - 保持整体故事节奏

5. **时间线清晰**
   - 用明确的时间标记（如：早上7:00、三天后、同时）
   - 闪回、插叙要有明确标注
   - 保持因果逻辑

【故事内容】
{story_text}

【开始创作】
请严格按照上述格式，将故事完整转换为专业剧本。记住：
- 不遗漏任何情节
- 人物描述要一致
- 动作要细致可视化
- 场景要连贯流畅"""

                # 调用AI生成
                print("[DEBUG] 调用API生成剧本...")
                script = client.chat([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ], temperature=0.75)  # 适中的temperature保证创意和稳定性平衡
                
                print(f"[OK] API响应成功，长度: {len(script)} 字符")
                
                # 在主线程更新UI
                print("[DEBUG] 准备更新UI和状态栏")
                self.after(0, self._show_script_result, script)
                self.after(0, lambda: self.status.set("专业剧本生成完成"))
                if hasattr(self, 'header_status_var'):
                    self.after(0, lambda: self.header_status_var.set("完成"))
                if hasattr(self, 'update_header_status'):
                    self.after(0, lambda: self.update_header_status("剧本生成完成", "OK"))
                
                # 自动保存剧本到项目
                print("[DEBUG] 开始自动保存剧本到项目")
                if hasattr(self, '_auto_save_script_to_project'):
                    self.after(0, lambda s=script: self._auto_save_script_to_project(s))
                
            except Exception as e:
                error_msg = f"生成剧本失败: {str(e)}"
                self.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.after(0, lambda: self.status.set("❌ 剧本生成失败"))
        
        # 在后台线程执行
        threading.Thread(target=task, daemon=True).start()
    
    def _show_script_result(self, script: str):
        """显示生成的剧本"""
        if hasattr(self, 'script_text'):
            self.script_text.config(state="normal")
            self.script_text.delete("1.0", END)
            self.script_text.insert(END, script)
            self.script_text.config(state="disabled")
            
            # 自动切换到剧本标签页
            if hasattr(self, 'director_notebook'):
                self.director_notebook.select(0)  # 切换到第一个标签（剧本）

