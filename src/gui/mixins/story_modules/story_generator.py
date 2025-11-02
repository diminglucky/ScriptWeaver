"""Story功能模块"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog, scrolledtext
import tkinter as tk
from tkinter import ttk
import threading
import re
import time
from pathlib import Path
from dotenv import load_dotenv

from src.clients.deepseek_client import DeepSeekClient
# 延迟导入：只在使用时才导入，避免启动时加载 sentence_transformers (3.8秒)
# from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
# from src.kb.search import KnowledgeBaseSearcher, SearchConfig
from src.utils.text import sanitize as _sanitize


class StoryGeneratorMixin:
	"""Story story_generator 功能"""
	
	def on_generate(self) -> None:
		query = self._get_prompt_content()
		if not query:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		
		# 获取选中的故事生成API配置
		selected_api = self.story_gen_api.get() if hasattr(self, 'story_gen_api') else "DeepSeek"
		if selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API预设: {selected_api}")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
			return
		
		# 检查是否使用项目故事库
		use_project_stories = self.use_project_stories.get() if hasattr(self, 'use_project_stories') else False
		
		# 如果启用了项目故事库，确保不使用model_only模式
		if use_project_stories and self.model_only.get():
			self.model_only.set(False)
		
		if self.model_only.get():
			self._generate_model_only(query)
			return
		
		# 如果启用了项目故事库，检查是否需要构建
		if use_project_stories:
			index_path = Path(self.index_dir.get()) / "kb.index"
			if not index_path.exists():
				if messagebox.askyesno("提示", "项目故事知识库未构建，是否现在构建？\n\n这将扫描projects目录下的所有story.txt文件并构建索引。"):
					self.on_build_project_stories_kb()
					# 等待构建完成（简单延迟，实际应该用回调）
					import time
					time.sleep(2)
					# 重新检查索引是否存在
					if not (Path(self.index_dir.get()) / "kb.index").exists():
						messagebox.showwarning("提示", "索引构建可能未完成，请稍后再试或手动构建索引")
						return
				else:
					return
		
		need_build = False
		index_path = Path(self.index_dir.get()) / "kb.index"
		if not index_path.exists():
			if messagebox.askyesno("提示", "未找到索引，是否现在根据当前数据目录自动构建？"):
				need_build = True
			else:
				return
		def task():
			try:
				# 延迟导入：只在需要时才加载（避免启动时加载 sentence_transformers）
				from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
				from src.kb.search import KnowledgeBaseSearcher, SearchConfig
				
				# 捕获变量到本地作用域（避免闭包问题）
				api_name = selected_api
				
				self.after(0, lambda: self.set_busy(True))
				status_msg = f"使用 {api_name} 检索素材并生成正文中..."
				self.after(0, lambda msg=status_msg: self.status.set(msg))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("准备生成故事...", "📝"))
				
				load_dotenv()
				if need_build:
					if hasattr(self, 'update_header_status'):
						self.after(0, lambda: self.update_header_status("正在构建索引...", "⏳"))
					cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
					KnowledgeBaseIngestor(cfg).build()
				
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("检索资料中...", "🔍"))
				searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self.index_dir.get()), top_k=self.top_k.get()))
				results = searcher.search(query, self.top_k.get())
				contexts = [c for c, _s, _m in results]
				
				# 使用选中的API配置
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("AI创作故事中...", "📝"))
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				# 等待清空完成再继续
				self.after(0, lambda: self.output.delete("1.0", END))
				time.sleep(0.05)  # 短暂等待UI操作完成
				
				# 检查是否需要分段生成
				target_chars = self.target_chars.get()
				parsed_sections = self._parse_outline_sections(self.current_outline) if self.current_outline else []
				
				# 构建系统提示词（根据是否使用项目故事库调整）
				use_project_stories = self.use_project_stories.get() if hasattr(self, 'use_project_stories') else False
				
				# 获取故事类型
				category = self.category.get() if hasattr(self, 'category') else ""
				category_guidance = self._get_category_guidance(category) if hasattr(self, '_get_category_guidance') else ""
				
				# 检测用户是否明确指定了开头
				explicit_opening = self._extract_explicit_opening(query) if hasattr(self, '_extract_explicit_opening') else None
				
				if use_project_stories and contexts:
					# 构建system_prompt，优先处理用户明确指定的开头
					system_prompt_parts = [
						"🚨🚨🚨 **强制要求：你必须像在跟最好的朋友分享你的亲身经历一样写这个故事！** 🚨🚨🚨\n\n",
					]
					
					# 如果用户明确指定了开头，优先使用用户指定的开头
					if explicit_opening:
						system_prompt_parts.append(
							f"🎯🎯🎯 **用户明确指定的开头（最高优先级！必须严格遵守！）** 🎯🎯🎯\n"
							f"用户明确要求：故事必须以以下内容开头：\n"
							f"【{explicit_opening}】\n\n"
							f"⚠️ 重要：\n"
							f"1. 故事的第一句话必须是：{explicit_opening}\n"
							f"2. 不能添加任何前缀，不能修改这句话\n"
							f"3. 这是用户明确要求的，优先级高于所有其他规则\n"
							f"4. 在这句话之后，再按照下面的要求继续写作\n\n"
						)
					
					system_prompt_parts.append(
						"⚠️⚠️⚠️ **开头的绝对要求（必须严格遵守！）** ⚠️⚠️⚠️\n"
					)
					
					if not explicit_opening:
						system_prompt_parts.append(
							"1. **开头必须符合故事的时代背景和类型**：\n"
							"   ⚠️ 重要：开头必须符合故事发生的时代背景！\n"
							"   ❌ 如果故事发生在70年代、80年代等没有手机的年代，绝对不能用手机相关开头！\n"
							"   ❌ 如果故事发生在乡村、古代等场景，不能用手机相关开头！\n"
							"   ✅ 只有现代城市故事才可以用手机相关开头，且不能千篇一律！\n"
							"2. **开头必须自然、多样、独特，绝对不能千篇一律**：\n"
							"   ❌ 禁止每次都用同一个开头模式（比如每次都\"手机震动\"、每次都\"手机屏幕亮起\"、每次都\"手机响了\"等）\n"
							"   ❌ 禁止任何重复的开头模式！每次都要用完全不同的开头方式！\n"
							"   ✅ 必须多样：每次都要用不同的开头方式，让每个故事的开头都独特自然\n"
							"3. **开头示例（根据时代背景选择）**：\n"
							"   ✅ 现代城市：\"我妈给我打电话\"、\"我收到一条短信\"、\"我推开宿舍门\"、\"那天下雨，我站在车站等车。\"\n"
							"   ✅ 70年代/80年代/乡村：\"那是个夏天的傍晚，我坐在院子里乘凉。\"、\"那是1975年的夏天。\"、\"我推开那扇木门，看见他坐在院子里。\"、\"那时候我还小，每天都要下地干活。\"\n"
							"   ⚠️ 写开头前必须：先判断故事的时代背景，如果70年代/80年代/乡村/古代等，绝对不能用手机相关开头！\n\n"
						)
					else:
						system_prompt_parts.append(
							"⚠️ 注意：用户已明确指定开头，请严格按照用户指定的开头开始，然后自然过渡到后续内容。\n\n"
						)
					
					system_prompt_parts.append(
						"🎯 **核心目标**：像**用户亲身经历写出来的**，不是创作出来的小说。\n"
						"   • 读者要感觉：\"这是他的真实经历，不是编的\"\n"
						"   • 语言要像：真实的人在回忆和讲述自己的经历\n"
						"   • 细节要像：只有亲身经历的人才有的细节\n"
						"   • 情感要像：真实经历过的人才会有的反应\n\n"
						"⚠️ **核心原则**：\n"
						"1. **这是你的亲身经历**：写的时候要问：如果这件事真的发生在我身上，我会怎么跟朋友说？\n"
						"2. **禁止比喻和文学化**：不能用\"像...一样\"、\"飘得像血\"、\"心跳漏了一拍\"等\n"
						"3. **必须像亲身经历**：记忆模糊（\"可能是我记错了\"）、真实时间感（\"那时候我记得\"）、真实情感（\"我当时真的懵了\"）、真实细节（\"我那天穿着那件黑T恤\"）\n"
						"4. **必须口语化**：多用\"说实话\"、\"真的\"、\"可能是我看错了\"（每300字至少用1次）\n"
						"5. **必须简单直接**：\"头发很长\"而不是\"长发垂到腰际\"，\"我当时真的吓到了\"而不是\"全身血液都凉了\"\n"
						"6. **对话必须短**：\"这什么情况？\"而不是\"这到底是什么情况？\"\n\n"
						"🎯 **情节结构优化（必须严格遵守）**：\n"
						"📊 **节奏控制**：\n"
						"• 每200-300字必须有一个小冲突/转折/新信息/悬念（\"钩子\"）\n"
						"• 每500字必须有一个情绪起伏（紧张→舒缓→更紧张，或开心→低落→更开心）\n"
						"• 每800字必须有一个情节推进（事情有进展，不是原地踏步）\n"
						"• 禁止平铺直叙：不能连续500字都没有任何冲突或转折\n\n"
						"🎢 **冲突设计**：\n"
						"• 开篇100字内必须有第一个冲突或悬念（立即抓住读者）\n"
						"• 每个冲突都要有铺垫：重要转折前必须有2-3个细节铺垫\n"
						"• 冲突要有层次：小冲突→中等冲突→大冲突，逐步升级\n"
						"• 冲突要有后果：每个冲突都要有结果，不能不了了之\n"
						"• 冲突要真实：\"他给我打电话，但我没接\"、\"我到了才发现门锁了\"这种真实的小冲突\n\n"
						"🔄 **反转设置**：\n"
						"• 每个故事至少要有1-2个反转（读者意想不到的发展）\n"
						"• 反转必须有铺垫：前面不经意提到的细节，后面成为关键\n"
						"• 反转要合理：既要意外，又要合理（\"原来是...\"）\n"
						"• 反转要真实：\"我以为是A，结果是B\"（真实的反转，不是戏剧化的）\n\n"
						"📈 **情节推进**：\n"
						"• 每段都要推进情节：不能只是描述，要有事情发生\n"
						"• 每段都要有新信息：揭示新事实、新人物、新情况\n"
						"• 每段都要有情感变化：人物情绪要有变化（平静→紧张→恐惧）\n"
						"• 每段都要有行动：人物要有具体行动，不能只是思考\n\n"
						"🎯 **悬念设置**：\n"
						"• 开篇就要有悬念：\"我从来没想过...\"、\"直到那天我才知道...\"\n"
						"• 每300字埋一个悬念：\"我当时还不知道...\"、\"后来我才明白...\"\n"
						"• 悬念要逐步揭示：不要一次性全说出来，要慢慢揭示\n"
						"• 悬念要有答案：每个悬念都要有答案，不能悬而不决\n\n"
						"💎 **细节层次优化**：\n"
						"• **环境细节**：每500字至少3个环境细节（\"那天特别冷\"、\"房间里特别安静\"、\"灯光特别暗\"）\n"
						"• **动作细节**：每300字至少2个动作细节（\"我推开门\"、\"他抬头看我\"、\"我拿出手机\"）\n"
						"• **情感细节**：每400字至少1个情感细节（\"我当时真的懵了\"、\"我那时候心跳特别快\"）\n"
						"• **对话细节**：每500字至少1段对话（推动情节，不是废话）\n\n"
						"💬 **对话优化**：\n"
						"• 对话要短：每句话不超过15字（\"你确定？\"、\"我也不知道\"）\n"
						"• 对话要有信息量：每句话都要推进情节或揭示人物\n"
						"• 对话要有潜台词：\"你觉得呢？\"（暗示不确定）、\"好吧\"（暗示妥协）\n"
						"• 对话要有冲突：\"不行\"、\"为什么？\"、\"因为...\"\n\n"
						"💭 **情感递进**：\n"
						"• 情感要有变化：不能一直保持同一情绪（平静→紧张→恐惧→震惊）\n"
						"• 情感要有层次：\"我当时有点紧张\"→\"我那时候心跳特别快\"→\"我当时真的吓到了\"\n"
						"• 情感要真实：\"我当时真的懵了\"、\"说实话，我现在想起来还后怕\"\n"
						"• 情感要有原因：每个情感变化都要有明确的原因\n\n"
						f"{category_guidance}"
						"💡 特别提示：系统已为你检索到相关的优秀参考故事。学习它们的真实感、口语化表达，但创造出全新的真实故事。\n\n"
						"⚠️ **最后提醒**：\n"
					)
					
					if explicit_opening:
						system_prompt_parts.append(
							f"1. **最高优先级：故事的第一句话必须是：{explicit_opening}（用户明确要求，必须严格遵守！）**\n"
							"2. **开头绝对不能千篇一律！**每次都要用不同的开头方式！\n"
							"3. 写每一句话前都要问：如果这件事真的发生在我身上，我会怎么跟朋友说？这句话我会说给朋友听吗？如果不会，改！"
						)
					else:
						system_prompt_parts.append(
							"1. **开头必须符合故事的时代背景！**如果故事发生在70年代/80年代/乡村/古代等，绝对不能用手机相关开头！\n"
							"2. **开头绝对不能千篇一律！**每次都要用不同的开头方式！\n"
							"3. 写每一句话前都要问：如果这件事真的发生在我身上，我会怎么跟朋友说？这句话我会说给朋友听吗？如果不会，改！"
						)
					
					system_prompt = "".join(system_prompt_parts)
				else:
					# 构建system_prompt，优先处理用户明确指定的开头
					system_prompt_parts = [
						"🚨🚨🚨 **强制要求：你必须像在跟最好的朋友分享你的亲身经历一样写这个故事！** 🚨🚨🚨\n\n",
					]
					
					# 如果用户明确指定了开头，优先使用用户指定的开头
					if explicit_opening:
						system_prompt_parts.append(
							f"🎯🎯🎯 **用户明确指定的开头（最高优先级！必须严格遵守！）** 🎯🎯🎯\n"
							f"用户明确要求：故事必须以以下内容开头：\n"
							f"【{explicit_opening}】\n\n"
							f"⚠️ 重要：\n"
							f"1. 故事的第一句话必须是：{explicit_opening}\n"
							f"2. 不能添加任何前缀，不能修改这句话\n"
							f"3. 这是用户明确要求的，优先级高于所有其他规则\n"
							f"4. 在这句话之后，再按照下面的要求继续写作\n\n"
						)
					
					system_prompt_parts.append(
						"⚠️⚠️⚠️ **开头的绝对要求（必须严格遵守！）** ⚠️⚠️⚠️\n"
					)
					
					if not explicit_opening:
						system_prompt_parts.append(
							"1. **开头必须符合故事的时代背景和类型**：\n"
							"   ⚠️ 重要：开头必须符合故事发生的时代背景！\n"
							"   ❌ 如果故事发生在70年代、80年代等没有手机的年代，绝对不能用手机相关开头！\n"
							"   ❌ 如果故事发生在乡村、古代等场景，不能用手机相关开头！\n"
							"   ✅ 只有现代城市故事才可以用手机相关开头，且不能千篇一律！\n"
							"2. **开头必须自然、多样、独特，绝对不能千篇一律**：\n"
							"   ❌ 禁止每次都用同一个开头模式（比如每次都\"手机震动\"、每次都\"手机屏幕亮起\"、每次都\"手机响了\"等）\n"
							"   ❌ 禁止任何重复的开头模式！每次都要用完全不同的开头方式！\n"
							"   ✅ 必须多样：每次都要用不同的开头方式，让每个故事的开头都独特自然\n"
							"3. **开头示例（根据时代背景选择）**：\n"
							"   ✅ 现代城市：\"我妈给我打电话\"、\"我收到一条短信\"、\"我推开宿舍门\"、\"那天下雨，我站在车站等车。\"\n"
							"   ✅ 70年代/80年代/乡村：\"那是个夏天的傍晚，我坐在院子里乘凉。\"、\"那是1975年的夏天。\"、\"我推开那扇木门，看见他坐在院子里。\"、\"那时候我还小，每天都要下地干活。\"\n"
							"   ⚠️ 写开头前必须：先判断故事的时代背景，如果70年代/80年代/乡村/古代等，绝对不能用手机相关开头！\n\n"
						)
					else:
						system_prompt_parts.append(
							"⚠️ 注意：用户已明确指定开头，请严格按照用户指定的开头开始，然后自然过渡到后续内容。\n\n"
						)
					
					system_prompt_parts.append(
						"🎯 **核心目标**：像**用户亲身经历写出来的**，不是创作出来的小说。\n"
						"   • 读者要感觉：\"这是他的真实经历，不是编的\"\n"
						"   • 语言要像：真实的人在回忆和讲述自己的经历\n"
						"   • 细节要像：只有亲身经历的人才有的细节\n"
						"   • 情感要像：真实经历过的人才会有的反应\n\n"
						"⚠️ **核心原则**：\n"
						"1. **这是你的亲身经历**：写的时候要问：如果这件事真的发生在我身上，我会怎么跟朋友说？\n"
						"2. **禁止比喻和文学化**：不能用\"像...一样\"、\"飘得像血\"、\"心跳漏了一拍\"等\n"
						"3. **必须像亲身经历**：记忆模糊（\"可能是我记错了\"）、真实时间感（\"那时候我记得\"）、真实情感（\"我当时真的懵了\"）、真实细节（\"我那天穿着那件黑T恤\"）\n"
						"4. **必须口语化**：多用\"说实话\"、\"真的\"、\"可能是我看错了\"（每300字至少用1次）\n"
						"5. **必须简单直接**：\"头发很长\"而不是\"长发垂到腰际\"，\"我当时真的吓到了\"而不是\"全身血液都凉了\"\n"
						"6. **对话必须短**：\"这什么情况？\"而不是\"这到底是什么情况？\"\n\n"
						"🎯 **情节结构优化（必须严格遵守）**：\n"
						"📊 **节奏控制**：\n"
						"• 每200-300字必须有一个小冲突/转折/新信息/悬念（\"钩子\"）\n"
						"• 每500字必须有一个情绪起伏（紧张→舒缓→更紧张，或开心→低落→更开心）\n"
						"• 每800字必须有一个情节推进（事情有进展，不是原地踏步）\n"
						"• 禁止平铺直叙：不能连续500字都没有任何冲突或转折\n\n"
						"🎢 **冲突设计**：\n"
						"• 开篇100字内必须有第一个冲突或悬念（立即抓住读者）\n"
						"• 每个冲突都要有铺垫：重要转折前必须有2-3个细节铺垫\n"
						"• 冲突要有层次：小冲突→中等冲突→大冲突，逐步升级\n"
						"• 冲突要有后果：每个冲突都要有结果，不能不了了之\n"
						"• 冲突要真实：\"他给我打电话，但我没接\"、\"我到了才发现门锁了\"这种真实的小冲突\n\n"
						"🔄 **反转设置**：\n"
						"• 每个故事至少要有1-2个反转（读者意想不到的发展）\n"
						"• 反转必须有铺垫：前面不经意提到的细节，后面成为关键\n"
						"• 反转要合理：既要意外，又要合理（\"原来是...\"）\n"
						"• 反转要真实：\"我以为是A，结果是B\"（真实的反转，不是戏剧化的）\n\n"
						"📈 **情节推进**：\n"
						"• 每段都要推进情节：不能只是描述，要有事情发生\n"
						"• 每段都要有新信息：揭示新事实、新人物、新情况\n"
						"• 每段都要有情感变化：人物情绪要有变化（平静→紧张→恐惧）\n"
						"• 每段都要有行动：人物要有具体行动，不能只是思考\n\n"
						"🎯 **悬念设置**：\n"
						"• 开篇就要有悬念：\"我从来没想过...\"、\"直到那天我才知道...\"\n"
						"• 每300字埋一个悬念：\"我当时还不知道...\"、\"后来我才明白...\"\n"
						"• 悬念要逐步揭示：不要一次性全说出来，要慢慢揭示\n"
						"• 悬念要有答案：每个悬念都要有答案，不能悬而不决\n\n"
						"💎 **细节层次优化**：\n"
						"• **环境细节**：每500字至少3个环境细节（\"那天特别冷\"、\"房间里特别安静\"、\"灯光特别暗\"）\n"
						"• **动作细节**：每300字至少2个动作细节（\"我推开门\"、\"他抬头看我\"、\"我拿出手机\"）\n"
						"• **情感细节**：每400字至少1个情感细节（\"我当时真的懵了\"、\"我那时候心跳特别快\"）\n"
						"• **对话细节**：每500字至少1段对话（推动情节，不是废话）\n\n"
						"💬 **对话优化**：\n"
						"• 对话要短：每句话不超过15字（\"你确定？\"、\"我也不知道\"）\n"
						"• 对话要有信息量：每句话都要推进情节或揭示人物\n"
						"• 对话要有潜台词：\"你觉得呢？\"（暗示不确定）、\"好吧\"（暗示妥协）\n"
						"• 对话要有冲突：\"不行\"、\"为什么？\"、\"因为...\"\n\n"
						"💭 **情感递进**：\n"
						"• 情感要有变化：不能一直保持同一情绪（平静→紧张→恐惧→震惊）\n"
						"• 情感要有层次：\"我当时有点紧张\"→\"我那时候心跳特别快\"→\"我当时真的吓到了\"\n"
						"• 情感要真实：\"我当时真的懵了\"、\"说实话，我现在想起来还后怕\"\n"
						"• 情感要有原因：每个情感变化都要有明确的原因\n\n"
						f"{category_guidance}"
						"⚠️ **最后提醒**：\n"
					)
					
					if explicit_opening:
						system_prompt_parts.append(
							f"1. **最高优先级：故事的第一句话必须是：{explicit_opening}（用户明确要求，必须严格遵守！）**\n"
							"2. **开头绝对不能千篇一律！**每次都要用不同的开头方式！\n"
							"3. 写每一句话前都要问：如果这件事真的发生在我身上，我会怎么跟朋友说？这句话我会说给朋友听吗？如果不会，改！"
						)
					else:
						system_prompt_parts.append(
							"1. **开头必须符合故事的时代背景！**如果故事发生在70年代/80年代/乡村/古代等，绝对不能用手机相关开头！\n"
							"2. **开头绝对不能千篇一律！**每次都要用不同的开头方式！\n"
							"3. 写每一句话前都要问：如果这件事真的发生在我身上，我会怎么跟朋友说？这句话我会说给朋友听吗？如果不会，改！"
						)
					
					system_prompt = "".join(system_prompt_parts)
				
				# 如果字数 > 8000 且有目录，则分段生成
				if target_chars > 8000 and parsed_sections:
					# 提取章节标题列表（_generate_in_sections需要字符串列表）
					section_titles = [s['title'] for s in parsed_sections]
					self._generate_in_sections(client, query, contexts, section_titles, target_chars)
				else:
					# 一次性生成（原逻辑）
					self.after(0, lambda: self.output.insert(END, "生成中...\n\n"))
					time.sleep(0.05)  # 确保提示文字显示
					
					prompt = self._build_prompt(query, contexts, self.category.get(), self.current_outline)
					for delta in client.stream([
						{"role": "system", "content": system_prompt},
						{"role": "user", "content": prompt},
					], temperature=self.temperature.get(), max_tokens=int(target_chars*2.5)):
						# 使用 after() 在主线程更新UI，实现线程安全的打字机效果
						self.after(0, lambda text=delta: self._insert_text_safe(text))
				
				self.after(0, lambda: self.status.set("生成完成"))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("故事生成完成", "✅"))
				# 自动保存到当前项目（在主线程执行）
				self.after(100, lambda: self._auto_save_to_project())
			except Exception as e:
				import traceback
				# 在lambda外捕获错误信息（避免闭包问题）
				error_msg = "生成出错:\n" + traceback.format_exc() + "\n"
				error_str = str(e)
				# 在主线程更新UI
				self.after(0, lambda msg=error_msg: self.output.insert(END, msg))
				self.after(0, lambda err=error_str: messagebox.showerror("错误", err))
				self.after(0, lambda: self.status.set("生成失败"))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成故事失败", "❌"))
			finally:
				self.after(0, lambda: self.set_busy(False))
		threading.Thread(target=task, daemon=True).start()

	
	def on_auto_generate_all(self) -> None:
		"""自动连续生成所有章节（委托给 on_generate_all_sections）"""
		# 直接调用 outline_generator.py 中的实现
		self.on_generate_all_sections()
	
	
	def _generate_model_only(self, query) -> None:
		def task():
			try:
				self.after(0, lambda: self.set_busy(True))
				
				# 获取选中的故事生成API配置
				selected_api = self.story_gen_api.get() if hasattr(self, 'story_gen_api') else "DeepSeek"
				if selected_api not in self.api_presets:
					# 捕获变量到本地作用域
					api_name = selected_api
					error_msg = f"未找到API预设: {api_name}"
					self.after(0, lambda msg=error_msg: messagebox.showerror("错误", msg))
					return
				
				api_config = self.api_presets[selected_api]
				api_key = _sanitize(api_config.get("key", ""))
				
				# 捕获变量到本地作用域（避免闭包问题）
				api_name = selected_api
				status_msg = f"使用 {api_name} 准备生成..."
				self.after(0, lambda msg=status_msg: self.status.set(msg))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("AI创作故事中...", "📝"))
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				# 等待清空完成再继续
				self.after(0, lambda: self.output.delete("1.0", END))
				time.sleep(0.05)  # 短暂等待UI操作完成
				
				# 检查是否需要分段生成
				target_chars = self.target_chars.get()
				parsed_sections = self._parse_outline_sections(self.current_outline) if self.current_outline else []
				
				# 如果字数 > 8000 且有目录，则分段生成
				if target_chars > 8000 and parsed_sections:
					# 提取章节标题列表（_generate_in_sections需要字符串列表）
					section_titles = [s['title'] for s in parsed_sections]
					self._generate_in_sections(client, query, [], section_titles, target_chars)
				else:
					# 一次性生成（原逻辑）
					self.after(0, lambda: self.output.insert(END, "生成中...\n\n"))
					time.sleep(0.05)  # 确保提示文字显示
					
					prompt = self._build_prompt(query, [], self.category.get(), self.current_outline)
					for delta in client.stream([
						{"role": "system", "content": "你是2024年的知乎顶级故事作者，文风现代、口语化、接地气。你深谙当代网络表达习惯，善于用生动细节、强烈对比、戏剧冲突抓住读者。你的故事节奏紧凑、反转频出、铺垫扎实，让人欲罢不能。"},
						{"role": "user", "content": prompt},
					], temperature=self.temperature.get(), max_tokens=int(target_chars*2.5)):
						# 使用 after() 在主线程更新UI，实现线程安全的打字机效果
						self.after(0, lambda text=delta: self._insert_text_safe(text))
				
				self.after(0, lambda: self.status.set("生成完成"))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("故事生成完成", "✅"))
				# 自动保存到当前项目（在主线程执行）
				self.after(100, lambda: self._auto_save_to_project())
			except Exception as e:
				import traceback
				# 在lambda外捕获错误信息（避免闭包问题）
				error_msg = "\n\n生成出错:\n" + traceback.format_exc() + "\n"
				error_str = str(e)
				# 在主线程更新UI
				self.after(0, lambda msg=error_msg: self.output.insert(END, msg))
				self.after(0, lambda err=error_str: messagebox.showerror("错误", err))
				self.after(0, lambda: self.status.set("生成失败"))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成故事失败", "❌"))
			finally:
				self.after(0, lambda: self.set_busy(False))
		threading.Thread(target=task, daemon=True).start()
	
	
	def _insert_text_safe(self, text: str) -> None:
		"""线程安全地插入文本到output，实现打字机效果"""
		try:
			self.output.insert(END, text)
			self.output.see(END)
			self.update_idletasks()
		except Exception as e:
			# 静默处理错误，避免中断生成
			pass
	