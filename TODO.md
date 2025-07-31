# TODO.md

- [x] `samples` を新APIへ更新する
- [x] 実験が終了しても実験ごとのログファイルが閉じられない問題を修正
- [x] ログビューに `logger.exception` 時の例外の内容が表示されないバグを修正
  **実装方針**: 元のTkinterLogHandlerベースで例外情報を含めるように修正した。TkinterLogHandler.emit()メソッドでrecord.exc_infoをチェックし、traceback.format_exception()を使ってスタックトレースを含む完全な例外情報を表示するようにした。view.pyの重複クラスも削除済み。
- [x] 実験がエラー終了したらエラーダイアログで通知するようにする。
  **実装方針**: View クラスに show_error_dialog() メソッドを追加（tkinter.messagebox使用）し、View.update_experiment_state() に "error" 状態の処理を追加。ExperimentService の _run_lifecycle() メソッドでエラー時に適切なエラー情報を記録・伝達し、コントローラー経由でエラー発生時にダイアログを表示する。
- [x] ログビューの改善。
    - TreeViewにして見やすく。
    - ログレベルでフィルタできるようにする。default: INFO
    - exp.logger からのログだけを表示するようにもできるようにする。default: on
  **実装方針**: 
    1. view.pyのログタブ（221-229行目）を tk.Text から ttk.Treeview に変更。列: タイムスタンプ、レベル、ロガー名、メッセージ
    2. ログレベルフィルタ用の ttk.Combobox を追加（DEBUG,INFO,WARNING,ERROR,CRITICAL）、デフォルト: INFO
    3. 実験ログのみ表示する ttk.Checkbutton を追加、デフォルト: ON
    4. TkinterLogHandler を修正して構造化されたログレコード情報をキューに送信
    5. コントローラーのログ更新処理（_on_timer_update_log）をTreeView用に修正
    6. ログエントリを保存して、フィルタ設定変更時に既存ログも再フィルタリング可能にした
- [ ] Plotterから `Experiment` クラスにアクセスできるように。
- [ ] 実験スレッドが `await` 中でも中止できるように。
- [ ] 長時間実験するとPlotterが重くなる問題をなんとかする。
    - 適宜な待機時間を設けるなど？
    - 直近のデータしかPlotterに渡さないなど。
- [ ] 監視モード実装
