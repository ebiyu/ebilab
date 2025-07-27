import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Dict, Any, List
from logging import getLogger, Handler, LogRecord
import datetime
import queue
import threading

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..api.fields import OptionField, FloatField, IntField, StrField, BoolField, SelectField

logger = getLogger(__name__)


class TkinterLogHandler(Handler):
    """tkinterのTextウィジェットにログを出力するシンプルなハンドラー"""
    
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue
        
    def emit(self, record: LogRecord):
        """ログレコードをキューに追加するだけ"""
        try:
            # ログメッセージをフォーマット
            timestamp = datetime.datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            level = record.levelname
            message = record.getMessage()
            formatted_message = f"{timestamp} - {level} - {message}\n"
            
            # キューにメッセージを追加
            self.log_queue.put(formatted_message)
        except Exception:
            # ハンドラー内でエラーが発生してもアプリケーションを止めない
            pass

class View(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ebilab UI")
        self.geometry("1200x700")

        # コントローラーからのコールバック
        self.on_experiment_selected: Optional[Callable[[str], None]] = None
        self.on_start_experiment: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_stop_experiment: Optional[Callable[[], None]] = None
        self.on_history_selected: Optional[Callable[[str], None]] = None

        # UI要素の参照
        self.exp_combo: Optional[ttk.Combobox] = None
        self.start_button: Optional[ttk.Button] = None
        self.stop_button: Optional[ttk.Button] = None
        self.param_entries: Dict[str, ttk.Entry] = {}
        self.result_tree: Optional[ttk.Treeview] = None
        self.log_text: Optional[tk.Text] = None
        self.history_tree: Optional[ttk.Treeview] = None

        # matplotlib関連
        self.figure: Optional[Figure] = None
        self.ax = None
        self.canvas: Optional[FigureCanvasTkAgg] = None

        self._create_ui()

    def _append_log_to_text(self, message: str):
        """ログテキストウィジェットにメッセージを追加"""
        try:
            if self.log_text:
                self.log_text.insert("end", message)
                self.log_text.see("end")
                
                # 行数が多くなりすぎた場合は古い行を削除
                lines = int(self.log_text.index('end-1c').split('.')[0])
                if lines > 1000:  # 1000行を超えたら古い行を削除
                    self.log_text.delete('1.0', '100.0')
        except Exception:
            pass

    def _create_ui(self):
        """UIの構築"""
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

        history_tab = self._create_history_tab(notebook)
        notebook.add(history_tab, text="実験履歴")

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

        # 実験パラメータフレーム
        self.params_frame = ttk.Labelframe(frame, text="実験パラメータ", padding=10)
        self.params_frame.grid(row=2, column=0, sticky="nsew")
        self.params_frame.columnconfigure(1, weight=1)

        # デフォルトのパラメータ
        self._create_default_parameters()

        # ボタンフレーム
        button_frame = ttk.Frame(frame, padding=(0, 20, 0, 0))
        button_frame.grid(row=3, column=0, sticky="ew")
        button_frame.columnconfigure((0, 1), weight=1)

        self.start_button = ttk.Button(
            button_frame, text="実験開始", command=self._on_start_clicked
        )
        self.start_button.grid(row=0, column=0, sticky="ew", padx=2)

        self.stop_button = ttk.Button(
            button_frame, text="中断", state="disabled", command=self._on_stop_clicked
        )
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=2)

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

    def _create_history_tab(self, parent_notebook):
        """「実験履歴」タブの中身を作成する"""
        frame = ttk.Frame(parent_notebook, padding=5)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        columns = ("timestamp", "name", "comment")
        self.history_tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.history_tree.heading("timestamp", text="実行日時")
        self.history_tree.heading("name", text="実験名")
        self.history_tree.heading("comment", text="コメント")
        self.history_tree.column("timestamp", width=80, anchor="center")
        self.history_tree.column("name", width=80, anchor="center")
        self.history_tree.insert("", "end", values=("12:15:30", "IV測定", "良好な結果"))
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_selected)
        self.history_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        plot_button = ttk.Button(
            frame, text="選択した実験のグラフを表示", command=self._on_plot_history_clicked
        )
        plot_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        return frame

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

        # -- 下半分: 結果とログを切り替えるタブ --
        result_log_notebook = ttk.Notebook(display_pane)
        display_pane.add(result_log_notebook, weight=1)

        
        # -- タブ1: ログビュー --
        log_tab = ttk.Frame(result_log_notebook, padding=5)
        result_log_notebook.add(log_tab, text="ログ")

        self.log_text = tk.Text(log_tab, height=10)
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar = ttk.Scrollbar(log_tab, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        log_scrollbar.pack(side="right", fill="y")

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

        return display_pane

    # イベントハンドラー
    def _on_experiment_combo_changed(self, event):
        """実験選択コンボボックスが変更されたとき"""
        if self.on_experiment_selected:
            selected = self.exp_combo.get()
            self.on_experiment_selected(selected)

    def _on_start_clicked(self):
        """実験開始ボタンがクリックされたとき"""
        if self.on_start_experiment:
            params = self.get_experiment_parameters()
            logger.debug(f"Starting experiment with parameters: {params}")
            self.on_start_experiment(params)

    def _on_stop_clicked(self):
        """実験中断ボタンがクリックされたとき"""
        if self.on_stop_experiment:
            self.on_stop_experiment()

    def _on_history_selected(self, event):
        """実験履歴が選択されたとき"""
        if self.history_tree and self.history_tree.selection():
            item = self.history_tree.selection()[0]
            values = self.history_tree.item(item, "values")
            if self.on_history_selected and values:
                self.on_history_selected(values[0])  # timestampを使用

    def _on_plot_history_clicked(self):
        """履歴プロットボタンがクリックされたとき"""
        if self.history_tree and self.history_tree.selection():
            item = self.history_tree.selection()[0]
            values = self.history_tree.item(item, "values")
            if self.on_history_selected and values:
                self.on_history_selected(values[0])

    # パブリックメソッド（コントローラーから呼び出される）
    def set_experiment_list(self, experiment_names: List[str]):
        """実験リストを設定"""
        if self.exp_combo:
            self.exp_combo["values"] = experiment_names
            if experiment_names:
                self.exp_combo.current(0)

    def get_experiment_parameters(self) -> Dict[str, Any]:
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
                    # param_entries[name]に対応するOptionFieldがSelectFieldかつchoices型がint/floatなら変換
                    field = self.param_fields[name]
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
                        params[name] = value
                    if "." in value:
                        params[name] = float(value)
                    else:
                        try:
                            params[name] = int(value)
                        except ValueError:
                            params[name] = value  # 文字列として保存
                else:
                    # その他のウィジェットの場合
                    params[name] = widget.get() if hasattr(widget, 'get') else None
            except (ValueError, AttributeError):
                params[name] = None
        return params

    def set_experiment_parameters(self, param_fields: Dict[str, OptionField]):
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
            if self.stop_button:
                self.stop_button.config(state="normal")
            self.add_log_message("実験が開始されました。")

        elif state == "stopping":
            if self.stop_button:
                self.stop_button.config(state="disabled", text="停止中...")
            self.add_log_message("実験を停止しています...")

        elif state in ["finished", "idle"]:
            if self.start_button:
                self.start_button.config(state="normal")
            if self.stop_button:
                self.stop_button.config(state="disabled", text="中断")
            if state == "finished":
                self.add_log_message("実験が完了しました。")

    def add_result_row(self, data: Dict[str, Any]):
        """結果テーブルに新しい行を追加"""

        if self.result_tree:
            columns = self.result_tree["columns"]
            values = [data.get(col, "") for col in columns]

            self.result_tree.insert("", "end", values=values)

            # スクロールを最下部に移動
            children = self.result_tree.get_children()
            if children:
                self.result_tree.see(children[-1])

    def add_log_message(self, message: str):
        """ログメッセージを追加（loggerを使用）"""
        logger.info(message)

    def clear_results(self):
        """結果をクリア"""
        if self.result_tree:
            # 既存の結果をクリア
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
    
    def set_result_columns(self, columns: List[str]):
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
        x_data: List[float],
        y_data: List[float],
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


if __name__ == "__main__":
    app = View()
    app.mainloop()
