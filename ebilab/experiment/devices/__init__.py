"""
Classes to control experimental devices
"""

import os
is_mock_enabled = bool(os.environ.get("EBILAB_MOCK"))
del os

from ._visa.K34411A import K34411A
from ._visa.A707 import A707
from ._visa.E4980 import E4980
