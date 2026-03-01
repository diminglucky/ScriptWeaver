"""
角色设定表生成器
将多角度、多表情的人物照片拼接成专业的角色设定表
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import os
import platform
import logging


logger = logging.getLogger(__name__)


class CharacterSheetBuilder:
	"""角色设定表构建器"""
	
	# 标准布局配置
	LAYOUTS = {
		"standard_3x5": {
			"name": "标准版 (3视图×5表情)",
			"rows": 5,  # 5种表情
			"cols": 3,  # 3个视角
			"angles": ["front", "side", "back"],
			"expressions": ["neutral", "happy", "sad", "angry", "surprised"],
			"cell_size": (400, 400),
			"padding": 20,
			"header_height": 100,
			"label_height": 50
		},
		"simple_3x1": {
			"name": "三视图版 (仅3视角)",
			"rows": 1,
			"cols": 3,
			"angles": ["front", "side", "back"],
			"expressions": ["neutral"],
			"cell_size": (500, 500),
			"padding": 30,
			"header_height": 120,
			"label_height": 60
		},
		"expression_5x1": {
			"name": "表情版 (仅5表情)",
			"rows": 1,
			"cols": 5,
			"angles": ["front"],
			"expressions": ["neutral", "happy", "sad", "angry", "surprised"],
			"cell_size": (300, 300),
			"padding": 20,
			"header_height": 100,
			"label_height": 60
		},
		"compact_2x3": {
			"name": "紧凑版 (2视角×3表情)",
			"rows": 3,
			"cols": 2,
			"angles": ["front", "three-quarter"],
			"expressions": ["neutral", "happy", "sad"],
			"cell_size": (400, 400),
			"padding": 20,
			"header_height": 100,
			"label_height": 50
		}
	}
	
	# 角度和表情的中文名称映射
	ANGLE_NAMES = {
		"front": "正面",
		"side": "侧面",
		"back": "背面",
		"three-quarter": "斜侧"
	}
	
	EXPRESSION_NAMES = {
		"neutral": "😐 中性",
		"happy": "😊 开心",
		"sad": "😢 悲伤",
		"angry": "😠 愤怒",
		"surprised": "😮 惊讶"
	}
	
	@classmethod
	def build_character_sheet(
		cls,
		character_name: str,
		photos_dir: Path,
		output_path: Path,
		layout: str = "standard_3x5",
		background_color: Tuple[int, int, int] = (245, 245, 245),
		show_labels: bool = True,
		show_description: bool = True,
		character_description: str = ""
	) -> Optional[Path]:
		"""
		生成角色设定表
		
		Args:
			character_name: 角色名称
			photos_dir: 照片目录
			output_path: 输出路径
			layout: 布局类型
			background_color: 背景颜色
			show_labels: 是否显示标签
			show_description: 是否显示角色描述
			character_description: 角色描述文本
		
		Returns:
			生成的设定表路径，失败返回None
		"""
		if layout not in cls.LAYOUTS:
			print(f"❌ 无效的布局类型: {layout}")
			return None
		
		config = cls.LAYOUTS[layout]
		print(f"\n{'='*60}")
		print(f"🎨 开始生成角色设定表: {character_name}")
		print(f"📐 布局: {config['name']}")
		print(f"{'='*60}\n")
		
		# 收集所有需要的照片
		photos = cls._collect_photos(character_name, photos_dir, config)
		
		if not photos:
			print(f"❌ 未找到足够的照片文件")
			return None
		
		# 计算画布尺寸
		cell_width, cell_height = config["cell_size"]
		padding = config["padding"]
		header_height = config["header_height"]
		label_height = config["label_height"] if show_labels else 0
		
		# 总尺寸计算
		canvas_width = config["cols"] * cell_width + (config["cols"] + 1) * padding
		canvas_height = (
			header_height +  # 顶部标题区
			config["rows"] * cell_height +  # 照片区域
			config["rows"] * label_height +  # 标签区域
			(config["rows"] + 1) * padding  # 间距
		)
		
		# 如果显示描述，增加底部空间
		description_height = 0
		if show_description and character_description:
			description_height = 150
			canvas_height += description_height
		
		print(f"📏 画布尺寸: {canvas_width} × {canvas_height}")
		
		# 创建画布
		canvas = Image.new("RGB", (canvas_width, canvas_height), background_color)
		draw = ImageDraw.Draw(canvas)
		
		# 绘制标题
		cls._draw_header(draw, character_name, canvas_width, header_height, config['name'])
		
		# 绘制表格和照片
		y_offset = header_height + padding
		
		for row_idx, expr in enumerate(config["expressions"]):
			x_offset = padding
			
			for col_idx, angle in enumerate(config["angles"]):
				# 查找对应的照片
				photo_key = (angle, expr)
				if photo_key in photos:
					photo_img = photos[photo_key]
					
					# 调整照片大小并粘贴
					resized_photo = cls._resize_and_crop(photo_img, (cell_width, cell_height))
					canvas.paste(resized_photo, (x_offset, y_offset))
					
					# 绘制边框
					draw.rectangle(
						[x_offset, y_offset, x_offset + cell_width, y_offset + cell_height],
						outline=(200, 200, 200),
						width=2
					)
				else:
					# 如果照片不存在，绘制占位符
					draw.rectangle(
						[x_offset, y_offset, x_offset + cell_width, y_offset + cell_height],
						fill=(220, 220, 220),
						outline=(180, 180, 180),
						width=2
					)
					# 绘制"缺失"文字
					cls._draw_text_centered(
						draw, "照片缺失", 
						(x_offset + cell_width // 2, y_offset + cell_height // 2),
						font_size=24, color=(150, 150, 150)
					)
				
				# 绘制标签
				if show_labels:
					label_y = y_offset + cell_height + 5
					angle_name = cls.ANGLE_NAMES.get(angle, angle)
					expr_name = cls.EXPRESSION_NAMES.get(expr, expr)
					
					# 第一行显示角度
					if row_idx == 0:
						cls._draw_text_centered(
							draw, angle_name,
							(x_offset + cell_width // 2, y_offset - 15),
							font_size=20, color=(80, 80, 80), bold=True
						)
					
					# 每列第一个显示表情
					if col_idx == 0:
						# 在照片左侧绘制表情标签（垂直居中）
						cls._draw_text_right_aligned(
							draw, expr_name,
							(x_offset - 10, y_offset + cell_height // 2),
							font_size=18, color=(80, 80, 80)
						)
				
				x_offset += cell_width + padding
			
			y_offset += cell_height + label_height + padding
		
		# 绘制底部描述
		if show_description and character_description:
			cls._draw_description(
				draw, character_description,
				padding, canvas_height - description_height + 20,
				canvas_width - 2 * padding, description_height - 40
			)
		
		# 保存图片
		try:
			canvas.save(str(output_path), quality=95)
			print(f"✅ 角色设定表已保存: {output_path}")
			print(f"📊 文件大小: {output_path.stat().st_size / 1024:.1f} KB\n")
			return output_path
		except Exception as e:
			print(f"❌ 保存失败: {e}")
			return None
	
	@classmethod
	def _collect_photos(
		cls,
		character_name: str,
		photos_dir: Path,
		config: dict
	) -> Dict[Tuple[str, str], Image.Image]:
		"""收集所有需要的照片"""
		photos = {}
		
		for angle in config["angles"]:
			for expr in config["expressions"]:
				# 构建可能的文件名
				angle_name = cls.ANGLE_NAMES.get(angle, angle)
				expr_name = cls.EXPRESSION_NAMES.get(expr, expr).split()[-1]  # 去除emoji
				
				possible_filenames = [
					f"{character_name}_{angle_name}_{expr_name}.png",
					f"{character_name}_{angle_name}.png",
					f"{character_name}_{expr_name}.png",
					f"{character_name}.png"
				]
				
				# 尝试加载照片
				for filename in possible_filenames:
					photo_path = photos_dir / filename
					if photo_path.exists():
						try:
							img = Image.open(photo_path)
							photos[(angle, expr)] = img
							print(f"✅ 找到照片: {filename}")
							break
						except Exception as e:
							print(f"⚠️ 无法加载照片 {filename}: {e}")
		
		print(f"\n📸 共找到 {len(photos)} 张照片")
		return photos
	
	@classmethod
	def _resize_and_crop(cls, img: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
		"""调整图片大小并裁剪为目标尺寸（保持比例）"""
		target_width, target_height = target_size
		img_width, img_height = img.size
		
		# 计算缩放比例（保证覆盖整个目标区域）
		scale = max(target_width / img_width, target_height / img_height)
		
		# 缩放
		new_width = int(img_width * scale)
		new_height = int(img_height * scale)
		img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
		
		# 居中裁剪
		left = (new_width - target_width) // 2
		top = (new_height - target_height) // 2
		img_cropped = img_resized.crop((left, top, left + target_width, top + target_height))
		
		return img_cropped
	
	@classmethod
	def _draw_header(cls, draw: ImageDraw.Draw, character_name: str, width: int, height: int, layout_name: str):
		"""绘制顶部标题"""
		# 绘制标题背景
		draw.rectangle([0, 0, width, height], fill=(60, 60, 60))
		
		# 绘制角色名
		cls._draw_text_centered(
			draw, f"《 {character_name} 》角色设定表",
			(width // 2, height // 2 - 10),
			font_size=36, color=(255, 255, 255), bold=True
		)
		
		# 绘制布局名称
		cls._draw_text_centered(
			draw, layout_name,
			(width // 2, height // 2 + 25),
			font_size=16, color=(200, 200, 200)
		)
	
	@classmethod
	def _draw_description(cls, draw: ImageDraw.Draw, text: str, x: int, y: int, width: int, height: int):
		"""绘制底部描述"""
		# 绘制描述背景
		draw.rectangle([x - 10, y - 10, x + width + 10, y + height + 10], fill=(255, 255, 255), outline=(200, 200, 200), width=2)
		
		# 绘制标题
		cls._draw_text_left_aligned(
			draw, "角色描述:",
			(x, y),
			font_size=18, color=(80, 80, 80), bold=True
		)
		
		# 绘制描述文本（多行）
		lines = cls._wrap_text(text, width, font_size=14)
		y_text = y + 30
		for line in lines[:5]:  # 最多5行
			cls._draw_text_left_aligned(
				draw, line,
				(x, y_text),
				font_size=14, color=(100, 100, 100)
			)
			y_text += 22
	
	@classmethod
	def _wrap_text(cls, text: str, max_width: int, font_size: int = 14) -> List[str]:
		"""文本自动换行"""
		# 简化版：按字符数估算
		chars_per_line = max_width // (font_size + 2)
		lines = []
		current_line = ""
		
		for char in text:
			if len(current_line) >= chars_per_line or char == '\n':
				lines.append(current_line)
				current_line = char if char != '\n' else ""
			else:
				current_line += char
		
		if current_line:
			lines.append(current_line)
		
		return lines
	
	@classmethod
	def _draw_text_centered(
		cls, draw: ImageDraw.Draw, text: str, position: Tuple[int, int],
		font_size: int = 20, color: Tuple[int, int, int] = (0, 0, 0), bold: bool = False
	):
		"""绘制居中文本"""
		font = cls._load_font(font_size)
		
		# 获取文本边界框
		bbox = draw.textbbox((0, 0), text, font=font)
		text_width = bbox[2] - bbox[0]
		text_height = bbox[3] - bbox[1]
		
		# 计算居中位置
		x = position[0] - text_width // 2
		y = position[1] - text_height // 2
		
		draw.text((x, y), text, fill=color, font=font)
	
	@classmethod
	def _draw_text_left_aligned(
		cls, draw: ImageDraw.Draw, text: str, position: Tuple[int, int],
		font_size: int = 20, color: Tuple[int, int, int] = (0, 0, 0), bold: bool = False
	):
		"""绘制左对齐文本"""
		font = cls._load_font(font_size)
		
		draw.text(position, text, fill=color, font=font)
	
	@classmethod
	def _draw_text_right_aligned(
		cls, draw: ImageDraw.Draw, text: str, position: Tuple[int, int],
		font_size: int = 20, color: Tuple[int, int, int] = (0, 0, 0)
	):
		"""绘制右对齐文本（垂直居中）"""
		font = cls._load_font(font_size)
		
		bbox = draw.textbbox((0, 0), text, font=font)
		text_width = bbox[2] - bbox[0]
		text_height = bbox[3] - bbox[1]
		
		x = position[0] - text_width
		y = position[1] - text_height // 2
		
		draw.text((x, y), text, fill=color, font=font)

	@classmethod
	def _candidate_font_paths(cls) -> List[str]:
		"""Return platform-appropriate font candidates for CJK-safe rendering."""
		system = platform.system()
		if system == "Windows":
			return [
				"C:/Windows/Fonts/msyh.ttc",
				"C:/Windows/Fonts/simhei.ttf",
				"C:/Windows/Fonts/arial.ttf",
			]
		if system == "Darwin":
			return [
				"/System/Library/Fonts/PingFang.ttc",
				"/System/Library/Fonts/Hiragino Sans GB.ttc",
				"/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
			]
		return [
			"/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
			"/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
			"/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
			"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
		]

	@classmethod
	def _load_font(cls, font_size: int):
		"""Load a usable font on each platform and gracefully fallback."""
		for font_path in cls._candidate_font_paths():
			if not os.path.exists(font_path):
				continue
			try:
				return ImageFont.truetype(font_path, font_size)
			except Exception as e:
				logger.debug("Font load failed (%s): %s", font_path, e)
		return ImageFont.load_default()

