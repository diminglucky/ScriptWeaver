"""
人物一致性优化器
提供多种技术来提升同一角色在不同照片中的视觉一致性
"""

import re
from typing import Dict, List, Tuple


class ConsistencyOptimizer:
	"""人物一致性优化工具"""
	
	# 一致性关键特征提取规则
	FEATURE_KEYWORDS = {
		# 五官特征
		"eyes": ["眼睛", "眼眶", "眼神", "双眼", "目光", "眼珠", "瞳孔", "eyes", "eye", "gaze"],
		"nose": ["鼻子", "鼻梁", "鼻尖", "nose", "nostril"],
		"mouth": ["嘴", "嘴唇", "唇", "mouth", "lips"],
		"face_shape": ["脸型", "脸形", "圆脸", "方脸", "瓜子脸", "鹅蛋脸", "face shape", "oval", "round"],
		"eyebrows": ["眉毛", "眉形", "眉", "eyebrow", "brow"],
		
		# 发型特征
		"hair_color": ["黑发", "白发", "金发", "棕发", "红发", "银发", "粉发", "蓝发", 
					   "black hair", "white hair", "blonde", "brown hair", "red hair"],
		"hair_style": ["短发", "长发", "中长发", "齐肩", "披肩", "马尾", "双马尾", "发髻",
					   "short hair", "long hair", "ponytail", "bun"],
		"hair_texture": ["直发", "卷发", "波浪", "straight hair", "curly", "wavy"],
		
		# 身材特征
		"height": ["身高", "高", "cm", "米", "height", "tall", "short"],
		"build": ["身材", "体型", "苗条", "瘦", "胖", "魁梧", "健壮",
				  "slim", "thin", "fat", "muscular", "build"],
		
		# 年龄特征
		"age": ["岁", "年龄", "young", "old", "middle-aged", "years old"],
		
		# 肤色特征
		"skin": ["肤色", "皮肤", "白皙", "古铜", "深色", "浅色",
				 "skin", "pale", "fair", "dark", "tan"],
		
		# 特殊标记
		"marks": ["疤痕", "痣", "胎记", "纹身", "酒窝",
				  "scar", "mole", "birthmark", "tattoo", "dimple"],
	}
	
	# 一致性增强词汇
	CONSISTENCY_BOOSTERS = {
		"zh": {
			"identity": ["同一个人", "完全相同的人", "保持外貌完全一致", "同一角色"],
			"features": ["固定特征", "不变的外貌", "一致的五官", "相同的面部特征"],
			"recognition": ["可识别的", "辨识度高", "特征明显", "独特且不变"],
			"facial": ["相同的脸型", "一模一样的五官", "固定的面部轮廓", "不变的脸部特征"],
		},
		"en": {
			"identity": ["same person", "exact same individual", "completely consistent appearance", "identical character"],
			"features": ["fixed characteristics", "unchanged look", "consistent facial features", "same face structure"],
			"recognition": ["recognizable", "distinctive", "clear identifying features", "unique and unchanging"],
			"facial": ["same face shape", "identical facial features", "fixed facial contours", "unchanging face structure"],
		}
	}
	
	@classmethod
	def extract_critical_features(cls, description: str) -> Dict[str, str]:
		"""
		提取最关键的一致性特征（脸型、发型、服装）
		
		Args:
			description: 人物描述
		
		Returns:
			关键特征字典 {feature_type: feature_description}
		"""
		critical_features = {}
		
		# 1. 脸型关键词
		face_shapes = [
			"瓜子脸", "鹅蛋脸", "圆脸", "方脸", "长脸", "菱形脸", "心形脸",
			"oval face", "round face", "square face", "heart-shaped face", "diamond face"
		]
		
		for shape in face_shapes:
			if shape in description:
				pattern = rf'[^，。,.\n]*{re.escape(shape)}[^，。,.\n]*'
				matches = re.findall(pattern, description, re.IGNORECASE)
				if matches:
					critical_features["face_shape"] = matches[0].strip()
					break
		
		# 2. 发型关键词（长度+样式）
		hair_keywords = [
			"短发", "长发", "中长发", "齐肩", "披肩", "及腰", "马尾", "双马尾", "发髻", "盘发",
			"直发", "卷发", "波浪", "黑发", "白发", "金发", "棕发", "银发",
			"short hair", "long hair", "shoulder-length", "ponytail", "bun", 
			"straight hair", "curly", "wavy", "black hair", "blonde"
		]
		
		hair_desc_parts = []
		for keyword in hair_keywords:
			if keyword in description:
				pattern = rf'[^，。,.\n]*{re.escape(keyword)}[^，。,.\n]*'
				matches = re.findall(pattern, description, re.IGNORECASE)
				hair_desc_parts.extend(matches)
		
		if hair_desc_parts:
			# 去重并合并
			unique_parts = list(set([p.strip() for p in hair_desc_parts]))
			critical_features["hair"] = "，".join(unique_parts[:3])  # 最多3个描述
		
		# 3. 服装关键词（颜色+款式）
		clothing_keywords = [
			"西装", "衬衫", "T恤", "连衣裙", "外套", "夹克", "毛衣", "卫衣",
			"黑色", "白色", "灰色", "蓝色", "红色", "绿色", "粉色", "棕色", "深色", "浅色",
			"suit", "shirt", "dress", "jacket", "sweater", "coat",
			"black", "white", "gray", "blue", "red", "green", "pink", "brown", "dark", "light"
		]
		
		clothing_desc_parts = []
		for keyword in clothing_keywords:
			if keyword in description:
				pattern = rf'[^，。,.\n]*{re.escape(keyword)}[^，。,.\n]*'
				matches = re.findall(pattern, description, re.IGNORECASE)
				clothing_desc_parts.extend(matches)
		
		if clothing_desc_parts:
			unique_parts = list(set([p.strip() for p in clothing_desc_parts]))
			critical_features["clothing"] = "，".join(unique_parts[:3])
		
		return critical_features
	
	@classmethod
	def extract_face_shape(cls, description: str) -> str:
		"""
		专门提取脸型特征（向后兼容）
		"""
		critical = cls.extract_critical_features(description)
		return critical.get("face_shape", "")
	
	@classmethod
	def extract_key_features(cls, description: str) -> Dict[str, List[str]]:
		"""
		从人物描述中提取关键特征
		
		Args:
			description: 人物描述文本
		
		Returns:
			特征字典，key为特征类型，value为提取的特征词列表
		"""
		features = {}
		
		for feature_type, keywords in cls.FEATURE_KEYWORDS.items():
			found_features = []
			for keyword in keywords:
				# 查找包含关键词的句子片段
				pattern = rf'[^，。,.\n]*{re.escape(keyword)}[^，。,.\n]*'
				matches = re.findall(pattern, description, re.IGNORECASE)
				if matches:
					found_features.extend(matches)
			
			if found_features:
				# 去重并限制数量
				unique_features = list(set(found_features))[:3]
				features[feature_type] = unique_features
		
		return features
	
	@classmethod
	def build_consistency_prompt(
		cls,
		description: str,
		language: str = "zh",
		emphasis_level: str = "medium"
	) -> str:
		"""
		构建一致性增强的提示词
		
		Args:
			description: 原始描述
			language: 语言（zh/en）
			emphasis_level: 强调级别（low/medium/high）
		
		Returns:
			增强后的描述
		"""
		# 提取关键特征
		key_features = cls.extract_key_features(description)
		
		# 🎯 提取最关键的三大特征：脸型、发型、服装
		critical_features = cls.extract_critical_features(description)
		
		# 构建增强描述
		enhanced_parts = [description]
		
		# 🎯 重复最关键的特征（脸型、发型、服装）
		if emphasis_level == "high":
			# 高级别：每个特征重复3次
			for feature_type in ["face_shape", "hair", "clothing"]:
				if feature_type in critical_features and critical_features[feature_type]:
					enhanced_parts.extend([critical_features[feature_type]] * 3)
		elif emphasis_level == "medium":
			# 中级别：每个特征重复2次
			for feature_type in ["face_shape", "hair", "clothing"]:
				if feature_type in critical_features and critical_features[feature_type]:
					enhanced_parts.extend([critical_features[feature_type]] * 2)
		
		# 添加一致性增强词汇
		boosters = cls.CONSISTENCY_BOOSTERS.get(language, cls.CONSISTENCY_BOOSTERS["zh"])
		
		if emphasis_level == "high":
			# 高强调：添加所有类型的增强词，特别强调面部特征
			enhanced_parts.extend(boosters["identity"][:2])
			enhanced_parts.extend(boosters["features"][:2])
			enhanced_parts.extend(boosters["facial"][:2])  # 强调面部一致性
		elif emphasis_level == "medium":
			# 中强调：适度添加
			enhanced_parts.extend(boosters["identity"][:1])
			enhanced_parts.extend(boosters["features"][:1])
			enhanced_parts.extend(boosters["facial"][:1])  # 添加面部一致性
		# low级别不添加额外词汇
		
		# 重复关键特征（提高权重）
		if emphasis_level in ["medium", "high"]:
			important_features = []
			
			# 优先重复最重要的面部特征（脸型最关键！）
			priority_types = ["face_shape", "eyes", "nose", "mouth", "hair_color", "hair_style", "age"]
			
			# high级别：重复更多次
			repeat_count = 2 if emphasis_level == "high" else 1
			
			for feature_type in priority_types:
				if feature_type in key_features:
					for _ in range(repeat_count):
						important_features.extend(key_features[feature_type][:1])
			
			if important_features:
				enhanced_parts.extend(important_features)
		
		# 组合
		separator = "，" if language == "zh" else ", "
		return separator.join(enhanced_parts)
	
	@classmethod
	def add_consistency_markers(
		cls,
		description: str,
		character_id: str = "",
		language: str = "zh"
	) -> str:
		"""
		添加一致性标记到描述中
		
		Args:
			description: 人物描述
			character_id: 角色ID（用于标记）
			language: 语言
		
		Returns:
			带标记的描述
		"""
		if character_id:
			if language == "zh":
				marker = f"【角色代号：{character_id}】"
			else:
				marker = f"[Character ID: {character_id}]"
			
			return f"{marker} {description}"
		
		return description
	
	@classmethod
	def optimize_for_batch_generation(
		cls,
		description: str,
		batch_type: str = "angle",
		language: str = "zh"
	) -> str:
		"""
		为批量生成优化描述
		
		Args:
			description: 原始描述
			batch_type: 批量类型（angle/expression/variant）
			language: 语言
		
		Returns:
			优化后的描述
		"""
		# 根据批量类型添加特定提示
		if batch_type == "angle":
			# 多角度生成：强调面部、发型、服装的完全一致性
			if language == "zh":
				hints = [
					"完全相同的脸型和五官",
					"一模一样的面部轮廓",
					"完全一致的发型发长",  # ← 新增！强调发型
					"完全相同的发型",
					"保持服装颜色和款式完全一致",  # ← 加强！强调服装颜色
					"相同的衣服",
					"同一个人的不同角度",
					"面部特征绝对不变",
					"头发长度和样式不变",  # ← 新增！再次强调头发
					"服装细节完全相同"  # ← 新增！强调服装细节
				]
			else:
				hints = [
					"exact same face shape and features",
					"identical facial contours",
					"completely same hairstyle and hair length",  # ← 新增！
					"exact same hair",
					"completely consistent clothing color and style",  # ← 加强！
					"same outfit",
					"same person from different angles",
					"absolutely unchanged facial characteristics",
					"hair length and style unchanged",  # ← 新增！
					"clothing details exactly the same"  # ← 新增！
				]
		
		elif batch_type == "expression":
			# 多表情生成：强调五官的完全一致性
			if language == "zh":
				hints = [
					"完全相同的脸型",
					"一模一样的五官轮廓",
					"保持面部结构不变",
					"只改变表情",
					"同一张脸不同表情"
				]
			else:
				hints = [
					"exact same face shape",
					"identical facial contours",
					"keep facial structure unchanged",
					"only change expression",
					"same face with different expressions"
				]
		
		elif batch_type == "variant":
			# 多变体生成：强调基础外貌的一致性
			if language == "zh":
				hints = [
					"完全相同的脸型和五官",
					"保持面部特征和体型一致",
					"只改变服装和配饰",
					"同一个人不同造型"
				]
			else:
				hints = [
					"exact same face shape and features",
					"keep face and body consistent",
					"only change clothing and accessories",
					"same person with different styles"
				]
		
		else:
			hints = []
		
		# 添加提示
		separator = "，" if language == "zh" else ", "
		if hints:
			return f"{description}{separator}{separator.join(hints)}"
		
		return description
	
	@classmethod
	def get_consistency_report(cls, description: str) -> Dict:
		"""
		生成一致性分析报告
		
		Args:
			description: 人物描述
		
		Returns:
			分析报告字典
		"""
		features = cls.extract_key_features(description)
		
		report = {
			"total_features": len(features),
			"feature_types": list(features.keys()),
			"feature_details": features,
			"consistency_score": 0,
			"suggestions": []
		}
		
		# 计算一致性分数（0-100）
		# 基于特征完整性
		max_types = len(cls.FEATURE_KEYWORDS)
		score = (len(features) / max_types) * 100
		report["consistency_score"] = int(score)
		
		# 生成建议
		important_missing = []
		for feature_type in ["eyes", "face_shape", "hair_color", "hair_style", "age"]:
			if feature_type not in features:
				important_missing.append(feature_type)
		
		if important_missing:
			report["suggestions"].append({
				"type": "missing_features",
				"message": f"建议补充以下特征以提高一致性：{', '.join(important_missing)}",
				"severity": "medium"
			})
		
		if len(description) < 50:
			report["suggestions"].append({
				"type": "too_short",
				"message": "描述过于简单，建议添加更多细节特征",
				"severity": "high"
			})
		
		if "特殊标记" not in features:
			report["suggestions"].append({
				"type": "no_unique_marks",
				"message": "建议添加独特标记（如痣、疤痕等）以提高辨识度",
				"severity": "low"
			})
		
		return report

