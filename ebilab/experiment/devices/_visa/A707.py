from typing import List

from ..visa import VisaDevice
from .. import is_mock_enabled

class A707(VisaDevice):
    """
    Keithley 707A Switching Matrix
    """

    _idn_pattern = "707A"

    def _initialize(self, **kwargs):
        self.visa_write("*RST;*CLS")
        self.visa_write('E0P0X')

    def close_only(self, contacts: List[str]):
        """
        Open all switch and close only specified switch

        Args:
            contacts (list): like `["A2", "B4", "C5"]`
        """
        string = "".join(["C" + contact for contact in contacts])
        self.visa_write(f'E0P0{string}X')

if is_mock_enabled:
    class A707:
        def close_only(self, contacts: List[str]):
            pass
