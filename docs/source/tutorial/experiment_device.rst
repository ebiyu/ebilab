####################
実験装置の制御
####################

:py:mod:`ebilab.visa` モジュールを用いることで、VISA対応の実験装置を制御できます。

以下のコードは、デジタルマルチメーターを用いて抵抗の測定を行なうサンプルです。

.. literalinclude:: ../../../sample/multimeter.py
   :language: python
   :linenos:

*************************
デバイスの接続
*************************

:py:mod:`ebilab.visa` モジュールに含まれる該当デバイスのクラスを import して使用します。

.. code-block:: python

    from ebilab.visa import K34411A

    # 自動検出で接続
    multimeter = K34411A()

クラスのインスタンスを初期化したタイミングで、自動的に接続されているデバイスを検出します。
デバイスを検出できなかった場合、例外が発生します。

アドレス指定による接続
=========================

同種のデバイスを複数台接続する場合や、自動検出が上手く動作しない場合は、
``addr`` 引数でVISAアドレスを直接指定できます。

.. code-block:: python

    from ebilab.visa import K34411A

    # アドレスを指定して接続
    multimeter = K34411A(addr="USB0::0x2A8D::0x0101::MY12345678::INSTR")

デバイスアドレスの確認
=========================

接続後、 ``addr`` プロパティでデバイスのアドレスを確認できます。

.. code-block:: python

    multimeter = K34411A()
    print(multimeter.addr)  # 例: "USB0::0x2A8D::0x0101::MY12345678::INSTR"

*************************
サポートされているデバイス
*************************

現在サポートされているデバイスは以下の通りです。

.. list-table::
   :widths: 30 30 40
   :header-rows: 1

   * - クラス名
     - デバイス
     - 説明
   * - :py:class:`K34411A <ebilab.visa.K34411A>`
     - Keysight 34411A
     - デジタルマルチメーター
   * - :py:class:`K34465A <ebilab.visa.K34465A>`
     - Keysight 34465A
     - デジタルマルチメーター
   * - :py:class:`E4980 <ebilab.visa.E4980>`
     - Keysight E4980A/AL
     - LCRメーター
   * - :py:class:`A707 <ebilab.visa.A707>`
     - 第一電子 A707
     - 電源

.. note::

    デバイスの全ての操作が実装されているわけではありません。
    サポートされていない操作が必要な場合は、 `visa_write()` や `visa_query()` を用いて直接SCPIコマンドを送信してください。
    
    また、必要に応じて `pyvisa_inst` プロパティから直接 `pyvisa` のインスタンスにアクセスすることもできます。
    
    さらに必要であれば、
    :py:class:`VisaDevice <ebilab.visa.VisaDevice>` を継承して
    独自のデバイスクラスを作成できます。

*************************
独自デバイスの実装
*************************

サポートされていないデバイスを使用する場合は、 :py:class:`VisaDevice <ebilab.visa.VisaDevice>` を
継承して独自のクラスを実装できます。

.. code-block:: python

    from ebilab.visa import VisaDevice

    class MyDevice(VisaDevice):

        # IDN応答の検証パターン（部分一致）
        idn_pattern = r"MY_MANUFACTURER,MY_MODEL"
        
        def _initialize(self, **kwargs: Any) -> None:
            # SCPIコマンドを送信して初期設定
            self.visa_write("*RST;*CLS")
            self.visa_write("CONF:PARAM DEF")

        def measure_something(self):
            # SCPIコマンドを送信して結果を取得
            return float(self.visa_query("MEAS:SOMETHING?"))

        def set_parameter(self, value):
            # SCPIコマンドを送信
            self.visa_write(f"CONF:PARAM {value}")
