import queue
from typing import List, Optional, Type
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkf

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ._experiment_controller import IExperimentPlotter, IExperimentUI, IExperimentProtocol
from .options import FloatField, SelectField

# windows dpi workaround
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2) 
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

class ExperimentUITkinter(IExperimentUI):
    _data_queue: queue.Queue
    _state: str = "stopped"
    _plotter: Optional[IExperimentPlotter] = None
    _update_experiment_loop_id: Optional[str] = None
    _options_widget = []
    _options_textvars = []

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

        ctrl_frm = ttk.Frame(frm, padding=10, relief="solid")
        ctrl_frm.grid(column=0, row=0, sticky="new")
        ctrl_frm.rowconfigure(0, weight=1)
        ctrl_frm.columnconfigure(0, weight=1)
        ctrl_frm.columnconfigure(1, weight=1)
        ctrl_frm.columnconfigure(2, weight=1)

        experiment_list_pane = ttk.Frame(ctrl_frm, padding=10, relief="solid")
        experiment_list_pane.grid(column=0, row=0, sticky=tk.NSEW)
        experiment_list_pane.columnconfigure(0, weight=1)
        experiment_list_pane.rowconfigure(1, weight=1)
        tk.Label(experiment_list_pane, justify="center", text="Experiment List").grid(column=0, row=0, sticky=tk.N)

        self._experiment_list_var = tk.StringVar(value=[])
        self._experiment_list = tk.Listbox(experiment_list_pane, listvariable=self._experiment_list_var, exportselection=False, height=5)
        self._experiment_list.grid(column=0, row=1, sticky=tk.NSEW)
        self._experiment_list.bind("<<ListboxSelect>>", self._handle_experiment_change)

        self._options_pane = ttk.Frame(ctrl_frm, padding=10, relief="solid")
        self._options_pane.grid(column=1, row=0, sticky=tk.NSEW)
        self._options_pane.columnconfigure(0, weight=1)
        tk.Label(self._options_pane, justify="center", text="Options").grid(column=0, row=0, sticky=tk.N)

        plotter_list_pane = ttk.Frame(ctrl_frm, padding=10, relief="solid")
        plotter_list_pane.grid(column=2, row=0, sticky=tk.NSEW)
        plotter_list_pane.columnconfigure(0, weight=1)
        plotter_list_pane.rowconfigure(1, weight=1)
        tk.Label(plotter_list_pane, justify="center", text="Plotter List").grid(column=0, row=0, sticky=tk.N)

        self._plotter_list_var = tk.StringVar(value=[])
        self._plotter_list = tk.Listbox(plotter_list_pane, listvariable=self._plotter_list_var, exportselection=False, height=5)
        self._plotter_list.grid(column=0, row=1, sticky=tk.NSEW)
        self._plotter_list.bind("<<ListboxSelect>>", self._handle_plotter_change)

        buttons_pane = ttk.Frame(ctrl_frm, padding=10, relief="solid")
        buttons_pane.grid(column=3, row=0, sticky="nes")

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
        #self._result_tree.grid()

        lh = tkf.Font(font='TkDefaultFont').metrics('linespace')
        style = ttk.Style()
        style.configure('Treeview', rowheight=lh)
    
    def _handle_quit(self):
        if self._update_experiment_loop_id is not None:
            self._root.after_cancel(self._update_experiment_loop_id)
        self._root.quit()
        self._root.destroy()

    def _get_current_experiment(self) -> Type[IExperimentProtocol]:
        idx = self._experiment_list.curselection()[0]
        return self.experiments[idx]

    def _handle_experiment_change(self, _):
        if not self._experiment_list.curselection():
            return

        idx = self._experiment_list.curselection()[0]
        self._plotter_list_var.set(list(map(lambda cls:cls.name, self.experiments[idx].plotter_classes)))
        self._plotter_list.select_clear(0, tk.END)
        self._plotter_list.selection_set(0)

        # update cols
        Experiment = self.experiments[idx]
        columns = ["t", "time"] + Experiment.columns
        self._result_tree["columns"] = columns
        self._result_tree.column("#0", width=0, stretch=False)
        for col in columns:
            self._result_tree.heading(col, text=col)
            self._result_tree.column(col, minwidth=100, anchor='c', stretch=True)

        self._experiment_label_var.set(Experiment.name)

        # update options
        for widgets in self._options_pane.winfo_children():
            widgets.destroy()

        tk.Label(self._options_pane, justify="center", text="Options").grid(column=0, row=0, sticky=tk.N)

        self._options_widget = []
        self._options_textvars = []

        for i, (key, field) in enumerate(Experiment.options.items() or []):
            if isinstance(field, FloatField):
                label = tk.Label(self._options_pane, text=key)
                label.grid(row=i + 1, column=0, sticky=tk.W + tk.N)

                var = tk.StringVar(value=str(field.default))
                var.trace("w", self._validate_options_and_update_ui)
                widget = tk.Entry(self._options_pane, textvariable=var)
                widget.grid(row=i + 1, column=1, sticky=tk.EW + tk.N)

                self._options_textvars.append(var)
                self._options_widget.append(widget)
                continue
            elif isinstance(field, SelectField):
                label = tk.Label(self._options_pane, text=key)
                label.grid(row=i + 1, column=0, sticky=tk.W + tk.N)

                var = tk.StringVar(value=str(field.choices[field.default_index]))
                var.trace("w", self._validate_options_and_update_ui)
                widget = ttk.Combobox(self._options_pane, textvariable=var, state="readonly", values=field.choices)
                widget.grid(row=i + 1, column=1, sticky=tk.EW + tk.N)

                self._options_textvars.append(var)
                self._options_widget.append(widget)
                continue
            raise ValueError("Unknown field type.")

        self._validate_options_and_update_ui()

    def _get_options(self) -> Optional[dict]:
        Experiment = self._get_current_experiment()
        if Experiment.options.items() is None:
            return {}
        ret = {}
        for (key, field), widget, var in zip(Experiment.options.items(), self._options_widget, self._options_textvars):
            if isinstance(field, FloatField):
                try:
                    val = float(var.get())
                except ValueError:
                    return None
                if field.min is not None and val < field.min:
                    return None
                if field.max is not None and val > field.max:
                    return None
                ret[key] = val
                continue
            elif isinstance(field, SelectField):
                if len(field.choices) == 0:
                    return ValueError("Field has no choices.")
                if isinstance(field.choices[0], int):
                    val = int(var.get())
                elif isinstance(field.choices[0], float):
                    val = float(var.get())
                else:
                    val = var.get()
                ret[key] = val
                continue
            raise ValueError("Unknown field type.")
        return ret

    def _options_is_valid(self):
        return self._get_options() is not None

    def _validate_options_and_update_ui(self, *_):
        if self._state != "stopped":
            return
        if self._options_is_valid() and self._experiment_label_var.get() != "":
            self._start_button["state"] = "normal"
        else:
            self._start_button["state"] = "disabled"

    def _handle_plotter_change(self, _):
        if not self._plotter_list.curselection():
            return

        if self._experiment_list.curselection() and self._plotter_list.curselection():
            self._start_button["state"] = "normal"
            self._validate_options_and_update_ui(self)

    def launch(self):
        self._create_ui()

        # insert data
        self._experiment_list_var.set(list(map(lambda cls:cls.name, self.experiments)))

        self._update_experiment_loop_id = self._root.after(30, self._update_experiment_loop)
        self._root.mainloop()

    def _get_data_from_queue(self):
        d = []
        while True:
            try:
                d.append(self._data_queue.get(False))
            except queue.Empty:
                return d

    def _update_experiment_loop(self):
        self._update_ui_from_state()
        if self._state != "stopped":
            data = self._get_data_from_queue()

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

            if len(self._data) > 0:
                df = pd.DataFrame(self._data)
                self._plotter.update(df)
                self._canvas.draw()

        self._update_experiment_loop_id = self._root.after(30, self._update_experiment_loop)
    
    def _handle_start_experiment(self):
        experiment_idx = self._experiment_list.curselection()[0]
        plotter_idx = self._plotter_list.curselection()[0]
        self.delegate.handle_ui_start(experiment_idx, plotter_idx)

    def _handle_stop_experiment(self):
        self.delegate.handle_ui_stop()

    @property
    def data_queue(self) -> queue.Queue:
        return self._data_queue

    experiments: List[Type[IExperimentProtocol]]

    def set_plotter(self, plotter: Optional[IExperimentPlotter]):
        self._plotter = plotter

    def _update_ui_from_state(self):
        if self._state == "running":
            self._start_button["state"] = "disabled"
            self._stop_button["state"] = "normal"
            self._quit_button["state"] = "disabled"
            self._stop_button["text"] = "Stop"
            self._experiment_label_entry["state"] = "disabled"
            for widget in self._options_widget:
                widget["state"] = "disabled" 
        elif self._state == "stopping":
            self._start_button["state"] = "disabled"
            self._stop_button["state"] = "normal"
            self._quit_button["state"] = "normal"
            self._stop_button["text"] = "Stopping..."
            self._experiment_label_entry["state"] = "disabled"
            for widget in self._options_widget:
                widget["state"] = "disabled" 
        else:
            if self._experiment_list.curselection() and self._plotter_list.curselection():
                self._start_button["state"] = "normal"
                self._validate_options_and_update_ui()
            else:
                self._start_button["state"] = "disabled"
            self._experiment_label_entry["state"] = "normal"
            for widget in self._options_widget:
                if isinstance(widget, ttk.Combobox):
                    widget["state"] = "readonly" 
                else:
                    widget["state"] = "normal" 
            self._stop_button["state"] = "disabled"
            self._quit_button["state"] = "enabled"
            self._stop_button["text"] = "Stop"

    def update_state(self, state: str):
        self._state = state

    def reset_data(self):
        self._fig.clf()
        self._data = []
        self._data_queue = queue.Queue()
        if self._plotter is not None:
            self._plotter.fig = self._fig
            self._plotter.prepare()

    def get_options(self) -> dict:
        options = self._get_options()
        if options is None:
            raise RuntimeError()
        return options

    @property
    def experiment_label(self) -> str:
        return self._experiment_label_var.get()
