from __future__ import annotations

from typing import Any

from ..visa import VisaDevice


class K34411A(VisaDevice):
    """
    Keysight 6½ Digit Digital Multimeter 34411A
    """

    _idn_pattern = "34411A"

    _option_nplc = [
        "0.001",
        "0.002",
        "0.006",
        "0.02",
        "0.06",
        "0.2",
        "1",
        "2",
        "10",
        "100",
    ]
    _option_r_range = [
        "auto",
        "1E+2",
        "1E+3",
        "1E+4",
        "1E+5",
        "1E+6",
        "1E+7",
        "1E+8",
        "1E+9",
    ]
    _option_v_range = ["auto", "1E-1", "1E+0", "1E+1", "1E+2", "1E+3"]

    def _initialize(self, **kwargs: Any) -> None:
        self.visa_write("*RST;*CLS")
        self.visa_write("RES:RANG:AUTO ON")
        self.visa_write("TRIG:SOUR BUS")

    def measure_resistance(self, *, nplc: str | None = None, range: str = "auto") -> float:
        """
        Measure resistance once

        Args:
            nplc (Optional[str]): String from
                {"0.001", "0.002", "0.006", "0.02", "0.06", "0.2", "1", "2", "10", "100"}
            range (Optional[str]): String from
                {"auto", "1E+2", "1E+3", "1E+4", "1E+5", "1E+6", "1E+7", "1E+8", "1E+9"}
        """

        # validate input
        if nplc and nplc not in self._option_nplc:
            raise ValueError(f'NPLC value "{nplc}" is invalid.')
        if range not in self._option_r_range:
            raise ValueError(f'Range value "{range}" is invalid.')

        self.visa_write("CONF:RES")
        if nplc:
            self.visa_write(f"RES:NPLC {nplc}")

        if range == "auto":
            self.visa_write("RES:RANG:AUTO ON")
        else:
            self.visa_write(f"RES:RANG {range}")

        val = self.visa_query("READ?")
        return float(val)

    def measure_resistance_4w(self, *, nplc: str | None = None, range: str = "auto") -> float:
        """
        Measure resistance once by 4 wire method

        Args:
            nplc (Optional[str]): String from
                {"0.001", "0.002", "0.006", "0.02", "0.06", "0.2", "1", "2", "10", "100"}
            range (Optional[str]): String from
                {"auto", "1E+2", "1E+3", "1E+4", "1E+5", "1E+6", "1E+7", "1E+8", "1E+9"}
        """

        # validate input
        if nplc and nplc not in self._option_nplc:
            raise ValueError(f'NPLC value "{nplc}" is invalid.')
        if range not in self._option_r_range:
            raise ValueError(f'Range value "{range}" is invalid.')

        self.visa_write("CONF:FRES")
        if nplc:
            self.visa_write(f"FRES:NPLC {nplc}")

        if range == "auto":
            self.visa_write("FRES:RANG:AUTO ON")
        else:
            self.visa_write(f"FRES:RANG {range}")

        val = self.visa_query("READ?")
        return float(val)

    def measure_voltage(self, *, nplc: str | None = None, range: str = "auto") -> float:
        """
        Measure resistance once

        Args:
            nplc (Optional[str]): String from
                {"0.001", "0.002", "0.006", "0.02", "0.06", "0.2", "1", "2", "10", "100"}
            range (Optional[str]): String from
                {"auto", "1E-1", "1E+0", "1E+1", "1E+2", "1E+3"}
        """

        # validate input
        if nplc and nplc not in self._option_nplc:
            raise ValueError(f'NPLC value "{nplc}" is invalid.')

        if range not in self._option_v_range:
            raise ValueError(f'Range value "{range}" is invalid.')

        self.visa_write("CONF:VOLT")
        if nplc:
            self.visa_write(f"VOLT:NPLC {nplc}")

        if range == "auto":
            self.visa_write("VOLT:RANG:AUTO ON")
        else:
            self.visa_write(f"VOLT:RANG {range}")

        val = self.visa_query("READ?")
        return float(val)
