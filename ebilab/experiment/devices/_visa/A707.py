from time import sleep
from typing import List

from ..visa import VisaDevice
from .. import is_mock_enabled

class A707(VisaDevice):
    """
    Keithley 707A Switching Matrix
    """

    _idn_pattern = "707A"

    def _initialize(self, **kwargs):
        self.visa_write("XRX")
        sleep(1)

    def close_only(self, contacts: List[str]):
        """
        Open all switch and close only specified switch

        Args:
            contacts (list): like `["A2", "B4", "C5"]`
        """
        string = ",".join([contact for contact in contacts])
        self.visa_write(f'E0P0C{string}X')
        sleep(0.1)

if is_mock_enabled:
    class A707:
        def close_only(self, contacts: List[str]):
            pass
