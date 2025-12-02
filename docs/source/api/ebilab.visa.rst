ebilab.visa
===========

VISA対応デバイスを制御するためのパッケージです。

.. module:: ebilab.visa

.. note::

    VISAドライバー（Keysight-VISA または NI-VISA）がインストールされている必要があります。

Base Class
----------

.. autoclass:: ebilab.visa.VisaDevice
    :members:
    :undoc-members:
    :show-inheritance:

Supported Devices
-----------------

Keysight 34411A (Digital Multimeter)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: ebilab.visa.K34411A
    :members:
    :undoc-members:
    :show-inheritance:

Keysight 34465A (Digital Multimeter)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: ebilab.visa.K34465A
    :members:
    :undoc-members:
    :show-inheritance:

Keysight E4980A/AL (LCR Meter)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: ebilab.visa.E4980
    :members:
    :undoc-members:
    :show-inheritance:

Daiichi Electronics A707 (Power Supply)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: ebilab.visa.A707
    :members:
    :undoc-members:
    :show-inheritance:
