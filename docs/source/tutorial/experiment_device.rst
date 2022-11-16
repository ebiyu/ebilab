####################
実験装置の制御
####################

:py:mod:`ebilab.experiment.devices` モジュールを用いることで、実験装置の制御ができます。

以下のコードは、デジタルマルチメーターを用いて抵抗の測定を行なうサンプルです。

.. literalinclude:: ../../../sample/multimeter.py
   :language: python
   :linenos:

実験装置の制御を行なうには、 :py:mod:`ebilab.experiment.devices` モジュールに含まれる該当デバイスのクラスを import してください。

クラスのインスタンスを初期化したタイミングで、自動的に接続されているデバイスを検出します。
デバイスを検出できなかった場合、 :py:class:`DeviceNotFoundError <ebilab.experiment.devices.visa.VisaDevice.DeviceNotFoundError>` を送出します。

.. note::

    デバイスの全ての操作が実装されているわけではありません。
    対応していない操作が必要な場合の手順は、後ほどドキュメントに追記します。

