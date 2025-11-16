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
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
