import pytest

from ebilab.analysis2.base import DfProcess
from ebilab.analysis2.options import IntField, StrField


def test_get_options():
    class TestDfProcess(DfProcess):
        a = IntField(default=1)

    options = TestDfProcess.get_options()
    assert len(options.keys()) == 1
    assert "a" in options
    assert options["a"].default == 1

    class TestDfProcess(DfProcess):
        a = IntField(default=1)
        s = StrField(default="test")

    options = TestDfProcess.get_options()
    assert len(options.keys()) == 2
    assert "a" in options
    assert "s" in options
    assert options["a"].default == 1
    assert options["s"].default == "test"


def test_get_options_fallback():
    class TestDfProcess(DfProcess):
        options = {"a": IntField(default=1)}

    options = TestDfProcess.get_options()
    assert len(options.keys()) == 1
    assert "a" in options
    assert options["a"].default == 1


def test_plotter_inject_options():
    class TestDfProcess(DfProcess):
        a = IntField(default=1)

    test = TestDfProcess({"a": 2})
    assert test.a == 2
    assert test.kwargs["a"] == 2


def test_plotter_missing_options():
    class TestDfProcess(DfProcess):
        a = IntField(default=1)

    with pytest.raises(ValueError):
        TestDfProcess({})
