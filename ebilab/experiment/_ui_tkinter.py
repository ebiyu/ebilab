from __future__ import annotations

import datetime
import queue
import subprocess
import time
import tkinter as tk
import tkinter.font as tkf
from logging import getLogger
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, TypeVar

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ._experiment_controller import EventLog, ExperimentController
from ._experiment_manager import ExperimentManager, ExperimentProtocolInfo
from .options import BoolField, FloatField, IntField, OptionField, SelectField, StrField
from .protocol import (
    ExperimentPlotter,
    ExperimentProtocol,
    PlotterContext,
)

logger = getLogger(__name__)
T = TypeVar("T")

# windows dpi workaround
try:
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # type: ignore
except:  # noqa: E722
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # type: ignore
    except:  # noqa: E722
        pass


class ProtocolTree(ttk.Treeview):
    """
    Treeview which can show list of ExperimentProtocol
    """

    def __init__(self, master: ttk.Widget, experiment_manager: ExperimentManager) -> None:
        super().__init__(master, padding=10, selectmode="browse")
        self.bind("<<TreeviewSelect>>", self._on_change)
        self.experiment_manager = experiment_manager

        self._insert_experiments("", self.experiment_manager.experiments)
        # TODO: listen change

    def _insert_experiments(self, parent: str, experiments: list[ExperimentProtocolInfo]) -> None:
        for i, experiment in enumerate(experiments):
            if experiment.children is not None:
                id = self.insert(
                    parent, "end", text=experiment.label, iid=experiment.key, open=True
                )
                self._insert_experiments(id, experiment.children)
                continue
            if experiment.protocol is not None:
                self.insert(
                    parent,
                    "end",
                    text=experiment.protocol.get_summary(),
                    iid=experiment.key,
                )

    def _on_change(self, *args, **kwargs) -> None:  # type: ignore
        self.event_generate("<<ExperimentChange>>")

    @property
    def selected_experiment_info(self) -> ExperimentProtocolInfo | None:
        """
        Active experiment
        """
        selection = self.selection()
        if len(selection) == 0:
            return None
        # ids = selection[0].split(".")
        return self.experiment_manager.get_experiment_by_key(selection[0])

    @property
    def selected_experiment(self) -> type[ExperimentProtocol] | None:
        """
        Active experiment
        """
        info = self.selected_experiment_info
        if info is None:
            return None
        return info.protocol


class DevelopPane(ttk.Frame):
    _active_experiment_key: str | None

    def __init__(self, master: ttk.Widget, *, experiment_manager: ExperimentManager) -> None:
        super().__init__(master, padding=10, relief="solid")
        self.create_widgets()
        self.experiment_manager = experiment_manager
        self._active_experiment_key = None

    def create_widgets(self) -> None:
        tk.Label(self, justify=tk.LEFT, text="Development").pack(
            side=tk.TOP, fill=tk.X, expand=False
        )

        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(side=tk.TOP, fill=tk.X, expand=False)

        self.open_button = ttk.Button(buttons_frame, text="Open", command=self._handle_open)
        self.open_button.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.reload_button = ttk.Button(buttons_frame, text="Reload", command=self._handle_reload)
        self.reload_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # TODO: reload is not implemented

        self.on_experiment_change(None)

    def _handle_reload(self) -> None:
        if self._active_experiment_key is not None:
            self.experiment_manager.reload(self._active_experiment_key)

    def _handle_open(self) -> None:
        experiment = self._active_experiment_info
        if experiment is None:
            return

        logger.info(f"Opening {str(experiment.filepath)}")
        subprocess.Popen(["notepad.exe", str(experiment.filepath)])

    def on_experiment_change(self, experiment_key: str | None) -> None:
        self._active_experiment_key = experiment_key
        if experiment_key is None:
            self.open_button["state"] = "disabled"
            self.reload_button["state"] = "disabled"
        else:
            self.open_button["state"] = "normal"
            self.reload_button["state"] = "normal"

    @property
    def _active_experiment_info(self) -> ExperimentProtocolInfo | None:
        if self._active_experiment_key is None:
            return None
        return self.experiment_manager.get_experiment_by_key(self._active_experiment_key)


