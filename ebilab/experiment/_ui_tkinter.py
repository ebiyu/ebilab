import queue
from typing import List, Optional, Type, Literal
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkf

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ._experiment_controller import IExperimentPlotter, IExperimentUI, IExperimentProtocol

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
    _state: Literal["running", "stopping", "stopped"] = "stopped"
    _plotter: Optional[IExperimentPlotter] = None
    _update_experiment_loop_id: Optional[str] = None

    def __init__(self) -> None:
        super().__init__()
        self._data_queue = queue.Queue()
        self._data = []

    def _create_ui(self):
        self._root = tk.Tk()
        self._root.state("zoomed")
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)

        frm = ttk.Frame(self._root, padding=10)
        frm.grid()

        ctrl_frm = ttk.Frame(frm, padding=10)
        ctrl_frm.grid(column=0, row=0)

        experiment_list_pane = ttk.Frame(ctrl_frm, padding=10)
        experiment_list_pane.grid(column=0, row=0)
        tk.Label(experiment_list_pane, justify="center", text="Experiment List").grid(column=0, row=0)

        self._experiment_list_var = tk.StringVar(value=[])
        self._experiment_list = tk.Listbox(experiment_list_pane, listvariable=self._experiment_list_var, exportselection=False)
        self._experiment_list.grid(column=0, row=1)
        self._experiment_list.bind("<<ListboxSelect>>", self._handle_experiment_change)

        plotter_list_pane = ttk.Frame(ctrl_frm, padding=10)
        plotter_list_pane.grid(column=1, row=0)
        tk.Label(plotter_list_pane, justify="center", text="Plotter List").grid(column=0, row=0)

        self._plotter_list_var = tk.StringVar(value=[])
        self._plotter_list = tk.Listbox(plotter_list_pane, listvariable=self._plotter_list_var, exportselection=False)
        self._plotter_list.grid(column=0, row=1)
        self._plotter_list.bind("<<ListboxSelect>>", self._handle_plotter_change)

        buttons_pane = ttk.Frame(ctrl_frm, padding=10)
        buttons_pane.grid(column=2, row=0)

        self._start_button = ttk.Button(buttons_pane, text="Start", command=self._handle_start_experiment, state="disabled")
        self._start_button.grid(column=0, row=0)
        self._stop_button = ttk.Button(buttons_pane, text="Stop", command=self._handle_stop_experiment, state="disabled")
        self._stop_button.grid(column=0, row=1)
        self._quit_button = ttk.Button(buttons_pane, text="Quit", command=self._handle_quit)
        self._quit_button.grid(column=0, row=2)

        plot_frm = ttk.Frame(frm, padding=10)
        plot_frm.grid(column=0, row=1)

        self._fig = plt.figure(figsize=(6, 3), dpi=30, constrained_layout=True)
        self._canvas = FigureCanvasTkAgg(self._fig, master=plot_frm)
        self._canvas.get_tk_widget().grid(column=0, row=0)

        table_frm = ttk.Frame(frm, padding=10)
        table_frm.grid(column=0, row=2)

        self._result_tree = ttk.Treeview(table_frm)
        self._result_tree.column("#0", width=0)
        self._result_tree.grid()

        lh = tkf.Font(font='TkDefaultFont').metrics('linespace')
        style = ttk.Style()
        style.configure('Treeview', rowheight=lh)
    
    def _handle_quit(self):
        if self._update_experiment_loop_id is not None:
            self._root.after_cancel(self._update_experiment_loop_id)
        self._root.quit()
        self._root.destroy()

    def _handle_experiment_change(self, _):
        if not self._experiment_list.curselection():
            return

        idx = self._experiment_list.curselection()[0]
        self._plotter_list_var.set(list(map(lambda cls:cls.name, self.experiments[idx].plotter_classes)))
        self._plotter_list.select_clear(0, tk.END)

        Experiment = self.experiments[idx]
        columns = ["t", "time"] + Experiment.columns
        self._result_tree["columns"] = columns
        #self._result_tree.heading('#0',text='')
        for col in columns:
            self._result_tree.heading(col, text=col)

    def _handle_plotter_change(self, _):
        if not self._plotter_list.curselection():
            return

        if self._experiment_list.curselection() and self._plotter_list.curselection():
            self._start_button["state"] = "normal"

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

    def update_state(self, state: Literal["running", "stopping", "stopped"]):
        self._state = state

        if self._state == "running":
            self._start_button["state"] = "disabled"
            self._stop_button["state"] = "normal"
            self._quit_button["state"] = "disabled"
            self._stop_button["text"] = "Stop"
        elif self._state == "stopping":
            self._start_button["state"] = "disabled"
            self._stop_button["state"] = "normal"
            self._quit_button["state"] = "normal"
            self._stop_button["text"] = "Stopping..."
        else:
            if self._experiment_list.curselection() and self._plotter_list.curselection():
                self._start_button["state"] = "normal"
            else:
                self._start_button["state"] = "disabled"
            self._stop_button["state"] = "disabled"
            self._quit_button["state"] = "enabled"
            self._stop_button["text"] = "Stop"

    def reset_data(self):
        self._fig.clf()
        self._data = []
        if self._plotter is not None:
            self._plotter.fig = self._fig
            self._plotter.prepare()