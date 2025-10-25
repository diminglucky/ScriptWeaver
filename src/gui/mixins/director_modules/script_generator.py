"""
脚本生成器 - 将故事转换为制片级剧本
"""

from tkinter import messagebox, END
from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize


class ScriptGeneratorMixin:
	"""脚本生成功能"""
	
	def _on_story_to_script(self) -> None:
		"""将故事转换为剧本"""
		story_text = self.output.get("1.0", END).strip()
		if not story_text:
			messagebox.showwarning("提示", "请先生成或粘贴故事内容")
			return
		
		# 获取API配置
		api_key = _sanitize(self.api_key.get())
		base_url = _sanitize(self.base_url.get())
		model = _sanitize(self.model.get())
		
		if not api_key:
			messagebox.showerror("错误", "请先配置故事生成的API Key")
			return
		
		def task():
			try:
				self.status.set("📝 正在将故事转换为剧本...")
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("转换为剧本中...", "📝"))
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=base_url,
					model=model,
				)
				
				# 生成剧本 - 极致详细版
				instruction = """
你是好莱坞顶级编剧和导演。请将以下故事转换为**电影级超详细剧本**，要求图片化呈现每一个细节。

## 剧本格式要求（必须严格遵守）

### 场景标题格式
【场景X】INT/EXT - 具体地点 - 时间段
示例：【场景1】INT - 办公室 - 清晨7点

### 每个场景必须包含：

1. **环境描述**（尽可能详细，100-200字）
   - 具体地点的详细描述（墙壁颜色、地板材质、家具摆放）
   - 光线效果（阳光角度、灯光类型、阴影位置、色温）
   - 氛围感受（紧张、温馨、压抑等，用具体细节体现）
   - 背景音效提示（环境声、音乐情绪）
   - 前景、中景、背景各层次的物品

2. **人物登场**（每个人物单独描述）
   格式：[人物名] - 外貌特征 - 服装 - 表情 - 姿态
   示例：[李明] - 25岁，黑框眼镜，整洁短发 - 蓝色格子衬衫，黑色长裤 - 表情疲惫，眼神呆滞 - 弓着背坐在办公桌前

3. **动作描述**（极度详细，分解每一个小动作，50-100字）
   - 人物的身体动作（起始→过程→结束，要有时间感）
   - 面部表情变化（眼睛、眉毛、嘴角、脸颊肌肉）
   - 手势、眼神、呼吸
   - 移动路径（从A点到B点，速度、姿态）
   - 与物品的互动（触摸、拿起、放下）
   示例：李明缓缓抬起头，眼皮沉重地睁开，揉了揉布满血丝的眼睛。他深深叹了一口气，胸口起伏明显。右手食指和中指有节奏地敲击着键盘，频率从每秒2次逐渐变慢到每秒1次。左手撑着额头，拇指和食指按压着太阳穴。

4. **对话**（如有）
   格式：
   李明："......"（语气：疲惫无奈）
   
5. **镜头建议**
   - 景别：特写/近景/中景/全景/远景
   - 角度：平视/俯视/仰视
   - 运动：固定/推拉/摇移/跟随
   
6. **情绪氛围**
   - 当前情绪基调
   - 情绪转折点（如有）

7. **连贯性提示**
   - 与上一场景的关系
   - 情节推进要点

## 输出要求

1. 每个场景必须包含以上所有元素
2. 描述要具体到可以直接画面呈现
3. 人物的外貌、服装、表情必须前后一致
4. 场景之间要有明确的因果关系和情节推进
5. 重点描述人物的**细微表情变化**和**肢体语言**
6. 环境细节要能体现情节氛围
7. **不要限制字数，越详细越好！每个场景尽可能详细描述**

## 特别注意
- 描述要像给画师的指令一样精确
- 每个动作、表情都要有画面感
- 场景转换要自然连贯
- 重要物品要反复提及以保持一致性

故事内容：
"""
				
				script = client.chat([
					{"role": "system", "content": "你是好莱坞顶级编剧和导演，擅长创作视觉化的详细剧本。每个场景都要像电影画面一样清晰。"},
					{"role": "user", "content": instruction + "\n\n" + story_text}
				], temperature=0.85)
				
				# 显示剧本
				self.after(0, self._show_script_result, script)
				
			except Exception as e:
				self.after(0, lambda: messagebox.showerror("错误", f"生成剧本失败: {str(e)}"))
			finally:
				self.status.set("✅ 剧本转换完成")
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("完成", "✅"))
		
		import threading
		threading.Thread(target=task, daemon=True).start()
	
	def _show_script_result(self, script: str) -> None:
		"""显示剧本结果"""
		if not hasattr(self, 'script_text'):
			messagebox.showinfo("结果", script[:500] + "...\n\n(详细内容已保存)")
		else:
			self.script_text.config(state="normal")
			self.script_text.delete("1.0", END)
			self.script_text.insert(END, script)
			self.script_text.config(state="disabled")
