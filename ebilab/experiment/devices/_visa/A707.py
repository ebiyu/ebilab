from __future__ import annotations

from time import sleep
from typing import Any

from ..visa import VisaDevice


class A707(VisaDevice):
    """
    Keithley 707A Switching Matrix
    """

    _idn_pattern = "707A"

    def _initialize(self, **kwargs: Any) -> None:
        self.visa_write("XRX")
        sleep(1)

    def close_only(self, contacts: list[str]) -> None:
        """
        Open all switch and close only specified switch

        Args:
            contacts (list): like `["A2", "B4", "C5"]`
        """
        if len(contacts) == 0:
            self.visa_write("E0P0X")
        else:
            string = ",".join([contact for contact in contacts])
            self.visa_write(f"E0P0C{string}X")
        sleep(0.1)

    def open_all(self) -> None:
        self.close_only([])
