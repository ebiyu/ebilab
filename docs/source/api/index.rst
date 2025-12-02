API Reference
=======================

API in this pages are public APIs.
These APIs support backport compatibility.

.. warning::

    v3 は開発中のため、APIは変更される可能性があります。

Core APIs
---------

.. toctree::
    :maxdepth: 1

    ebilab.api
    ebilab.visa
    ebilab.gui

Utilities
---------

.. toctree::
    :maxdepth: 1

    ebilab.project

Legacy APIs (deprecated)
------------------------

.. warning::

    以下のAPIは v3 で削除されました。

    * ``ebilab.experiment`` - ``ebilab.api`` に置き換えられました
    * ``ebilab.experiment.devices`` - ``ebilab.visa`` に移動しました
    * ``ebilab.analysis`` / ``ebilab.analysis2`` - 削除されました
