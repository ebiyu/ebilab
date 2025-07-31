# TODO.md

- [x] `samples` を新APIへ更新する
- [x] 実験が終了しても実験ごとのログファイルが閉じられない問題を修正
- [x] ログビューに `logger.exception` 時の例外の内容が表示されないバグを修正
  **実装方針**: 元のTkinterLogHandlerベースで例外情報を含めるように修正した。TkinterLogHandler.emit()メソッドでrecord.exc_infoをチェックし、traceback.format_exception()を使ってスタックトレースを含む完全な例外情報を表示するようにした。view.pyの重複クラスも削除済み。
- [ ] 実験がエラー終了したらエラーダイアログで通知するようにする。
- [ ] ログビューの改善。
    - TreeViewにして見やすく。
    - ログレベルでフィルタできるようにする。default: INFO
    - exp.logger からのログだけを表示するようにもできるようにする。default: on
- [ ] Plotterから `Experiment` クラスにアクセスできるように。
- [ ] 実験スレッドが `await` 中でも中止できるように。
- [ ] 長時間実験するとPlotterが重くなる問題をなんとかする。
    - 適宜な待機時間を設けるなど？
    - 直近のデータしかPlotterに渡さないなど。
- [ ] 監視モード実装
