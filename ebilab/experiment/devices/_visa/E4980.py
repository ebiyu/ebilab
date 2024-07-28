from __future__ import annotations

import time
import warnings
from typing import Any, overload

from typing_extensions import deprecated

from ..visa import VisaDevice


class E4980(VisaDevice):
    """
    Keysight E4980A Precision LCR Meter
    """

    _idn_pattern = "E4980"

    def _initialize(self, **kwargs: Any) -> None:
        self.visa_write("*RST;*CLS")
        self.visa_write("FORMAT ASC;TRIG:SOUR BUS")
        self.visa_write(":INIT:CONT ON")
        self.visa_write(":TRIG:DEL 0")
        self.visa_write("*SRE 1")

    # ampl (deprecated)
    @overload
    @deprecated("Parameter 'ampl' is deprecated. Use 'voltage' instead.")
    def trigger(
        self,
        f: float,
        *,
        time: str = "MED",
        ampl: float = 0.1,
        format: str = "ZTD",
    ) -> tuple[float, float]:
        pass

    # voltage / current (exclusive)
    @overload
    def trigger(
        self,
        f: float,
        *,
        time: str = "MED",
        voltage: float | None = None,
        current: float | None = None,
        format: str = "ZTD",
    ) -> tuple[float, float]:
        pass

    def trigger(
        self,
        f: float,
        *,
        time: str = "MED",
        ampl: float | None = None,
        voltage: float | None = None,
        current: float | None = None,
        format: str = "ZTD",
    ) -> tuple[float, float]:
        """
        measure impedance

        Args:
            f (float): frequency to measure

        Keyword Args:
            voltage (float): measurement amplitude [V]. Voltage and current are exclusive.
            current (float): measurement amplitude [A]. Voltage and current are exclusive.
            time (str): measurement time from {"LONG", "MED", "SHORT"}
            format (str): format of return value from
                {"CPD", "CPQ", "CPG", "CPRP", "CSD", "CSQ", "CSRS", "LPD", "LPQ", "LPG", "LPRP",
                "LSD", "LSQ", "LSRS", "RX", "ZTD", "ZTR", "GB", "YTD", "YTR"}

        Returns:
            [float, float]: Measured impedance value
        """

        # valitdate args
        if time not in ["LONG", "MED", "SHORT"]:
            raise ValueError(f"Unknown time: {time}")
        if format not in [
            "CPD",
            "CPQ",
            "CPG",
            "CPRP",
            "CSD",
            "CSQ",
            "CSRS",
            "LPD",
            "LPQ",
            "LPG",
            "LPRP",
            "LSD",
            "LSQ",
            "LSRS",
            "RX",
            "ZTD",
            "ZTR",
            "GB",
            "YTD",
            "YTR",
        ]:
            raise ValueError(f"Unknown format: {format}")

        self.visa_write(f"FUNC:IMP {format}")
        self.visa_write(f"APER {time}")

        if ampl is not None:
            if voltage is not None or current is not None:
                raise ValueError("`ampl` is specified with voltage or current. Remove `ampl`.")
            voltage = ampl
            warnings.warn("ampl is deprecated. Use voltage instead.", DeprecationWarning)
        if voltage is not None:
            self.visa_write(f"VOLT {voltage}")
        elif current is not None:
            self.visa_write(f"CURR {current}")
        else:
            self.visa_write("VOLT 0.1")

        self.visa_write(f"FREQ:CW {f}")

        ret = self.visa_query("*TRG")
        Z, t, *_ = map(float, ret.split(","))
        return (Z, t)

    def meas_open(self, *, wait: bool = True) -> None:
        self.visa_write("CORR:OPEN:EXEC")
        if wait:
            self.wait_correction()

    def meas_short(self, *, wait: bool = True) -> None:
        self.visa_write("CORR:SHORT:EXEC")
        if wait:
            self.wait_correction()

    def wait_correction(self) -> None:
        self.pyvisa_inst.timeout = None
        while True:
            time.sleep(0.1)
            ret = int(self.visa_query(":STAT:OPER:COND?"))
            if (ret & 1) == 0:
                self.pyvisa_inst.timeout = 10000
                break
