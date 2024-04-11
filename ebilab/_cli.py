from pathlib import Path
import sys
import time
import os
import shutil
import importlib
import inspect
from subprocess import PIPE, STDOUT, Popen
import datetime
from logging import getLogger, StreamHandler, FileHandler, Formatter, INFO, DEBUG, WARNING

from .project import get_current_project
from .experiment import ExperimentProtocol, launch_experiment

# This import may fail if git is not installed
try:
    from git import Repo
    from git.exc import GitCommandNotFound
except:
    pass

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import click

@click.group()
def cli():
    pass

@cli.command(help="Discover experiment recipes and launch GUI")
@click.argument("path")
def experiment(path: str):
    target = Path(path).resolve()

    if not target.exists():
        print("File not exists")
        exit(1)

    if not target.is_dir():
        print("You have to specify directory")
        exit(1)

    setup_logger(target.name)

    logger = getLogger(__name__)

    # Discover protocols
    sys.path.append(str(target.parent))
    files = target.glob("*.py")
    protocols = []
    for file in files:
        mod = importlib.import_module(target.name + "." + file.stem)

        for _, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and issubclass(obj, ExperimentProtocol) and obj.__name__ != "ExperimentProtocol":
                logger.debug(f"Loaded {obj.__name__} from {file}")
                protocols.append(obj)
    protocols.sort(key=lambda p:p.name)

    logger.info(f"Found {len(protocols)} protocols")

    launch_experiment(protocols)

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
        print(f"file or directory \"{path}\" already exists.")
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
    except:
        print("Git initialization failed, skipping...")

    print(f"Initialized project \"{name}\"")



@cli.command()
@click.option("-f", is_flag=True, default=False, help="Delete files actually.")
def clean(f):
    project = get_current_project()
    project.clean_files(dry=not f)

def setup_logger(libname: str):
    # Set up logging
    os.makedirs("logs", exist_ok=True)
    formatter = Formatter("%(asctime)s %(name)s:%(lineno)s %(funcName)s [%(levelname)s]: %(message)s")
    simple_formatter = Formatter("%(asctime)s [%(levelname)s]: %(message)s")
    dateTag = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    info_handler = FileHandler(filename=f"logs/{dateTag}.log")
    info_handler.setLevel(INFO)
    info_handler.setFormatter(formatter)
    debug_handler = FileHandler(filename=f"logs/{dateTag}.debug.log")
    debug_handler.setLevel(DEBUG)
    debug_handler.setFormatter(formatter)
    stream_handler = StreamHandler()
    stream_handler.setLevel(WARNING)
    stream_handler.setFormatter(simple_formatter)

    getLogger("ebilab").setLevel(DEBUG)
    getLogger(libname).setLevel(DEBUG)
    getLogger("__main__").setLevel(DEBUG)
    logger = getLogger()
    logger.addHandler(stream_handler)
    logger.addHandler(info_handler)
    logger.addHandler(debug_handler)
