# import libary
import logging
import os
import configparser
import sys
# endregion

"""
資料夾初始化
"""

# 取得當前目錄
if getattr(sys, 'frozen', False):
    # 如果是打包後的可執行文件
    current_directory = os.path.dirname(sys.executable)
else:
    # 如果是未打包的原始腳本
    current_directory = os.path.dirname(os.path.abspath(__file__))
csv_directory = os.path.join(current_directory, 'csv')


def check_folder_path_exists(folder_Path: os.path):
    if not os.path.exists(folder_Path):
        os.makedirs(folder_Path)
        logging.warning(f"資料夾 '{folder_Path}' 已建立。")


csv_dir = os.path.join(current_directory, 'csv')
log_dir = os.path.join(current_directory, 'log')
json_dir = os.path.join(current_directory, 'json')
post_draft_dir = os.path.join(current_directory, 'post_draft')
# 檢查工作目錄是否有資料夾
check_folder_path_exists(csv_dir)
check_folder_path_exists(log_dir)
check_folder_path_exists(json_dir)
check_folder_path_exists(post_draft_dir)


# 如果 config.ini 不存在則將 sample 改名拿來用
if not os.path.exists(os.path.join(current_directory, 'config.ini')):
    os.rename(os.path.join(current_directory, 'config_sample.ini'),
              os.path.join(current_directory, 'config.ini'))

# 如果 free_shop_last_post_sample.csv 不存在則將 free_shop_last_post_sample.csv 改名拿來用
if not os.path.exists(os.path.join(csv_directory, 'free_shop_last_post.csv')):
    os.rename(os.path.join(csv_directory, 'free_shop_last_post_sample.csv'),
              os.path.join(csv_directory, 'free_shop_last_post.csv'))

# Load configparser
config = configparser.ConfigParser()
config_path = os.path.join(current_directory, 'config.ini')
config.read(config_path, encoding="utf-8")

# 設置日誌
Log_Mode = config.get('Log', 'Log_Mode')
# 日誌格式
Log_Format = '%(asctime)s | %(filename)s | %(funcName)s | %(levelname)s:%(message)s'
log_file_path = os.path.join(
    current_directory, 'log', 'env_initialization.log')
logging.basicConfig(level=getattr(logging, Log_Mode.upper()),
                    format=Log_Format,
                    handlers=[logging.FileHandler(log_file_path, 'a', 'utf-8'),
                              logging.StreamHandler()])
