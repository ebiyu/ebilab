# sample of multi-thread measuremnt & plotting
import queue
import inspect
import copy
import sys
from threading import Thread
import time
import datetime
from typing import Optional, List
import os

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd

class Plotter:
    def prepare(self):
        raise NotImplementedError("Plotter::prepare() must be implemented")

    def update(self, df: pd.DataFrame):
        raise NotImplementedError("Plotter::update() must be implemented")

class Experiment:
    started_time: float # in sec
    running = False
    columns = None
    filename = "experiment"

    _plotter: Optional[Plotter] = None
    _data_queue: queue.Queue
    _data = []
    _experiment_thread = None
    _completed = False

    @property
    def plotter(self) -> Optional[Plotter]:
        return self._plotter
    
    @plotter.setter
    def plotter(self, plotter: Optional[Plotter]):
        if self.running:
            raise RuntimeError("Plotter cannnot be set during experiment!!")
        self._plotter = plotter

    def _get_data_from_queue(self):
        d = []
        while True:
            try:
                d.append(self._data_queue.get(False))
            except queue.Empty:
                return d

    def _write_to_file(self, row):
        row_list = [str(row["t"])]
        for col in self.columns:
            if col in row:
                row_list.append(str(row[col]))
            else:
                row_list.append("")
        self._f.write(",".join(row_list)+ "\n")
        print(",\t".join(row_list))

    def _main_loop(self):
        while self._experiment_thread is not None and self._experiment_thread.is_alive():
            # get data from experiment thread
            data = self._get_data_from_queue()

            for d in data:
                self._data.append(d)
                self._write_to_file(d)

            if self._plotter is not None:
                if len(self._data) > 0:
                    df = pd.DataFrame(self._data)
                    self._plotter.update(df)

                plt.gcf().canvas.draw_idle()
                plt.gcf().canvas.flush_events()

    def start(self):
        if self.columns is None:
            raise NotImplementedError("Experiment::columns is not specified")

        if self._plotter is not None:
            self._plotter.prepare()
            plt.pause(0.01)

        self.running = True

        self.started_time = time.perf_counter()
        self._data_queue = queue.Queue()

        # start experiment thread
        def run():
            self.steps()
            time.sleep(1)
            self._completed = True

        self._experiment_thread = Thread(target=run)
        self._experiment_thread.daemon = True
        self._experiment_thread.start()

        dir = "data"
        if not os.path.exists(dir):
            os.mkdir(dir)

        filename = dir + "/" + self.filename + "-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".csv"

        with open(filename, "w") as self._f:
            # write headers
            header = ["t", "time"] + self.columns
            self._f.write(",".join(header) + "\n")
            print(",\t".join(header))

            try:
                self._main_loop()

                # show plot in successful exit
                if self._completed:
                    print("Measurement completed.", file=sys.stderr)
                    if self._plotter is not None:
                        if len(self._data) > 0:
                            df = pd.DataFrame(self._data)
                            self._plotter.update(df)
                        plt.show()
            finally:
                self.running = False
                plt.close()
    
    def get_t(self):
        return time.perf_counter() - self.started_time

    def send_row(self, row, *, capture: List[str] = None):
        row = copy.copy(row)
        row["t"] = self.get_t()
        row["time"] = time.time()

        if capture:
            frame = inspect.currentframe()
            try:
                local_vars = frame.f_back.f_locals
            finally:
                del frame

            for var in capture:
                if var in row:
                    raise ValueError(f"Duplicate key: `{var}` is defined in row and capture.")
                if var not in local_vars:
                    raise RuntimeError(f"No local variable `{var}` is found.")
                row[var] = local_vars[var]

        self._data_queue.put(row)

    def steps(self):
        raise NotImplementedError("Experiment::steps() must be implemented")
