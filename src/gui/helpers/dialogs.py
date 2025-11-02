"""
自定义对话框模块
提供美观的、适配主题的对话框组件
"""

import tkinter as tk
from tkinter import scrolledtext


def show_input_dialog(parent, title, prompt, width=400, height=180, initial_value="", multiline=False):
	"""显示自定义输入对话框
	
	Args:
		parent: 父窗口
		title: 对话框标题
		prompt: 提示文本
		width: 对话框宽度
		height: 对话框高度
		initial_value: 输入框初始值
		multiline: 是否使用多行输入框（支持滚动）
	
	Returns:
		用户输入的文本，如果取消则返回None
	"""
	dialog = tk.Toplevel(parent)
	dialog.title(title)
	
	# 如果是多行模式，使用更大的默认高度
	if multiline and height < 250:
		height = 300
	
	dialog.geometry(f"{width}x{height}")
	dialog.resizable(False, False)
	dialog.transient(parent)
	dialog.grab_set()
	
	# 居中显示
	dialog.update_idletasks()
	x = (dialog.winfo_screenwidth() // 2) - (width // 2)
	y = (dialog.winfo_screenheight() // 2) - (height // 2)
	dialog.geometry(f"{width}x{height}+{x}+{y}")
	
	# 根据主题设置背景色
	try:
		from ..theme import Theme
		bg_color = Theme.BG_SECONDARY
		fg_color = Theme.TEXT_PRIMARY
		entry_bg = Theme.SURFACE
		button_bg = Theme.PRIMARY
	except:
		bg_color = "#2b2b2b"
		fg_color = "#e0e0e0"
		entry_bg = "#1e1e1e"
		button_bg = "#007acc"
	
	dialog.configure(bg=bg_color)
	
	# 创建内容区域
	content_frame = tk.Frame(dialog, bg=bg_color)
	content_frame.pack(fill="both", expand=True, padx=20, pady=20)
	
	# 提示文本
	label = tk.Label(
		content_frame,
		text=prompt,
		font=("", 11),
		bg=bg_color,
		fg=fg_color,
		anchor="w",
		justify="left"
	)
	label.pack(fill="x", pady=(0, 12))
	
	# 输入框
	result = [None]  # 使用列表来存储结果，以便在闭包中修改
	
	if multiline:
		# 多行输入框（带滚动条）
		input_widget = scrolledtext.ScrolledText(
			content_frame,
			font=("", 11),
			bg=entry_bg,
			fg=fg_color,
			insertbackground=button_bg,
			relief="flat",
			bd=2,
			wrap="word",
			height=8
		)
		input_widget.pack(fill="both", expand=True)
		
		if initial_value:
			input_widget.insert("1.0", initial_value)
			input_widget.see("1.0")  # 滚动到开头
		
		input_widget.focus_set()
		
		def on_ok():
			result[0] = input_widget.get("1.0", "end-1c").strip()
			dialog.destroy()
		
		# 多行模式下，Ctrl+Enter 提交，ESC 取消
		input_widget.bind("<Control-Return>", lambda e: on_ok())
	else:
		# 单行输入框
		entry_var = tk.StringVar(value=initial_value)
		input_widget = tk.Entry(
			content_frame,
			textvariable=entry_var,
			font=("", 12),
			bg=entry_bg,
			fg=fg_color,
			insertbackground=button_bg,
			relief="flat",
			bd=2
		)
		input_widget.pack(fill="x", ipady=8)
		input_widget.focus_set()
		input_widget.select_range(0, tk.END)  # 选中所有文本
		
		def on_ok():
			result[0] = entry_var.get()
			dialog.destroy()
		
		# 单行模式下，Enter 提交
		input_widget.bind("<Return>", lambda e: on_ok())
	
	# 按钮区域
	button_frame = tk.Frame(content_frame, bg=bg_color)
	button_frame.pack(fill="x", pady=(20 if not multiline else 12, 0))
	
	def on_cancel():
		result[0] = None
		dialog.destroy()
	
	# OK按钮
	ok_btn = tk.Button(
		button_frame,
		text="OK" + (" (Ctrl+Enter)" if multiline else ""),
		command=on_ok,
		bg=button_bg,
		fg="#FFFFFF",
		font=("", 10, "bold"),
		relief="flat",
		cursor="hand2",
		width=15 if multiline else 10,
		pady=8
	)
	ok_btn.pack(side=tk.LEFT, padx=(0, 10))
	
	# Cancel按钮
	cancel_btn = tk.Button(
		button_frame,
		text="Cancel",
		command=on_cancel,
		bg=entry_bg,
		fg=fg_color,
		font=("", 10),
		relief="flat",
		cursor="hand2",
		width=10,
		pady=8
	)
	cancel_btn.pack(side=tk.LEFT)
	
	# 绑定ESC键
	dialog.bind("<Escape>", lambda e: on_cancel())
	
	# 等待对话框关闭
	dialog.wait_window()
	
	return result[0]

