"""
分镜头列表生成器 - 从剧本生成分镜头列表
"""

from tkinter import messagebox, END
from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize
import json


class ShotListGeneratorMixin:
	"""分镜头生成功能"""
	
	def _on_script_to_shots(self) -> None:
		"""将剧本转换为分镜头列表"""
		print("\n=== 开始生成分镜头 ===")
		
		# 检查剧本控件是否存在
		if not hasattr(self, 'script_text'):
			print("❌ 错误：script_text 控件不存在")
			messagebox.showwarning("提示", "请先生成剧本\n\n（导演页面未正确初始化，请重启应用）")
			return
		
		# 获取剧本内容
		try:
			script_text = self.script_text.get("1.0", END).strip()
			print(f"📝 剧本长度: {len(script_text)} 字符")
		except Exception as e:
			print(f"❌ 获取剧本内容失败: {e}")
			messagebox.showerror("错误", f"无法读取剧本内容：{str(e)}")
			return
		
		if not script_text:
			messagebox.showwarning("提示", "剧本内容为空\n\n请先点击【步骤1】生成剧本")
			return
		
		# 获取API配置
		try:
			api_key = _sanitize(self.api_key.get()) if hasattr(self, 'api_key') else ""
			base_url = _sanitize(self.base_url.get()) if hasattr(self, 'base_url') else ""
			model = _sanitize(self.model.get()) if hasattr(self, 'model') else ""
			
			print(f"🔑 API Key: {'已配置' if api_key else '未配置'}")
			print(f"🌐 Base URL: {base_url or '未配置'}")
			print(f"🤖 Model: {model or '未配置'}")
		except Exception as e:
			print(f"❌ 获取API配置失败: {e}")
			messagebox.showerror("错误", f"无法读取API配置：{str(e)}")
			return
		
		if not api_key:
			messagebox.showerror("错误", "请先配置API Key\n\n请到【故事生成】→【配置】页面配置API")
			return
		
		if not base_url:
			messagebox.showwarning("警告", "Base URL 未配置，将使用默认值")
			base_url = "https://api.deepseek.com"
		
		if not model:
			messagebox.showwarning("警告", "Model 未配置，将使用默认值")
			model = "deepseek-chat"
		
		def task():
			try:
				self.status.set("🎬 正在生成分镜头列表...")
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成分镜头...", "🎬"))
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=base_url,
					model=model,
				)
				
				# 生成分镜头 - 超详细版
				instruction = """
你是好莱坞顶级分镜师。请将剧本分解为**可视化的详细分镜头**，每个分镜必须能直接生成连贯的图片。

## 分镜头要求（极度详细）

### 每个分镜必须包含：

1. **所属场景编号** - 标注来自剧本的哪个场景
2. **镜头编号** - Shot #1, #2...
3. **镜头类型**：
   - 远景(Extreme Wide Shot) - 展示整体环境
   - 全景(Wide Shot) - 人物全身+环境
   - 中景(Medium Shot) - 人物腰部以上
   - 近景(Close-up) - 人物面部
   - 特写(Extreme Close-up) - 眼睛、手等细节
   
4. **场景位置** - 精确位置（如"教室第三排靠窗"）

5. **视觉描述** (150-250字，尽可能详细) - 必须包含：
   - 环境细节：墙壁颜色材质、地板纹理、家具品牌款式、装饰物品
   - 光线：来源方向、强度数值、颜色色温、阴影形状长度
   - 色调：冷/暖色调、明暗对比度、主色调和辅助色
   - 天气/时间：晴/阴/雨/雪，精确到小时分钟
   - 前景/中景/背景：每一层有什么物品，位置，大小
   - 质感：粗糙/光滑、新旧程度、材质反光

6. **人物详细信息** - 每个人物必须描述：
   - 完整外貌：年龄、发型、发色、脸型、眼睛、服装
   - 精确表情：眼神、嘴角、眉毛、脸部肌肉
   - 具体姿势：站/坐/蹲、手的位置、头的角度
   - 细微动作：眨眼、咬唇、握拳、呼吸

7. **动作描述** (80-150字，极度详细)：
   - 开始状态（身体各部位的初始位置）
   - 动作过程（分解为3-5个连续步骤，每步骤1-2秒）
   - 中间变化（表情、呼吸、重心转移）
   - 结束状态（最终姿态和表情）
   - 速度节奏：快速/缓慢/突然/有停顿
   - 力度：轻柔/用力/犹豫/果断

8. **情绪表达**：
   - 主要情绪（如"紧张"）
   - 情绪程度（轻微/明显/强烈）
   - 身体语言体现

9. **服装道具** - 必须前后一致：
   - 每件衣服的颜色、款式
   - 配饰（眼镜、手表、包等）
   - 手持物品

10. **镜头运动**：
    - 固定/推进/拉远/摇移/跟随
    - 角度：平视/俯视/仰视
    - 焦距：广角/标准/长焦

11. **场景连贯性**：
    - 与上一镜头的关系
    - 时间连续/跳跃
    - 空间变化

**输出格式（严格JSON）：**
```json
{
  "shots": [
    {
      "scene_id": "场景1",
      "shot_number": 1,
      "shot_type": "Wide Shot",
      "location": "高中教室 - 第三排靠窗位置",
      "visual_description": "清晨6点50分的高中教室，初升的金色阳光以45度角从东侧三扇大窗户斜射进来，在米白色瓷砖地板上投下三道长达4米的矩形光斑，边缘清晰锐利。32套棕色木质课桌椅整齐排列成8行4列，每张桌面都反射着微弱光泽，桌角有岁月磨损的痕迹。黑板墨绿色，长4米高1.2米，上面残留着昨日的白色粉笔字迹「明日测验」，粉笔槽里散落着彩色粉笔头。窗台上摆放着6盆绿萝，叶片油亮，泥土微湿。空气中浮动着细小的灰尘颗粒在光柱中缓慢旋转闪烁，营造出宁静的氛围。教室后墙贴着红色公告栏，钉着各种通知单和成绩表。前景是木质讲台，高0.8米，上面放着一本翻开的教案和一支红笔。天花板是白色，有8盏日光灯管，此刻未开启。墙壁是浅蓝色，贴着名人名言海报。",
      "characters": ["张强"],
      "character_details": {
        "张强": {
          "appearance": "17岁男生，身高约172cm，短寸黑发，浓眉大眼，国字脸，皮肤略显苍白",
          "expression": "眼神迷茫空洞，嘴唇紧闭，眉头微微皱起，眼圈发红显得疲惫，面无表情看向窗外",
          "posture": "站在教室门口，身体略微前倾，双手自然垂在身侧，肩膀有些耷拉",
          "clothing": "白色短袖衬衫校服（领口第一颗扣子解开），深蓝色校裤，黑色布鞋，背着深灰色双肩包"
        }
      },
      "action": "【0-1秒】张强的右手抬起，五指微微张开，手掌接触到半掩的深棕色木门，指尖感受到门板的凉意。【1-2秒】他缓慢用力推门，门轴发出轻微的吱呀声，门板以每秒20度的速度向内打开。【2-4秒】张强站在门口停顿，双眼从左向右缓慢扫视教室，眼神空洞迷茫，视线依次掠过黑板-讲台-课桌-窗户，眼球转动但焦点涣散。【4-5秒】他迈出右脚，脚掌重重落在地板上，膝盖微曲，重心前移。【5-6秒】左脚跟上，整个人走进教室，肩膀略微下垂显得疲惫。【6-7秒】头部向右转动约30度，目光穿过窗户投向远处的操场，眼神中闪过一丝复杂的情绪。",
      "emotion": "孤独、疲惫、茫然（程度：明显）",
      "props": ["双肩包（灰色，左肩带略松）", "教室门（半开）", "阳光光斑"],
      "lighting": "自然光，色温5500K，来自右侧窗户，高对比度，人物半身在阴影中半身被照亮",
      "atmosphere": "寂静、略带压抑、清晨的宁静感",
      "camera": {
        "movement": "固定镜头",
        "angle": "平视略偏低（与人物眼睛齐平再低5度）",
        "lens": "35mm广角，景深f/2.8"
      },
      "continuity": "故事开场，确立主角和环境氛围，为后续情节铺垫"
    }
  ]
}
```

## 特别要求（关键！）

1. **连贯性第一（最重要！）**：
   - 人物外貌、服装在所有镜头中**完全一致**（发型、服装颜色、配饰）
   - 场景元素（如教室布局、家具位置）**绝对不变**
   - 光线变化要符合时间推移（如早上→中午，阴影位置变化）
   - 道具和背景物品要反复出现，强化记忆点
   - **每个镜头的描述要引用上一镜头的元素，形成连贯**

2. **可画面化（精确到像素）**：
   - 每个描述必须像给专业画师的精确指令
   - 细节具体到：颜色RGB值、位置坐标、大小尺寸
   - 避免任何抽象描述，全部用具体视觉元素
   - 物品要标注材质、新旧、反光度

3. **情节推进**：
   - 每个镜头推动故事发展
   - 镜头间有明确因果关系
   - 情绪有起伏变化

4. **镜头节奏**：
   - 关键情节用近景/特写
   - 环境交代用全景
   - 情绪高潮用特写
   - **镜头数量不限，根据故事需要，越详细越好**

5. **表情动作**：
   - 表情变化要细致（如"眼神从迷茫转为坚定"）
   - 动作要分解步骤
   - 肢体语言要体现情绪
   - **每个细微动作都要描述，不要省略任何细节**

剧本内容：
"""
				
				response = client.chat([
					{"role": "system", "content": "你是专业的分镜师。你必须且只能输出JSON格式，绝对不要输出任何解释、前言、后记或markdown标记。直接输出{开头}结尾的纯JSON。"},
					{"role": "user", "content": instruction + "\n\n" + script_text + "\n\n记住：只输出JSON，从{开始到}结束，不要任何其他内容！"}
				], temperature=0.5)
				
				# 解析JSON - 增强容错
				try:
					print(f"\n=== AI返回内容（前500字）===\n{response[:500]}\n")
					
					# 清理可能的markdown代码块标记
					import re
					response = re.sub(r'```json\s*', '', response)
					response = re.sub(r'```\s*', '', response)
					response = response.strip()
					
					# 尝试多种方式提取JSON
					shots_data = None
					
					# 方法1: 查找完整的JSON对象
					json_pattern = r'\{[\s\S]*"shots"[\s\S]*\}'
					json_match = re.search(json_pattern, response)
					
					if json_match:
						json_str = json_match.group()
						try:
							shots_data = json.loads(json_str)
						except:
							# 尝试清理可能的问题字符
							json_str = json_str.replace('\n', ' ').replace('\r', '')
							shots_data = json.loads(json_str)
					else:
						# 方法2: 简单的开始和结束查找
						json_start = response.find('{')
						json_end = response.rfind('}') + 1
						if json_start != -1 and json_end > json_start:
							json_str = response[json_start:json_end]
							shots_data = json.loads(json_str)
					
					if shots_data and 'shots' in shots_data:
						print(f"✅ 成功解析JSON，共 {len(shots_data['shots'])} 个分镜")
						# 打印第一个分镜的结构用于调试
						if shots_data['shots']:
							print(f"第一个分镜的字段: {list(shots_data['shots'][0].keys())}")
						self.after(0, self._show_shots_result, shots_data)
					else:
						raise ValueError("JSON中没有找到shots字段")
						
				except json.JSONDecodeError as e:
					print(f"JSON解析错误: {str(e)}")
					print(f"尝试解析的内容:\n{response[:1000]}")
					self.after(0, lambda: messagebox.showerror("错误", f"分镜头格式错误：{str(e)}\n请查看控制台输出"))
				except Exception as e:
					print(f"处理错误: {str(e)}")
					self.after(0, lambda: messagebox.showerror("错误", f"处理失败：{str(e)}"))
				
			except Exception as e:
				self.after(0, lambda: messagebox.showerror("错误", f"生成分镜头失败: {str(e)}"))
			finally:
				self.status.set("✅ 分镜头生成完成")
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("完成", "✅"))
		
		import threading
		threading.Thread(target=task, daemon=True).start()
	
	def _show_shots_result(self, shots_data: dict) -> None:
		"""显示分镜头结果"""
		if not hasattr(self, 'shots_list'):
			shots_text = f"共生成 {len(shots_data.get('shots', []))} 个分镜头"
			messagebox.showinfo("结果", shots_text)
		else:
			# 保存分镜头数据
			self.current_shots = shots_data.get('shots', [])
			
			# 在界面上显示
			self.shots_list.config(state="normal")
			self.shots_list.delete("1.0", END)
			
			for shot in self.current_shots:
				shot_num = shot.get('shot_number', 0)
				scene_id = shot.get('scene_id', '未知场景')
				shot_type = shot.get('shot_type', '未知类型')
				location = shot.get('location', shot.get('scene_description', '未知位置'))
				
				# 处理visual_description（可能在不同字段）
				visual_desc = shot.get('visual_description', '') or shot.get('scene_description', '')
				
				# 处理characters（可能是列表或字符串）
				chars = shot.get('characters', [])
				if isinstance(chars, list):
					characters = ', '.join(chars) if chars else '无'
				else:
					characters = str(chars) if chars else '无'
				
				# 处理action
				action = shot.get('action', '')
				
				# 构建显示文本
				shot_info = f"【镜头 {shot_num}】{scene_id} - {shot_type}\n"
				if location:
					shot_info += f"位置: {location[:60]}{'...' if len(location) > 60 else ''}\n"
				if characters != '无':
					shot_info += f"人物: {characters}\n"
				if visual_desc:
					shot_info += f"画面: {visual_desc[:100]}{'...' if len(visual_desc) > 100 else ''}\n"
				if action:
					shot_info += f"动作: {action[:80]}{'...' if len(action) > 80 else ''}\n"
				shot_info += "\n"
				
				self.shots_list.insert(END, shot_info)
			
			self.shots_list.config(state="disabled")
			
			# 更新分镜选择下拉框 - 使用after确保在主线程中执行
			def update_combo():
				if hasattr(self, 'shot_select_combo'):
					shot_options = ["全部分镜"] + [
						f"分镜{s.get('shot_number', i+1)} - {s.get('scene_id', '场景')} - {s.get('shot_type', '未知')}"
						for i, s in enumerate(self.current_shots)
					]
					try:
						self.shot_select_combo['values'] = shot_options
						self.shot_select_combo.current(0)
						self.shot_select_combo.update_idletasks()
						print(f"✅ 已更新分镜选择下拉框，共 {len(self.current_shots)} 个分镜")
						print(f"下拉框选项: {shot_options[:3]}...")
					except Exception as e:
						print(f"❌ 更新下拉框失败: {str(e)}")
				else:
					print("⚠️ 警告：未找到 shot_select_combo 控件")
			
			# 延迟执行确保UI线程
			self.after(100, update_combo)
			
			messagebox.showinfo("成功", f"生成了 {len(self.current_shots)} 个分镜头\n\n请查看下拉框选择分镜")
