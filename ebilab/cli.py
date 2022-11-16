from pathlib import Path
import sys
import time
import os
from subprocess import PIPE, STDOUT, Popen

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import click

@click.group()
def cli():
    pass


@cli.command()
@click.argument("path")
def watch(path: str):
    target = Path(path).resolve()

    if not target.exists():
        print("File not exists")
        exit(1)

    if target.suffix != ".py":
        print("Python please")
        exit(1)


    print(target)

    class Handler(PatternMatchingEventHandler):
        last_trigger_time = None
        def __init__(self, patterns=None, ignore_patterns=None, ignore_directories=False, case_sensitive=False):
            super().__init__(patterns, ignore_patterns, ignore_directories, case_sensitive)

        def on_modified(self, event):
            current_time = time.time()
            if self.last_trigger_time and current_time - self.last_trigger_time < 1:
                return

            self.last_trigger_time = current_time
            print("running...")

            try:
                my_env = os.environ.copy()
                size = os.get_terminal_size()
                my_env["COLUMNS"] = str(size.columns)
                my_env["LINES"] = str(size.lines)
                my_env["EBILAB_SOURCE"] = "WATCH"

                p = Popen(["python", target.absolute()], stdout=PIPE, stderr=STDOUT, env=my_env)
                if p.stdout is None:
                    return
                while p.returncode == None:
                    data = p.stdout.read(1)
                    sys.stdout.buffer.write(data)
                    # sys.stdout.flush()
                    p.poll()

            finally:
                self.last_trigger_time = time.time()
                print("done")

    event_handler = Handler([target.name])
    observer = Observer()
    observer.schedule(event_handler, target.parent)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

@cli.command()
@click.argument("name")
def init(name: str):
    path = Path(name)
    if path.exists():
        print(f"file or directory {path} already exists.")
        exit(1)

    path.mkdir()
    for dir in ["original", "input", "output", "plot"]:
        (path / dir).mkdir()
        with open(path / dir/ ".gitignore", "w") as f:
            f.write("*\n!.gitignore")

    (path / "main.py").touch()

