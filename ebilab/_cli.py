from __future__ import annotations

import datetime
import os
import shutil
import sys
import time
from logging import (
    DEBUG,
    INFO,
    FileHandler,
    Formatter,
    StreamHandler,
    getLogger,
)
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen
from typing import Any

from .experiment._experiment_manager import ExperimentManager
from .project import get_current_project

# This import may fail if git is not installed
try:
    from git import Repo  # type: ignore # TODO
    from git.exc import GitCommandNotFound
except:  # noqa: E722
    pass

import click
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer


@click.group()
def cli() -> None:
    pass


@cli.command(help="Discover experiment recipes and launch GUI")
@click.argument("path")
def experiment(path: str) -> None:
    from .experiment._ui_tkinter import ExperimentUITkinter

    target = Path(path).resolve()
    setup_logger(target.name)

    experiment_manager = ExperimentManager.discover(target)
    ui = ExperimentUITkinter(experiment_manager)
    ui.launch()


def print_message_full(message: str) -> None:
    size = shutil.get_terminal_size((80, 20))
    terminal_width = size.columns

    if len(message) > terminal_width - 4:
        # Message exceeds terminal width
        print("=" * terminal_width)
        print(message)
        print("=" * terminal_width)
    else:
        # Message fits in terminal width
        print(f" {message} ".center(terminal_width, "="))


@cli.command()
@click.argument("path")
@click.option(
    "--watch-project",
    is_flag=True,
    default=False,
    help="Watch project directory instead of file.",
)
def watch(path: str, watch_project: bool = False) -> None:
    target = Path(path).resolve()
    project = get_current_project()

    if not target.exists():
        print("File not exists")
        exit(1)

    if target.suffix != ".py":
        print("Python please")
        exit(1)

    class Handler(PatternMatchingEventHandler):
        last_trigger_time: float | None = None

        def __init__(
            self,
            patterns: list[str] | None = None,
            ignore_patterns: list[str] | None = None,
            ignore_directories: bool = False,
            case_sensitive: bool = False,
        ):
            super().__init__(patterns, ignore_patterns, ignore_directories, case_sensitive)  # type: ignore

        def on_modified(self, event: Any) -> None:
            current_time = time.time()
            if self.last_trigger_time and current_time - self.last_trigger_time < 1:
                return

            src_path = Path(event.src_path)
            print(f"Change detected: {src_path.relative_to(project.path.root)}")

            self.last_trigger_time = current_time
            print_message_full(f"Running {target.relative_to(project.path.root)}")

            try:
                my_env = os.environ.copy()
                size = shutil.get_terminal_size()
                my_env["COLUMNS"] = str(size.columns)
                my_env["LINES"] = str(size.lines)
                my_env["EBILAB_SOURCE"] = "WATCH"

                p = Popen(
                    ["python", target.absolute()],
                    stdout=PIPE,
                    stderr=STDOUT,
                    env=my_env,
                )
                if p.stdout is None:
                    return
                while p.returncode is None:
                    data = p.stdout.read(1)
                    sys.stdout.buffer.write(data)
                    # sys.stdout.flush()
                    p.poll()

            finally:
                self.last_trigger_time = time.time()
                print_message_full(f"Completed {target.relative_to(project.path.root)}")

    if watch_project:
        event_handler = Handler(["*.py"])
        observer = Observer()  # type: ignore
        observer.schedule(event_handler, project.path.root, recursive=True)  # type: ignore
        observer.start()  # type: ignore
        print(f"Watching directory: {project.path.root}")
    else:
        event_handler = Handler([target.name])
        observer = Observer()  # type: ignore
        observer.schedule(event_handler, target.parent)  # type: ignore
        observer.start()  # type: ignore
        print(f"Watching file: {target}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()  # type: ignore
    observer.join()


@cli.command()
@click.argument("name")
def init(name: str) -> None:
    path = Path(name)
    if path.exists():
        print(f'file or directory "{path}" already exists.')
        exit(1)

    template_dir = Path(__file__).resolve().parent / "data" / "project-template"
    shutil.copytree(template_dir, path)

    # git initialization
    try:
        repo = Repo.init(path)
        if input("Will you track original data by git? (Y/n) > ") != "n":
            os.remove(path / "data" / "original" / ".gitignore")
        repo.git.add(A=True)
        repo.git.commit(m="init: initialized by `ebilab init`")
    except GitCommandNotFound:
        print("Git command not found, skipping...")
    except:  # noqa: E722
        print("Git initialization failed, skipping...")

    print(f'Initialized project "{name}"')


@cli.command()
@click.option("-f", is_flag=True, default=False, help="Delete files actually.")
def clean(f: bool) -> None:
    project = get_current_project()
    project.clean_files(dry=not f)


def setup_logger(libname: str) -> None:
    # Set up logging
    os.makedirs("logs", exist_ok=True)
    formatter = Formatter(
        "%(asctime)s %(name)s:%(lineno)s %(funcName)s [%(levelname)s]: %(message)s"
    )
    simple_formatter = Formatter("%(asctime)s [%(levelname)s]: %(message)s")
    dateTag = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    info_handler = FileHandler(filename=f"logs/{dateTag}.log")
    info_handler.setLevel(INFO)
    info_handler.setFormatter(formatter)
    debug_handler = FileHandler(filename=f"logs/{dateTag}.debug.log")
    debug_handler.setLevel(DEBUG)
    debug_handler.setFormatter(formatter)
    stream_handler = StreamHandler()
    stream_handler.setLevel(INFO)
    stream_handler.setFormatter(simple_formatter)

    getLogger("ebilab").setLevel(DEBUG)
    getLogger(libname).setLevel(DEBUG)
    getLogger("__main__").setLevel(DEBUG)
    logger = getLogger()
    logger.addHandler(stream_handler)
    logger.addHandler(info_handler)
    logger.addHandler(debug_handler)
