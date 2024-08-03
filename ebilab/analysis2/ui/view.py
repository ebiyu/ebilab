from __future__ import annotations

import tkinter as tk
from logging import getLogger
from pathlib import Path
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..base import DfPlotter
from ..project import Project
from ..subproject import DfProcessManifest, DfProcessStep, InputManifest, PlotterStep, SubProject

logger = getLogger(__name__)


# # windows dpi workaround
# try:
#     import ctypes

#     ctypes.windll.shcore.SetProcessDpiAwareness(2)  # type: ignore
# except:  # noqa: E722
#     try:
#         ctypes.windll.user32.SetProcessDPIAware()  # type: ignore
#     except:  # noqa: E722
#         pass


class View(tk.Tk):
    project: Project

    def __init__(self, project: Project):
        self.project = project

        # create main window
        super().__init__()
        self.title("My App")
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
        col1 = ttk.Frame(self, border=1, relief="solid")
        col1.pack(side="left", fill="both", expand=True)
        col2 = ttk.Frame(self, border=1, relief="solid")
        col2.pack(side="left", fill="both", expand=True)
        col3 = ttk.Frame(self, border=1, relief="solid")
        col3.pack(side="left", fill="both", expand=True)
        col4 = ttk.Frame(self, border=1, relief="solid")
        col4.pack(side="left", fill="both", expand=True)

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
        self.output_list = ttk.Treeview(col1)
        self.output_list.pack(fill="both", expand=True)

        # col2
        tk.Label(col2, text="Current Process").pack()
        self.process_recipe_list = ttk.Treeview(col2)
        self.process_recipe_list.pack(fill="both", expand=True)

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

        self._plot_fig = plt.figure(figsize=(6, 6), constrained_layout=True)
        self._plot_canvas = FigureCanvasTkAgg(self._plot_fig, master=col3)
        self._plot_canvas.draw()
        self._plot_canvas.get_tk_widget().pack(fill="both", expand=True)

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

    def update_subproject_list(self) -> None:
        self.subprojects_dropdown["values"] = list(self.project.subprojects.keys())
        self.subprojects_dropdown["state"] = "readonly"
        if not self.subprojects_dropdown.get():
            self.subprojects_dropdown.set(list(self.project.subprojects.keys())[0])

        self.handle_on_select_subproject()

    def update_input_output_list(self) -> None:
        self.input_list.delete(*self.input_list.get_children())
        self.output_list.delete(*self.output_list.get_children())

        if not self._subproject:
            return

        for item in self._subproject.inputs:
            self.input_list.insert("", "end", text=item.name)

        # TODO: update output

    def update_process_list(self) -> None:
        self.process_list.delete(*self.process_list.get_children())

        if not self._subproject:
            return

        for name in self._subproject.df_processes.keys():
            self.process_list.insert("", "end", text=name)

    def update_process_recipe_list(self) -> None:
        self.process_recipe_list.delete(*self.process_recipe_list.get_children())

        if not self._subproject:
            return

        if not self._subproject.current_recipe:
            return

        self.process_recipe_list.insert(
            "", "end", text=self._subproject.current_recipe.input, iid="input", open=True
        )

        for i, step in enumerate(self._subproject.current_recipe.process_steps):
            self.process_recipe_list.insert("input", "end", text=step.df_process, iid=f"step-{i}")

    def update_plotter_list(self) -> None:
        self.plotter_list.delete(*self.plotter_list.get_children())
        for name in self._plotter_list.keys():
            self.plotter_list.insert("", "end", text=name)

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

        # plotter = self._plotter_list[self._subproject.current_recipe.plotter.plotter]()
        self._plot_fig.clear()
        try:
            self._subproject.plot_from_process_manifest(
                self._subproject.current_recipe, self._plot_fig
            )
            # plotter.plotself._subproject.current_recipe.plotter.kwargs, self._plot_fig)
        # TODO: implement j
        # TODO: handle error
        except Exception:
            logger.exception("Error occurred while plotting")

        self._plot_canvas.draw()

    # Event handlers
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

        path = self.project.path.data_original / iid
        self._subproject.inputs.append(InputManifest(name=name, original=path))

        self.update_input_output_list()

    def handle_on_select_subproject(self) -> None:
        self.update_input_output_list()
        self.update_process_recipe_list()
        self.update_process_list()
        self.update_plotter_list()

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

        self.update_process_recipe_list()

    def handle_on_select_plotter(self) -> None:
        logger.debug("handle_on_select_plotter called")
        if not self._subproject:
            return

        selected = self.plotter_list.selection()
        if not selected:
            return

        iid = selected[0]
        name = self.plotter_list.item(iid)["text"]

        if not self._subproject.current_recipe:
            return

        self._subproject.current_recipe.plotter = PlotterStep(plotter=name, kwargs={})

        self.update_plot()

    def handle_open_original_data_window(self) -> None:
        self.update_original_data_list()
        self.original_data_window.deiconify()
        self.original_data_window.focus_force()
        self.original_data_window.grab_set()  # make modal

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

        self._subproject.current_recipe.process_steps.append(
            DfProcessStep(df_process=name, kwargs={})
        )

        self.update_process_recipe_list()

    def handle_close_original_data_window(self) -> None:
        self.original_data_window.withdraw()
        self.original_data_window.grab_release()

    def handle_close_main_window(self) -> None:
        self.destroy()
        self.quit()
