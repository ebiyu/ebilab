from unittest import TestCase
import os
from pathlib import Path

from ebilab.project import get_current_project

class TestFoo(TestCase):
    def test_paths(self):
        os.chdir(Path(__file__).resolve().parent / "sample")
        project = get_current_project()
        self.assertTrue(project.path.data_input.exists())
        self.assertTrue(project.path.data_output.exists())
        self.assertTrue(project.path.data_original.exists())

    def test_parent_paths(self):
        os.chdir(Path(__file__).resolve().parent / "sample" / "other_dir")
        project = get_current_project()
        self.assertTrue(project.path.data_input.exists())
        self.assertTrue(project.path.data_output.exists())
        self.assertTrue(project.path.data_original.exists())
