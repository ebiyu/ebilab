from logging import getLogger
import queue
import time
from typing import List, Optional, Type, Dict
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkf

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ._experiment_controller import ExperimentPlotter, IExperimentUI, ExperimentProtocol, PlotterContext
from .options import OptionField, FloatField, SelectField

logger = getLogger(__name__)

# windows dpi workaround
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2) 
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

class OptionsPane(ttk.Frame):
    __label: str
    __fields: Dict[str, OptionField]
    __enabled = True
    __options: dict
    __is_valid = True

    def __init__(self, master, label):
        super().__init__(master, padding=10)
        self.__fields = {}
        self.__label = label

        # build UI
        self.columnconfigure(0, weight=1)
        self._build_fields({})

    def _build_fields(self, fields: Dict[str, OptionField]):
        for widgets in self.winfo_children():
            widgets.destroy()

        tk.Label(self, justify="center", text=self.__label).grid(column=0, row=0, sticky=tk.N)

        self._options_widget = []
        self._options_textvars = []

        for i, (key, field) in enumerate(fields.items()):
            if isinstance(field, FloatField):
                label = tk.Label(self, text=key)
                label.grid(row=i + 1, column=0, sticky=tk.W + tk.N)

                var = tk.StringVar(value=str(field.default))
                var.trace("w", self._on_update)
                widget = tk.Entry(self, textvariable=var)
                widget.grid(row=i + 1, column=1, sticky=tk.EW + tk.N)

                self._options_textvars.append(var)
                self._options_widget.append(widget)
                continue
            elif isinstance(field, SelectField):
                label = tk.Label(self, text=key)
                label.grid(row=i + 1, column=0, sticky=tk.W + tk.N)

                var = tk.StringVar(value=str(field.choices[field.default_index]))
                var.trace("w", self._on_update)
                widget = ttk.Combobox(self, textvariable=var, state="readonly", values=field.choices)
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

    def _on_update(self, *args, **kwargs):
        opt = self._get_options()
        if opt is None:
            self.__is_valid = False
        else:
            self.__is_valid = True
            self.__options = opt

        self.event_generate("<<OptionsPaneUpdate>>")

    @property
    def fields(self) -> Dict[str, OptionField]:
        return self.__fields

    @fields.setter
    def fields(self, fields):
        self.__fields = fields
        self._build_fields(fields)

    def _get_options(self) -> Optional[dict]:
        ret = {}
        for (key, field), widget, var in zip(self.fields.items(), self._options_widget, self._options_textvars):
            if isinstance(field, FloatField):
                try:
                    val = float(var.get())
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
            raise TypeError("Unknown field type.")
        return ret

    @property
    def options(self) -> dict:
        assert self.__options is not None
        return self.__options

    @property
    def is_valid(self) -> bool:
        return self.__is_valid

    @property
    def enabled(self) -> bool:
        return self.__enabled

    @enabled.setter
    def enabled(self, enabled: bool):
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

