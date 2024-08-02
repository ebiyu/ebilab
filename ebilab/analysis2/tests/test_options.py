from ebilab.analysis2.options import BoolField, FloatField, IntField, SelectField, StrField


def test_make_instance():
    FloatField(default=1.0)
    SelectField(choices=["a", "b"])
    IntField(default=1)
    StrField(default="test")
    BoolField(default=True)