# tk.Variable()
class OptionsPane(ttk.Frame):
    __label: str
    __fields: dict[str, OptionField]
    __enabled = True
    __options: dict[str, Any]
    __is_valid = True

    def __init__(self, master: ttk.Widget, label: str) -> None:
        super().__init__(master, padding=10)
        self.__fields = {}
        self.__label = label

        # build UI
        self.columnconfigure(0, weight=1)
        self._build_fields({})

    def _build_fields(self, fields: dict[str, OptionField]):  # type: ignore
        for widgets in self.winfo_children():
            widgets.destroy()

        tk.Label(self, justify="center", text=self.__label).grid(column=0, row=0, sticky=tk.N)

        self._options_widget = []
        self._options_textvars = []

        for i, (key, field) in enumerate(fields.items()):
            if isinstance(field, FloatField):
                label = tk.Label(self, text=key)
                label.grid(row=i + 1, column=0, sticky=tk.W + tk.N)

                var: Any = tk.StringVar(value=str(field.default))
                var.trace("w", self._on_update)
                widget: Any = tk.Entry(self, textvariable=var)
                widget.grid(row=i + 1, column=1, sticky=tk.EW + tk.N)

                self._options_textvars.append(var)
                self._options_widget.append(widget)
                continue
            elif isinstance(field, SelectField):
                label = tk.Label(self, text=key)
                label.grid(row=i + 1, column=0, sticky=tk.W + tk.N)

                var = tk.StringVar(value=str(field.choices[field.default_index]))
                var.trace("w", self._on_update)
                widget = ttk.Combobox(
                    self, textvariable=var, state="readonly", values=field.choices
                )
                widget.grid(row=i + 1, column=1, sticky=tk.EW + tk.N)

                self._options_textvars.append(var)
                self._options_widget.append(widget)
                continue
            elif isinstance(field, IntField):
                label = tk.Label(self, text=key)
                label.grid(row=i + 1, column=0, sticky=tk.W + tk.N)

                var = tk.StringVar(value=str(field.default))
                var.trace("w", self._on_update)
                widget = tk.Entry(self, textvariable=var)
                widget.grid(row=i + 1, column=1, sticky=tk.EW + tk.N)

                self._options_textvars.append(var)
                self._options_widget.append(widget)
                continue
            elif isinstance(field, StrField):
                label = tk.Label(self, text=key)
                label.grid(row=i + 1, column=0, sticky=tk.W + tk.N)

                var = tk.StringVar(value=str(field.default))
                var.trace("w", self._on_update)
                widget = tk.Entry(self, textvariable=var)
                widget.grid(row=i + 1, column=1, sticky=tk.EW + tk.N)

                self._options_textvars.append(var)
                self._options_widget.append(widget)
                continue
            elif isinstance(field, BoolField):
                label = tk.Label(self, text=key)
                label.grid(row=i + 1, column=0, sticky=tk.W + tk.N)

                var = tk.BooleanVar(value=field.default)
                var.trace("w", self._on_update)
                widget = tk.Checkbutton(self, variable=var)
                widget.grid(row=i + 1, column=1, sticky=tk.EW + tk.N)

                self._options_textvars.append(var)
                self._options_widget.append(widget)
                continue
            raise TypeError("Unknown field type.")

        opt = self._get_options()
        if opt is None:
            raise RuntimeError("Unexpected invalid value")
        self.__options = opt
        self.__is_valid = True

    def _on_update(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        opt = self._get_options()
        if opt is None:
            self.__is_valid = False
        else:
            self.__is_valid = True
            self.__options = opt

        self.event_generate("<<OptionsPaneUpdate>>")

    @property
    def fields(self) -> dict[str, OptionField]:
        return self.__fields

    @fields.setter
    def fields(self, fields: dict[str, OptionField]) -> None:
        self.__fields = fields
        self._build_fields(fields)

    def _get_options(self) -> dict[str, Any] | None:
        ret = {}
        for (key, field), widget, var in zip(
            self.fields.items(), self._options_widget, self._options_textvars
        ):
            if isinstance(field, FloatField):
                try:
                    val: Any = float(var.get())
                except ValueError:
                    logger.debug(f"Validation failed: {key} = {var.get()} is not float.")
                    return None
                if field.min is not None and val < field.min:
                    logger.debug(f"Validation failed: {key} = {val} < {field.min}.")
                    return None
                if field.max is not None and val > field.max:
                    logger.debug(f"Validation failed: {key} = {val} > {field.max}.")
                    return None
                ret[key] = val
                continue
            elif isinstance(field, SelectField):
                if len(field.choices) == 0:
                    raise ValueError("SelectField has no choices.")
                if isinstance(field.choices[0], int):
                    val = int(var.get())
                elif isinstance(field.choices[0], float):
                    val = float(var.get())
                else:
                    val = var.get()
                ret[key] = val
                continue
            elif isinstance(field, IntField):
                try:
                    val = int(var.get())
                except ValueError:
                    logger.debug(f"Validation failed: {key} = {var.get()} is not int.")
                    return None
                if field.min is not None and val < field.min:
                    logger.debug(f"Validation failed: {key} = {val} < {field.min}.")
                    return None
                if field.max is not None and val > field.max:
                    logger.debug(f"Validation failed: {key} = {val} > {field.max}.")
                    return None
                ret[key] = val
                continue
            elif isinstance(field, StrField):
                val = var.get()
                if (not field.allow_blank) and len(val) == 0:
                    logger.debug(f"Validation failed: {key} is blank.")
                    return None
                ret[key] = val
                continue
            elif isinstance(field, BoolField):
                val = var.get()
                ret[key] = val
                continue
            raise TypeError("Unknown field type.")
        return ret

    @property
    def options(self) -> dict[str, Any]:
        assert self.__options is not None
        return self.__options

    @property
    def is_valid(self) -> bool:
        return self.__is_valid

    @property
    def enabled(self) -> bool:
        return self.__enabled

    @enabled.setter
    def enabled(self, enabled: bool) -> None:
        self.__enabled = enabled

        if enabled:
            for widget in self._options_widget:
                if isinstance(widget, ttk.Combobox):
                    widget["state"] = "readonly"
                else:
                    widget["state"] = "normal"
        else:
            for widget in self._options_widget:
                widget["state"] = "disabled"


class ExperimentUITkinter:
    _data: list[dict[str, Any]]
    _data_queue: queue.Queue[dict[str, Any]]
    _log_queue: queue.Queue[EventLog]
    _log_cnt = 0

    _state: str = "stopped"
    _plotter: ExperimentPlotter | None = None
    _update_experiment_loop_id: str | None = None
    _protocol_options_pane: OptionsPane
    _plotter_options_pane: OptionsPane

    experiment_manager: ExperimentManager
    experiment_controller: ExperimentController | None = None
    active_experiment: ExperimentProtocol | None = None

    def __init__(self, experiment_manager: ExperimentManager) -> None:
        super().__init__()
        self.experiment_manager = experiment_manager

    def _create_ui(self) -> None:
        self._root = tk.Tk()
        self._root.iconbitmap(default=str(Path(__file__).parent.parent / "icon.ico"))
        self._root.state("zoomed")
        self._root.rowconfigure(0, weight=1)
        self._root.columnconfigure(0, minsize=300)
        self._root.columnconfigure(1, weight=1)

        # frames
        sidebar_frm = ttk.Frame(self._root, padding=10, relief="solid")
        sidebar_frm.grid(row=0, column=0, sticky=tk.NSEW)
        main_frm = ttk.Frame(self._root, padding=10, relief="solid")
        main_frm.grid(row=0, column=1, sticky=tk.NSEW)

        # experiment list pane
        experiment_list_pane = ttk.Frame(sidebar_frm, padding=10, relief="solid")
        experiment_list_pane.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        tk.Label(experiment_list_pane, justify="center", text="Experiments").pack(
            side=tk.TOP, fill=tk.Y, expand=False
        )

        self._protocol_tree = ProtocolTree(experiment_list_pane, self.experiment_manager)
        self._protocol_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._protocol_tree.bind("<<ExperimentChange>>", self._handle_experiment_change)

        self._description_label = ttk.Label(sidebar_frm, text="-")
        self._description_label.pack(side=tk.TOP, fill=tk.X)

        self.develop_pane = DevelopPane(sidebar_frm, experiment_manager=self.experiment_manager)
        self.develop_pane.pack(side=tk.TOP, fill=tk.X)

        # plotter options pane
        self._protocol_options_pane = OptionsPane(sidebar_frm, "Experiment options")
        self._protocol_options_pane.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # buttons pane
        buttons_pane = ttk.Frame(sidebar_frm, padding=10, relief="solid")
        buttons_pane.pack(side=tk.TOP, fill=tk.BOTH)

        self._experiment_label_var = tk.StringVar(value="")
        self._experiment_label_var.trace_add("write", self._validate_options_and_update_ui)
        tk.Label(buttons_pane, justify=tk.LEFT, text="Filename:").pack(
            side=tk.TOP, fill=tk.X, expand=False
        )
        self._experiment_label_entry = tk.Entry(
            buttons_pane, textvariable=self._experiment_label_var
        )
        self._experiment_label_entry.pack(side=tk.TOP, fill=tk.X, expand=False)

        self._start_button = ttk.Button(
            buttons_pane,
            text="Start",
            command=self._handle_start_experiment,
            state="disabled",
        )
        self._start_button.pack(side=tk.TOP, fill=tk.X, expand=False)
        self._stop_button = ttk.Button(
            buttons_pane,
            text="Stop",
            command=self._handle_stop_experiment,
            state="disabled",
        )
        self._stop_button.pack(side=tk.TOP, fill=tk.X, expand=False)
        self._quit_button = ttk.Button(buttons_pane, text="Quit", command=self._handle_quit)
        self._quit_button.pack(side=tk.TOP, fill=tk.X, expand=False)

        self._current_time = tk.StringVar(value="")
        current_time_label = tk.Label(
            buttons_pane, textvariable=self._current_time, font=("Arial", 18)
        )
        current_time_label.pack(side=tk.TOP, fill=tk.X, expand=False)

        self._current_t = tk.StringVar(value="-")
        current_t_label = tk.Label(buttons_pane, textvariable=self._current_t, font=("Arial", 18))
        current_t_label.pack(side=tk.TOP, fill=tk.X, expand=False)

        self._plotter_nb = ttk.Notebook(main_frm)
        tab1 = tk.Frame(self._plotter_nb)
        self._plotter_nb.pack(side=tk.TOP, fill=tk.BOTH)

        # タブに表示する文字列の設定
        self._plotter_nb.add(tab1, text="-")
        self._plotter_nb.bind("<<NotebookTabChanged>>", self._handle_plotter_change)

        # plot range
        plot_frm = ttk.Frame(main_frm, padding=10, relief="solid")
        plot_frm.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        plot_frm.rowconfigure(0, weight=1)
        plot_frm.columnconfigure(0, weight=1)
        plot_frm.columnconfigure(1, minsize=300)

        self._fig = plt.figure(figsize=(6, 3), dpi=100, constrained_layout=True)
        self._canvas = FigureCanvasTkAgg(self._fig, master=plot_frm)
        self._canvas.get_tk_widget().grid(row=0, column=0, sticky=tk.NSEW)

        # plotter options pane
        self._plotter_options_pane = OptionsPane(plot_frm, "Plot options")
        self._plotter_options_pane.grid(row=0, column=1, sticky=tk.NSEW)

        # bottom notebook
        self._bottom_nb = ttk.Notebook(main_frm)
        self._bottom_nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        table_frm = ttk.Frame(self._bottom_nb, padding=10)
        table_frm.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_frm = ttk.Frame(self._bottom_nb, padding=10)
        log_frm.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._bottom_nb.add(table_frm, text="Result")
        self._bottom_nb.add(log_frm, text="Log")

        self._result_tree = ttk.Treeview(table_frm)
        self._result_tree.column("#0", width=0)
        self._result_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self._log_tree = ttk.Treeview(log_frm)
        self._log_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._log_tree.column("#0", width=0, stretch=False)
        self._log_tree["columns"] = ["t", "time", "message"]
        self._log_tree.heading("message", text="message")
        self._log_tree.heading("time", text="time")
        self._log_tree.column("time", width=100, stretch=False)
        self._log_tree.heading("t", text="t")
        self._log_tree.column("t", width=150, stretch=False)

        lh = tkf.Font(font="TkDefaultFont").metrics("linespace")
        style = ttk.Style()
        style.configure("Treeview", rowheight=lh)

    def _handle_quit(self) -> None:
        if self._state != "stopped":
            self._handle_stop_experiment()
        if self._update_experiment_loop_id is not None:
            self._root.after_cancel(self._update_experiment_loop_id)
        self._root.quit()
        self._root.destroy()

    def _handle_experiment_change(self, _: Any) -> None:
        experiment_info = self._protocol_tree.selected_experiment_info
        experiment = self._protocol_tree.selected_experiment
        if not experiment or not experiment_info:
            return

        self.reset_data()

        # update description
        self._description_label["text"] = experiment.get_description()

        # update develop pane
        self.develop_pane.on_experiment_change(experiment_info.key)

        # update plotter list (tab)
        for tab in self._plotter_nb.tabs():  # type: ignore
            self._plotter_nb.forget(tab)

        for name in map(lambda cls: cls.name, experiment.plotter_classes or []):
            tab = tk.Frame(self._plotter_nb)
            self._plotter_nb.add(tab, text=name)
        if len(experiment.plotter_classes or []) == 0:
            tab = tk.Frame(self._plotter_nb)
            self._plotter_nb.add(tab, text="-")

        self._handle_plotter_change()

        # update cols
        columns = ["t", "time"] + experiment.columns
        self._result_tree["columns"] = columns
        self._result_tree.column("#0", width=0, stretch=False)
        self._result_tree.heading("time", text="time")
        self._result_tree.column("time", width=100, stretch=False)
        self._result_tree.heading("t", text="t")
        self._result_tree.column("t", width=150, stretch=False)

        for col in columns[2:]:
            self._result_tree.heading(col, text=col)
            self._result_tree.column(col, minwidth=100, anchor="center", stretch=True)

        self._experiment_label_var.set(experiment.name)

        self._protocol_options_pane.fields = experiment.options or {}

        self._validate_options_and_update_ui()
        self._update_ui_from_state()

    def _validate_options_and_update_ui(self, *_: Any) -> None:
        if self._state != "stopped":
            return
        if self._protocol_options_pane.is_valid and self._experiment_label_var.get() != "":
            self._start_button["state"] = "normal"
        else:
            self._start_button["state"] = "disabled"

    def _handle_plotter_change(self, *args: Any, **kwargs: Any) -> None:
        try:
            experiment = self._protocol_tree.selected_experiment
            if experiment is None:
                return
            plotter_idx = self._plotter_nb.index(self._plotter_nb.select())  # type: ignore
            Plotter = (experiment.plotter_classes or [])[plotter_idx]
        except IndexError:
            return
        self._plotter_options_pane.fields = Plotter.options or {}
        self._reset_plotter()

    def launch(self) -> None:
        """
        Entrypoint (called from launch_experiment())
        """
        self._create_ui()
        self._update_experiment_loop_id = self._root.after(30, self._update_experiment_loop)
        self._root.protocol("WM_DELETE_WINDOW", self._handle_quit)
        self._root.mainloop()

    def _get_data_from_queue(self, queue_: queue.Queue[T]) -> list[T]:
        d: list[T] = []
        while True:
            try:
                d.append(queue_.get(False))
            except queue.Empty:
                return d

    def _update_experiment_loop(self) -> None:
        """
        Called every 30 ms
        """

        try:
            self._update_ui_from_state()
            # update clock
            time_str = datetime.datetime.now().strftime("%H:%M:%S")
            self._current_time.set(time_str)

            if self._state == "stopped":
                self._current_t.set("-")
            else:
                t = self.experiment_controller._get_t()
                self._current_t.set(f"t = {t:.0f}")

            if self._state != "stopped":
                data = self._get_data_from_queue(self._data_queue)

                for d in data:
                    self._data.append(d)

                    experiment = self._protocol_tree.selected_experiment
                    if experiment is None:
                        return

                    columns = experiment.columns

                    # insert to table
                    row_list = [str(d["t"]), str(d["time"])]
                    for col in columns:
                        if col in d:
                            row_list.append(str(d[col]))
                        else:
                            row_list.append("")
                    self._result_tree.insert("", tk.END, values=row_list)
                    self._result_tree.yview_moveto(1)
                self._draw_plot()

                # update logs
                logs = self._get_data_from_queue(self._log_queue)
                for log in logs:
                    self._log_tree.insert(
                        "", tk.END, values=[log["t"], log["time"], log["message"]]
                    )
                    self._log_tree.yview_moveto(1)
                    self._log_cnt += 1
                    self._bottom_nb.tab(1, text=f"Log ({self._log_cnt})")
        finally:
            self._update_experiment_loop_id = self._root.after(30, self._update_experiment_loop)

    def _draw_plot(self) -> None:
        if len(self._data) > 0 and self._plotter:
            df = pd.DataFrame(self._data)
            time_before_plot = time.perf_counter()
            self._plotter.update(df, self._get_plotter_context())
            logger.debug(f"Plotter.update took {time.perf_counter() - time_before_plot} s")
            time_before_draw = time.perf_counter()
            self._canvas.draw()
            logger.debug(f"canvas.draw took {time.perf_counter() - time_before_draw} s")

    def _handle_start_experiment(self) -> None:
        """
        event handler for button
        """

        experiment = self._protocol_tree.selected_experiment
        if experiment is None:
            logger.warn("Cannot start experiment because selected_experiment is none")
            return
        self.active_experiment = experiment()  # generate instance
        options = self._protocol_options_pane.options

        # generate instance
        self.experiment_controller = ExperimentController(self.active_experiment)

        # register event handlers
        self.experiment_controller.event_state_change.add_listener(
            self._handler_experiment_state_change
        )
        self.experiment_controller.event_error.add_listener(self._handler_experiment_error)
        self.experiment_controller.event_data_row.add_listener(self._handler_experiment_data_row)
        self.experiment_controller.event_log.add_listener(self._handle_experiment_log)

        self._state = "running"  # FIXME: workaround for reset_data()
        self.reset_data()

        self.experiment_controller.start(options, self.experiment_label)

    def _handle_stop_experiment(self) -> None:
        """
        event handler for button
        """
        if self.experiment_controller is not None:
            self.experiment_controller.stop()
            self.experiment_controller = None
            self.active_experiment = None

    # handlers for ExperimentManager event
    def _handler_experiment_state_change(self, state: str) -> None:
        """handle ExperimentManager event"""
        self._state = state

    def _handler_experiment_error(self, error: str) -> None:
        """handle ExperimentManager event"""
        self.show_error(error)

    def _handler_experiment_data_row(self, row: dict[str, Any]) -> None:
        """handle ExperimentManager event"""
        self._data_queue.put(row)

    def _handle_experiment_log(self, log: EventLog) -> None:
        """handle ExperimentManager event"""
        self._log_queue.put(log)

    def _update_ui_from_state(self) -> None:
        if self._state == "running":
            self._start_button["state"] = "disabled"
            self._stop_button["state"] = "normal"
            self._quit_button["state"] = "disabled"
            self._stop_button["text"] = "Stop"
            self._experiment_label_entry["state"] = "disabled"
            self._protocol_tree.state(("disabled",))
            self._protocol_options_pane.enabled = False
        elif self._state == "stopping":
            self._start_button["state"] = "disabled"
            self._stop_button["state"] = "normal"
            self._quit_button["state"] = "normal"
            self._stop_button["text"] = "Stopping..."
            self._experiment_label_entry["state"] = "disabled"
            self._protocol_tree.state(("disabled",))
            self._protocol_options_pane.enabled = False
        else:
            if self._protocol_tree.selected_experiment:
                self._start_button["state"] = "normal"
                self._validate_options_and_update_ui()
            else:
                self._start_button["state"] = "disabled"
            self._experiment_label_entry["state"] = "normal"
            self._protocol_tree.state(("!disabled",))
            self._protocol_options_pane.enabled = True
            self._stop_button["state"] = "disabled"
            self._quit_button["state"] = "enabled"
            self._stop_button["text"] = "Stop"

    def reset_data(self) -> None:
        self._data = []
        self._data_queue = queue.Queue()
        self._log_queue = queue.Queue()
        self._log_cnt = 0
        self._bottom_nb.tab(1, text="Log")
        self._result_tree.delete(*self._result_tree.get_children())
        self._reset_plotter()

    def _reset_plotter(self) -> None:
        self._fig.clf()

        try:
            Experiment = self._protocol_tree.selected_experiment
            if Experiment is None:
                self._plotter = None
                return
            plotter_idx = self._plotter_nb.index(self._plotter_nb.select())  # type: ignore
            Plotter = (Experiment.plotter_classes or [])[plotter_idx]
        except IndexError:
            self._plotter = None
            return

        self._plotter = Plotter()
        self._plotter.fig = self._fig  # type: ignore
        if self._state == "running":
            ctx = self._get_plotter_context()
            self._plotter.prepare(ctx)  # type: ignore

    def _get_plotter_context(self) -> PlotterContext:
        return PlotterContext(
            plotter_options=self._plotter_options_pane.options,
            protocol_options=self._protocol_options_pane.options,
        )

    @property
    def experiment_label(self) -> str:
        return self._experiment_label_var.get()

    def show_error(self, msg: str) -> None:
        messagebox.showerror("Error", msg)
