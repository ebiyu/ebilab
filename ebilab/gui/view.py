from __future__ import annotations

import tkinter as tk
from logging import getLogger
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image, ImageTk

from ..api.fields import BoolField, FloatField, IntField, OptionField, SelectField, StrField

logger = getLogger(__name__)


class View(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ebilab UI")
        self.geometry("1200x700")

        # コントローラーからのコールバック
        self.on_experiment_selected: Callable[[str], None] | None = None
        self.on_plotter_selected: Callable[[str], None] | None = None
        self.on_plotter_parameter_changed: Callable[[], None] | None = None
        self.on_start_experiment: Callable[[dict[str, Any]], None] | None = None
        self.on_debug_experiment: Callable[[dict[str, Any]], None] | None = None
        self.on_stop_experiment: Callable[[], None] | None = None
        self.on_sync: Callable[[], None] | None = None
        self.on_history_selected: Callable[[str], None] | None = None
        self.on_history_comment_updated: Callable[[str, str], None] | None = None

        # UI要素の参照
        self.exp_combo: ttk.Combobox | None = None
        self.plotter_combo: ttk.Combobox | None = None
        self.start_button: ttk.Button | None = None
        self.debug_button: ttk.Button | None = None
        self.stop_button: ttk.Button | None = None
        self.sync_button: ttk.Button | None = None
        self.param_entries: dict[str, ttk.Entry] = {}
        self.plotter_param_entries: dict[str, ttk.Entry] = {}
        self.result_tree: ttk.Treeview | None = None
        self.log_tree: ttk.Treeview | None = None
        self.current_log_level: tk.StringVar | None = None
        self.log_level_buttons: dict[str, ttk.Button] = {}
        self.exp_only_var: tk.BooleanVar | None = None
        self.history_tree: ttk.Treeview | None = None
        self.comment_edit_entry: ttk.Entry | None = None  # コメント編集用Entry
        self.top_debug_warning_label: tk.Label | None = None  # トップレベル警告ラベル

        # ログデータの保存（フィルタリング用）
        self.log_entries: list[dict[str, Any]] = []

        # matplotlib関連
        self.figure: Figure | None = None
        self.ax = None
        self.canvas: FigureCanvasTkAgg | None = None

        # アイコンを読み込み（適切なサイズで）
        icon_size = self._calculate_icon_size()
        self._load_icons(icon_size)

        self._create_ui()
        self._setup_keyboard_shortcuts()

    def _calculate_icon_size(self):
        return (30, 30)
        """画面サイズに応じて適切なアイコンサイズを計算する"""
        try:
            # 画面の幅と高さを取得
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()

            # 解像度に基づいてアイコンサイズを決定
            # 一般的なサイズ基準:
            # - 小さな画面 (1366x768以下): 16px
            # - 中程度の画面 (1920x1080): 20px
            # - 大きな画面 (2560x1440以上): 24px
            # - 4K画面 (3840x2160以上): 32px

            if screen_width <= 1366 or screen_height <= 768:
                return (16, 16)
            elif screen_width <= 1920 or screen_height <= 1080:
                return (20, 20)
            elif screen_width <= 2560 or screen_height <= 1440:
                return (24, 24)
            else:  # 4K or larger
                return (28, 28)

        except Exception:
            # エラーの場合はデフォルトサイズを返す
            return (20, 20)

    def _load_icons(self, icon_size=(20, 20)):
        """アイコン画像を読み込む"""
        try:
            # アイコンディレクトリのパスを取得
            icons_dir = Path(__file__).parent / "icons"

            # 各アイコンを読み込み、リサイズしてPhotoImageに変換
            self.play_icon = self._load_and_resize_icon(icons_dir / "play.png", icon_size)
            self.debug_icon = self._load_and_resize_icon(icons_dir / "debug.png", icon_size)
            self.stop_icon = self._load_and_resize_icon(icons_dir / "stop.png", icon_size)
            self.sync_icon = self._load_and_resize_icon(icons_dir / "sync.png", icon_size)

        except Exception as e:
            logger.warning(f"アイコンの読み込みに失敗しました: {e}")
            # フォールバック用に None を設定
            self.play_icon = None
            self.debug_icon = None
            self.stop_icon = None
            self.sync_icon = None

    def _load_and_resize_icon(self, icon_path, size):
        """アイコンを読み込んでリサイズする"""
        try:
            # PILでイメージを開く
            image = Image.open(icon_path)
            # リサイズ（アンチエイリアシング付き）
            image = image.resize(size, Image.Resampling.LANCZOS)
            # tkinterで使用できるPhotoImageに変換
            return ImageTk.PhotoImage(image)
        except Exception as e:
            logger.warning(f"アイコンのリサイズに失敗しました ({icon_path}): {e}")
            return None

    def _create_tooltip(self, widget, text):
        """ウィジェットにツールチップを追加"""

        def on_enter(event):
            # ツールチップウィンドウを作成
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

            label = tk.Label(
                tooltip,
                text=text,
                background="lightyellow",
                relief="solid",
                borderwidth=1,
                font=("Arial", 9),
            )
            label.pack()

            # ツールチップを保存（離脱時に削除するため）
            widget.tooltip = tooltip

        def on_leave(event):
            # ツールチップを削除
            if hasattr(widget, "tooltip"):
                widget.tooltip.destroy()
                delattr(widget, "tooltip")

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def add_log_entry(self, log_info: dict[str, Any]):
        """ログTreeViewにログエントリを追加"""
        try:
            if not self.log_tree:
                return

            # ログデータを保存（フィルタ再適用のため）
            self.log_entries.append(log_info)

            # 行数制限（1000行を超えたら古いエントリを削除）
            if len(self.log_entries) > 1000:
                self.log_entries = self.log_entries[-900:]  # 900行残す

            # フィルタリング処理
            if not self._should_show_log(log_info):
                return

            self._add_log_to_tree(log_info)

        except Exception:
            pass

    def _add_log_to_tree(self, log_info: dict[str, Any]):
        """ログエントリをTreeViewに追加（内部使用）"""
        # メッセージに例外情報があれば追加
        message = log_info["message"]
        if "exception" in log_info:
            message += f"\n{log_info['exception']}"

        # TreeViewに追加
        level = log_info["level"]
        item_id = self.log_tree.insert(
            "",
            "end",
            values=(log_info["timestamp"], level, log_info["logger_name"], message),
            tags=(level,),  # ログレベルをタグとして設定
        )

        # 最新エントリまでスクロール
        self.log_tree.see(item_id)

    def _should_show_log(self, log_info: dict[str, Any]) -> bool:
        """ログをフィルタリングして表示するかどうかを判定"""
        # ログレベルフィルタ
        if self.current_log_level:
            selected_level = self.current_log_level.get()
            level_map = {
                "DEBUG": 10,
                "INFO": 20,
                "WARNING": 30,
                "ERROR": 40,
                "CRITICAL": 50,
            }
            min_level = level_map.get(selected_level, 20)  # デフォルトはINFO
            if log_info["level_no"] < min_level:
                return False

        # 実験ログのみフィルタ
        if self.exp_only_var and self.exp_only_var.get():
            logger_name = log_info["logger_name"]
            # 実験関連のロガー名パターンをチェック
            if not logger_name.startswith("ebilab.experiment"):
                return False

        return True

    def clear_log(self):
        """ログをクリア"""
        if self.log_tree:
            for item in self.log_tree.get_children():
                self.log_tree.delete(item)
        self.log_entries.clear()

    def _refresh_log_display(self):
        """現在のフィルタ設定でログ表示を更新"""
        if not self.log_tree:
            return

        # TreeViewをクリア
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)

        # 保存されたログエントリを再フィルタリングして表示
        for log_info in self.log_entries:
            if self._should_show_log(log_info):
                self._add_log_to_tree(log_info)

    def _create_ui(self):
        """UIの構築"""
        # --- トップレベルデバッグ警告（初期状態では非表示）---
        self.top_debug_warning_label = tk.Label(
            self,
            text="⚠ デバッグモード実行中 - データは保存されません ⚠",
            bg="#dc3545",
            fg="white",
            font=("Arial", 10, "bold"),
            pady=3,
            height=1,
        )
        # 初期状態では非表示

        # --- メインの2カラム構成 ---
        main_pane = ttk.PanedWindow(self, orient="horizontal")
        main_pane.pack(fill="both", expand=True)

        # 1. 左側のコントロールパネル
        control_frame = self._create_control_panel(main_pane)
        main_pane.add(control_frame, weight=1)

        # 2. 右側の表示エリア (プロット + 結果/ログタブ)
        display_frame = self._create_display_panel(main_pane)
        main_pane.add(display_frame, weight=3)

    def _create_control_panel(self, parent):
        """左側のコントロールパネルを作成する"""
        frame = ttk.Frame(parent, padding=(10, 10, 5, 10))

        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True)

        settings_tab = self._create_settings_tab(notebook)
        notebook.add(settings_tab, text="実験設定")

        return frame

    def _create_settings_tab(self, parent_notebook):
        """「実験設定」タブの中身を作成する"""
        frame = ttk.Frame(parent_notebook, padding=5)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="実験選択").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.exp_combo = ttk.Combobox(frame, values=["IV測定", "抵抗の時間変化"], state="readonly")
        self.exp_combo.current(0)
        self.exp_combo.bind("<<ComboboxSelected>>", self._on_experiment_combo_changed)
        self.exp_combo.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        # プロッター選択
        ttk.Label(frame, text="プロッター選択").grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.plotter_combo = ttk.Combobox(frame, values=[], state="readonly")
        self.plotter_combo.bind("<<ComboboxSelected>>", self._on_plotter_combo_changed)
        self.plotter_combo.grid(row=3, column=0, sticky="ew", pady=(0, 15))

        # プロッターパラメータフレーム
        self.plotter_params_frame = ttk.Labelframe(frame, text="プロッターパラメータ", padding=10)
        self.plotter_params_frame.grid(row=4, column=0, sticky="nsew")
        self.plotter_params_frame.columnconfigure(1, weight=1)

        # 実験パラメータフレーム
        self.params_frame = ttk.Labelframe(frame, text="実験パラメータ", padding=10)
        self.params_frame.grid(row=5, column=0, sticky="nsew")
        self.params_frame.columnconfigure(1, weight=1)

        # デフォルトのパラメータ
        self._create_default_parameters()

        # ボタンフレーム
        button_frame = ttk.Frame(frame, padding=(0, 20, 0, 0))
        button_frame.grid(row=6, column=0, sticky="ew")
        button_frame.columnconfigure(0, weight=3)  # メインボタン用（重み大）
        button_frame.columnconfigure(1, weight=1)  # サブボタン用（重み小）

        # 1段目: 開始ボタン（大）とデバッグボタン（小）
        self.start_button = ttk.Button(
            button_frame,
            image=self.play_icon if self.play_icon else None,
            text="▶" if not self.play_icon else "",
            command=self._on_start_clicked,
        )
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 2), pady=(0, 2))
        self._create_tooltip(self.start_button, "実験開始 (F5)")

        self.debug_button = ttk.Button(
            button_frame,
            image=self.debug_icon if self.debug_icon else None,
            text="🐛" if not self.debug_icon else "",
            command=self._on_debug_clicked,
        )
        self.debug_button.grid(row=0, column=1, sticky="ew", padx=(2, 0), pady=(0, 2))
        self._create_tooltip(self.debug_button, "デバッグ実行 (F6)")

        # 2段目: 中断ボタン（大）と同期ボタン（小）
        self.stop_button = ttk.Button(
            button_frame,
            image=self.stop_icon if self.stop_icon else None,
            text="⏹" if not self.stop_icon else "",
            state="disabled",
            command=self._on_stop_clicked,
        )
        self.stop_button.grid(row=1, column=0, sticky="ew", padx=(0, 2), pady=(2, 0))
        self._create_tooltip(self.stop_button, "実験中断 (F9)")

        self.sync_button = ttk.Button(
            button_frame,
            image=self.sync_icon if self.sync_icon else None,
            text="🔄" if not self.sync_icon else "",
            state="disabled",
            command=self._on_sync_clicked,
        )
        self.sync_button.grid(row=1, column=1, sticky="ew", padx=(2, 0), pady=(2, 0))
        self._create_tooltip(self.sync_button, "同期 (F12)")

        return frame

    def _create_default_parameters(self):
        """デフォルトのパラメータ入力フィールドを作成"""
        ttk.Label(self.params_frame, text="開始電圧 (V):").grid(row=0, column=0, sticky="w")
        self.param_entries["start_voltage"] = ttk.Entry(self.params_frame)
        self.param_entries["start_voltage"].grid(row=0, column=1, sticky="ew")
        self.param_entries["start_voltage"].insert(0, "0.0")

        ttk.Label(self.params_frame, text="終了電圧 (V):").grid(row=1, column=0, sticky="w")
        self.param_entries["end_voltage"] = ttk.Entry(self.params_frame)
        self.param_entries["end_voltage"].grid(row=1, column=1, sticky="ew")
        self.param_entries["end_voltage"].insert(0, "1.0")

        ttk.Label(self.params_frame, text="ステップ数:").grid(row=2, column=0, sticky="w")
        self.param_entries["steps"] = ttk.Entry(self.params_frame)
        self.param_entries["steps"].grid(row=2, column=1, sticky="ew")
        self.param_entries["steps"].insert(0, "10")

    def _create_display_panel(self, parent):
        """右側の表示エリア（プロット＋結果/ログタブ）を作成する"""
        display_pane = ttk.PanedWindow(parent, orient="vertical")

        # -- 上半分: プロットエリア --
        plot_frame = ttk.Frame(display_pane)

        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Real-time Plot")
        self.ax.set_xlabel("X-axis")
        self.ax.set_ylabel("Y-axis")
        self.ax.grid(True)
        self.figure.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True, padx=5, pady=(10, 5))
        display_pane.add(plot_frame, weight=3)

        # -- 下半分: 結果とログと実験履歴を切り替えるタブ --
        result_log_notebook = ttk.Notebook(display_pane)
        display_pane.add(result_log_notebook, weight=1)

        # -- タブ1: ログビュー --
        log_tab = ttk.Frame(result_log_notebook, padding=5)
        result_log_notebook.add(log_tab, text="ログ")

        # ログフィルターフレーム
        log_filter_frame = ttk.Frame(log_tab)
        log_filter_frame.pack(fill="x", pady=(0, 5))

        # ログレベルフィルタ（ボタン形式）
        ttk.Label(log_filter_frame, text="レベル:").pack(side="left", padx=(0, 5))

        # ログレベルボタンフレーム
        level_button_frame = ttk.Frame(log_filter_frame)
        level_button_frame.pack(side="left", padx=(0, 15))

        self.current_log_level = tk.StringVar(value="INFO")  # デフォルト値
        self.log_level_buttons = {}

        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        # ログレベル別の色設定（ログメッセージと同じ色）
        level_colors = {
            "DEBUG": {"bg": "#f5f5f5", "fg": "black"},  # グレー
            "INFO": {"bg": "#e3f2fd", "fg": "black"},  # 薄青
            "WARNING": {"bg": "#ffc107", "fg": "black"},  # 黄
            "ERROR": {"bg": "#dc3545", "fg": "white"},  # 赤
            "CRITICAL": {"bg": "#6f42c1", "fg": "white"},  # 紫
        }

        for level in levels:
            colors = level_colors[level]
            btn = tk.Button(
                level_button_frame,
                text=level,
                width=8,
                bg=colors["bg"],
                fg=colors["fg"],
                activebackground=colors["bg"],  # クリック時の背景色
                activeforeground=colors["fg"],  # クリック時の文字色
                relief="raised",
                bd=1,
                command=lambda lvl=level: self._set_log_level(lvl),
            )
            btn.pack(side="left", padx=1)
            self.log_level_buttons[level] = btn

        # 初期選択状態を設定
        self._update_level_button_styles()

        # 実験ログのみ表示フィルタ
        self.exp_only_var = tk.BooleanVar(value=True)  # デフォルトON
        exp_only_check = ttk.Checkbutton(
            log_filter_frame,
            text="実験ログのみ表示",
            variable=self.exp_only_var,
            command=self._on_log_filter_changed,
        )
        exp_only_check.pack(side="left", padx=(0, 15))

        # ログクリアボタン
        clear_log_btn = ttk.Button(log_filter_frame, text="ログクリア", command=self.clear_log)
        clear_log_btn.pack(side="right")

        # ログTreeView
        log_frame = ttk.Frame(log_tab)
        log_frame.pack(fill="both", expand=True)

        log_columns = ("timestamp", "level", "logger", "message")
        self.log_tree = ttk.Treeview(log_frame, columns=log_columns, show="headings", height=8)
        self.log_tree.heading("timestamp", text="時刻")
        self.log_tree.heading("level", text="レベル")
        self.log_tree.heading("logger", text="ロガー")
        self.log_tree.heading("message", text="メッセージ")

        # 列幅調整
        self.log_tree.column("timestamp", width=80, anchor="center")
        self.log_tree.column("level", width=70, anchor="center")
        self.log_tree.column("logger", width=120, anchor="w")
        self.log_tree.column("message", width=300, anchor="w")

        # ログレベル別のタグ設定（色分け用）
        self.log_tree.tag_configure("ERROR", foreground="white", background="#dc3545")  # 赤
        self.log_tree.tag_configure("WARNING", foreground="black", background="#ffc107")  # 黄
        self.log_tree.tag_configure("INFO", foreground="black", background="#e3f2fd")  # 薄青
        self.log_tree.tag_configure("DEBUG", foreground="black", background="#f5f5f5")  # グレー
        self.log_tree.tag_configure("CRITICAL", foreground="white", background="#6f42c1")  # 紫

        self.log_tree.pack(side="left", fill="both", expand=True)

        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=log_scrollbar.set)
        log_scrollbar.pack(side="right", fill="y")

        # 初期状態でロガー列の表示を設定
        self._update_logger_column_visibility()

        # -- タブ2: 結果テーブル --
        result_tab = ttk.Frame(result_log_notebook, padding=5)
        result_log_notebook.add(result_tab, text="結果")

        result_columns = ("timestamp", "voltage", "current", "comment")
        self.result_tree = ttk.Treeview(result_tab, columns=result_columns, show="headings")
        self.result_tree.heading("timestamp", text="Time")
        self.result_tree.heading("voltage", text="Voltage")
        self.result_tree.heading("current", text="Current")
        self.result_tree.heading("comment", text="Comment")
        self.result_tree.column("timestamp", width=100, anchor="center")
        self.result_tree.column("voltage", width=100, anchor="e")
        self.result_tree.column("current", width=100, anchor="e")
        self.result_tree.insert("", "end", values=("12:15:30.1", "-1.00 V", "0.01 A", ""))
        self.result_tree.pack(side="left", fill="both", expand=True)
        result_scrollbar = ttk.Scrollbar(
            result_tab, orient="vertical", command=self.result_tree.yview
        )
        self.result_tree.configure(yscrollcommand=result_scrollbar.set)
        result_scrollbar.pack(side="right", fill="y")

        # -- タブ3: 実験履歴 --
        history_tab = ttk.Frame(result_log_notebook, padding=5)
        result_log_notebook.add(history_tab, text="実験履歴")
        history_tab.rowconfigure(0, weight=1)
        history_tab.columnconfigure(0, weight=1)

        columns = ("timestamp", "name", "comment")
        self.history_tree = ttk.Treeview(history_tab, columns=columns, show="headings")
        self.history_tree.heading("timestamp", text="実行日時")
        self.history_tree.heading("name", text="実験名")
        self.history_tree.heading("comment", text="コメント")
        self.history_tree.column("timestamp", width=80, anchor="center")
        self.history_tree.column("name", width=80, anchor="center")
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_selected)
        self.history_tree.bind("<Double-Button-1>", self._on_history_double_click)
        self.history_tree.pack(side="left", fill="both", expand=True)

        history_scrollbar = ttk.Scrollbar(
            history_tab, orient="vertical", command=self.history_tree.yview
        )
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        history_scrollbar.pack(side="right", fill="y")

        return display_pane

    # イベントハンドラー
    def _on_experiment_combo_changed(self, event):
        """実験選択コンボボックスが変更されたとき"""
        if self.on_experiment_selected:
            selected = self.exp_combo.get()
            self.on_experiment_selected(selected)

    def _on_plotter_combo_changed(self, event):
        """プロッター選択コンボボックスが変更されたとき"""
        if self.on_plotter_selected:
            selected = self.plotter_combo.get()
            self.on_plotter_selected(selected)

    def _on_start_clicked(self):
        """実験開始ボタンがクリックされたとき"""
        if self.on_start_experiment:
            params = self.get_experiment_parameters()
            logger.debug(f"Starting experiment with parameters: {params}")
            self.on_start_experiment(params)

    def _on_debug_clicked(self):
        """デバッグ実行ボタンがクリックされたとき"""
        if self.on_debug_experiment:
            params = self.get_experiment_parameters()
            logger.debug(f"Starting debug experiment with parameters: {params}")
            self.on_debug_experiment(params)

    def _on_stop_clicked(self):
        """実験中断ボタンがクリックされたとき"""
        if self.on_stop_experiment:
            self.on_stop_experiment()

    def _on_sync_clicked(self):
        """Syncボタンがクリックされたとき"""
        if self.on_sync:
            self.on_sync()

    def _on_history_selected(self, event):
        """実験履歴が選択されたとき"""
        if self.history_tree and self.history_tree.selection():
            item_id = self.history_tree.selection()[0]
            # item_idが実験ID（iidとして設定したもの）
            if self.on_history_selected:
                self.on_history_selected(item_id)

    def _on_history_double_click(self, event):
        """実験履歴をダブルクリックしたとき（コメント編集）"""
        if not self.history_tree:
            return

        # クリックされた位置の項目を取得
        item = self.history_tree.identify("item", event.x, event.y)
        column = self.history_tree.identify("column", event.x, event.y)

        # コメント列（#3）がダブルクリックされた場合
        if item and column == "#3":
            # 既存のコメントを取得
            values = self.history_tree.item(item, "values")
            if not values or len(values) < 3:
                return

            current_comment = values[2]

            # Entryウィジェットを作成して配置
            bbox = self.history_tree.bbox(item, column)
            if bbox:
                # Entryウィジェットを作成
                self.comment_edit_entry = ttk.Entry(self.history_tree)
                self.comment_edit_entry.insert(0, current_comment)

                # Entryを表示
                self.comment_edit_entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])

                # フォーカスを設定
                self.comment_edit_entry.focus_set()
                self.comment_edit_entry.select_range(0, tk.END)

                # イベントハンドラーをバインド
                self.comment_edit_entry.bind("<Return>", lambda e: self._save_comment_edit(item))
                self.comment_edit_entry.bind("<Escape>", lambda e: self._cancel_comment_edit())
                self.comment_edit_entry.bind("<FocusOut>", lambda e: self._save_comment_edit(item))

    def _save_comment_edit(self, item_id):
        """コメント編集を保存"""
        if not self.comment_edit_entry:
            return

        new_comment = self.comment_edit_entry.get()

        # TreeViewの表示を更新
        values = list(self.history_tree.item(item_id, "values"))
        values[2] = new_comment
        self.history_tree.item(item_id, values=values)

        # コールバックを呼び出してデータを保存
        if self.on_history_comment_updated:
            self.on_history_comment_updated(item_id, new_comment)

        # Entryを削除
        self._cancel_comment_edit()

    def _cancel_comment_edit(self):
        """コメント編集をキャンセル"""
        if self.comment_edit_entry:
            self.comment_edit_entry.destroy()
            self.comment_edit_entry = None

    def _set_log_level(self, level: str):
        """ログレベルを設定"""
        self.current_log_level.set(level)
        self._update_level_button_styles()
        self._on_log_filter_changed()

    def _update_level_button_styles(self):
        """ログレベルボタンのスタイルを更新（選択状態の表示）"""
        if not self.current_log_level:
            return

        current_level = self.current_log_level.get()
        for level, button in self.log_level_buttons.items():
            if level == current_level:
                # 選択されたボタンのスタイル（押し込まれた見た目）
                button.configure(text=level, relief="sunken")
            else:
                # 非選択ボタンのスタイル（通常表示）
                button.configure(text=level, relief="raised")

    def _on_log_filter_changed(self, event=None):
        """ログフィルタが変更されたときの処理"""
        # ロガー列の表示/非表示を切り替え
        self._update_logger_column_visibility()

        # 既存のログ表示を現在のフィルタ設定で更新
        self._refresh_log_display()

    def _update_logger_column_visibility(self):
        """実験ログのみ表示設定に応じてロガー列の表示を切り替え"""
        if not self.log_tree or not self.exp_only_var:
            return

        if self.exp_only_var.get():
            # 実験ログのみ表示の場合、ロガー列を削除
            self.log_tree["displaycolumns"] = ("timestamp", "level", "message")
        else:
            # 全ログ表示の場合、ロガー列を表示
            self.log_tree["displaycolumns"] = ("timestamp", "level", "logger", "message")

    # パブリックメソッド（コントローラーから呼び出される）
    def set_experiment_list(self, experiment_names: list[str]):
        """実験リストを設定"""
        if self.exp_combo:
            self.exp_combo["values"] = experiment_names
            if experiment_names:
                self.exp_combo.current(0)

    def get_experiment_parameters(self) -> dict[str, Any]:
        """現在の実験パラメータを取得"""
        # TODO: validationを追加する
        params = {}
        for name, widget in self.param_entries.items():
            try:
                if isinstance(widget, ttk.Checkbutton):
                    # チェックボックスの場合
                    params[name] = widget.var.get()
                elif isinstance(widget, ttk.Combobox):
                    # コンボボックスの場合
                    value = widget.get()
                    field = self.param_fields.get(name) if hasattr(self, "param_fields") else None
                    if field and isinstance(field, SelectField):
                        # choicesの型を推測
                        if field.choices and isinstance(field.choices[0], int):
                            try:
                                params[name] = int(value)
                            except ValueError:
                                params[name] = value
                        elif field.choices and isinstance(field.choices[0], float):
                            try:
                                params[name] = float(value)
                            except ValueError:
                                params[name] = value
                        else:
                            params[name] = value
                    else:
                        params[name] = value
                elif isinstance(widget, ttk.Entry):
                    # エントリーの場合
                    value = widget.get()
                    # param_fieldsの型に応じて変換
                    field = self.param_fields.get(name) if hasattr(self, "param_fields") else None
                    if field:
                        if isinstance(field, FloatField):
                            try:
                                params[name] = float(value)
                            except ValueError:
                                params[name] = value
                        elif isinstance(field, IntField):
                            try:
                                params[name] = int(value)
                            except ValueError:
                                params[name] = value
                        elif isinstance(field, BoolField):
                            params[name] = bool(value)
                        else:
                            params[name] = value
                    else:
                        # フィールド情報がない場合は値から型を推測
                        if "." in value:
                            try:
                                params[name] = float(value)
                            except ValueError:
                                params[name] = value
                        else:
                            try:
                                params[name] = int(value)
                            except ValueError:
                                params[name] = value  # 文字列として保存
                else:
                    # その他のウィジェットの場合
                    params[name] = widget.get() if hasattr(widget, "get") else None
            except (ValueError, AttributeError):
                params[name] = None
        return params

    def get_plotter_parameters(self) -> dict[str, Any]:
        """現在のプロッターパラメータを取得"""
        params = {}
        for name, widget in self.plotter_param_entries.items():
            try:
                if isinstance(widget, ttk.Checkbutton):
                    # チェックボックスの場合
                    params[name] = widget.var.get()
                elif isinstance(widget, ttk.Combobox):
                    # コンボボックスの場合
                    value = widget.get()
                    field = (
                        self.plotter_param_fields.get(name)
                        if hasattr(self, "plotter_param_fields")
                        else None
                    )
                    if field and isinstance(field, SelectField):
                        # choicesの型を推測
                        if field.choices and isinstance(field.choices[0], int):
                            try:
                                params[name] = int(value)
                            except ValueError:
                                params[name] = value
                        elif field.choices and isinstance(field.choices[0], float):
                            try:
                                params[name] = float(value)
                            except ValueError:
                                params[name] = value
                        else:
                            params[name] = value
                    else:
                        params[name] = value
                elif isinstance(widget, ttk.Entry):
                    # エントリーの場合
                    value = widget.get()
                    # plotter_param_fieldsの型に応じて変換
                    field = (
                        self.plotter_param_fields.get(name)
                        if hasattr(self, "plotter_param_fields")
                        else None
                    )
                    if field:
                        if isinstance(field, FloatField):
                            try:
                                params[name] = float(value)
                            except ValueError:
                                params[name] = value
                        elif isinstance(field, IntField):
                            try:
                                params[name] = int(value)
                            except ValueError:
                                params[name] = value
                        elif isinstance(field, BoolField):
                            params[name] = bool(value)
                        else:
                            params[name] = value
                    else:
                        # フィールド情報がない場合は値から型を推測
                        if "." in value:
                            try:
                                params[name] = float(value)
                            except ValueError:
                                params[name] = value
                        else:
                            try:
                                params[name] = int(value)
                            except ValueError:
                                params[name] = value  # 文字列として保存
                else:
                    # その他のウィジェットの場合
                    params[name] = widget.get() if hasattr(widget, "get") else None
            except (ValueError, AttributeError):
                params[name] = None
        return params
        return params

    def set_plotter_list(self, plotter_names: list[str]):
        """プロッターリストを設定"""
        if self.plotter_combo:
            self.plotter_combo["values"] = plotter_names
            if plotter_names:
                self.plotter_combo.current(0)

    def set_plotter_parameters(self, fields: dict[str, Any]):
        """プロッターパラメータUIを設定"""
        # フィールド情報を保存
        self.plotter_param_fields = fields

        # 既存のウィジェットを削除
        for widget in self.plotter_params_frame.winfo_children():
            widget.destroy()
        self.plotter_param_entries.clear()

        row = 0
        for field_name, field in fields.items():
            # ラベルを作成
            label_text = field_name.replace("_", " ").title()
            ttk.Label(self.plotter_params_frame, text=f"{label_text}:").grid(
                row=row, column=0, sticky="w", pady=2
            )

            # フィールドの型に応じてウィジェットを作成
            if isinstance(field, BoolField):
                var = tk.BooleanVar(value=field.default)
                widget = ttk.Checkbutton(self.plotter_params_frame, variable=var)
                widget.var = var
                # パラメータ変更時にコールバックを呼び出し
                widget.configure(command=self._on_plotter_parameter_changed)
            elif isinstance(field, SelectField):
                widget = ttk.Combobox(
                    self.plotter_params_frame, values=field.choices, state="readonly"
                )
                widget.current(field.default_index)
                # パラメータ変更時にコールバックを呼び出し
                widget.bind("<<ComboboxSelected>>", lambda e: self._on_plotter_parameter_changed())
            else:
                widget = ttk.Entry(self.plotter_params_frame)
                widget.insert(0, str(field.default))
                # パラメータ変更時にコールバックを呼び出し（Enterキーまたはフォーカス離脱時）
                widget.bind("<Return>", lambda e: self._on_plotter_parameter_changed())
                widget.bind("<FocusOut>", lambda e: self._on_plotter_parameter_changed())

            widget.grid(row=row, column=1, sticky="ew", pady=2)
            self.plotter_param_entries[field_name] = widget
            row += 1

    def _on_plotter_parameter_changed(self):
        """プロッターパラメータが変更されたときの処理"""
        if self.on_plotter_parameter_changed:
            self.on_plotter_parameter_changed()

    def set_experiment_parameters(self, param_fields: dict[str, OptionField]):
        """実験パラメータフィールドを動的に設定"""
        # 既存のパラメータエントリをクリア
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_entries.clear()
        self.param_fields = param_fields

        # 新しいパラメータフィールドを作成
        for i, (name, field) in enumerate(param_fields.items()):
            label = ttk.Label(self.params_frame, text=f"{name}:")
            label.grid(row=i, column=0, sticky="w", pady=2)

            widget = self._create_field_widget(field)
            widget.grid(row=i, column=1, sticky="ew", pady=2)

            self.param_entries[name] = widget

    def _create_field_widget(self, field: OptionField) -> tk.Widget:
        """OptionFieldの種類に応じて適切なウィジェットを作成"""
        if isinstance(field, FloatField):
            entry = ttk.Entry(self.params_frame)
            entry.insert(0, str(field.default))
            return entry
        elif isinstance(field, IntField):
            entry = ttk.Entry(self.params_frame)
            entry.insert(0, str(field.default))
            return entry
        elif isinstance(field, StrField):
            entry = ttk.Entry(self.params_frame)
            entry.insert(0, field.default)
            return entry
        elif isinstance(field, BoolField):
            var = tk.BooleanVar(value=field.default)
            checkbox = ttk.Checkbutton(self.params_frame, variable=var)
            checkbox.var = var  # 変数を保存しておく
            return checkbox
        elif isinstance(field, SelectField):
            combo = ttk.Combobox(self.params_frame, values=field.choices, state="readonly")
            if 0 <= field.default_index < len(field.choices):
                combo.current(field.default_index)
            return combo
        else:
            # デフォルトはEntry
            entry = ttk.Entry(self.params_frame)
            return entry

    def update_experiment_state(self, state: str):
        """実験状態に基づいてUIを更新"""
        if state == "running":
            if self.start_button:
                self.start_button.config(state="disabled")
            if self.debug_button:
                self.debug_button.config(state="disabled")
            if self.stop_button:
                self.stop_button.config(state="normal")
            if self.sync_button:
                self.sync_button.config(state="normal")
            logger.info("実験が開始されました。")

        elif state == "stopping":
            if self.stop_button:
                self.stop_button.config(state="disabled")
            if self.sync_button:
                self.sync_button.config(state="disabled")
            logger.info("実験を停止しています...")

        elif state == "error":
            if self.start_button:
                self.start_button.config(state="normal")
            if self.debug_button:
                self.debug_button.config(state="normal")
            if self.stop_button:
                self.stop_button.config(state="disabled")
            if self.sync_button:
                self.sync_button.config(state="disabled")
            logger.error("実験がエラーで終了しました。")

        elif state in ["finished", "idle"]:
            if self.start_button:
                self.start_button.config(state="normal")
            if self.debug_button:
                self.debug_button.config(state="normal")
            if self.stop_button:
                self.stop_button.config(state="disabled")
            if self.sync_button:
                self.sync_button.config(state="disabled")
            if state == "finished":
                logger.info("実験が完了しました。")

    def add_result_row(self, data: dict[str, Any]):
        """結果テーブルに新しい行を追加"""

        if self.result_tree:
            columns = self.result_tree["columns"]
            values = [data.get(col, "") for col in columns]

            self.result_tree.insert("", "end", values=values)

            # スクロールを最下部に移動
            children = self.result_tree.get_children()
            if children:
                self.result_tree.see(children[-1])

    def show_debug_warning(self, show: bool):
        """デバッグモード警告の表示/非表示を切り替える"""
        if self.top_debug_warning_label:
            if show:
                self.top_debug_warning_label.pack(
                    side="top",
                    fill="x",
                    before=self.winfo_children()[1] if len(self.winfo_children()) > 1 else None,
                )
            else:
                self.top_debug_warning_label.pack_forget()

    def show_error_dialog(self, experiment_name: str, error_message: str = None):
        """実験エラー時にダイアログを表示"""
        title = "実験エラー"
        if error_message:
            message = (
                f"実験 '{experiment_name}' の実行中にエラーが発生しました。\n\n"
                f"{error_message}\n\n詳細はログファイルを確認してください。"
            )
        else:
            message = (
                f"実験 '{experiment_name}' の実行中にエラーが発生しました。\n\n"
                "詳細はログファイルを確認してください。"
            )

        messagebox.showerror(title, message)

    def show_general_error_dialog(self, title: str, message: str):
        """汎用的なエラーダイアログを表示"""
        messagebox.showerror(title, message)

    def clear_results(self):
        """結果をクリア"""
        if self.result_tree:
            # 既存の結果をクリア
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)

    def set_result_columns(self, columns: list[str]):
        """結果テーブルの列を設定"""
        if self.result_tree:
            # 列をクリアして新しい列を設定
            self.result_tree["columns"] = columns
            for col in columns:
                self.result_tree.heading(col, text=col)
                self.result_tree.column(col, anchor="center")
            # 既存の行をクリア
            self.clear_results()

    def update_plot(
        self,
        x_data: list[float],
        y_data: list[float],
        xlabel: str = "X-axis",
        ylabel: str = "Y-axis",
        title: str = "Real-time Plot",
    ):
        """プロットを更新"""
        if self.ax and self.canvas:
            self.ax.clear()
            self.ax.plot(x_data, y_data)
            self.ax.set_xlabel(xlabel)
            self.ax.set_ylabel(ylabel)
            self.ax.set_title(title)
            self.ax.grid(True)
            self.canvas.draw()

    def get_plot_figure(self) -> Figure | None:
        """プロット用のFigureオブジェクトを取得"""
        return self.figure

    def update_plot_display(self):
        """プロット表示を更新（再描画）"""
        if self.canvas:
            self.canvas.draw()

    def update_experiment_history(self, history_items: list[dict[str, str]]):
        """実験履歴を更新"""
        if not self.history_tree:
            return

        # 既存の項目をクリア
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        # 新しい項目を追加
        for item in history_items:
            self.history_tree.insert(
                "", "end", iid=item["id"], values=(item["timestamp"], item["name"], item["comment"])
            )

    def _setup_keyboard_shortcuts(self):
        """キーボードショートカットを設定"""
        # ウィンドウにフォーカスがある時にキーバインドが動作するよう設定
        self.focus_set()

        # ウィンドウ全体でキーイベントを受け取れるようにする
        self.bind_all("<F5>", self._keyboard_start_experiment)
        self.bind_all("<Alt-r>", self._keyboard_start_experiment)
        self.bind_all("<Control-r>", self._keyboard_start_experiment)
        self.bind_all("<F6>", self._keyboard_debug_experiment)
        self.bind_all("<F9>", self._keyboard_stop_experiment)
        self.bind_all("<Alt-s>", self._keyboard_stop_experiment)
        self.bind_all("<Control-s>", self._keyboard_stop_experiment)
        self.bind_all("<F12>", self._keyboard_sync)

    def _keyboard_start_experiment(self, event=None):
        """キーボードから実験開始を実行"""
        # 開始ボタンが有効な場合のみ実行
        if self.start_button and self.start_button["state"] != "disabled":
            self._on_start_clicked()

    def _keyboard_debug_experiment(self, event=None):
        """キーボードからデバッグ実行を実行"""
        # デバッグボタンが有効な場合のみ実行
        if self.debug_button and self.debug_button["state"] != "disabled":
            self._on_debug_clicked()

    def _keyboard_stop_experiment(self, event=None):
        """キーボードから実験停止を実行"""
        # 停止ボタンが有効な場合のみ実行
        if self.stop_button and self.stop_button["state"] != "disabled":
            self._on_stop_clicked()

    def _keyboard_sync(self, event=None):
        """キーボードからSyncを実行"""
        # Syncボタンが有効な場合のみ実行
        if self.sync_button and self.sync_button["state"] != "disabled":
            self._on_sync_clicked()


if __name__ == "__main__":
    app = View()
    app.mainloop()
