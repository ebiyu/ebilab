import warnings

from ._actions import agg_df_plotter, df_action, df_plotter
from ._preprocess import original
from ._process import aggregate, from_df, input, output

warnings.warn(
    "ebilab.analysis package is no longer maintained and will be removed in the future."
    "You are recommended to lock the version if you are using it.",
    UserWarning,
)

__all__ = [
    "from_df",
    "input",
    "output",
    "aggregate",
    "df_action",
    "df_plotter",
    "agg_df_plotter",
    "original",
]
