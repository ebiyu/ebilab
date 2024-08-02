import tkinter as tk
from tkinter import ttk


class View(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("My App")
        self.geometry("400x200")
        self.create_widgets()

    def create_widgets(self):
        self.label = ttk.Label(self, text="Hello, World!")
        self.label.pack(pady=10)
        self.button = ttk.Button(self, text="Click Me")
        self.button.pack(pady=10)


if __name__ == "__main__":
    app = View()
    app.mainloop()
