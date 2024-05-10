更新履歴
========

v2.5.0 (May 10, 2024)
---------------------

### Features

- `ebilab.experiment.devices` にて、いくつかのデバイスに関するメソッドを追加しました。
    - `A707` に、すべてのスイッチを開放する `open_all()` メソッドを実装しました。
    - `K34411A` に、4端子抵抗測定を行う `measure_resistance_4w()` メソッドを実装しました。

### Bug fixes

- `ebilab.experiment.devices` にて、いくつかのデバイスに関するメソッドを修正しました。
    - `A707` の `close_only()` に空の配列を渡すと無効なコマンドを送信するバグを修正しました。

v2.4.0 (Apr 11, 2024)
---------------------

### Features

-   experiment discovery 機能を追加しました。
    -   特定のフォルダを指定することで、そのフォルダに含まれる実験ファイルを自動で認識してウィンドウが起動します。
    -   `python -m ebilab experiment <directory>`
        にて実行が可能です。
-   `ebilab.experiment`
    で起動するウィンドウのレイアウトを変更しました。
    -   タブを活用することで、各種情報をより広いスペースで閲覧することができるようになりました。
-   `ExperimentProtocol` をまとめる
    `ExperimentGroup` を追加しました。
-   `ExperimentProtocol` の `register_plotter`
    にて、 `plotter_classes` を登録できるようにしました。
-   `ebilab.experiment`
    で起動するウィンドウにアイコンを追加しました。

### Bug fixes

-   gitがインストールされていない環境で、gitを利用しないにも関わらずエラーとなるバグを修正しました。

v2.3.0 (Apr 20, 2023)
---------------------

### Features

-   ebilab.experimentのOptionFieldにおいて、 `IntField` と
    `StrField` を追加しました。
    ([\#7](https://github.com/ebiyuu1121/ebilab/pull/7/))

### Contributors

-   [\@halphy](https://github.com/halphy)
    が最初のコントリビューションを行いました。ありがとうございます！

v2.2.1 (Jan 30, 2023)
---------------------

### Changes (unstable)

-   ebilab.analysisにおいて、生成されるプロジェクトのgitignoreファイルを変更しました。

v2.2.0 (Jan 30, 2023)
---------------------

### Features

-   ebilab.experimentにおいて、実験スクリプトからログ出力をするメソッド
    `ctx.log(msg)` を追加しました。

v2.1.1 (dec 14, 2022)
---------------------

### Features (unstable)

-   ebilab.analysisのpreprocessにおいて、ファイル先頭のコメント行を読み飛ばすようになりました。

v2.1.0 (dec 8, 2022)
--------------------

### Features

-   E4930 クラスに、校正機能を呼び出すメソッドを追加しました。

### Bug Fixes

-   A707クラスにおいて、初期化処理がうまくいかないことがあるバグを修正しました。

v2.0.0 (Dec 7, 2022)
--------------------

v2.0.0の正式版をリリースしました。 v1からの差分は以下の通りです。

```{note}
プレリリース版を含む詳細なリリースノートは、
{doc}`changelog-v2.0.0-pre` を参照してください。
```

### Breaking Changes

-   いくつかのデバイスの測定メソッドで、オプションをenumではなくstringで指定するようになりました。

-   フォルダ探索の際に、 `ebilab.ini`
    ファイルを探索するように変更しました。
-   `Experiment`, `Plotter` クラスを廃止しました。 `ExperimentProtocol`,
    `ExperimentPlotter`
    を利用した新しいインタフェースを利用してください。
    -   これらは v1.2.0 にて利用可能です。必要であればこちらを利用してください。
-   CSVファイルの先頭に実験条件などの3行分のコメントが挿入されるようになりました。

-   CSVファイルの保存先が日付ごとのフォルダになりました。

### Features

-   tkinterによるGUIサポートを追加しました。
-   `ExperimentProtocol`, `ExperimentPlotter`
    を利用した新しい実験定義のインタフェースを実装しました。
-   実験時にUIからファイル名を設定できるようにしました。
-   `ebilab.ini`
    ファイルがある場合にはoriginalフォルダにCSVファイルの保存先を設定するようになりました。
-   `ebilab init`
    コマンドでプロジェクトテンプレートからのプロジェクト作成ができるようになりました。
-   `E4980.trigger()`
    メソッドで出力フォーマットを指定できるようになりました。

### Bug Fixes

-   実験のファイル保存時のcsvのカラムが正常にならないバグを修正しました。
-   pyvisa\_device
    のデストラクタにおいて、接続を切断してしまうバグを修正しました。

### Experimental

-   デバイスの動作をモックして動作させることができるようになりました。
    環境変数 `EBILAB_MOCK`
    を1に設定することでモックが有効になり、デバイスはテストデータを返すようになります。
