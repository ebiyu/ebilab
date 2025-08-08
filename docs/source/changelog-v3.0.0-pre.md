Hう# v3.0.0 pre リリースノート

## v3.0.0a2 (Aug 06, 2025)

### Feat

* 実験の設定などが、メタデータとしてCSVファイルで保存されるようになりました。
* GUIから過去の実験データが見れるようになりました。
* `await` 中でも実験を中断できるようになりました。
* Plotter から Experiment インスタンスにアクセスできるようになりました。
    * これで実験パラメータやインスタンスプロパティに応じてプロットを変更できるようになります。
    * `self.experiment` でインスタンスにアクセスできます。
* GUI上でのログ表示機能を改善しました。
    * ログレベルによるフィルタリングを実装しました。既定のログレベルはINFOになります。
    * `ebilab` ライブラリ自体のログは既定で表示しないようにしました。
* エラーで実験が終了した際にダイアログで通知するようにしました。

### Bug fixes

* サンプルスクリプトを新APIに準拠したものに更新しました。
* 実験終了時にログファイルが正常にCloseされないバグを修正しました。
* GUIのログ画面に、 `logger.exception` で出力されたtracebackが表示されないバグを修正しました。

## v3.0.0a1 (Jul 31, 2025)

### Breaking Changes

**API changed drastically!!!!!**

* `ebilab.experiment.devices` 以下のVISAデバイスドライバは `ebilab.visa` へ移動しました。
* `ebilab.analysis` `ebilab.analysis2` `ebilab.experiment` は削除されました。
* v3 UIを実装しました。
    * オプションの指定が、 `options` 辞書への登録からモデルフィールドを用いた定義となりました。
    * データを記録しないデバッグ実行機能が追加されました。
    * `steps()` は `setup()` `steps()` `claenup()` へ分割されました。
    * `setup()` `steps()` `claenup()` 関数は `async` 関数になりました。
    * 実験データは `ctx.send_row` ではなく `yield` で記録するようになります。
    * 実験ログがPython標準の `logger` へ統合されました。

### New Feature

* 実験中にボタンを押したタイムスタンプを記録できる `sync` 機能を実装しました。
* ショートカットキーを追加しました。
    * F5→実験開始、F6→デバッグ実行、F9→実験終了、F12→sync

### Fix

* Keysight IO Librariesは存在する場合のみ読み込むようにしました(必須ではなくなります)。

## v3.0.0a0 (Jul 25, 2025)

### Refactor

* `setup.py` から `pyproject.toml` による管理へ移行しました。
* これに伴い、ビルドに `uv` を用いるようにしました。

