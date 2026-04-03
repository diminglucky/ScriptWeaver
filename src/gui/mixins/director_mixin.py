"""Director page UI and interactions."""

from __future__ import annotations

import tkinter as tk
from tkinter import BOTH, END, LEFT, RIGHT, VERTICAL, Y, messagebox, ttk

from ..helpers.director_script_builder import DirectorScriptBuilder
from ..theme import Theme


class DirectorMixin:
    """Director workflow page with quality-first interactions."""

    def _build_director_page(self) -> None:
        """Build director workflow page."""
        self._init_director_state()

        root = tk.Frame(self.page_director, bg=Theme.BG_SECONDARY)
        root.pack(fill=BOTH, expand=True, padx=12, pady=12)

        self._build_director_hero(root)
        self._build_director_metrics(root)
        self._build_director_body(root)

    def _init_director_state(self) -> None:
        """Initialize director page runtime state."""
        self._last_director_package: dict = {}
        self._director_tree_index_map: dict[str, int] = {}
        self._director_last_markdown_path = None
        self._director_selected_shot_no: int | None = None
        self._director_filter_job = None
        self._director_selection_sync_lock = False

    def _build_director_hero(self, parent: tk.Frame) -> None:
        """Build page hero with actions and process tips."""
        hero = tk.Frame(parent, bg=Theme.SURFACE, relief=tk.SOLID, borderwidth=1)
        hero.pack(fill="x", pady=(0, 10))

        title_wrap = tk.Frame(hero, bg=Theme.SURFACE)
        title_wrap.pack(fill="x", padx=14, pady=12)

        title_left = tk.Frame(title_wrap, bg=Theme.SURFACE)
        title_left.pack(side=LEFT, fill="x", expand=True)

        tk.Label(
            title_left,
            text="🎬 导演工作台",
            font=(Theme.FONT_FAMILY, 16, "bold"),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            title_left,
            text="从故事自动生成人物、导演脚本和可执行分镜，并对每个镜头做结构质检。",
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(4, 0))

        tk.Label(
            title_left,
            text="流程：① 生成脚本包 ② 修正问题镜头 ③ 按镜头导出提示词生成视频",
            font=(Theme.FONT_FAMILY, 9),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(2, 0))

        title_right = tk.Frame(title_wrap, bg=Theme.SURFACE)
        title_right.pack(side=RIGHT)

        self.btn_generate_director_page = tk.Button(
            title_right,
            text="🎞️ 生成导演脚本包",
            command=self._on_generate_director_package,
            bg=Theme.PRIMARY_DARK,
            fg=Theme.TEXT_PRIMARY,
            activebackground=Theme.PRIMARY,
            activeforeground=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=14,
            pady=8,
            cursor="hand2",
            font=(Theme.FONT_FAMILY, 10, "bold"),
        )
        self.btn_generate_director_page.pack(side=LEFT, padx=(0, 8))

        self.btn_copy_shot_detail = tk.Button(
            title_right,
            text="📋 复制镜头详情",
            command=self._on_copy_director_shot_detail,
            bg=Theme.SURFACE_LIGHT,
            fg=Theme.TEXT_PRIMARY,
            activebackground=Theme.BG_HOVER,
            activeforeground=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=12,
            pady=8,
            cursor="hand2",
            font=(Theme.FONT_FAMILY, 10),
        )
        self.btn_copy_shot_detail.pack(side=LEFT, padx=(0, 8))

        self.btn_copy_veo_prompt = tk.Button(
            title_right,
            text="🧠 复制Veo提示词",
            command=self._on_copy_director_veo_prompt,
            bg=Theme.SURFACE_LIGHT,
            fg=Theme.TEXT_PRIMARY,
            activebackground=Theme.BG_HOVER,
            activeforeground=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=12,
            pady=8,
            cursor="hand2",
            font=(Theme.FONT_FAMILY, 10),
        )
        self.btn_copy_veo_prompt.pack(side=LEFT)

    def _create_director_metric_card(self, parent, col: int, title: str, value_var: tk.StringVar) -> None:
        """Create one metric card."""
        card = tk.Frame(parent, bg=Theme.SURFACE, relief=tk.SOLID, borderwidth=1)
        card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 6, 0), pady=0)
        tk.Label(
            card,
            text=title,
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_SECONDARY,
        ).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(
            card,
            textvariable=value_var,
            font=(Theme.FONT_FAMILY, 14, "bold"),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=10, pady=(0, 8))

    def _build_director_metrics(self, root: tk.Frame) -> None:
        """Build top metric cards."""
        metrics = tk.Frame(root, bg=Theme.BG_SECONDARY)
        metrics.pack(fill="x", pady=(0, 10))
        for col in range(5):
            metrics.columnconfigure(col, weight=1)

        self.director_stat_shots_var = tk.StringVar(value="0")
        self.director_stat_chars_var = tk.StringVar(value="0")
        self.director_stat_duration_var = tk.StringVar(value="0 秒")
        self.director_stat_quality_var = tk.StringVar(value="0%")
        self.director_stat_problem_var = tk.StringVar(value="0")
        self.director_stat_selected_var = tk.StringVar(value="未选择")

        self._create_director_metric_card(metrics, 0, "分镜数量", self.director_stat_shots_var)
        self._create_director_metric_card(metrics, 1, "人物数量", self.director_stat_chars_var)
        self._create_director_metric_card(metrics, 2, "总时长", self.director_stat_duration_var)
        self._create_director_metric_card(metrics, 3, "结构完整度", self.director_stat_quality_var)
        self._create_director_metric_card(metrics, 4, "问题镜头", self.director_stat_problem_var)

    def _build_director_body(self, root: tk.Frame) -> None:
        """Build split body panels."""
        body = ttk.PanedWindow(root, orient="horizontal")
        body.pack(fill=BOTH, expand=True)

        left_panel = tk.Frame(body, bg=Theme.BG_SECONDARY)
        right_panel = tk.Frame(body, bg=Theme.BG_SECONDARY)
        body.add(left_panel, weight=3)
        body.add(right_panel, weight=2)

        self._build_director_left_panel(left_panel)
        self._build_director_right_panel(right_panel)

    def _build_director_left_panel(self, left_panel: tk.Frame) -> None:
        """Build shot table panel."""
        box = tk.Frame(left_panel, bg=Theme.SURFACE, relief=tk.SOLID, borderwidth=1)
        box.pack(fill=BOTH, expand=True, padx=(0, 8))
        self._build_director_left_header(box)
        self._build_director_left_tools(box)
        self._build_director_shot_table(box)

    def _build_director_left_header(self, box: tk.Frame) -> None:
        """Build shot table header."""
        header = tk.Frame(box, bg=Theme.SURFACE)
        header.pack(fill="x", padx=10, pady=(8, 6))
        tk.Label(
            header,
            text="🎬 分镜清单（人物 + 内容 + 质检）",
            font=(Theme.FONT_FAMILY, 12, "bold"),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
        ).pack(side=LEFT)
        self.director_table_hint_var = tk.StringVar(value="0 / 0")
        tk.Label(
            header,
            textvariable=self.director_table_hint_var,
            font=(Theme.FONT_FAMILY, 9),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_SECONDARY,
        ).pack(side=RIGHT)

    def _build_director_left_tools(self, box: tk.Frame) -> None:
        """Build filter controls."""
        tools = tk.Frame(box, bg=Theme.SURFACE)
        tools.pack(fill="x", padx=10, pady=(0, 6))

        self.director_filter_var = tk.StringVar(value="")
        self.director_filter_var.trace_add("write", self._on_director_filter_changed)
        filter_entry = tk.Entry(
            tools,
            textvariable=self.director_filter_var,
            width=26,
            bg=Theme.SURFACE_LIGHT,
            fg=Theme.TEXT_PRIMARY,
            insertbackground=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=Theme.BORDER,
            highlightcolor=Theme.BORDER_FOCUS,
        )
        filter_entry.pack(side=LEFT, padx=(0, 8))

        self.director_issue_only_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            tools,
            text="只看问题镜头",
            variable=self.director_issue_only_var,
            command=self._on_director_issue_only_changed,
            font=(Theme.FONT_FAMILY, 9),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_SECONDARY,
            activebackground=Theme.SURFACE,
            activeforeground=Theme.TEXT_PRIMARY,
            selectcolor=Theme.SURFACE_LIGHT,
            relief=tk.FLAT,
            highlightthickness=0,
            bd=0,
        ).pack(side=LEFT, padx=(0, 8))

        tk.Button(
            tools,
            text="清空筛选",
            command=self._clear_director_filter,
            bg=Theme.SURFACE_LIGHT,
            fg=Theme.TEXT_PRIMARY,
            activebackground=Theme.BG_HOVER,
            activeforeground=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            font=(Theme.FONT_FAMILY, 9),
        ).pack(side=LEFT)

    def _build_director_shot_table(self, box: tk.Frame) -> None:
        """Build shot treeview and scrolling."""
        table_wrap = tk.Frame(box, bg=Theme.SURFACE)
        table_wrap.pack(fill=BOTH, expand=True, padx=10, pady=(0, 8))

        columns = ("no", "scene", "chars", "action", "dur", "quality")
        self.director_shot_tree = ttk.Treeview(
            table_wrap,
            columns=columns,
            show="headings",
            height=14,
        )
        self.director_shot_tree.heading("no", text="#")
        self.director_shot_tree.heading("scene", text="场景")
        self.director_shot_tree.heading("chars", text="人物")
        self.director_shot_tree.heading("action", text="镜头内容")
        self.director_shot_tree.heading("dur", text="时长")
        self.director_shot_tree.heading("quality", text="质检")

        self.director_shot_tree.column("no", width=46, anchor="center", stretch=False)
        self.director_shot_tree.column("scene", width=200, anchor="w", stretch=True)
        self.director_shot_tree.column("chars", width=140, anchor="w", stretch=True)
        self.director_shot_tree.column("action", width=260, anchor="w", stretch=True)
        self.director_shot_tree.column("dur", width=64, anchor="center", stretch=False)
        self.director_shot_tree.column("quality", width=150, anchor="w", stretch=False)

        yscroll = ttk.Scrollbar(table_wrap, orient=VERTICAL, command=self.director_shot_tree.yview)
        self.director_shot_tree.configure(yscrollcommand=yscroll.set)
        self.director_shot_tree.pack(side=LEFT, fill=BOTH, expand=True)
        yscroll.pack(side=RIGHT, fill=Y)

        self.director_shot_tree.bind("<<TreeviewSelect>>", self._on_director_shot_selected)
        self.director_shot_tree.insert("", END, values=("-", "点击“生成导演脚本包”开始", "-", "-", "-", "-"))

    def _build_director_right_panel(self, right_panel: tk.Frame) -> None:
        """Build details, script, and quality panel."""
        right_split = ttk.PanedWindow(right_panel, orient="vertical")
        right_split.pack(fill=BOTH, expand=True)

        detail_box = tk.Frame(right_split, bg=Theme.SURFACE, relief=tk.SOLID, borderwidth=1)
        info_box = tk.Frame(right_split, bg=Theme.SURFACE, relief=tk.SOLID, borderwidth=1)
        right_split.add(detail_box, weight=3)
        right_split.add(info_box, weight=2)
        self._build_director_detail_box(detail_box)
        self._build_director_info_box(info_box)

    def _build_director_detail_box(self, detail_box: tk.Frame) -> None:
        """Build selected shot detail panel."""
        detail_header = tk.Frame(detail_box, bg=Theme.SURFACE)
        detail_header.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(
            detail_header,
            text="🔎 当前镜头详情",
            font=(Theme.FONT_FAMILY, 12, "bold"),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
        ).pack(side=LEFT)
        self.director_selected_title_var = tk.StringVar(value="未选择分镜")
        tk.Label(
            detail_header,
            textvariable=self.director_selected_title_var,
            font=(Theme.FONT_FAMILY, 9),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_SECONDARY,
        ).pack(side=RIGHT)
        self.director_shot_detail_text = tk.Text(
            detail_box,
            wrap=tk.WORD,
            font=(Theme.FONT_FAMILY_MONO, 10),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            insertbackground=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=12,
            pady=10,
        )
        self.director_shot_detail_text.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        self.director_shot_detail_text.insert("1.0", "选择左侧分镜后显示详细信息")

    def _build_director_info_box(self, info_box: tk.Frame) -> None:
        """Build character/script/quality tabs."""
        info_header = tk.Frame(info_box, bg=Theme.SURFACE)
        info_header.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(
            info_header,
            text="🧾 人物、脚本与质检报告",
            font=(Theme.FONT_FAMILY, 12, "bold"),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
        ).pack(side=LEFT)

        tabs = ttk.Notebook(info_box)
        tabs.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        tab_char = tk.Frame(tabs, bg=Theme.SURFACE)
        tab_script = tk.Frame(tabs, bg=Theme.SURFACE)
        tab_quality = tk.Frame(tabs, bg=Theme.SURFACE)
        tabs.add(tab_char, text="👥 人物")
        tabs.add(tab_script, text="📝 脚本")
        tabs.add(tab_quality, text="✅ 质检")
        self.director_characters_text = self._create_director_info_text(
            tab_char, font=(Theme.FONT_FAMILY, 10), placeholder="尚未生成人物信息"
        )
        self.director_characters_text.pack(fill=BOTH, expand=True)
        self.director_script_text = self._create_director_info_text(
            tab_script, font=(Theme.FONT_FAMILY, 10), placeholder="尚未生成导演脚本"
        )
        self.director_script_text.pack(fill=BOTH, expand=True)
        self.director_quality_text = self._create_director_info_text(
            tab_quality, font=(Theme.FONT_FAMILY_MONO, 10), placeholder="尚未生成质检报告"
        )
        self.director_quality_text.pack(fill=BOTH, expand=True)

    def _create_director_info_text(self, parent: tk.Frame, *, font: tuple, placeholder: str) -> tk.Text:
        """Create a shared text widget used by info tabs."""
        text_widget = tk.Text(
            parent,
            wrap=tk.WORD,
            font=font,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            insertbackground=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=8,
            pady=8,
        )
        text_widget.insert("1.0", placeholder)
        return text_widget

    def _update_director_page_with_package(self, package: dict, shot_lines: list[str], markdown_path=None) -> None:
        """Refresh director page from generated package."""
        del shot_lines  # UI now renders directly from structured package.

        normalized_package = package if isinstance(package, dict) else {}
        self._last_director_package = normalized_package
        self._director_last_markdown_path = markdown_path

        report = DirectorScriptBuilder.build_quality_report(normalized_package)
        self.director_stat_shots_var.set(str(report["total_shots"]))
        self.director_stat_chars_var.set(str(report["total_characters"]))
        self.director_stat_duration_var.set(f"{report['total_duration_sec']} 秒")
        self.director_stat_quality_var.set(f"{report['completeness_percent']}%")
        self.director_stat_problem_var.set(str(report["problem_shots"]))

        if hasattr(self, "director_characters_text"):
            self.director_characters_text.delete("1.0", END)
            self.director_characters_text.insert("1.0", self._build_director_character_text(normalized_package))

        if hasattr(self, "director_script_text"):
            script = str(normalized_package.get("director_script_markdown", "")).strip()
            self.director_script_text.delete("1.0", END)
            self.director_script_text.insert("1.0", script or "未返回导演脚本正文")

        if hasattr(self, "director_quality_text"):
            quality_text = DirectorScriptBuilder.to_quality_text(normalized_package)
            if markdown_path:
                quality_text = f"{quality_text}\n\n脚本文件：{markdown_path}"
            self.director_quality_text.delete("1.0", END)
            self.director_quality_text.insert("1.0", quality_text)

        self._render_director_shot_table(preserve_selection=True)

        try:
            if hasattr(self, "status"):
                self.status.set(
                    f"✅ 导演页已更新：{report['total_shots']} 个分镜，完整度 {report['completeness_percent']}%"
                )
        except Exception:
            pass

    def _build_director_character_text(self, package: dict) -> str:
        """Render character cards into rich text."""
        rows: list[str] = []
        characters = package.get("characters", []) if isinstance(package.get("characters"), list) else []
        for character in characters:
            if not isinstance(character, dict):
                continue
            name = str(character.get("name", "")).strip()
            if not name:
                continue
            role = str(character.get("role", "")).strip()
            appearance = str(character.get("appearance_anchor", "")).strip()
            goal = str(character.get("goal", "")).strip()
            arc = str(character.get("arc", "")).strip()
            voice_tone = str(character.get("voice_tone", "")).strip()
            consistency_notes = str(character.get("consistency_notes", "")).strip()

            rows.append(f"【{name}】")
            if role:
                rows.append(f"角色：{role}")
            if appearance:
                rows.append(f"外观锚点：{appearance}")
            if goal:
                rows.append(f"目标：{goal}")
            if arc:
                rows.append(f"弧光：{arc}")
            if voice_tone:
                rows.append(f"语气：{voice_tone}")
            if consistency_notes:
                rows.append(f"一致性备注：{consistency_notes}")
            rows.append("")

        return "\n".join(rows).strip() or "未返回人物信息"

    def _schedule_director_filter(self) -> None:
        """Debounce filter rendering to keep interaction smooth."""
        if self._director_filter_job is not None:
            try:
                self.after_cancel(self._director_filter_job)
            except Exception:
                pass
        self._director_filter_job = self.after(180, lambda: self._render_director_shot_table(preserve_selection=True))

    def _on_director_filter_changed(self, *_args) -> None:
        """On keyword filter changed."""
        self._schedule_director_filter()

    def _on_director_issue_only_changed(self) -> None:
        """Toggle issue-only filter."""
        self._render_director_shot_table(preserve_selection=True)

    def _clear_director_filter(self) -> None:
        """Clear filter controls."""
        self.director_issue_only_var.set(False)
        self.director_filter_var.set("")
        self._render_director_shot_table(preserve_selection=True)

    def _render_director_shot_table(self, preserve_selection: bool = True) -> None:
        """Render shot rows with current filters."""
        if not hasattr(self, "director_shot_tree"):
            return
        if not isinstance(getattr(self, "_last_director_package", None), dict):
            return

        previous_shot_no = self._resolve_director_previous_shot_no(preserve_selection)
        self._clear_director_shot_rows()
        shots = DirectorScriptBuilder.iter_shots(self._last_director_package)
        keyword, issue_only = self._get_director_filter_values()
        visible_count, target_iid = self._populate_director_shot_rows(
            shots, keyword=keyword, issue_only=issue_only, previous_shot_no=previous_shot_no
        )
        self.director_table_hint_var.set(f"{visible_count} / {len(shots)}")
        if visible_count == 0:
            self._render_director_empty_filter_state()
            return
        self._select_director_target_row(target_iid)

    def _resolve_director_previous_shot_no(self, preserve_selection: bool) -> int | None:
        """Resolve current selected shot number for selection preservation."""
        if not preserve_selection:
            return None
        selected_idx = self._get_selected_director_shot_index()
        selected_shot = self._get_director_shot_by_index(selected_idx) if selected_idx is not None else None
        if isinstance(selected_shot, dict):
            shot_no = selected_shot.get("shot_no")
            if shot_no is not None:
                return shot_no
        return self._director_selected_shot_no

    def _clear_director_shot_rows(self) -> None:
        """Clear tree rows and index map."""
        for item in self.director_shot_tree.get_children():
            self.director_shot_tree.delete(item)
        self._director_tree_index_map = {}

    def _get_director_filter_values(self) -> tuple[str, bool]:
        """Read keyword and issue-only filters from UI."""
        keyword = self.director_filter_var.get().strip().lower() if hasattr(self, "director_filter_var") else ""
        issue_only = bool(self.director_issue_only_var.get()) if hasattr(self, "director_issue_only_var") else False
        return keyword, issue_only

    def _populate_director_shot_rows(
        self,
        shots: list[dict],
        *,
        keyword: str,
        issue_only: bool,
        previous_shot_no: int | None,
    ) -> tuple[int, str | None]:
        """Insert filtered shot rows and return visible count + target iid."""
        visible_count = 0
        target_iid = None
        for idx, shot in enumerate(shots):
            issues = DirectorScriptBuilder.get_shot_quality_issues(shot)
            if not self._director_shot_matches_filters(shot, issues, keyword=keyword, issue_only=issue_only):
                continue
            iid, shot_no = self._insert_director_shot_row(idx, shot, issues)
            visible_count += 1
            if previous_shot_no is not None and str(shot_no) == str(previous_shot_no):
                target_iid = iid
        return visible_count, target_iid

    def _director_shot_matches_filters(self, shot: dict, issues: list[str], *, keyword: str, issue_only: bool) -> bool:
        """Check whether one shot should be visible under current filters."""
        if issue_only and not issues:
            return False
        if not keyword:
            return True
        haystack = self._build_director_shot_haystack(shot, issues)
        return keyword in haystack

    def _build_director_shot_haystack(self, shot: dict, issues: list[str]) -> str:
        """Build searchable haystack for one shot."""
        scene = f"{shot.get('location', '')} {shot.get('time', '')}".strip()
        chars = self._format_shot_character_names(shot)
        action = str(shot.get("action", "")).strip()
        return " ".join(
            [
                scene,
                chars,
                action,
                str(shot.get("veo_prompt", "")),
                " ".join(issues),
                str(shot.get("shot_type", "")),
                str(shot.get("camera_movement", "")),
            ]
        ).lower()

    def _insert_director_shot_row(self, idx: int, shot: dict, issues: list[str]) -> tuple[str, int]:
        """Insert one shot row and return iid + shot_no."""
        shot_no = shot.get("shot_no", idx + 1)
        scene = f"{shot.get('location', '')} {shot.get('time', '')}".strip() or "-"
        chars = self._format_shot_character_names(shot)
        action = str(shot.get("action", "")).strip()
        issue_summary = "通过" if not issues else issues[0]
        duration = f"{shot.get('duration_sec', '-')}" + ("秒" if str(shot.get("duration_sec", "")).strip() else "")
        action_short = action[:34] + "..." if len(action) > 34 else (action or "-")
        issue_short = issue_summary[:16] + "..." if len(issue_summary) > 16 else issue_summary

        iid = self.director_shot_tree.insert(
            "",
            END,
            values=(shot_no, scene, chars or "-", action_short, duration or "-", issue_short),
        )
        self._director_tree_index_map[iid] = idx
        return iid, shot_no

    def _render_director_empty_filter_state(self) -> None:
        """Render empty state when no shot matches current filters."""
        self.director_shot_tree.insert("", END, values=("-", "没有匹配的分镜", "-", "-", "-", "-"))
        self.director_stat_selected_var.set("未选择")
        self.director_selected_title_var.set("未选择分镜")
        if hasattr(self, "director_shot_detail_text"):
            self.director_shot_detail_text.delete("1.0", END)
            self.director_shot_detail_text.insert("1.0", "当前筛选条件下没有可显示的分镜")

    def _select_director_target_row(self, target_iid: str | None) -> None:
        """Select target row, fallback to first visible row."""
        if target_iid is None:
            rows = self.director_shot_tree.get_children()
            if rows:
                target_iid = rows[0]
        if target_iid is None:
            return
        self.director_shot_tree.selection_set(target_iid)
        self.director_shot_tree.focus(target_iid)
        self._on_director_shot_selected(None)

    @staticmethod
    def _format_shot_character_names(shot: dict) -> str:
        """Render compact character names."""
        names = DirectorScriptBuilder.extract_shot_characters(shot)
        return "、".join(names)

    def _get_selected_director_shot_index(self) -> int | None:
        """Resolve selected shot index from tree."""
        if not hasattr(self, "director_shot_tree"):
            return None
        selection = self.director_shot_tree.selection()
        if not selection:
            return None
        iid = selection[0]
        return self._director_tree_index_map.get(iid)

    def _get_director_shot_by_index(self, idx: int | None) -> dict | None:
        """Get shot dict by index in package shot_list."""
        if idx is None:
            return None
        shot_list = self._last_director_package.get("shot_list", [])
        if not isinstance(shot_list, list):
            return None
        if idx < 0 or idx >= len(shot_list):
            return None
        shot = shot_list[idx]
        return shot if isinstance(shot, dict) else None

    def _on_director_shot_selected(self, _event=None) -> None:
        """Render selected shot details on director page."""
        shot_index = self._get_selected_director_shot_index()
        shot = self._get_director_shot_by_index(shot_index)
        if shot is None:
            return

        detail_text = DirectorScriptBuilder.format_shot_detail(shot, fallback_index=shot_index or 0)
        self.director_shot_detail_text.delete("1.0", END)
        self.director_shot_detail_text.insert("1.0", detail_text)

        shot_no = shot.get("shot_no", (shot_index or 0) + 1)
        scene = f"{shot.get('location', '')} {shot.get('time', '')}".strip()
        self.director_stat_selected_var.set(str(shot_no))
        self.director_selected_title_var.set(f"Shot {shot_no} · {scene or '场景未命名'}")
        try:
            self._director_selected_shot_no = int(shot_no)
        except Exception:
            self._director_selected_shot_no = None

        self._sync_image_shot_selection(shot_index)

    def _sync_image_shot_selection(self, idx: int | None) -> None:
        """Sync selection to image tab shot list without feedback loops."""
        if idx is None:
            return
        if self._director_selection_sync_lock:
            return
        if not hasattr(self, "shots_listbox") or not hasattr(self, "parsed_shots"):
            return
        if idx < 0 or idx >= len(self.parsed_shots):
            return

        try:
            self._director_selection_sync_lock = True
            self.shots_listbox.selection_clear(0, END)
            self.shots_listbox.selection_set(idx)
            self.shots_listbox.activate(idx)
            self._on_shot_listbox_selected(None)
        except Exception:
            pass
        finally:
            self._director_selection_sync_lock = False

    def _on_copy_director_shot_detail(self) -> None:
        """Copy current shot detail text to clipboard."""
        idx = self._get_selected_director_shot_index()
        if idx is None:
            messagebox.showwarning("提示", "请先选择一个分镜")
            return
        if not hasattr(self, "director_shot_detail_text"):
            return

        content = self.director_shot_detail_text.get("1.0", END).strip()
        if not content:
            messagebox.showwarning("提示", "当前镜头详情为空")
            return

        self.clipboard_clear()
        self.clipboard_append(content)
        try:
            if hasattr(self, "status"):
                self.status.set("✅ 已复制当前镜头详情")
        except Exception:
            pass

    def _on_copy_director_veo_prompt(self) -> None:
        """Copy current shot veo prompt to clipboard."""
        idx = self._get_selected_director_shot_index()
        shot = self._get_director_shot_by_index(idx)
        if not shot:
            messagebox.showwarning("提示", "请先选择一个分镜")
            return

        prompt = str(shot.get("veo_prompt", "")).strip()
        if not prompt:
            messagebox.showwarning("提示", "当前镜头没有 Veo 提示词")
            return

        self.clipboard_clear()
        self.clipboard_append(prompt)
        try:
            if hasattr(self, "status"):
                self.status.set("✅ 已复制当前镜头 Veo 提示词")
        except Exception:
            pass

    def _open_director_page(self) -> None:
        """Quick jump helper."""
        if hasattr(self, "notebook") and hasattr(self, "page_director"):
            self.notebook.select(self.page_director)
        else:
            messagebox.showwarning("提示", "导演页面尚未初始化")
