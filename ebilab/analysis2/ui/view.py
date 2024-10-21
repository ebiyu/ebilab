from __future__ import annotations

import copy
import io
import tkinter as tk
from logging import getLogger
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

import matplotlib.pyplot as plt
from PIL import Image, ImageTk

from ..base import DfPlotter, DfProcess
from ..manifest import (
    DfProcessManifest,
    DfProcessStep,
    FileProcessStep,
    InputManifest,
    PlotterStep,
)
from ..options import InvalidInputError, OptionField
from ..project import Project
from ..subproject import SubProject
from .clipboard import copy_img_to_clipboard

logger = getLogger(__name__)


# # windows dpi workaround
try:
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(0)  # type: ignore
except:  # noqa: E722
    pass

event_disabled: bool = False


def update_method(func):
    """
    decorator to disable event
    """

    def wrapper(*args, **kwargs):
        global event_disabled

        event_disabled = True
        try:
            return func(*args, **kwargs)
        finally:
            event_disabled = False

    return wrapper


def event_handler(func):
    """
    decorator to add for event
    """

    def wrapper(*args, **kwargs):
        if event_disabled:
            logger.debug(f"event handler {func.__name__} skipped")
            return
        logger.debug(f"event handler {func.__name__} executed")
        func(*args, **kwargs)

    return wrapper


class OptionsPane(ttk.Frame):
    _fields: dict[str, OptionField]
    _enabled = True
    __options: dict[str, Any]
    _is_valid = True

    def __init__(self, master: ttk.Widget) -> None:
        super().__init__(master)
        self._fields = {}

        # build UI
        self.columnconfigure(0, weight=1)
        self._build_fields({})

        logger.debug("OptionsPane initialized")

    def _build_fields(self, fields: dict[str, OptionField]) -> None:
        for widgets in self.winfo_children():
            widgets.destroy()

        self._options_widgets = []
        self._options_vars = []

        for i, (key, field) in enumerate(fields.items()):
            label = tk.Label(self, text=key)
            label.grid(row=i, column=0, sticky=tk.W + tk.N)

            var, widget = field.build_widget(self)
            widget.grid(row=i, column=1, sticky=tk.EW + tk.N)
            var.trace_add("write", lambda *_: self._on_update())

            self._options_vars.append(var)
            self._options_widgets.append(widget)

        opt = self._get_options()
        if opt is None:
            raise RuntimeError("Unexpected invalid value")
        self.__options = opt
        self._is_valid = True

    def _on_update(self) -> None:
        logger.debug("OptionsPane._on_update called")
        opt = self._get_options()
        if opt is None:
            self._is_valid = False
        else:
            self._is_valid = True
            self.__options = opt

        self.event_generate("<<OptionsPaneUpdate>>")

    @property
    def fields(self) -> dict[str, OptionField]:
        return self._fields

    @fields.setter
    def fields(self, fields: dict[str, OptionField]) -> None:
        old_fields = self._fields
        self._fields = fields

        # detect difference
        if list((k, v.__class__) for k, v in old_fields.items()) != list(
            (k, v.__class__) for k, v in fields.items()
        ):
            self._build_fields(fields)
            logger.debug("Widgets in OptionsPage has rebuilt.")

    def _get_options(self) -> dict[str, Any] | None:
        ret = {}
        for (key, field), widget, var in zip(
            self.fields.items(), self._options_widgets, self._options_vars
        ):
            try:
                ret[key] = field.get_from_widget(var)
            except InvalidInputError:
                logger.debug(f"InvalidInputError: {key}")
                return None

        return ret

    @property
    def options(self) -> dict[str, Any]:
        assert self.__options is not None
        return self.__options

    @options.setter
    def options(self, options: dict[str, Any]) -> None:
        for (key, field), var in zip(self.fields.items(), self._options_vars):
            field.set_to_widget(var, options[key])

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled:
            for widget in self._options_widgets:
                if isinstance(widget, ttk.Combobox):
                    widget["state"] = "readonly"
                else:
                    widget["state"] = "normal"
        else:
            for widget in self._options_widgets:
                widget["state"] = "disabled"


