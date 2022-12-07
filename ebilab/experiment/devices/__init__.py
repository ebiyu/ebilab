"""
Classes to control experimental devices
"""

from logging import getLogger
logger = getLogger(__name__)

import os
is_mock_enabled = bool(os.environ.get("EBILAB_MOCK"))
if is_mock_enabled:
    logger.warn("Mocking of devices is enabled.")
del os
del getLogger
del logger


from ._visa.K34411A import K34411A
from ._visa.A707 import A707
from ._visa.E4980 import E4980
