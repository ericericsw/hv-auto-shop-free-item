import os
import sys
import logging
import configparser
import time
from datetime import datetime, timezone
import inspect
from utils.utils import get_current_directory, check_folder_path_exists


class UtcIsoFormatter(logging.Formatter):
    """
    一個穩健的 Formatter，確保在任何平台上都能產生 UTC 時間的 ISO 8601 格式。
    例如: '2025-10-13T06:30:59.123Z'
    """
    # 將 Formatter 的預設時間轉換器設定為 time.gmtime，這會讓 %(asctime)s 使用 UTC
    converter = time.gmtime

    def formatTime(self, record, datefmt=None):
        """
        覆寫 formatTime 方法，使用 datetime.isoformat() 來產生時間字串。
        """
        # 從日誌紀錄中取得 UTC 時間的 datetime 物件
        dt_utc = datetime.fromtimestamp(record.created, tz=timezone.utc)

        # 使用 .isoformat() 產生標準字串，並將 '+00:00' 替換為 'Z'
        # timespec='milliseconds' 確保精確度到小數點後三位
        return dt_utc.isoformat(timespec='milliseconds')


def setup_logger(name: str = __name__, log_filename: str = None) -> logging.Logger:
    """
    設定並返回一個 Logger。

    Args:
        name (str, optional): Logger 的名稱. Defaults to __name__.
        log_filename (str, optional): 指定日誌檔案名稱。
                                      若為 None，則自動偵測呼叫此函式的檔名作為日誌檔名。
                                      Defaults to None.

    Returns:
        logging.Logger: 設定完成的 Logger 物件。
    """
    # 取得當前目錄（支援打包）
    current_directory = get_current_directory()

    if getattr(sys, 'frozen', False):
        log_dir = os.path.join(current_directory, 'log')
    else:
        log_dir = os.path.join(
            os.path.dirname(current_directory), 'log')

    check_folder_path_exists(log_dir)

    # 讀取 config.ini
    config = configparser.ConfigParser()
    config.read(os.path.join(current_directory, 'config',
                'config.ini'), encoding="utf-8")
    log_mode = config.get('Log', 'Log_Mode', fallback='INFO')

    # --- 3. 動態決定日誌檔名 ---
    if log_filename:
        # 如果使用者手動提供了檔名，就使用它
        base_filename = log_filename
    else:
        # 否則，自動偵測呼叫者的檔名
        try:
            # inspect.stack()[1] 是呼叫 setup_logger 的那一層
            caller_frame = inspect.stack()[1]
            # caller_frame.filename 是呼叫者的完整檔案路徑
            caller_filepath = caller_frame.filename
            # 從完整路徑中取出檔名，並去掉副檔名
            base_filename = os.path.splitext(
                os.path.basename(caller_filepath))[0] + '.log'
        except IndexError:
            # 如果在某些特殊環境（如互動式終端）下無法偵測，則使用預設名稱
            base_filename = 'default.log'

    log_file_path = os.path.join(log_dir, base_filename)

    # 日誌設定
    log_format = '%(asctime)s | %(filename)s | %(funcName)s | %(levelname)s:%(message)s'

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_mode.upper(), logging.INFO))

    # --- 2. 實例化並使用我們自訂的 UtcIsoFormatter ---
    #    注意：因為時間格式完全由 UtcIsoFormatter 控制，所以不需要 datefmt 參數
    formatter = UtcIsoFormatter(log_format)

    # 清除既有的 handlers，避免重複添加
    if logger.hasHandlers():
        logger.handlers.clear()

    # Handler & Formatter
    file_handler = logging.FileHandler(log_file_path, 'a', 'utf-8')
    stream_handler = logging.StreamHandler()

    for handler in [file_handler, stream_handler]:
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger
