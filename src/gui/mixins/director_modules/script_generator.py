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
                system_prompt = """你是奥斯卡级别的电影编剧，曾为《肖申克的救赎》《盗梦空间》《阿凡达》等大片编写剧本。

【你的核心能力】
1. 将故事**完整、不遗漏**地转换为极具画面感的详细剧本
2. 保持人物外貌、服装的**绝对一致性**描述
3. 动作分解**极其细致**，每个细节都可视化
4. 场景过渡**自然流畅**，连贯性强
5. 对话真实，符合人物性格
6. 环境描述**详尽具体**，达到200-300字标准

【你的工作原则】
- ✅ 完整性 > 简洁性：宁可篇幅长，也不省略任何情节
- ✅ 详细性 > 概括性：每个场景都要充分展开，不能一笔带过
- ✅ 连贯性 > 独立性：场景之间要自然过渡，时间线清晰
- ✅ 一致性 > 变化性：人物外貌服装必须前后一致

【你的禁忌】
- ❌ 绝不省略故事中的任何情节、对话、人物
- ❌ 绝不简化场景描述，每个场景都要完整展开
- ❌ 绝不跳过时间点，每个关键动作都要标注时间
- ❌ 绝不改变人物外貌服装，必须保持一致"""

                user_prompt = f"""请将以下故事**完整、详细、连贯**地转换为专业电影剧本。

【核心要求】（⚠️ 必须严格遵守）

1. **完整性（最最重要！）**：
   - 故事中的**所有情节、人物、对话、细节**都必须体现
   - **绝对不能省略、不能跳过、不能简化、不能概括**任何内容
   - 每个场景都要完整展开，从开始到结束，不能一笔带过
   - 宁可篇幅很长，也绝不遗漏任何细节
   - 如果故事有10个情节，剧本就要有10个完整场景
   
2. **详细性（极其重要！）**：
   - 环境描述必须达到200-300字，包含空间布局、光线、视觉细节、音效、氛围
   - 人物外貌要具体：年龄、身高、体型、脸型、五官特点
   - 服装要详细：上衣、下装、鞋子、配饰的款式、颜色、材质
   - 动作要细致：身体动作、手部动作、面部表情、姿态细节
   - 每个时间点的动作、对话、情绪都要写清楚
   - 可以直接指导演员和摄影师拍摄
   
3. **连贯性**：
   - 场景过渡自然流畅，时间线清晰
   - 因果关系明确，逻辑合理
   - 情绪发展有层次，符合人物性格
   
4. **一致性（绝对要求！）**：
   - 同一人物的外貌、发型、服装在整个剧本中必须**完全一致**
   - 首次出现时详细描述，后续场景引用："穿着场景X中的XXX"
   - 除非剧情明确说明换装，否则服装不能改变

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
请严格按照上述格式，将故事**完整**转换为专业剧本。

⚠️ **特别强调（必须遵守的铁律）**：

1. **完整性铁律**：
   - ❌ 绝不省略故事中的任何情节、对话、人物
   - ❌ 绝不简化场景，每个场景都要完整展开
   - ❌ 绝不跳过细节，所有动作、对话、情绪都要写
   - ✅ 故事有多少情节，剧本就要有多少完整场景
   - ✅ 宁可写得很长很详细，也不要精简概括

2. **详细性铁律**：
   - ✅ 环境描述必须200-300字，不能少
   - ✅ 人物描述必须包含外貌、发型、服装的所有细节
   - ✅ 动作分解必须细致，包含身体、手部、面部、姿态
   - ✅ 每个时间点都要标注，不能跳跃

3. **一致性铁律**：
   - ✅ 同一人物的外貌、服装必须前后完全一致
   - ✅ 首次出现详细描述，后续引用："穿着场景X中的XXX"
   - ❌ 绝不随意改变人物外貌或服装

4. **质量标准**：
   - ✅ 完整性 > 简洁性（宁可长，不可省）
   - ✅ 详细性 > 概括性（宁可细，不可粗）
   - ✅ 具体性 > 抽象性（宁可实，不可虚）
   - ✅ 可视化 > 文字化（宁可画面感，不可文学化）

【最后提醒】
这是一个专业的电影剧本，要能直接指导拍摄。请把每个场景都当作一个独立的拍摄任务，提供足够详细的信息，让导演、演员、摄影师都能清楚知道要拍什么、怎么拍。"""

                # 判断是否需要分段生成
                story_length = len(story_text)
                print(f"📊 故事长度: {story_length} 字符")
                
                # 如果故事超过2500字，使用分段生成（降低阈值，确保质量）
                if story_length > 2500:
                    print("📑 故事较长，启用分段生成模式")
                    self.after(0, lambda: self._generate_script_in_sections(
                        client, system_prompt, story_text, api_key, base_url, model
                    ))
                else:
                    print("📝 使用单次生成模式（流式输出）")
                    # 使用流式生成
                    self.after(0, lambda: self._clear_script_text())
                    
                    full_script = ""
                    for chunk in client.stream([
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ], temperature=0.7):  # 降低temperature，提高稳定性和一致性
                        full_script += chunk
                        self.after(0, lambda text=chunk: self._append_script_text(text))
                    
                    print(f"[OK] 流式生成完成，总长度: {len(full_script)} 字符")
                    
                    # 在主线程更新UI
                    print("[DEBUG] 准备更新状态栏")
                    self.after(0, lambda: self.status.set("专业剧本生成完成"))
                    if hasattr(self, 'header_status_var'):
                        self.after(0, lambda: self.header_status_var.set("完成"))
                    if hasattr(self, 'update_header_status'):
                        self.after(0, lambda: self.update_header_status("剧本生成完成", "✅"))
                    
                    # 自动保存剧本到项目
                    print("[DEBUG] 开始自动保存剧本到项目")
                    if hasattr(self, '_auto_save_script_to_project'):
                        self.after(0, lambda s=full_script: self._auto_save_script_to_project(s))
                
            except Exception as e:
                error_msg = f"生成剧本失败: {str(e)}"
                self.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.after(0, lambda: self.status.set("❌ 剧本生成失败"))
        
        # 在后台线程执行
        threading.Thread(target=task, daemon=True).start()
    
    def _clear_script_text(self):
        """清空剧本文本框"""
        if hasattr(self, 'script_text'):
            self.script_text.config(state="normal")
            self.script_text.delete("1.0", END)
            self.script_text.config(state="disabled")
            
            # 自动切换到剧本标签页
            if hasattr(self, 'director_notebook'):
                self.director_notebook.select(0)
    
    def _append_script_text(self, text: str):
        """流式追加剧本文本（带滚动）"""
        if hasattr(self, 'script_text'):
            self.script_text.config(state="normal")
            self.script_text.insert(END, text)
            self.script_text.see(END)  # 自动滚动到底部
            self.script_text.config(state="disabled")
            self.update_idletasks()  # 强制UI刷新
    
    def _show_script_result(self, script: str):
        """显示生成的剧本（一次性显示）"""
        if hasattr(self, 'script_text'):
            self.script_text.config(state="normal")
            self.script_text.delete("1.0", END)
            self.script_text.insert(END, script)
            self.script_text.config(state="disabled")
            
            # 自动切换到剧本标签页
            if hasattr(self, 'director_notebook'):
                self.director_notebook.select(0)  # 切换到第一个标签（剧本）
    
    def _generate_script_in_sections(self, client, system_prompt, story_text, api_key, base_url, model):
        """分段生成剧本（用于长故事）"""
        print("="*60)
        print("📑 开始分段生成剧本")
        print("="*60)
        
        # 清空文本框
        self._clear_script_text()
        
        # 将故事分成多段（每段约2500字，确保质量和连贯性）
        section_size = 2500
        sections = []
        for i in range(0, len(story_text), section_size):
            sections.append(story_text[i:i+section_size])
        
        print(f"📊 总共分为 {len(sections)} 段，每段约 {section_size} 字")
        
        full_script = ""
        previous_content = ""  # 保存前面生成的内容，用于保持连贯
        
        def generate_section_in_thread(section_idx):
            nonlocal full_script, previous_content
            
            try:
                section_text = sections[section_idx]
                print(f"\n{'='*60}")
                print(f"📝 正在生成第 {section_idx + 1}/{len(sections)} 段剧本")
                print(f"{'='*60}")
                
                # 更新状态
                self.status.set(f"正在生成第 {section_idx + 1}/{len(sections)} 段剧本...")
                if hasattr(self, 'update_header_status'):
                    self.update_header_status(f"生成剧本 {section_idx + 1}/{len(sections)}", "📝")
                
                # 构建连贯性提示
                continuity_hint = ""
                if section_idx > 0:
                    # 提取前文最后800字作为上下文（增加上下文长度，提高连贯性）
                    prev_context = previous_content[-800:] if len(previous_content) > 800 else previous_content
                    continuity_hint = f"""
【前文剧本摘要】（⚠️ 必须仔细阅读，确保连贯！）
...{prev_context}

⚠️ **连贯性要求（极其重要）**：
1. **人物一致性**：
   - 人物外貌、发型、服装必须与前文**完全一致**
   - 如果前文已描述过某人物，直接引用："穿着场景X中的XXX服装"
   - 绝不能改变人物的外貌特征

2. **场景连贯性**：
   - 场景编号必须接续前文（不要重新从场景1开始）
   - 如果前文有未完成的场景，必须先完成该场景
   - 时间线要自然承接，不能跳跃

3. **剧情连贯性**：
   - 剧情要自然承接前文，不要重复前文内容
   - 人物情绪、状态要符合前文发展
   - 场景转场要合理

4. **格式一致性**：
   - 保持与前文相同的格式和详细程度
   - 环境描述、动作分解、情绪描写要同样详细
"""
                
                user_prompt = f"""请将以下故事片段**完整、详细、连贯**地转换为专业电影剧本。

{continuity_hint}

【核心要求】（⚠️ 必须严格遵守）

1. **完整性（最重要！）**：
   - 这段故事中的**所有情节、人物、对话、细节**都必须体现
   - **绝对不能省略、不能跳过、不能简化**任何内容
   - 每个场景都要完整展开，不能一笔带过
   - 宁可篇幅很长，也绝不遗漏细节

2. **详细性（极其重要！）**：
   - 环境描述必须达到200-300字
   - 人物外貌、服装要具体详细
   - 动作分解要细致（身体、手部、面部、姿态）
   - 每个时间点的动作、对话、情绪都要写清楚

3. **连贯性**：
   - 与前文保持连贯，场景过渡自然
   - 时间线清晰，因果关系明确
   - 情绪发展符合前文

4. **一致性（绝对要求！）**：
   - 人物外貌、服装必须与前文**完全一致**
   - 如果前文已描述过，直接引用："穿着场景X中的XXX"
   - 绝不能改变人物特征

【剧本格式】（与前文完全一致）

═══════════════════════════════════════
【场景X】INT/EXT - 具体地点 - 时间段
═══════════════════════════════════════

【环境描述】（200-300字，必须详细）
- 空间布局、光线氛围、视觉细节、环境音效、情绪基调

【人物登场】
- 外貌特征、发型发色、服装造型（详细）、初始状态

【剧情展开】（按时间顺序，动作细致分解）
[时间点 XX:XX] 场景建立/人物动作
动作：具体描述
对话："对话内容"
情绪：情绪描述

【镜头建议】
- 主镜头、拍摄角度、镜头运动、重点捕捉、拍摄要点

【场景结尾】
- 持续时长、转场方式、下一场景

【故事片段 {section_idx + 1}/{len(sections)}】
{section_text}

【开始创作】
请严格按照格式，将这段故事**完整、详细、连贯**地转换为剧本。

⚠️ **特别提醒**：
- ✅ 宁可写得很长很详细，也不要精简
- ✅ 每个场景都要完整展开，不能概括
- ✅ 人物描述必须与前文一致
- ✅ 场景编号要接续前文"""
                
                # 流式生成这一段（降低temperature，提高连贯性和一致性）
                section_script = ""
                for chunk in client.stream([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ], temperature=0.7):
                    section_script += chunk
                    full_script += chunk
                    self.after(0, lambda text=chunk: self._append_script_text(text))
                
                previous_content += section_script
                
                # 添加分段标记
                separator = f"\n\n{'='*60}\n【第 {section_idx + 1} 段完成，继续生成...】\n{'='*60}\n\n"
                if section_idx < len(sections) - 1:
                    self.after(0, lambda text=separator: self._append_script_text(text))
                    full_script += separator
                
                print(f"✅ 第 {section_idx + 1} 段完成，长度: {len(section_script)} 字符")
                
                # 继续生成下一段
                if section_idx < len(sections) - 1:
                    generate_section_in_thread(section_idx + 1)
                else:
                    # 全部完成
                    print(f"\n{'='*60}")
                    print(f"✅ 全部剧本生成完成！总长度: {len(full_script)} 字符")
                    print(f"{'='*60}\n")
                    
                    self.after(0, lambda: self.status.set(f"剧本生成完成（共 {len(sections)} 段）"))
                    if hasattr(self, 'update_header_status'):
                        self.after(0, lambda: self.update_header_status("剧本生成完成", "✅"))
                    
                    # 保存剧本
                    if hasattr(self, '_auto_save_script_to_project'):
                        self.after(0, lambda s=full_script: self._auto_save_script_to_project(s))
                
            except Exception as e:
                error_msg = f"第 {section_idx + 1} 段生成失败: {str(e)}"
                print(f"❌ {error_msg}")
                self.after(0, lambda msg=error_msg: messagebox.showerror("错误", msg))
                self.after(0, lambda: self.status.set(f"❌ 剧本生成失败（第{section_idx + 1}段）"))
        
        # 在后台线程开始生成第一段
        import threading
        threading.Thread(target=lambda: generate_section_in_thread(0), daemon=True).start()

