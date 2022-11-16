"""
Utility and base class related to visa
"""

from typing import Optional

import pyvisa

from typing import Dict, Optional
import os
import re
from dataclasses import dataclass

@dataclass
class _VisaManagerDevice:
    idn: str
    inst: pyvisa.Resource

class VisaManager:
    """
    Manager class of visa device based on pyvisa module

    Do not intialize directory, use :py:meth:`get_visa_manager() <ebilab.experiment.devices.visa.get_visa_manager>` method instead.
    """

    _rm: Optional[pyvisa.ResourceManager] = None
    _devices: Dict[str, _VisaManagerDevice] = {}

    @property
    def rm(self):
        """
        ResourceManager of pyvisa module
        """
        return self._rm

    def __del__(self):
        if self.rm:
            self.rm.close()

    def __init__(self):
        os.add_dll_directory('C:\\Program Files\\Keysight\\IO Libraries Suite\\bin') # omajinai

        rm = pyvisa.ResourceManager()
        visa_list = rm.list_resources()

        for addr in visa_list:
            try:
                inst = rm.open_resource(addr)
                try:
                    idn = inst.query('*IDN?')
                    self._devices[addr] = _VisaManagerDevice(idn, inst)
                except:
                    inst.close()
            except:
                pass

    def get_inst(self, pattern: str) -> Optional[pyvisa.Resource]:
        """
        Get pyvisa instance from pattern that matches *IDN? result.

        Args:
            pattern (str): regex pattern

        Returns:
            pyvisa Resource
        """
        for addr, device in self._devices.items():
            if re.search(pattern, device.idn):
                return device.inst
        return None

# To be singleton
_visa_manager = None
def get_visa_manager():
    """
    Function to get :py:class:`VisaManager <ebilab.experiment.devices.visa.VisaManager>` class.
    Many times of call of this function returns same VisaManager.

    Returns:
        VisaManager class
    """
    global _visa_manager
    if _visa_manager is None:
        _visa_manager = VisaManager()
    return _visa_manager


class DeviceNotFoundError(Exception):
    pass

class VisaDevice:
    """
    Base class of visa device.

    You can inherit this class and implement class to new device.

    Attributes:
        pyvisa_inst: instance from `ResourceManager.open_resource` of pyvisa module
            Please use this only when you use method which is not supported in VisaDevice class
    """

    _idn_pattern: Optional[str] = None
    def __init__(self, *, addr: str = None, **kwargs):
        if self._idn_pattern is None:
            raise NotImplementedError("idn_pattern is None")
        inst = get_visa_manager().get_inst(self._idn_pattern)
        if inst is None:
            raise DeviceNotFoundError(f"Device matching \"{self._idn_pattern}\" is not found")
        self.pyvisa_inst = inst
        self.pyvisa_inst.timeout = 10000
        self._initialize(**kwargs)

    def _initialize(self, **kwargs):
        raise NotImplementedError()

    def visa_write(self, cmd: str):
        """
        Send command to visa device
        Equivalent to :py:func:`inst.write` in pyvisa class
        """
        self.pyvisa_inst.write(cmd)

    def visa_query(self, cmd: str):
        """
        Send command to visa device and read output from device
        Equivalent to :py:func:`inst.query` in pyvisa class
        """
        return self.pyvisa_inst.query(cmd)
    
    def __del__(self) -> None:
        if hasattr(self, "pyvisa_inst") and self.pyvisa_inst is not None:
            self.pyvisa_inst.close()

