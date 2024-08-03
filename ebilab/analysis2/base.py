from io import TextIOWrapper

# import matplotlib.pyplot as plt  # type: ignore
import pandas as pd  # type: ignore
from matplotlib.figure import Figure  # type: ignore


class DfPlotter:
    def plot(self, df: pd.DataFrame, fig: Figure) -> None:
        raise NotImplementedError("plot method must be implemented in subclass")


class FileProcess:
    def process(self, fin: TextIOWrapper, fout: TextIOWrapper) -> None:
        raise NotImplementedError("process method must be implemented in subclass")


class DfProcess:
    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError("process method must be implemented in subclass")
