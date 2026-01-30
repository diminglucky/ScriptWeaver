"""人物处理功能"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, VERTICAL, Y, messagebox, filedialog
import tkinter as tk
from tkinter import ttk
import os
import threading
from pathlib import Path
from PIL import Image, ImageTk

from src.clients.deepseek_client import DeepSeekClient
from src.clients.image_client import OpenAIImageClient
from src.utils.text import sanitize as _sanitize
from ...helpers.character_prompt_builder import CharacterPromptBuilder
from ...helpers.character_sheet_builder import CharacterSheetBuilder


class CharacterSheetMixin:
	"""人物 char_sheet 功能"""
	
	def _on_generate_character_sheet(self) -> None:
		"""生成角色设定表"""
		selection = self.char_listbox.curselection()
		if not selection:
			messagebox.showwarning("提示", "请先选择一个人物！")
			return
		
		if not self.current_project:
			messagebox.showwarning("提示", "请先创建或打开一个项目！")
			return
		
		index = selection[0]
		character = self.character_list[index]
		character_name = character["name"]
		character_description = character.get("description", "")
		
		# 获取characters目录
		from pathlib import Path
		characters_dir = Path(self.current_project.project_dir) / "characters"
		
		if not characters_dir.exists():
			messagebox.showwarning("提示", f"未找到角色照片目录！\n请先生成人物照片。")
			return
		
		# 弹出布局选择对话框
		layout_dialog = tk.Toplevel(self)
		layout_dialog.title("选择角色设定表布局")
		layout_dialog.geometry("500x400")
		layout_dialog.configure(bg="#2b2b2b")
		layout_dialog.transient(self)
		layout_dialog.grab_set()
		
		# 标题
		title_label = tk.Label(layout_dialog, text=f"为 {character_name} 生成角色设定表", 
							   font=("", 16, "bold"), bg="#2b2b2b", fg="white")
		title_label.pack(pady=15)
		
		# 布局选择
		layout_frame = ttk.LabelFrame(layout_dialog, text="📐 选择布局模板", padding=15)
		layout_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))
		
		selected_layout = tk.StringVar(value="standard_3x5")
		
		for layout_key, layout_config in CharacterSheetBuilder.LAYOUTS.items():
			desc = f"{layout_config['name']}\n（{layout_config['rows']}行 × {layout_config['cols']}列）"
			rb = tk.Radiobutton(
				layout_frame, text=desc, variable=selected_layout, value=layout_key,
				bg="#f0f0f0", font=("", 11), anchor="w", padx=10, pady=8
			)
			rb.pack(fill="x", pady=5)
		
		# 选项
		options_frame = ttk.LabelFrame(layout_dialog, text="⚙️ 生成选项", padding=15)
		options_frame.pack(fill="x", padx=20, pady=(0, 15))
		
		show_labels_var = tk.BooleanVar(value=True)
		show_desc_var = tk.BooleanVar(value=True)
		
		tk.Checkbutton(options_frame, text="显示角度和表情标签", variable=show_labels_var,
					   bg="#f0f0f0", font=("", 10)).pack(anchor="w", pady=3)
		tk.Checkbutton(options_frame, text="显示角色描述", variable=show_desc_var,
					   bg="#f0f0f0", font=("", 10)).pack(anchor="w", pady=3)
		
		# 按钮
		btn_frame = ttk.Frame(layout_dialog)
		btn_frame.pack(fill="x", padx=20, pady=(0, 15))
		
		def on_confirm():
			layout_dialog.destroy()
			self._generate_sheet_async(
				character_name, characters_dir, character_description,
				selected_layout.get(), show_labels_var.get(), show_desc_var.get()
			)
		
		def on_cancel():
			layout_dialog.destroy()
		
		ttk.Button(btn_frame, text="✅ 生成", command=on_confirm).pack(side=LEFT, fill="x", expand=True, padx=(0, 5))
		ttk.Button(btn_frame, text="❌ 取消", command=on_cancel).pack(side=LEFT, fill="x", expand=True, padx=(5, 0))
	
	
	
	