更新履歴
========

v3.0.0 (Not released)
---------------------

v3.0.0をリリースしました。

```{note}
v2からの移行方法については {doc}`migration-v2-to-v3` を参照してください。

プレリリース版を含む詳細なリリースノートは {doc}`changelog-v3.0.0-pre` を参照してください。
```

### Breaking Changes

APIが大幅に刷新されました。

- `ExperimentProtocol` → `BaseExperiment`、`ExperimentPlotter` → `BasePlotter` にクラス名が変更されました。
- `ebilab.experiment` パッケージは削除され、`ebilab.api` と `ebilab.gui` に分割されました。
- `ebilab.experiment.devices` は `ebilab.visa` に移動しました。
- `ebilab.experiment.options` は `ebilab.api` に統合されました。
- `ebilab.analysis` / `ebilab.analysis2` パッケージは削除されました。
- オプション定義が辞書形式からクラス属性形式に変更されました。
- ライフサイクルメソッドが `steps(ctx)` から `setup()`, `steps()`, `cleanup()` の3メソッドに分割されました。
- すべてのライフサイクルメソッドが `async def` になりました。
- データ送信が `ctx.send_row()` から `yield` に変更されました。
- ログ出力が `ctx.log()` から `self.logger` (Python標準logger) に変更されました。
- Plotterの初期化メソッドが `prepare(ctx)` から `setup()` に変更されました。
- Plotterの更新メソッドが `update(df, ctx)` から `update(df)` に変更されました。
- 起動関数が `launch_experiment()` から `launch_gui()` に変更されました。
- `ExperimentProtocolGroup` によるグルーピング機能は削除されました。
- `python -m ebilab experiment` コマンドによるスクリプトの自動discover機能は削除されました。

### Features

- **新しいUI**: モダンなGUIを実装しました。
- **デバッグモード**: データを保存せずに実験を実行できるようになりました。
- **sync機能**: 実験中にボタンを押したタイムスタンプを記録できるようになりました。
- **実験履歴**: GUIから過去の実験データを閲覧できるようになりました。
- **メタデータ保存**: 実験の設定がJSONファイルにメタデータとして保存されるようになりました。
- **Plotterから実験インスタンスへのアクセス**: `self.experiment` で実験パラメータにアクセスできるようになりました。
- **is_running フラグ**: `self.experiment.is_running` で実験中かどうかを判定できるようになりました。
- **ナビゲーションツールバー**: プロット表示にmatplotlibのナビゲーションツールバーを追加しました。
- **VISAデバイスのアドレス指定**: `K34411A(addr="GPIB0::22::INSTR")` のようにアドレスを指定して接続できるようになりました。
- **新しいデバイス**: K34465A (Keysight 34465A) を追加しました。
- **ショートカットキー**: F5(実験開始)、F6(デバッグ実行)、F9(実験終了)、F12(sync)を追加しました。

### 自動追加される列

データには以下の列が自動で追加されます:

- `t`: 実験開始からの経過時間（秒）
- `time`: ISO形式のタイムスタンプ
- `sync_t`: 最後のsyncボタン押下からの経過時間

v2.9.0 (Jul 17, 2025)
---------------------

### Deprecations

- `ebilab.analysis` / `ebilab.analysis2` パッケージを非推奨化しました。
    - これらのパッケージは非推奨化され、今後のメンテナンスは行われません。また、今後のバージョンでは削除される予定です。

### Features

- `ebilab.experiment` で実験UIに t(経過時間)/time(絶対時刻) を表示するようにしました。
- `ebilab.experiment` でレシピのサブディレクトリ対応を追加しました。
- `ebilab.experiment` でソースコードのリロード機能、ソースコードを開く機能を追加しました。
- `ebilab.experiment` でdocstringからsummary/descriptionを取得・表示するようにしました。
- `device.E4980` で電圧/電流指定を追加し、amplを非推奨にしました。
    - Old: `E4980.trigger(ampl=0.1)`
    - New: `E4980.trigger(voltage=0.1)` or `E4980.trigger(current=0.001)`

### Bug Fixes

- `ebilab.experiment` でWindowを閉じた場合にエラーが発生する問題を修正しました。
- `ebilab.experiment` でPlotterが無い場合のエラーを防止しました。
- 出力名が空白のみの場合にエラーとするようバリデーションを追加しました。

### Changes

- `device.E4980` でamplと電圧/電流指定が同時に指定された場合に `ValueError` を発生させるよう変更しました。

v2.8.0 (July 5, 2024)
---------------------

### Features

- `ebilab.experiment` に `options.BoolField` を追加しました。

### Features (unstable)

- `ebilab.analysis` において、 `ebilab watch` コマンドに `--watch-project` オプションを追加しました。
    - ファイル単体ではなく、プロジェクト全体を監視して実行することができます。

v2.7.0 (May 16, 2024)
---------------------

### Features

- `ebilab.experiment` にて、 `ctx.sleep` 関数を追加しました。
    - 実験定義の中で `time.sleep` 関数を用いると、STOPボタンを押してもsleep中は実験が停止できません。そこで、代わりに `ctx.sleep` 関数を用いると、sleep中にSTOPボタンを押しても停止することができます。

### Policy Update

- バージョン更新ポリシーを変更し、semantic versioningにより準拠するようになりました。
    - 今後、より後方互換性を重視するようになります。
    - 新しいポリシーは以下の通りです。
        - a (Major version): 重要で破壊的な変更があった場合に更新されます。
        - b (Minor version): 新機能の追加や一部機能の仕様な変更など、軽微な変更があった場合に更新されます。
        - c (Patch version): 新メソッドの追加などの軽微な機能や、バグ修正など機能に変更がない場合に更新されます。ドキュメントに未完成(unstable)と明記されている機能に関しては、パッチバージョンで更新が行なわれることがあります。
    - minor versionやpatch versionに関しては後方互換性がありますが、バグに依存していた場合や内部機能をハックしていた場合にはその限りではありません。厳密な再現性のためにはバージョンの固定を行ってください。

v2.6.0 (May 14, 2024)
---------------------

### Features

- `ebilab.experiment` にて、実験時にPython例外が発生しても適切に処理するようにしました。

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
