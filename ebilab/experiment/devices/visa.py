"""
Utility and base class related to visa

This library depends on `pyvisa <https://pyvisa.readthedocs.io/>`_ for VISA control.
"""

# TODO: type

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from logging import getLogger
from typing import Any

import pyvisa

logger = getLogger(__name__)


@dataclass
class _VisaManagerDevice:
    idn: str
    inst: Any


class VisaManager:
    """
    Manager class of visa device based on pyvisa module

    Do not intialize directory, use
    :py:meth:`get_visa_manager() <ebilab.experiment.devices.visa.get_visa_manager>` method instead.
    """

    _rm: pyvisa.ResourceManager | None = None
    _devices: dict[str, _VisaManagerDevice] = {}

    @property
    def rm(self) -> pyvisa.ResourceManager | None:
        """
        ResourceManager of pyvisa module
        """
        return self._rm

    def __del__(self) -> None:
        for _, device in self._devices.items():
            device.inst.close()
        if self.rm:
            self.rm.close()

    def __init__(self) -> None:
        logger.debug("Initializing VisaManager")
        # omajinai
        os.add_dll_directory("C:\\Program Files\\Keysight\\IO Libraries Suite\\bin")  # type: ignore

        rm = pyvisa.ResourceManager()
        logger.info(f"Resource manager initialized: {str(rm)}")
        visa_list = rm.list_resources()
        logger.debug(f"List resources: {str(visa_list)}")

        for addr in visa_list:
            try:
                inst: Any = rm.open_resource(addr)
                try:
                    idn = inst.query("*IDN?")
                    logger.debug(f"*IDN? to {addr}: {idn}")
                    self._devices[addr] = _VisaManagerDevice(idn, inst)
                except:  # noqa: E722
                    logger.debug(f"No response to *IDN? from {addr}")
                    inst.close()
            except:  # noqa: E722
                pass

    def get_inst(self, pattern: str) -> Any | None:
        """
        Get pyvisa instance from pattern that matches *IDN? result.

        Args:
            pattern (str): regex pattern

        Returns:
            pyvisa Resource
        """
        for addr, device in self._devices.items():
            if re.search(pattern, device.idn):
                logger.info(f"{device.idn} ({addr}) matched {pattern}")
                return device.inst
        return None


# To be singleton
_visa_manager: VisaManager | None = None


def get_visa_manager() -> VisaManager:
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

    _idn_pattern: str | None = None
    pyvisa_inst: Any

    def __init__(self, *, addr: str | None = None, **kwargs: Any) -> None:
        if self._idn_pattern is None:
            raise NotImplementedError("idn_pattern is None")
        inst = get_visa_manager().get_inst(self._idn_pattern)
        if inst is None:
            raise DeviceNotFoundError(f'Device matching "{self._idn_pattern}" is not found')
        self.pyvisa_inst = inst
        self.pyvisa_inst.timeout = 10000
        logger.info(f"{self.__class__.__name__} is initializing...")
        self._initialize(**kwargs)
        logger.info(f"{self.__class__.__name__} has initialized")

    def _initialize(self, **kwargs: Any) -> None:
        raise NotImplementedError()

    def visa_write(self, cmd: str) -> None:
        """
        Send command to visa device
        Equivalent to :py:func:`inst.write` in pyvisa class
        """
        self.pyvisa_inst.write(cmd)
        logger.info(f"{self.__class__.__name__} -> device: {cmd}")

    def visa_query(self, cmd: str) -> str:
        """
        Send command to visa device and read output from device
        Equivalent to :py:func:`inst.query` in pyvisa class
        """
        logger.info(f"{self.__class__.__name__} -> device?: {cmd}")
        res: str = self.pyvisa_inst.query(cmd)
        logger.info(f"{self.__class__.__name__} <- device: {res}")
        return res
