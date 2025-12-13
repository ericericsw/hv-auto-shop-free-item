import os
import sys
import time
import datetime


def check_folder_path_exists(folder_Path: os.path):
    if not os.path.exists(folder_Path):
        os.makedirs(folder_Path)
        from utils.logger import setup_logger
        # 讀取 logger
        logger = setup_logger(__name__)
        logger.warning(f"資料夾 '{folder_Path}' 已建立。")


def get_current_directory():
    # 取得當前目錄
    if getattr(sys, 'frozen', False):
        # 如果是打包後的可執行文件
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 如果是未打包的原始腳本
        return os.path.dirname(os.path.abspath(__file__))


def get_now_time():
    """
    產生ISO格式時間，如：2025-12-13T14:31:04+00:00
    """

    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def convert_to_iso(date_str):
    """
    將 'YYYY-MM-DD HH:MM' 格式轉換為 ISO 8601 'YYYY-MM-DDTHH:MM:SS+00:00'
    如果轉換失敗，則回傳原始字串
    """
    try:
        # 1. 解析原始字串 (假設原始格式固定為 年-月-日 時:分)
        dt_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")

        # 2. 設定時區 (假設原始時間就是 UTC，若不是 UTC 需另外調整)
        # 使用 replace 強制加上 UTC 時區資訊 (+00:00)
        dt_obj = dt_obj.replace(tzinfo=datetime.timezone.utc)

        # 3. 轉出 ISO 格式字串
        return dt_obj.isoformat()
    except ValueError:
        # 如果格式不對 (例如空字串)，就回傳原本內容以免程式崩潰
        return date_str
