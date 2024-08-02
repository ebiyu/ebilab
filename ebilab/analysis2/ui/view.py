import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..project import Project


class View(tk.Tk):
    project: Project

    def __init__(self, project: Project):
        self.project = project

        super().__init__()
        self.title("My App")
        self.geometry("400x200")
        self.state("zoomed") # maximize window
        self.create_widgets()

        self.update_original_data_list()
        self.update_subproject_list

    def create_widgets(self):
        # create layout frames (4 columns)
        col1 = ttk.Frame(self, border=1, relief="solid")
        col1.pack(side="left", fill="both", expand=True)
        col2 = ttk.Frame(self, border=1, relief="solid")
        col2.pack(side="left", fill="both", expand=True)
        col3 = ttk.Frame(self, border=1, relief="solid")
        col3.pack(side="left", fill="both", expand=True)
        col4 = ttk.Frame(self, border=1, relief="solid")
        col4.pack(side="left", fill="both", expand=True)

        self.original_list = ttk.Treeview(col1)
        self.original_list.pack(fill="both", expand=True)

    def update_original_data_list(self):
        # clear list
        self.original_list.delete(*self.original_list.get_children())

        def relative_insert(path: Path):
            parent_iid = path.parent.relative_to(self.project.path.data_original).as_posix()
            if parent_iid == ".":  # root
                parent_iid = ""
            new_iid = path.relative_to(self.project.path.data_original).as_posix()
            if not self.original_list.exists(parent_iid):
                relative_insert(path.parent)
            self.original_list.insert(parent_iid, "end", text=path.name, iid=new_iid)

        # insert files  
        for item in self.project.get_original_files():
            relative_insert(item)

    def update_subproject_list(self):
        pass


if __name__ == "__main__":
    app = View()
    app.mainloop()
