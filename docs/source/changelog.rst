####################
更新履歴
####################

***********
v2.0.0a2
***********

BuG Fixes
===================

* 実験のファイル保存時のcsvのカラムが正常にならないバグを修正しました。


***********
v2.0.0a1
***********

Breaking Changes
===================

* フォルダ探索の際に、 :code:`ebilab.ini` ファイルを探索するように変更しました。
* :code:`ebilab.experiment.core` モジュールが廃止されました。互換性のためにしばらくは残されますが、

  .. code-block:: python

      from ebilab.experiment import Plotter, Experiment

  を使用してください。

Features
===================

* :code:`ebilab init` コマンドでプロジェクトテンプレートからのプロジェクト作成ができるようになりました。


***********
v2.0.0a0
***********

Breaking Changes
===================

* いくつかのデバイスの測定メソッドで、オプションをenumではなくstringで指定するようになりました。

Features
===================

* :py:func:`E4980.trigger() <ebilab.experiment.devices.E4980.trigger()>` メソッドで出力フォーマットを指定できるようになりました。