class View(tk.Tk):
    project: Project
    status_bar_timer: str | None = None
    _output_saved: bool = True
    event_disabled: bool = False  # avoid infinite loop

    @property
    def output_saved(self) -> bool:
        return self._output_saved

    @output_saved.setter
    def output_saved(self, value: bool) -> None:
        self._output_saved = value
        if value:
            self.title("ebilab.analysis2")
        else:
            self.title("ebilab.analysis2 (unsaved)")

    def __init__(self, project: Project):
        self.project = project

        # create main window
        super().__init__()
        self.title("ebilab.analysis2")
        self.geometry("400x200")
        self.state("zoomed")  # maximize window
        self.protocol("WM_DELETE_WINDOW", self.handle_close_main_window)
        self.create_widgets()

        # create sub window (original data)
        self.original_data_window = tk.Toplevel(self)
        self.original_data_window.title("Original Data")
        self.original_data_window.geometry("400x600")
        self.original_data_window.withdraw()  # hide window
        self.original_data_window.protocol(
            "WM_DELETE_WINDOW", self.handle_close_original_data_window
        )
        self.create_widgets_subwin()

        self.update_original_data_list()
        self.update_subproject_list()

    def create_widgets(self) -> None:
        """
        Build widgets
        """
        # create layout frames (4 columns)
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True)

        col1 = ttk.Frame(main_frame, border=1, relief="solid")
        col1.pack(side="left", fill="both", expand=True)
        col2 = ttk.Frame(main_frame, border=1, relief="solid")
        col2.pack(side="left", fill="both", expand=True)
        col3 = ttk.Frame(main_frame, border=1, relief="solid")
        col3.pack(side="left", fill="both", expand=True)
        col4 = ttk.Frame(main_frame, border=1, relief="solid")
        col4.pack(side="left", fill="both", expand=True)

        # create menu
        menu = tk.Menu(self)
        self.config(menu=menu)
        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Load", command=lambda: self.handle_load(), accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="Save", command=lambda: self.handle_save(), accelerator="Ctrl+S"
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Exit", command=self.handle_close_main_window, accelerator="Ctrl+W"
        )

        # create status bar
        self.status_bar = StatusBar(self)

        # shortcut keys
        self.bind("<Control-o>", lambda _: self.handle_load())
        self.bind("<Control-s>", lambda _: self.handle_save())
        self.bind("<Control-w>", lambda _: self.handle_close_main_window())

        # create widgets
        # col1
        subprojects_frame = ttk.Frame(col1)
        subprojects_frame.pack(fill="x")
        tk.Label(subprojects_frame, text="Subprojects").pack(side="left")
        self.subprojects_dropdown = ttk.Combobox(subprojects_frame)
        self.subprojects_dropdown.pack(side="left", fill="x", expand=True)
        self.subprojects_dropdown.bind(
            "<<ComboboxSelected>>", lambda _: self.handle_on_select_subproject()
        )

        open_original_data_button = ttk.Button(
            col1, text="Open Original Data", command=self.handle_open_original_data_window
        )
        open_original_data_button.pack(fill="x")

        tk.Label(col1, text="Input").pack()
        self.input_list = ttk.Treeview(col1)
        self.input_list.pack(fill="both", expand=True)
        self.input_list.bind("<<TreeviewSelect>>", lambda _: self.handle_on_select_input())

        tk.Label(col1, text="Output").pack()
        output_frame = ttk.Frame(col1)
        output_frame.pack(fill="both", expand=True)
        output_list_frame = ttk.Frame(output_frame)
        output_list_frame.pack(side="left", fill="both", expand=True)
        self.output_name_var = tk.StringVar()
        output_name_entry = ttk.Entry(output_list_frame, textvariable=self.output_name_var)
        output_name_entry.pack(fill="x")
        self.output_list = ttk.Treeview(output_list_frame)
        self.output_list.pack(fill="both", expand=True)
        self.output_list.bind("<<TreeviewSelect>>", lambda _: self.handle_on_select_output())
        output_buttons_frame = ttk.Frame(output_frame)
        output_buttons_frame.pack(side="right", fill="y")

        output_add_button = ttk.Button(
            output_buttons_frame, text="<\nS\na\nv\ne", command=lambda: self.handle_save_output()
        )
        output_add_button.pack(fill="both", expand=True)
        output_remove_button = ttk.Button(
            output_buttons_frame, text=">\nL\no\na\nd", command=lambda: self.handle_load_output()
        )
        output_remove_button.pack(fill="both", expand=True)

        # col2
        tk.Label(col2, text="Current Process").pack()
        self.process_recipe_list = ttk.Treeview(col2)
        self.process_recipe_list.pack(fill="both", expand=True)
        self.process_recipe_list.bind(
            "<<TreeviewSelect>>", lambda _: self.handle_on_select_process()
        )

        self.process_name_var = tk.StringVar(value="-")
        process_name_label = tk.Label(col2, textvariable=self.process_name_var)
        process_name_label.pack(fill="x")

        self.process_options_pane = OptionsPane(col2)
        self.process_options_pane.pack(fill="both", expand=True)
        self.process_options_pane.bind(
            "<<OptionsPaneUpdate>>", lambda _: self.handle_on_edit_process_options()
        )

        delete_button = ttk.Button(col2, text="Delete", command=self.handle_delete_process_step)
        delete_button.pack(fill="x")

        tk.Label(col2, text="Process List").pack()
        self.process_list = ttk.Treeview(col2)
        self.process_list.pack(fill="both", expand=True)

        process_add_button = ttk.Button(col2, text="Add", command=self.handle_add_process)
        process_add_button.pack(fill="x")

        # col3
        tk.Label(col3, text="Plotters").pack()
        self.plotter_list = ttk.Treeview(col3)
        self.plotter_list.pack(fill="both", expand=True)
        self.plotter_list.bind("<<TreeviewSelect>>", lambda _: self.handle_on_select_plotter())

        # plotter canvas
        self._plot_canvas = tk.Canvas(master=col3)
        self._plot_canvas.pack(fill="both", expand=True)

        copy_plotter_image_button = ttk.Button(
            col3, text="Copy image", command=self.handle_copy_plotter_image
        )
        copy_plotter_image_button.pack(fill="x")

        self.plotter_options_pane = OptionsPane(col3)
        self.plotter_options_pane.pack(fill="both", expand=True)
        self.plotter_options_pane.bind(
            "<<OptionsPaneUpdate>>", lambda _: self.handle_on_edit_plotter_options()
        )

        # col4

    def create_widgets_subwin(self):
        """
        Build widgets for subwindow (original data)
        """
        # subwindow (original data)
        tk.Label(self.original_data_window, text="Original Data").pack()
        self.original_list = ttk.Treeview(self.original_data_window)
        self.original_list.pack(fill="both", expand=True)
        self.original_list.bind("<Double-1>", lambda _: self.handle_add_to_input())
        self.original_list.bind("<<TreeviewSelect>>", lambda _: on_original_list_change())

        def on_original_list_change():
            self.input_filename_var.set(
                self.original_list.item(self.original_list.selection()[0])["text"].replace(
                    ".csv", ""
                )
            )

        self.input_filename_var = tk.StringVar()
        self.input_filename_entry = ttk.Entry(
            self.original_data_window, textvariable=self.input_filename_var
        )
        self.input_filename_entry.pack(fill="x")

        subwindow_buttons = ttk.Frame(self.original_data_window)
        subwindow_buttons.pack(fill="x")
        add_to_input_button = ttk.Button(
            subwindow_buttons, text="Append", command=self.handle_add_to_input
        )
        add_to_input_button.pack(side="left", fill="x", expand=True)
        add_to_input_button = ttk.Button(
            subwindow_buttons, text="Close", command=self.handle_close_original_data_window
        )
        add_to_input_button.pack(side="left", fill="x", expand=True)

    @property
    def _subproject(self) -> SubProject | None:
        return self.project.subprojects.get(self.subprojects_dropdown.get())

    @property
    def _plotter_list(self) -> dict[str, type[DfPlotter]]:
        if not self._subproject:
            return {}
        return self._subproject.df_plotters

    # Update methods (idempotent / 冪等)
    @update_method
    def update_original_data_list(self) -> None:
        # clear list
        self.original_list.delete(*self.original_list.get_children())

        def relative_insert(path: Path):
            parent_iid = path.parent.relative_to(self.project.path.data_original).as_posix()
            if parent_iid == ".":  # root
                parent_iid = ""
            new_iid = path.relative_to(self.project.path.data_original).as_posix()
            if not self.original_list.exists(parent_iid):
                relative_insert(path.parent)
            self.original_list.insert(parent_iid, "end", text=path.name, iid=new_iid, open=True)

        # insert files
        for item in self.project.get_original_files():
            relative_insert(item)

    @update_method
    def update_subproject_list(self) -> None:
        self.subprojects_dropdown["values"] = list(self.project.subprojects.keys())
        self.subprojects_dropdown["state"] = "readonly"
        if not self.subprojects_dropdown.get():
            self.subprojects_dropdown.set(list(self.project.subprojects.keys())[0])

        self.update_input_output_list()
        self.update_process_recipe_list()
        self.update_process_list()
        self.update_plotter_list()

    @update_method
    def update_input_output_list(self) -> None:
        self.input_list.delete(*self.input_list.get_children())
        self.output_list.delete(*self.output_list.get_children())

        if not self._subproject:
            return

        for input_name in self._subproject.manifest.inputs.keys():
            self.input_list.insert("", "end", text=input_name)

        for output_name in self._subproject.manifest.outputs.keys():
            self.output_list.insert("", "end", text=output_name)

    @update_method
    def update_process_list(self) -> None:
        self.process_list.delete(*self.process_list.get_children())

        if not self._subproject:
            return

        for name in self._subproject.df_processes.keys():
            self.process_list.insert("", "end", text=name)

    @update_method
    def update_process_recipe_list(self) -> None:
        current = self.process_recipe_list.selection()
        self.process_recipe_list.delete(*self.process_recipe_list.get_children())

        if not self._subproject:
            return

        if not self._subproject.current_recipe:
            return

        self.process_recipe_list.insert(
            "", "end", text=self._subproject.current_recipe.input, iid="input", open=True
        )

        for i, step in enumerate(self._subproject.current_recipe.process_steps):
            process_class = self._subproject.get_class_from_name(step.df_process, DfProcess)
            process_instance = process_class(step.kwargs)
            self.process_recipe_list.insert(
                "input", "end", text=process_instance.get_caption(), iid=f"step-{i}"
            )

        self.process_recipe_list.selection_set(current)

    @update_method
    def update_process_options(self) -> None:
        if not self._subproject:
            return

        if not self._subproject.current_recipe:
            return

        selected = self.process_recipe_list.selection()
        if not selected:
            self.process_options_pane.fields = {}
            self.process_name_var.set("-")
            return

        iid = selected[0]
        if iid == "input":
            self.process_options_pane.fields = {}
            self.process_name_var.set("-")
            return

        step_i = int(iid.split("-")[1])
        df_process = self._subproject.current_recipe.process_steps[step_i].df_process
        process_class = self._subproject.get_class_from_name(df_process, DfProcess)

        self.process_options_pane.fields = process_class.get_options()
        self.process_options_pane.options = self._subproject.current_recipe.process_steps[
            step_i
        ].kwargs
        self.process_name_var.set(df_process)

    @update_method
    def update_plotter_options(self) -> None:
        if not self._subproject:
            return

        if not self._subproject.current_recipe:
            return

        plotter = self._subproject.current_recipe.plotter
        if not plotter:
            self.plotter_options_pane.fields = {}
            return

        plotter_name = plotter.plotter
        plotter_class = self._subproject.get_class_from_name(plotter_name, DfPlotter)

        self.plotter_options_pane.fields = plotter_class.get_options()
        self.plotter_options_pane.options = plotter.kwargs

    @update_method
    def update_plotter_list(self) -> None:
        self.plotter_list.delete(*self.plotter_list.get_children())
        for name in self._plotter_list.keys():
            self.plotter_list.insert("", "end", text=name)

    @update_method
    def update_plot(self) -> None:
        logger.debug("update_plot called")
        if not self._subproject:
            logger.debug("no subproject")
            return

        if not self._subproject.current_recipe:
            logger.debug("no current recipe")
            return

        if not self._subproject.current_recipe.plotter:
            return

        fig = plt.figure(figsize=(8, 6), constrained_layout=True)
        try:
            self._subproject.plot_from_process_manifest(self._subproject.current_recipe, fig)
        # TODO: handle error
        except Exception:
            logger.exception("Error occurred while plotting")
            return

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        img = Image.open(buf)
        self._plot_image_pil = img

        self.update()
        canvas_width = self._plot_canvas.winfo_width()
        canvas_height = self._plot_canvas.winfo_height()

        resize_ratio = min(canvas_width / img.width, canvas_height / img.height) * 0.9

        resized_img = img.resize(
            size=(
                int(img.width * resize_ratio),
                int(img.height * resize_ratio),
            )
        )
        img_tk = ImageTk.PhotoImage(resized_img)

        self._plot_canvas.create_image(
            canvas_width / 2,
            canvas_height / 2,
            image=img_tk,
        )
        self._plot_image_tk = img_tk  # keep reference to avoid GC

    # Event handlers
    @event_handler
    def handle_add_to_input(self) -> None:
        """
        Add selected items in original list to the input list
        """
        if not self._subproject:
            return

        name = self.input_filename_var.get()
        if not name:
            return

        selected = self.original_list.selection()
        if not selected:
            return
        iid = selected[0]

        # skip if it has children (directory)
        if self.original_list.get_children(iid):
            return

        # path = self.project.path.data_original / iid
        self._subproject.manifest.inputs[name] = InputManifest(
            original=iid,
            file_process_steps=[FileProcessStep("ebilab.analysis2.process.RemoveCommentLine", {})],
        )
        self._subproject.save_manifest()

        self.update_input_output_list()

    @event_handler
    def handle_on_select_subproject(self) -> None:
        self.update_input_output_list()
        self.update_process_recipe_list()
        self.update_process_list()
        self.update_plotter_list()

    @event_handler
    def handle_on_select_input(self) -> None:
        if not self._subproject:
            return

        selected = self.input_list.selection()
        if not selected:
            return

        iid = selected[0]
        name = self.input_list.item(iid)["text"]

        if not self._subproject.current_recipe:
            self._subproject.current_recipe = DfProcessManifest(input=name)
        else:
            self._subproject.current_recipe.input = name
        self.output_saved = False

        self.update_process_recipe_list()
        self.update_process_list()
        self.update_plot()

    @event_handler
    def handle_on_select_output(self) -> None:
        """
        Just update entry widget
        """
        if not self._subproject:
            return

        selected = self.output_list.selection()
        if not selected:
            return

        iid = selected[0]
        name = self.output_list.item(iid)["text"]

        self.output_name_var.set(name)

    @event_handler
    def handle_on_select_process(self) -> None:
        self.update_process_options()

    @event_handler
    def handle_on_edit_process_options(self) -> None:
        options = self.process_options_pane.options

        if not self._subproject:
            return

        if not self._subproject.current_recipe:
            return

        selected = self.process_recipe_list.selection()
        if not selected:
            return

        iid = selected[0]
        if iid == "input":
            return

        step_i = int(iid.split("-")[1])
        self._subproject.current_recipe.process_steps[step_i].kwargs = options
        self.output_saved = False

        self.update_plot()
        self.update_process_recipe_list()

    @event_handler
    def handle_on_edit_plotter_options(self) -> None:
        options = self.plotter_options_pane.options

        if not self._subproject:
            return

        if not self._subproject.current_recipe:
            return

        plotter = self._subproject.current_recipe.plotter
        if plotter is None:
            self.plotter_options_pane.fields = {}
            return

        plotter.kwargs = options
        self.plotter_saved = False

        self.update_plot()

    @event_handler
    def handle_on_select_plotter(self) -> None:
        if not self._subproject:
            return

        selected = self.plotter_list.selection()
        if not selected:
            return

        iid = selected[0]
        name = self.plotter_list.item(iid)["text"]

        if not self._subproject.current_recipe:
            return

        plotter_class = self._subproject.get_class_from_name(name, DfPlotter)
        self._subproject.current_recipe.plotter = PlotterStep(
            plotter=name, kwargs=plotter_class.get_default_options()
        )
        self.plotter_saved = False

        self.update_plot()
        self.update_plotter_options()

    @event_handler
    def handle_open_original_data_window(self) -> None:
        self.update_original_data_list()
        self.original_data_window.deiconify()
        self.original_data_window.focus_force()
        self.original_data_window.grab_set()  # make modal

    @event_handler
    def handle_add_process(self) -> None:
        if not self._subproject:
            return

        selected = self.process_list.selection()
        if not selected:
            return

        iid = selected[0]
        name = self.process_list.item(iid)["text"]

        if not self._subproject.current_recipe:
            return

        process_class = self._subproject.get_class_from_name(name, DfProcess)
        self._subproject.current_recipe.process_steps.append(
            DfProcessStep(df_process=name, kwargs=process_class.get_default_options())
        )
        self.output_saved = False

        self.update_process_recipe_list()

    @event_handler
    def handle_delete_process_step(self):
        if not self._subproject:
            return

        if not self._subproject.current_recipe:
            return

        selected = self.process_recipe_list.selection()
        if not selected:
            return

        iid = selected[0]
        if iid == "input":
            return

        step_i = int(iid.split("-")[1])
        self._subproject.current_recipe.process_steps.pop(step_i)

        self.update_process_list()
        self.update_process_recipe_list()
        self.update_process_options()
        self.update_plot()

    @event_handler
    def handle_copy_plotter_image(self) -> None:
        self._plot_image_pil
        if hasattr(self, "_plot_image_pil") and self._plot_image_pil:
            copy_img_to_clipboard(self._plot_image_pil)

    @event_handler
    def handle_close_original_data_window(self) -> None:
        self.original_data_window.withdraw()
        self.original_data_window.grab_release()

    @event_handler
    def handle_close_main_window(self) -> None:
        if not self.output_saved:
            message = "Unsaved changes will be lost. Are you sure you want to exit?"
            if not messagebox.askyesno("Load", message):
                return

        self.destroy()
        self.quit()

    @event_handler
    def handle_save(self) -> None:
        if not self._subproject:
            return
        self.status_bar.show("Saving...")
        self.update_idletasks()
        self._subproject.save_manifest()
        self.status_bar.show("Saved")

    @event_handler
    def handle_load(self) -> None:
        if not self._subproject:
            return

        # dialogue
        if not self.output_saved:
            message = (
                "Unsaved changes will be lost. Are you sure you want to reload the manifest file?"
            )
            if not messagebox.askyesno("Load", message):
                return

        self.status_bar.show("Loading...")
        self.update_idletasks()
        self._subproject.load_manifest()

        self.update_input_output_list()
        self.update_process_list()
        self.update_process_recipe_list()
        self.update_plotter_list()
        self.update_plot()

        self.status_bar.show("Loaded")

    @event_handler
    def handle_load_output(self) -> None:
        if not self._subproject:
            return

        selected = self.output_list.selection()
        if not selected:
            return

        iid = selected[0]
        name = self.output_list.item(iid)["text"]

        self._subproject.current_recipe = copy.deepcopy(self._subproject.manifest.outputs[name])
        self.output_saved = True

        self.update_process_recipe_list()
        self.update_plot()

    @event_handler
    def handle_save_output(self) -> None:
        if not self._subproject:
            return

        output_name = self.output_name_var.get()
        if not output_name or output_name.replace(" ", "") == "":
            messagebox.showerror("Error", "Output name is required")

        if not self._subproject.current_recipe:
            return

        recipe_to_save = copy.deepcopy(self._subproject.current_recipe)
        recipe_to_save.plotter = None
        self._subproject.manifest.outputs[output_name] = recipe_to_save
        self._subproject.save_manifest()

        self.output_saved = True

        self.update_input_output_list()


class StatusBar(tk.Frame):
    def __init__(self, master=None, idle_text: str = "Status: Ready"):
        super().__init__(master)
        self.label = tk.Label(self, text=idle_text, relief="sunken", anchor="w")
        self.label.pack(fill="x")
        self.pack(side="bottom", fill="x")

        self.idle_text = idle_text
        self.timer: str | None = None

    def show(self, message: str) -> None:
        self.label["text"] = message
        if self.timer:
            self.after_cancel(self.timer)
            self.timer = None
        self.timer = self.after(5000, self.clear)

    def clear(self) -> None:
        self.label["text"] = self.idle_text
