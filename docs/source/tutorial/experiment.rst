####################
実験の制御と可視化
####################

実験中には、測定値をグラフによって可視化したいことがあります。
これを実現するために、ebilabを用いることができます。

***************
簡易的な実装
***************

簡易的には、 :code:`matplotlib` を用いて、以下のようなコードで実現することができます。
これは、マルチメーターを用いて抵抗を測定してプロットするプログラムです。

.. code-block:: python
    :linenos:

    from datetime import datetime
    import pandas as pd
    import matplotlib.pyplot as plt
    from ebilab.visa import K34411A

    fig, ax = plt.subplots(1, 1)
    plt.pause(0.01)

    multimeter = K34411A()
    data = []
    started_at = datetime.now()
    while True:
        R = multimeter.measure_resistance()
        t = (datetime.now() - started_at).total_seconds()
        print(R)

        # update plot
        data.append({"t": t, "R": R})
        df = pd.DataFrame(data)
        ax.cla()
        ax.plot(df["t"], df["R"])
        ax.set_xlabel("Time")
        ax.set_ylabel("Resistance")
        ax.grid()
        plt.pause(0.1)


実際にこのようなコードで運用するには、いくつか問題があります。

* 実験のロジックを定義するコードと可視化のためのコードが混在している

  * 外れ値をフィルタリングしてプロットしたい場合など、どこまでが実験のロジックでどこからが可視化のためのロジックなのかが分かりづらくなる。

* matplotlibの描画によってデータの取得がブロッキングされ、データの取得速度に影響する。
* プログラムファイルへのデータ保存やグラフでの可視化のコードに関して、プログラムを作成する際に同じようなコードを何度も書く必要がある。

**********************************************************************************************************************************
ebilabを利用した実装
**********************************************************************************************************************************

ebilabを用いることで、
これらの問題を解決することができます。

上記のコードは、以下のように書き変えることができます。


.. literalinclude:: ../../../sample/random_walk.py
   :language: python
   :linenos:

:py:class:`BaseExperiment <ebilab.api.BaseExperiment>` クラス、 :py:class:`BasePlotter <ebilab.api.BasePlotter>` クラスを継承し、
実験のロジックと可視化のロジックをそれぞれ実装することで、実験を設計することができます。
これにより、ロジックを適切に分割し、読みやすいコードを実現することができます。
また、クラス単位で定義することにより、同じ実験で可視化の方法だけを変更したり、別の実験でも同一の可視化方法を用いるなど、
それぞれのコンポーネントを再利用しやすくなります。

ファイルへの保存やプロット用プログラムへのデータの受け渡しに関して考慮する必要はありません。
また、matplotlibの描画中にもデータの取得を継続するため、マルチスレッド処理を行なっていますが、その制御に関しては考慮する必要はありません。

********************
実際の実装
********************

ユーザーは以下のクラスを実装する必要があります。

Experiment クラス
================================

実験のロジックは、:py:class:`BaseExperiment <ebilab.api.BaseExperiment>` を継承して定義します。

.. literalinclude:: ../../../sample/random_walk.py
   :language: python
   :lines: 10-45

基本的な構造
--------------------

* :code:`name` : 実験の名前。csvファイル名のベースになります。
* :code:`columns` : 記録用のcsvファイルの列名を指定します。
* **パラメータ定義**: :code:`FloatField`, :code:`SelectField`, :code:`IntField`, :code:`StrField`, :code:`BoolField` などのフィールドクラスを用いて、GUIから設定できるパラメータを定義します。

ライフサイクルメソッド
--------------------

実験は以下の3つの :code:`async` メソッドで構成されます。

* :code:`async def setup()` : 実験の準備。デバイスへの接続などを行います。
* :code:`async def steps()` : データを :code:`yield` するメインループ。
* :code:`async def cleanup()` : 正常終了・中断・エラー時に必ず呼ばれる後処理。

:code:`steps()` メソッドでは、 :code:`yield` を使用して測定データを記録します。
:code:`yield` で返された辞書は、CSVファイルに保存され、GUIで可視化されます。

.. note::

    :code:`time.sleep()` の代わりに :code:`await asyncio.sleep()` を使用してください。
    これにより、スリープ中でも実験を中断できます。

ロギング
--------------------

実験中のログは :code:`self.logger` を通じて出力できます。
出力したログは、GUIのログビューアに表示される他、ログファイルにも保存されます（デバッグモードでは保存されない）。

.. code-block:: python

    self.logger.info("情報メッセージ")
    self.logger.debug("デバッグメッセージ")
    self.logger.warning("警告メッセージ")
    self.logger.error("エラーメッセージ")

Plotter クラス
================================

可視化のロジックは、:py:class:`BasePlotter <ebilab.api.BasePlotter>` を継承して定義します。
:code:`@Experiment.register_plotter` デコレータで実験クラスに関連付けます。

.. literalinclude:: ../../../sample/random_walk.py
   :language: python
   :lines: 48-70

* :code:`name` : プロッターの識別名。GUIのドロップダウンに表示されます。
* :code:`setup()` : プロットの初期設定。プロッターがアクティブになった際に一度だけ呼ばれます。
* :code:`update(df)` : データが更新されるたびに呼ばれます。 :code:`df` は :code:`pandas.DataFrame` で、全ての実験データが含まれます。

Plotterのパラメータ
--------------------

:code:`Plotter` にもフィールドを定義できます。これらはGUIから実験中でも変更できます。

.. code-block:: python

    @RandomWalkExperiment.register_plotter
    class HistgramPlotter(BasePlotter):
        name = "histgram"
        bins = FloatField(default=10.0)  # GUIから変更可能なパラメータ

        def update(self, df):
            self._ax.hist(df["v"], bins=int(self.bins))

Experimentへのアクセス
--------------------

:code:`self.experiment` を通じて、実験インスタンスのパラメータにアクセスできます。

.. code-block:: python

    def update(self, df):
        # 実験パラメータを参照
        title = f"step={self.experiment.step}"
        self._ax.set_title(title)

また、 :code:`self.experiment.is_running` で実験が実行中かどうかを確認できます。
これを使って、実行中と履歴表示でプロットの挙動を変えることができます。

実験の実行
====================

定義したクラスを用いて、以下のように実験を実行できます。

.. literalinclude:: ../../../sample/random_walk.py
   :language: python
   :lines: 106-

.. note::

    複数の実験クラスを指定することができます。GUIのドロップダウンから選択できます。

********************
フィールドの種類
********************

パラメータ定義に使用できるフィールドクラスは以下の通りです。

.. list-table::
   :widths: 20 30 50
   :header-rows: 1

   * - フィールド
     - 用途
     - パラメータ
   * - :code:`FloatField`
     - 浮動小数点数
     - :code:`default`, :code:`min`, :code:`max`
   * - :code:`IntField`
     - 整数
     - :code:`default`, :code:`min`, :code:`max`
   * - :code:`StrField`
     - 文字列
     - :code:`default`, :code:`allow_blank`
   * - :code:`BoolField`
     - 真偽値
     - :code:`default`
   * - :code:`SelectField`
     - 選択肢
     - :code:`choices`, :code:`default_index`

使用例:

.. code-block:: python

    class MyExperiment(BaseExperiment):
        # 浮動小数点数パラメータ（範囲指定あり）
        voltage = FloatField(default=1.0, min=0.0, max=10.0)

        # 整数パラメータ
        count = IntField(default=100, min=1)

        # 文字列パラメータ
        sample_name = StrField(default="sample1")

        # 真偽値パラメータ
        auto_save = BoolField(default=True)

        # 選択肢パラメータ
        mode = SelectField(choices=["fast", "normal", "slow"], default_index=1)

********************
データの保存
********************

* スクリプト実行時のカレントディレクトリ配下に :code:`data` ディレクトリが作成され、csvファイルが保存されます。
* ファイル名は :code:`name` プロパティで指定した名前に日時が付加されます。
* 自動的に :code:`t` 列（実験開始からの経過秒数）と :code:`sync_t` 列（syncボタンからの経過秒数）が追加されます。

********************
ショートカットキー
********************

GUIでは以下のショートカットキーが使用できます。

* :code:`F5` : 実験開始
* :code:`F6` : デバッグ実行（データを保存しない）
* :code:`F9` : 実験終了
* :code:`F12` : sync（タイムスタンプを記録）
