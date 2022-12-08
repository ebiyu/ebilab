###########################
v2.0.0 pre リリースノート
###########################

.. warning::

    正式リリース版のリリースノートに関しては、 :doc:`changelog` を参照してください。

**************************
v2.0.0 (Dec 8, 2022)
**************************

v2.0.0の正式版をリリースしました。

Breaking Changes
===================

* IExperimentProtocol, IExpriemntPlotter クラスの名称を ExperimentProtocol, ExperimentPlotter へ変更しました。

Features
===================

* plotter_options

**************************
v2.0.0b1 (Dec 6, 2022)
**************************

Breaking Changes
===================

* IExpriemntPlotter クラスの :py:func:`prepare() <ebilab.experiment.ExperimentPlotter.prepare()>`,
  :py:func:`update() <ebilab.experiment.ExperimentPlotter.update()>` メソッドの引数に
  :py:class:`PlotterContext <ebilab.experiment.PlotterContext>` が渡されるようになりました。

Experimental
===================

* デバイスの動作をモックして動作させることができるようになりました。
  環境変数 :code:`EBILAB_MOCK` を1に設定することでモックが有効になり、デバイスはテストデータを返すようになります。

**************************
v2.0.0b0 (Dec 1, 2022)
**************************

Breaking Changes
===================


* IExpriemntProtocol クラスの :py:func:`steps() <ebilab.experiment.ExperimentProtocol.steps()>` メソッドの引数に渡されていた
  optionは、:py:class:`ProtocolContext <ebilab.experiment.ProtocolContext>` に含めて渡されるようになりました。
* CSVファイルの先頭に実験条件などの3行分のコメントが挿入されるようになりました。
* CSVファイルの保存先が日付ごとのフォルダになりました。

Features
===================

* 実験時にUIからファイル名を設定できるようにしました。
* 実験選択時に、自動的に最初のPlotterが選択されるようにしました。
* :py:class:`SelectField <ebilab.experiment.options.SelectField>` を実装しました。
* :code:`ebilab.ini` ファイルがある場合にはoriginalフォルダにCSVファイルの保存先を設定するようになりました。

Bug Fixes
====================

* 実験再開時にデータが残ることがあるバグを修正しました。

**************************
v2.0.0a3 (Nov 29, 2022)
**************************

Breaking Changes
===================

* :code:`Experiment`, :code:`Plotter` クラスを廃止しました。

    * これらが利用可能なバージョンを v1.2.0 としてリリースしました。必要であればこちらを利用してください。

Features
===================

* 新しい実験定義のインタフェースを実装しました。
* tkinterによるGUIサポートを追加しました。

Bug Fixes
===================

* pyvisa_device のデストラクタにおいて、接続を切断してしまうバグを修正しました。


**************************
v2.0.0a2 (Nov 25, 2022)
**************************

Bug Fixes
===================

* 実験のファイル保存時のcsvのカラムが正常にならないバグを修正しました。


**************************
v2.0.0a1 (Nov 17, 2022)
**************************

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


**************************
v2.0.0a0 (Nov 17, 2022)
**************************

Breaking Changes
===================

* いくつかのデバイスの測定メソッドで、オプションをenumではなくstringで指定するようになりました。

Features
===================

* :py:func:`E4980.trigger() <ebilab.experiment.devices.E4980.trigger()>` メソッドで出力フォーマットを指定できるようになりました。


