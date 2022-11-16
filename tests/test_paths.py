from unittest import TestCase
import os
from pathlib import Path

class TestFoo(TestCase):
    def test_paths(self):
        from ebilab.analysis.paths import paths
        os.chdir(Path(__file__).resolve().parent / "sample")
        self.assertTrue(paths.data.exists())
        self.assertTrue(paths.input.exists())
        self.assertTrue(paths.output.exists())
        self.assertTrue(paths.original.exists())

    def test_parent_paths(self):
        from ebilab.analysis.paths import paths
        os.chdir(Path(__file__).resolve().parent / "sample" / "other_dir")
        self.assertTrue(paths.data.exists())
        self.assertTrue(paths.input.exists())
        self.assertTrue(paths.output.exists())
        self.assertTrue(paths.original.exists())
