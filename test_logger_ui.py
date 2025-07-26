#!/usr/bin/env python3
"""
loggerがUIに出力されるかテストするスクリプト
スレッドセーフなログ機能をテスト
"""

import logging
import time
import threading
from ebilab.gui.view import View

# ログレベルを設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_logger_ui():
    """UIでloggerの出力をテスト"""
    
    # UIを作成
    app = View()
    
    def send_background_logs():
        """バックグラウンドスレッドからログを送信"""
        logger.info("バックグラウンドスレッド開始")
        for i in range(20):
            logger.info(f"バックグラウンドログ {i+1}")
            logger.debug(f"デバッグメッセージ {i+1}")
            if i % 5 == 0:
                logger.warning(f"警告メッセージ {i+1}")
            if i % 10 == 0:
                logger.error(f"エラーメッセージ {i+1}")
            time.sleep(0.2)
        logger.info("バックグラウンドスレッド完了")
    
    def send_test_logs():
        logger.info("=== ログテスト開始 ===")
        logger.debug("デバッグ情報")
        logger.warning("警告メッセージ")
        logger.error("エラーメッセージ")
        
        # バックグラウンドスレッドを開始
        thread = threading.Thread(target=send_background_logs, daemon=True)
        thread.start()
        
        # 定期的なログテスト
        app.after(8000, lambda: logger.info("8秒後のメッセージ"))
        app.after(12000, lambda: logger.warning("12秒後の警告"))
    
    # 初期化完了後にテストログを送信
    app.after(500, send_test_logs)
    
    # アプリケーション実行
    app.mainloop()

if __name__ == "__main__":
    test_logger_ui()
