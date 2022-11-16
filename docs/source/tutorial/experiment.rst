####################
実験の設計
####################

実験中には、測定値をグラフによって可視化したいことがあります。
これを実現するために、 :py:mod:`ebilab.experiment.core` モジュールを用いることができます。

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
    from ebilab.experiment.devices import K34411A

    fig, ax = plt.subplots(1, 1)
    plt.pause(0.01)

    multimeter = K34411A()
    data = []
    started_at = datetime.now()
    while True:
        R = multimeter.measure_resistance()
        t = (datetime.now() - started_at).total_seconds()
        print(v)

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

このコードにはいくつか問題があります。

* 実験のロジックを定義するコードと可視化のためのコードが混在している

  * 外れ値をフィルタリングしてプロットしたい場合など、どこまでが実験のロジックでどこからが可視化のためのロジックなのかが分かりづらくなる。

* matplotlibの描画によってデータの取得がブロッキングされ、データの取得速度に影響する。
* プログラムファイルへのデータ保存やグラフでの可視化のコードに関して、プログラムを作成する際に同じようなコードを何度も書く必要がある。

**********************************************************************************************************************************
:py:class:`Experiment <ebilab.experiment.core.Experiment>` ・ :py:class:`Plotter <ebilab.experiment.core.Plotter>` を利用した実装
**********************************************************************************************************************************

:py:mod:`ebilab.experiment.core` モジュール に含まれる
:py:class:`Experiment <ebilab.experiment.core.Experiment>` クラス、 :py:class:`Plotter <ebilab.experiment.core.Plotter>` クラスを用いることで、
これらの問題を解決することができます。

上記のコードは、以下のように書き変えることができます。


.. literalinclude:: ../../../sample/cont_r.py
   :language: python
   :linenos:

:py:class:`Experiment <ebilab.experiment.core.Experiment>` クラス、 :py:class:`Plotter <ebilab.experiment.core.Plotter>` クラスを継承し、
実験のロジックと可視化のロジックをそれぞれ定義することで、実験を設計することができます。
これにより、ロジックを適切に分割し、読みやすいコードを実現することができます。
また、クラス単位で定義することにより、同じ実験で可視化の方法だけを変更したり、別の実験でも同一の可視化方法を用いるなど、
それぞれのコンポーネントを再利用しやすくなります。

ファイルへの保存やプロット用プログラムへのデータの受け渡しに関して考慮する必要はありません。
また、matplotlibの描画中にもデータの取得を継続するため、マルチスレッド処理を行なっていますが、その制御に関しては考慮する必要はありません。

********************
実際の実装
********************

ユーザーは以下のクラスを実装する必要があります。

Experient クラス
====================

実験のロジックは、以下のように定義されます。


.. literalinclude:: ../../../sample/cont_r.py
   :language: python
   :lines: 8-16

* クラスの :code:`columns` プロパティを用いて、記録用のcsvファイルの列を指定します。
* steps関数に、実際の実験の処理を定義します。

    * 実験を途中で中断できるようにするため、 :code:`self.running` をチェックして :code:`False` だった場合はスクリプトを終了してください。
    * :code:`self.send_row()` メソッドを用いて、測定結果のデータを記録することができます。

      * メソッド実行1回あたり、csvファイル1行になります。省略された項目の列は空欄となります。
      * ファイルへの保存やタイムスタンプの挿入などは、自動で行なわれます。

* スクリプト実行時のカレントディレクトリ配下に :code:`data` ディレクトリが作成され、csvファイルが保存されます。
  クラスの :code:`filename` プロパティで指定した名前に、自動で日時が記録され、ファイル名となります。

Plotter クラス
====================

可視化のロジックは、以下のように定義されます。

.. note::

    リアルタイムプロットが必要ない場合は実装を省略することができます。
    その場合でも、ファイルへの自動保存などの恩恵を得ることができます。

.. literalinclude:: ../../../sample/cont_r.py
   :language: python
   :lines: 18-32

* prepareコマンドは初回のみ実行されます。
* updateコマンドは、定期的に実行されます。

実験の実行
====================

定義したクラスを用いて、以下のように実験を実行できます。


.. literalinclude:: ../../../sample/cont_r.py
   :language: python
   :lines: 34-

.. note::

    リアルタイムプロットが必要ない場合はplotterの指定は必要ありません。

