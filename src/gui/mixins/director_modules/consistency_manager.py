"""
一致性管理系统 - 确保分镜头中人物和服装保持一致
"""

from typing import Dict, List
import json


class ConsistencyManagerMixin:
	"""人物一致性管理功能"""
	
	def create_consistency_sheet(self, characters: List[str], shots: List[Dict]) -> Dict:
		"""
		创建人物一致性设定表
		
		Args:
			characters: 故事中出现的人物列表
			shots: 分镜头列表
			
		Returns:
			一致性设定表
		"""
		
		consistency = {
			"version": "1.0",
			"characters": {},
			"color_palette": {},
			"lighting_style": "natural",
			"atmosphere": "general"
		}
		
		# 为每个人物创建设定表
		for char_name in characters:
			consistency["characters"][char_name] = {
				"basic_info": {
					"name": char_name,
					"age": "未设定",
					"gender": "未设定",
					"nationality": "chinese"
				},
				"appearance": {
					"face": {
						"shape": "未设定",
						"skin_tone": "未设定",
						"eyes": "未设定",
						"nose": "未设定",
						"mouth": "未设定",
						"special_marks": "无"
					},
					"hair": {
						"color": "未设定",
						"length": "未设定",
						"style": "未设定",
						"texture": "未设定"
					}
				},
				"outfits": {
					"default": {
						"top": "未设定",
						"bottom": "未设定",
						"shoes": "未设定",
						"accessories": "未设定"
					}
				},
				"expressions": {
					"general": "中性"
				},
				"reference_images": [],
				"constraint_prompt": self._generate_constraint_prompt(char_name, {})
			}
		
		return consistency
	
	def update_character_details(self, consistency: Dict, char_name: str, details: Dict) -> Dict:
		"""
		更新人物细节信息
		
		Args:
			consistency: 当前的一致性设定表
			char_name: 人物名称
			details: 要更新的细节信息
			
		Returns:
			更新后的一致性设定表
		"""
		
		if char_name not in consistency["characters"]:
			return consistency
		
		# 更新基本信息
		if "basic_info" in details:
			consistency["characters"][char_name]["basic_info"].update(details["basic_info"])
		
		# 更新外观信息
		if "appearance" in details:
			consistency["characters"][char_name]["appearance"].update(details["appearance"])
		
		# 更新服装信息
		if "outfits" in details:
			consistency["characters"][char_name]["outfits"].update(details["outfits"])
		
		# 更新表情信息
		if "expressions" in details:
			consistency["characters"][char_name]["expressions"].update(details["expressions"])
		
		# 重新生成约束提示词
		consistency["characters"][char_name]["constraint_prompt"] = \
			self._generate_constraint_prompt(char_name, consistency["characters"][char_name])
		
		return consistency
	
	def _generate_constraint_prompt(self, char_name: str, char_info: Dict) -> str:
		"""
		根据人物信息生成约束提示词
		用于传递给图片生成API
		"""
		
		basic = char_info.get("basic_info", {})
		appearance = char_info.get("appearance", {})
		outfits = char_info.get("outfits", {})
		
		prompt = f"【{char_name}一致性约束 - 必须严格遵守】\n"
		
		# 基本信息
		age = basic.get("age", "")
		gender = basic.get("gender", "")
		if age or gender:
			prompt += f"年龄性别: {age}, {gender}\n"
		
		# 面部特征
		face = appearance.get("face", {})
		if face.get("shape"):
			prompt += f"脸型: {face['shape']}\n"
		if face.get("skin_tone"):
			prompt += f"肤色: {face['skin_tone']}\n"
		if face.get("eyes"):
			prompt += f"眼睛: {face['eyes']}\n"
		
		# 发型
		hair = appearance.get("hair", {})
		if hair.get("color") and hair.get("length"):
			prompt += f"发型: {hair['color']}{hair['length']}, {hair.get('style', '')}\n"
		
		# 服装（默认）
		default_outfit = outfits.get("default", {})
		if any(default_outfit.values()):
			prompt += "服装: "
			outfit_parts = []
			if default_outfit.get("top"):
				outfit_parts.append(default_outfit["top"])
			if default_outfit.get("bottom"):
				outfit_parts.append(default_outfit["bottom"])
			if default_outfit.get("shoes"):
				outfit_parts.append(default_outfit["shoes"])
			if outfit_parts:
				prompt += ", ".join(outfit_parts) + "\n"
		
		# 表情
		expressions = char_info.get("expressions", {})
		if expressions:
			prompt += "表情: " + ", ".join(expressions.values()) + "\n"
		
		prompt += f"\n生成的{char_name}必须严格按照上述特征，确保在所有镜头中保持一致。"
		
		return prompt
	
	def get_shot_constraints(self, consistency: Dict, shot: Dict) -> Dict:
		"""
		获取特定镜头的一致性约束
		
		Args:
			consistency: 一致性设定表
			shot: 镜头信息
			
		Returns:
			该镜头的约束信息
		"""
		
		constraints = {
			"shot_number": shot.get("shot_number", 0),
			"characters_in_shot": shot.get("characters", []),
			"character_constraints": {},
			"lighting": shot.get("lighting", ""),
			"atmosphere": shot.get("atmosphere", ""),
			"color_hints": consistency.get("color_palette", {})
		}
		
		# 为每个出现在该镜头的人物添加约束
		for char_name in shot.get("characters", []):
			if char_name in consistency["characters"]:
				char_data = consistency["characters"][char_name]
				
				# 获取该镜头的特定服装（如果有）
				character_details = shot.get("character_details", {}).get(char_name, "")
				
				constraints["character_constraints"][char_name] = {
					"base_constraint": char_data["constraint_prompt"],
					"shot_specific": character_details,
					"expression": char_data.get("expressions", {}).get(f"shot_{shot.get('shot_number')}", ""),
					"outfit_override": None
				}
		
		return constraints
	
	def build_shot_prompt_with_constraints(self, shot: Dict, constraints: Dict) -> str:
		"""
		根据约束条件为镜头构建最终的提示词
		
		Args:
			shot: 镜头信息
			constraints: 该镜头的约束信息
			
		Returns:
			完整的提示词，包含约束条件
		"""
		
		prompt = ""
		
		# 添加人物约束
		if constraints["character_constraints"]:
			prompt += "【人物一致性约束】\n"
			for char_name, char_constraints in constraints["character_constraints"].items():
				if char_constraints["shot_specific"]:
					prompt += f"{char_name}: {char_constraints['shot_specific']}\n"
				if char_constraints["expression"]:
					prompt += f"表情: {char_constraints['expression']}\n"
		
		# 添加场景描述
		prompt += "\n【场景描述】\n"
		prompt += shot.get("scene_description", "") + "\n"
		
		# 添加动作
		if shot.get("action"):
			prompt += f"\n【动作】\n{shot['action']}\n"
		
		# 添加光线和氛围
		if shot.get("lighting"):
			prompt += f"\n【光线】\n{shot['lighting']}\n"
		
		if shot.get("atmosphere"):
			prompt += f"\n【氛围】\n{shot['atmosphere']}\n"
		
		# 添加摄影指导
		if shot.get("camera_notes"):
			prompt += f"\n【摄影指导】\n{shot['camera_notes']}\n"
		
		# 添加质量关键词
		prompt += "\n【质量要求】\n高质量、清晰、专业、细节清晰、8K分辨率"
		
		return prompt
	
	def export_consistency_sheet(self, consistency: Dict, file_path: str) -> None:
		"""
		导出一致性设定表为JSON文件
		"""
		with open(file_path, 'w', encoding='utf-8') as f:
			json.dump(consistency, f, ensure_ascii=False, indent=2)
	
	def import_consistency_sheet(self, file_path: str) -> Dict:
		"""
		从JSON文件导入一致性设定表
		"""
		with open(file_path, 'r', encoding='utf-8') as f:
			return json.load(f)
	
	def validate_consistency(self, consistency: Dict) -> List[str]:
		"""
		验证一致性设定表的完整性
		
		Returns:
			警告信息列表
		"""
		
		warnings = []
		
		for char_name, char_info in consistency.get("characters", {}).items():
			# 检查基本信息
			basic = char_info.get("basic_info", {})
			if not basic.get("age"):
				warnings.append(f"⚠️  {char_name} 的年龄未设定")
			if not basic.get("gender"):
				warnings.append(f"⚠️  {char_name} 的性别未设定")
			
			# 检查外观信息
			appearance = char_info.get("appearance", {})
			face = appearance.get("face", {})
			if not face.get("shape"):
				warnings.append(f"⚠️  {char_name} 的脸型未设定")
			
			hair = appearance.get("hair", {})
			if not hair.get("color"):
				warnings.append(f"⚠️  {char_name} 的发色未设定")
			
			# 检查服装
			outfits = char_info.get("outfits", {})
			if not outfits.get("default"):
				warnings.append(f"⚠️  {char_name} 的默认服装未设定")
		
		return warnings
