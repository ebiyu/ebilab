import time
import copy
import queue
import os
import datetime
from threading import Thread
import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ._core import ExperimentContextDelegate, Experiment, Plotter

class GUIExperimentApp(ExperimentContextDelegate):
    _root: tk.Tk

    _running = False
    _completed = False
    _running_experiment_idx = None
    _running_plotter_idx = None
    _running_experiment_class = None
    _running_plotter_class = None
    _running_experiment = None # instantiated
    _running_plotter = None # instantiated

    _file = None

    def __init__(self, experiments: list):
        self._experiments = experiments

    def _create_ui(self):
        self._root = tk.Tk()
        self._root.state("zoomed")
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)

        frm = ttk.Frame(self._root, padding=10)
        frm.grid()
        #frm.rowconfigure(0, weight=0)
        #frm.rowconfigure(1, weight=1)
        #frm.rowconfigure(2, weight=0)

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
        self._quit_button = ttk.Button(buttons_pane, text="Quit", command=self._root.destroy)
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

    def start(self):
        self._create_ui()

        # insert data
        self._experiment_list_var.set(list(map(lambda cls:cls[0].filename, self._experiments)))

        self._root.after(30, self._update_experiment_loop)
        self._root.mainloop()

    def _handle_experiment_change(self, _):
        if not self._experiment_list.curselection():
            return

        idx = self._experiment_list.curselection()[0]
        self._plotter_list_var.set(list(map(lambda cls:cls.name, self._experiments[idx][1])))
        self._plotter_list.select_clear(0, tk.END)

        Experiment = self._experiments[idx][0]
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

    def _handle_start_experiment(self):
        self._start_button["state"] = "disabled"
        self._stop_button["state"] = "normal"
        self._quit_button["state"] = "disabled"
        self._experiment_list["state"] = "disabled"
        self._plotter_list["state"] = "disabled"

        self._running_experiment_idx = self._experiment_list.curselection()[0]
        self._running_plotter_idx = self._plotter_list.curselection()[0]
        self._running_experiment_class = self._experiments[self._running_experiment_idx][0]
        self._running_plotter_class = self._experiments[self._running_experiment_idx][1][self._running_plotter_idx]
        self._running_experiment = self._running_experiment_class()
        self._running_plotter = self._running_plotter_class()


        dir = "data"
        if not os.path.exists(dir):
            os.mkdir(dir)
        self._filename = dir + "/" + self._running_experiment.filename + "-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".csv"
        self._file = open(self._filename, "w")

            # write headers
        header = ["t", "time"] + self._running_experiment.columns
        self._file.write(",".join(header) + "\n")

        self._fig.clf()
        self._running_plotter.fig = self._fig
        self._running_plotter.prepare()
        for i in self._result_tree.get_children():
           self._result_tree.delete(i)

        self._running_experiment.delegate = self

        def run():
            self._running_experiment.steps()
            time.sleep(1)
            self._completed = True

        self._started_time = time.perf_counter()
        self._data_queue = queue.Queue()
        self._data = []

        self._running = True
        self._experiment_thread = Thread(target=run)
        self._experiment_thread.daemon = True
        self._experiment_thread.start()

    def _handle_stop_experiment(self):
        self._stop_button["text"] = "Stopping..."
        self._stop_button["state"] = "disabled"
        self._quit_button["state"] = "normal"
        self._root.update()

        self._running = False
        self._experiment_thread.join()

        self._stop_button["text"] = "Stop"
        self._start_button["state"] = "normal"

    def _get_data_from_queue(self):
        d = []
        while True:
            try:
                d.append(self._data_queue.get(False))
            except queue.Empty:
                return d

    def _get_t(self):
        return time.perf_counter() - self._started_time

    def _update_experiment_loop(self):
        try:
            if not self._running:
                return
            if not self._experiment_thread.is_alive():
                self._running = False
                self._start_button["state"] = "normal"
                self._stop_button["state"] = "disabled"
                return

            data = self._get_data_from_queue()

            for d in data:
                self._data.append(d)

                # insert to table
                row_list = [str(d["t"]), str(d["time"])]
                for col in self._running_experiment.columns:
                    if col in d:
                        row_list.append(str(d[col]))
                    else:
                        row_list.append("")
                self._result_tree.insert("", tk.END, values=row_list)
                self._result_tree.yview_moveto(1)
                self._file.write(",".join(row_list) + "\n")

            if len(self._data) > 0:
                df = pd.DataFrame(self._data)
                self._running_plotter.update(df)
                self._canvas.draw()

        finally:
            self._root.after(30, self._update_experiment_loop)

    # delegate

    def experiment_ctx_send_row(self, row=None):
        if row is None:
            return

        row = copy.copy(row)

        row["t"] = self._get_t()
        row["time"] = datetime.datetime.now()

        self._data_queue.put(row)


    def experiment_ctx_get_t(self) -> float:
        return self._get_t()

    def experiment_ctx_is_running(self) -> bool:
        return self._running

    def __del__(self):
        if self._file is not None:
            self._file.close()