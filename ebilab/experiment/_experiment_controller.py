from __future__ import annotations

import copy
import csv
import datetime
import io
import os
import socket
import time
from logging import getLogger
from pathlib import Path
from threading import Thread
from typing import Any, TypedDict

from ..project import get_current_project
from .protocol import ExperimentContext, ExperimentContextDelegate, ExperimentProtocol
from .util import Event

logger = getLogger(__name__)


class ExperimentStoppedByUser(Exception):
    """
    Raised when user pressed 'stop' button
    """

    def __str__(self) -> str:
        return "User has stopped the experiment"


class EventLog(TypedDict):
    t: float
    time: datetime.datetime
    message: str


class ExperimentController(ExperimentContextDelegate):
    experiment: ExperimentProtocol

    _ctx: ExperimentContext
    _running = False
    _file: io.TextIOWrapper | None
    _log_file: io.TextIOWrapper | None

    def __init__(self, experiment: ExperimentProtocol):
        self.experiment = experiment

        # setup events
        self.event_state_change = Event[str]()
        self.event_error = Event[str]()
        self.event_data_row: Event[dict[str, Any]] = Event()
        self.event_log = Event[EventLog]()

    def _get_comment_line(self, experiment: ExperimentProtocol, options: dict[str, Any]) -> str:
        """
        Returns:
            str: includes trailing NL
        """
        exp_name = experiment.name
        date = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        pc_name = socket.gethostname()
        options_str = ", ".join([f"{k}: {v}" for k, v in options.items()]) if options else ""

        comment_str = ""
        comment_str += f"# {exp_name} experiment: Ran at {date} in {pc_name}\n"
        comment_str += f"# {options_str}\n"
        comment_str += "#\n"
        return comment_str

    def start(self, options: dict[str, Any], label: str | None = None) -> None:
        """
        Experiment core logic
        """
        logger.info("starting experiment")
        self._options = options

        self.event_state_change.notify("running")

        self._ctx = ExperimentContext(delegate=self)

        # file
        try:
            logger.debug("ebilab project found")
            data_dir = get_current_project().path.data_original
        except:  # noqa: E722 FIXME
            logger.debug("ebilab project not found")
            data_dir = Path(".") / "data"
        dir = data_dir / datetime.datetime.now().strftime("%y%m%d")
        os.makedirs(dir, exist_ok=True)
        label = label or self.experiment.name
        filename = label + "-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".csv"
        log_filename = label + "-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".log"
        self._filename = dir / filename
        logger.info(f"Output file: {self._filename}")
        self._file = open(self._filename, "w", newline="")
        self._log_file = open(dir / log_filename, "w", newline="")
        self._csv_writer = csv.writer(self._file, quoting=csv.QUOTE_NONNUMERIC)

        comment_lines = self._get_comment_line(self.experiment, self._options)
        logger.debug("Comment_lines: " + comment_lines)
        self._file.write(comment_lines)

        header = ["t", "time"] + self.experiment.columns
        logger.debug("Header: " + str(header))
        self._csv_writer.writerow(header)

        def run() -> None:
            try:
                self.experiment.steps(self._ctx)
            except ExperimentStoppedByUser:
                logger.info("experiment stopped by user")
            except Exception as e:
                # print error info
                self._ctx.log(f"Python error occured: {e}")
                logger.exception("Python error occured during experiment")
                self.event_error.notify(f"Python error occured: {e}")
            finally:
                logger.debug("running_experiment finished, waiting 1sec")
                time.sleep(1)
                self._running = False
                self.event_state_change.notify("stopped")

                logger.info("running_experiment finished")

        self._started_time = time.perf_counter()
        logger.debug(f"started_time: {self._started_time}")
        self._running = True
        self._experiment_thread = Thread(target=run)
        self._experiment_thread.daemon = True
        self._experiment_thread.start()
        logger.info("experiment thread started")

    def stop(self) -> None:
        logger.debug("stopping experiment")
        self.event_state_change.notify("stopping")

        self._running = False
        if self._experiment_thread is not None:
            logger.info("joining experiment thread")
            self._experiment_thread.join()
        self.event_state_change.notify("stopped")

        if self._file is not None:
            self._file.close()
            self._file = None
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None
        logger.debug("stopped experiment")

    def _get_t(self) -> float:
        return time.perf_counter() - self._started_time

    # ExperimentContextDelegate
    def experiment_ctx_delegate_send_row(self, row: dict[str, Any]) -> None:
        row = copy.copy(row)
        row["t"] = self._get_t()
        row["time"] = datetime.datetime.now()

        self.event_data_row.notify(row)

        # write to file
        cols = ["t", "time"] + self.experiment.columns
        row_list = [row.get(col) for col in cols]
        self._csv_writer.writerow(row_list)

    def experiment_ctx_delegate_send_log(self, message: str) -> None:
        t = self._get_t()
        time = datetime.datetime.now()
        if self._log_file is None:
            logger.warn(f"Failed to write message '{time} t={t}: {message}'")
            return
        self.event_log.notify(
            {
                "t": t,
                "time": time,
                "message": message,
            }
        )
        self._log_file.write(f"{time} t={t}: {message}\n")

        # TODO: write to file

    def experiment_ctx_delegate_get_t(self) -> float:
        return self._get_t()

    def experiment_ctx_delegate_get_options(self) -> dict[str, Any]:
        return self._options

    def experiment_ctx_delegate_loop(self) -> None:
        if not self._running:
            raise ExperimentStoppedByUser()

    def __del__(self) -> None:
        if self._file is not None:
            self._file.close()