class ExperimentUITkinter(IExperimentUI):
    _data_queue: queue.Queue
    log_queue: queue.Queue

    _state: str = "stopped"
    _plotter: Optional[ExperimentPlotter] = None
    _update_experiment_loop_id: Optional[str] = None
    _protocol_options_pane: OptionsPane
    _plotter_options_pane: OptionsPane

    def __init__(self) -> None:
        super().__init__()

    def _create_ui(self):
        self._root = tk.Tk()
        self._root.state("zoomed")
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)

        frm = ttk.Frame(self._root, padding=10, relief="solid")
        frm.grid(sticky="nsew")
        frm.columnconfigure(0, weight=1)
        frm.rowconfigure(1, weight=1)
        frm.rowconfigure(2, weight=1)
        frm.rowconfigure(3, weight=1)

        ctrl_frm = ttk.Frame(frm, padding=10, relief="solid")
        ctrl_frm.grid(column=0, row=0, sticky="new")
        ctrl_frm.rowconfigure(0, weight=1)
        ctrl_frm.columnconfigure(0, weight=1)
        ctrl_frm.columnconfigure(1, weight=1)
        ctrl_frm.columnconfigure(2, weight=1)
        ctrl_frm.columnconfigure(3, weight=1)

        experiment_list_pane = ttk.Frame(ctrl_frm, padding=10, relief="solid")
        experiment_list_pane.grid(column=0, row=0, sticky=tk.NSEW)
        experiment_list_pane.columnconfigure(0, weight=1)
        experiment_list_pane.rowconfigure(1, weight=1)
        tk.Label(experiment_list_pane, justify="center", text="Experiment List").grid(column=0, row=0, sticky=tk.N)

        self._experiment_list_var = tk.StringVar(value=[])
        self._experiment_list = tk.Listbox(experiment_list_pane, listvariable=self._experiment_list_var, exportselection=False, height=5)
        self._experiment_list.grid(column=0, row=1, sticky=tk.NSEW)
        self._experiment_list.bind("<<ListboxSelect>>", self._handle_experiment_change)

        # options pane
        self._protocol_options_pane = OptionsPane(ctrl_frm, "Experiment options")
        self._protocol_options_pane.grid(column=1, row=0, sticky=tk.NSEW)

        plotter_list_pane = ttk.Frame(ctrl_frm, padding=10, relief="solid")
        plotter_list_pane.grid(column=2, row=0, sticky=tk.NSEW)
        plotter_list_pane.columnconfigure(0, weight=1)
        plotter_list_pane.rowconfigure(1, weight=1)
        tk.Label(plotter_list_pane, justify="center", text="Plotter List").grid(column=0, row=0, sticky=tk.N)

        self._plotter_list_var = tk.StringVar(value=[])
        self._plotter_list = tk.Listbox(plotter_list_pane, listvariable=self._plotter_list_var, exportselection=False, height=5)
        self._plotter_list.grid(column=0, row=1, sticky=tk.NSEW)
        self._plotter_list.bind("<<ListboxSelect>>", self._handle_plotter_change)

        # options pane
        self._plotter_options_pane = OptionsPane(ctrl_frm, "Plot options")
        self._plotter_options_pane.grid(column=3, row=0, sticky=tk.NSEW)

        buttons_pane = ttk.Frame(ctrl_frm, padding=10, relief="solid")
        buttons_pane.grid(column=4, row=0, sticky="nes")

        self._experiment_label_var = tk.StringVar(value="")
        self._experiment_label_var.trace("w", self._validate_options_and_update_ui)
        tk.Label(buttons_pane, justify=tk.LEFT, text="Filename:").grid(column=0, row=0, sticky=tk.W)
        self._experiment_label_entry = tk.Entry(buttons_pane, textvariable=self._experiment_label_var)
        self._experiment_label_entry.grid(column=0, row=1)

        self._start_button = ttk.Button(buttons_pane, text="Start", command=self._handle_start_experiment, state="disabled")
        self._start_button.grid(column=0, row=2)
        self._stop_button = ttk.Button(buttons_pane, text="Stop", command=self._handle_stop_experiment, state="disabled")
        self._stop_button.grid(column=0, row=3)
        self._quit_button = ttk.Button(buttons_pane, text="Quit", command=self._handle_quit)
        self._quit_button.grid(column=0, row=4)

        plot_frm = ttk.Frame(frm, padding=10, relief="solid")
        plot_frm.grid(column=0, row=1, sticky=tk.NSEW)
        plot_frm.columnconfigure(0, weight=1)
        plot_frm.rowconfigure(0, weight=1)

        self._fig = plt.figure(figsize=(6, 3), dpi=100, constrained_layout=True)
        self._canvas = FigureCanvasTkAgg(self._fig, master=plot_frm)
        self._canvas.get_tk_widget().grid(column=0, row=0, sticky=tk.NSEW)

        table_frm = ttk.Frame(frm, padding=10, relief="solid")
        table_frm.grid(column=0, row=2, sticky="wes")
        table_frm.columnconfigure(0, weight=1)
        table_frm.rowconfigure(0, weight=1)

        self._result_tree = ttk.Treeview(table_frm)
        self._result_tree.column("#0", width=0)
        self._result_tree.grid(row=0, column=0, sticky=tk.NSEW)

        log_frm = ttk.Frame(frm, padding=10, relief="solid")
        log_frm.grid(column=0, row=3, sticky="wes")
        log_frm.columnconfigure(0, weight=1)
        log_frm.rowconfigure(0, weight=1)

        self._log_tree = ttk.Treeview(log_frm)
        self._log_tree.column("#0", width=0, stretch=False)
        self._log_tree.grid(row=0, column=0, sticky=tk.NSEW)
        self._log_tree["columns"] = ["t", "time", "message"]
        self._log_tree.heading("message", text="message")
        self._log_tree.heading("time", text="time")
        self._log_tree.column("time", width=100, stretch=False)
        self._log_tree.heading("t", text="t")
        self._log_tree.column("t", width=150, stretch=False)

        lh = tkf.Font(font='TkDefaultFont').metrics('linespace')
        style = ttk.Style()
        style.configure('Treeview', rowheight=lh)

    def _handle_quit(self):
        if self._update_experiment_loop_id is not None:
            self._root.after_cancel(self._update_experiment_loop_id)
        self._root.quit()
        self._root.destroy()

    def _get_current_experiment(self) -> Type[ExperimentProtocol]:
        idx = self._experiment_list.curselection()[0]
        return self.experiments[idx]

    def _handle_experiment_change(self, _):
        if not self._experiment_list.curselection():
            return

        self.reset_data()

        idx = self._experiment_list.curselection()[0]
        self._plotter_list_var.set(list(map(lambda cls:cls.name, self.experiments[idx].plotter_classes)))
        self._plotter_list.select_clear(0, tk.END)
        self._plotter_list.selection_set(0)
        self._handle_plotter_change()

        # update cols
        Experiment = self.experiments[idx]
        columns = ["t", "time"] + Experiment.columns
        self._result_tree["columns"] = columns
        self._result_tree.column("#0", width=0, stretch=False)
        self._result_tree.heading("time", text="time")
        self._result_tree.column("time", width=100, stretch=False)
        self._result_tree.heading("t", text="t")
        self._result_tree.column("t", width=150, stretch=False)

        for col in columns[2:]:
            self._result_tree.heading(col, text=col)
            self._result_tree.column(col, minwidth=100, anchor='center', stretch=True)


        self._experiment_label_var.set(Experiment.name)

        self._protocol_options_pane.fields = Experiment.options or {}

        self._validate_options_and_update_ui()

    def _validate_options_and_update_ui(self, *_):
        if self._state != "stopped":
            return
        if self._protocol_options_pane.is_valid and self._experiment_label_var.get() != "":
            self._start_button["state"] = "normal"
        else:
            self._start_button["state"] = "disabled"

    def _handle_plotter_change(self, *args, **kwargs):
        try:
            exp_idx = self._experiment_list.curselection()[0]
            Experiment = self.experiments[exp_idx]
            plotter_idx = self._plotter_list.curselection()[0]
            Plotter = Experiment.plotter_classes[plotter_idx]
        except IndexError:
            return
        self._plotter_options_pane.fields = Plotter.options or {}
        self._reset_plotter()

    def launch(self):
        self._create_ui()

        # insert data
        self._experiment_list_var.set(list(map(lambda cls:cls.name, self.experiments)))

        self._update_experiment_loop_id = self._root.after(30, self._update_experiment_loop)
        self._root.mainloop()

    def _get_data_from_queue(self, queue_):
        d = []
        while True:
            try:
                d.append(queue_.get(False))
            except queue.Empty:
                return d

    def _update_experiment_loop(self):
        self._update_ui_from_state()
        if self._state != "stopped":
            data = self._get_data_from_queue(self._data_queue)

            for d in data:
                self._data.append(d)

                experiment_idx = self._experiment_list.curselection()[0]
                columns = self.experiments[experiment_idx].columns

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
            logs = self._get_data_from_queue(self.log_queue)
            for log in logs:
                self._log_tree.insert("", tk.END, values=[log["t"], log["time"], log["message"]])
                self._log_tree.yview_moveto(1)

        self._update_experiment_loop_id = self._root.after(30, self._update_experiment_loop)

    def _draw_plot(self):
        if len(self._data) > 0 and self._plotter:
            df = pd.DataFrame(self._data)
            time_before_plot = time.perf_counter()
            self._plotter.update(df, self._get_plotter_context())
            logger.debug(f"Plotter.update took {time.perf_counter() - time_before_plot} s")
            time_before_draw = time.perf_counter()
            self._canvas.draw()
            logger.debug(f"canvas.draw took {time.perf_counter() - time_before_draw} s")

    def _handle_start_experiment(self):
        experiment_idx = self._experiment_list.curselection()[0]
        self.delegate.handle_ui_start(experiment_idx)

    def _handle_stop_experiment(self):
        self.delegate.handle_ui_stop()

    @property
    def data_queue(self) -> queue.Queue:
        return self._data_queue

    experiments: List[Type[ExperimentProtocol]]

    def set_plotter(self, plotter: Optional[ExperimentPlotter]):
        self._plotter = plotter

    def _update_ui_from_state(self):
        if self._state == "running":
            self._start_button["state"] = "disabled"
            self._stop_button["state"] = "normal"
            self._quit_button["state"] = "disabled"
            self._stop_button["text"] = "Stop"
            self._experiment_label_entry["state"] = "disabled"
            self._experiment_list["state"] = "disabled"
            self._protocol_options_pane.enabled = False
        elif self._state == "stopping":
            self._start_button["state"] = "disabled"
            self._stop_button["state"] = "normal"
            self._quit_button["state"] = "normal"
            self._stop_button["text"] = "Stopping..."
            self._experiment_label_entry["state"] = "disabled"
            self._experiment_list["state"] = "disabled"
            self._protocol_options_pane.enabled = False
        else:
            if self._experiment_list.curselection():
                self._start_button["state"] = "normal"
                self._validate_options_and_update_ui()
            else:
                self._start_button["state"] = "disabled"
            self._experiment_label_entry["state"] = "normal"
            self._experiment_list["state"] = "normal"
            self._protocol_options_pane.enabled = True
            self._stop_button["state"] = "disabled"
            self._quit_button["state"] = "enabled"
            self._stop_button["text"] = "Stop"

    def update_state(self, state: str):
        self._state = state

    def reset_data(self):
        self._data = []
        self._data_queue = queue.Queue()
        self.log_queue = queue.Queue()
        self._result_tree.delete(*self._result_tree.get_children())
        self._reset_plotter()

    def _reset_plotter(self):
        self._fig.clf()

        try:
            exp_idx = self._experiment_list.curselection()[0]
            Experiment = self.experiments[exp_idx]
            plotter_idx = self._plotter_list.curselection()[0]
            Plotter = Experiment.plotter_classes[plotter_idx]
        except IndexError:
            self._plotter = None
            return

        self._plotter = Plotter()
        self._plotter.fig = self._fig
        if self._state == "running":
            ctx = self._get_plotter_context()
            self._plotter.prepare(ctx)

    def _get_plotter_context(self):
        return  PlotterContext(
            plotter_options=self._plotter_options_pane.options,
            protocol_options=self.get_options(),
        )

    def get_options(self) -> dict:
        return self._protocol_options_pane.options

    @property
    def experiment_label(self) -> str:
        return self._experiment_label_var.get()
