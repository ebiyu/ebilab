from enum import Enum

from ..visa import VisaDevice
from .. import is_mock_enabled

class E4980(VisaDevice):
    """
    Keysight E4980A Precision LCR Meter
    """

    _idn_pattern = "E4980"

    def _initialize(self, **kwargs):
        self.visa_write("*RST;*CLS")
        self.visa_write('FORMAT ASC;TRIG:SOUR BUS')
        self.visa_write(':INIT:CONT ON')
        self.visa_write(':TRIG:DEL 0')
        self.visa_write('*SRE 1')

    def trigger(self, f: float, *, time: str = "MED", ampl: float = 0.1, format: str = "ZTD"):
        """
        measure impedance

        Args:
            f (float): frequency to measure

        Keyword Args:
            ampl (float): measurement amplitude [V]
            time (str): measurement time from {"LONG", "MED", "SHORT"}
            format (str): format of return value from
                {"CPD", "CPQ", "CPG", "CPRP", "CSD", "CSQ", "CSRS", "LPD", "LPQ", "LPG", "LPRP", "LSD", "LSQ", "LSRS", "RX", "ZTD", "ZTR", "GB", "YTD", "YTR"}

        Returns:
            [float, float]: Measured impedance value
        """

        # valitdate args
        if time not in ["LONG", "MED", "SHORT"]:
            raise ValueError(f"Unknown time: {time}")
        if format not in ["CPD", "CPQ", "CPG", "CPRP", "CSD", "CSQ", "CSRS", "LPD", "LPQ", "LPG", "LPRP", "LSD", "LSQ", "LSRS", "RX", "ZTD", "ZTR", "GB", "YTD", "YTR"]:
            raise ValueError(f"Unknown format: {format}")

        self.visa_write(f'FUNC:IMP {format}')
        self.visa_write(f'APER {time}')
        self.visa_write(f'VOLT {ampl}')
        self.visa_write(f'FREQ:CW {f}')

        ret = self.visa_query(f'*TRG')
        Z, t, *_ = map(float, ret.split(","))
        return (Z, t)

if is_mock_enabled:
    class E4980:
        def trigger(self, f: float, *, time: str = "MED", ampl: float = 0.1, format: str = "ZTD"):
            from time import sleep
            from random import random
            sleep(0.4)
            return 1e6 / f * (0.9 + random() * 0.2), random() * 20 - 10
