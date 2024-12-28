# import libary
import requests
import json
import time
import datetime
import re
import logging
import os
import configparser
import pytz
import csv
import sys
from collections import defaultdict
import forums_crawler
# endregion

# 指定時區
timezone = pytz.timezone('Asia/Taipei')

# 取得當前目錄
current_Directory = os.path.dirname(os.path.abspath(__file__))
csv_directory = os.path.join(current_Directory, 'csv')

# 檢查工作目錄是否有資料夾，沒有的話建立 log 資料夾
log_dir = os.path.join(current_Directory, 'log')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    print('created {} folder'.format(log_dir))

if not os.path.exists(os.path.join(current_Directory, 'config.ini')):
    os.rename(os.path.join(current_Directory, 'config_sample.ini'),
              os.path.join(current_Directory, 'config.ini'))

# Load configparser
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'config.ini')
config.read(config_path, encoding="utf-8")

# 設置日誌
Log_Mode = config.get('Log', 'Log_Mode')
Log_Format = '%(asctime)s %(filename)s %(levelname)s:%(message)s'
log_file_path = os.path.join(
    current_Directory, 'log', 'sample.log')
logging.basicConfig(level=getattr(logging, Log_Mode.upper()),
                    format=Log_Format,
                    handlers=[logging.FileHandler(log_file_path, 'a', 'utf-8'),
                              logging.StreamHandler()])


def check_folder_path_exists(folder_Path: os.path):
    if not os.path.exists(folder_Path):
        os.makedirs(folder_Path)
        logging.warning('created {} folder'.format(folder_Path))


def get_item_list():
    item_list = []
    item_list_csv_path = os.path.join(csv_directory, 'item_list.csv')
    with open(item_list_csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            item_list.append(row['item_name'])
    return item_list


def get_free_shop_order_setting(file_path: os.path):
    """
    讀取店家設定

    """

    # 初始化一個字典來存儲分組資料
    temp_data = defaultdict(lambda: {
        'item_info': [],
        'item_suit_cool_time_day': [],
        'item_suit_order_limit': [],
        'item_suit_level_limit_min': [],
        'item_suit_level_limit_max': []
    })

    order_setting = defaultdict(lambda: {
        'item_info': [],
        'item_suit_cool_time_day': int,
        'item_suit_order_limit': int,
        'item_suit_level_limit_min': int,
        'item_suit_level_limit_max': int
    })

    # 讀取 CSV 檔案
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:

            try:
                # 檢查 item_suit_id 是否在 item_list.csv 中匹配到（不分大小寫）
                if not any(item.lower() == row['item_name'].lower() for item in get_item_list()):
                    logging.critical(
                        '{} not in item list'.format(row['item_name']))
                    sys.exit()
                item_number = int(row['item_number'])
                item_suit_cool_time_day = int(row['item_suit_cool_time_day'])
                item_suit_order_limit = int(row['item_suit_order_limit'])
                item_suit_level_limit_min = int(
                    row['item_suit_level_limit_min'])
                item_suit_level_limit_max = int(
                    row['item_suit_level_limit_max'])
            except ValueError as e:
                logging.critical('setting value issye')
                logging.critical(e)
                sys.exit()

            item_suit_id = row['item_suit_id']
            temp_data[item_suit_id]['item_info'].append(
                {'item_name': row['item_name'], 'item_number': item_number})
            temp_data[item_suit_id]['item_suit_cool_time_day'].append(
                item_suit_cool_time_day)
            temp_data[item_suit_id]['item_suit_order_limit'].append(
                item_suit_order_limit)
            temp_data[item_suit_id]['item_suit_level_limit_min'].append(
                item_suit_level_limit_min)
            temp_data[item_suit_id]['item_suit_level_limit_max'].append(
                item_suit_level_limit_max)

    for item_id, item_data in temp_data.items():
        order_setting[item_id]['item_info'] = item_data['item_info']

        if item_data['item_suit_cool_time_day']:
            order_setting[item_id]['item_suit_cool_time_day'] = max(
                item_data['item_suit_cool_time_day'])
        else:
            order_setting[item_id]['item_suit_cool_time_day'] = 7
            logging.warning(
                'lost setting:item_suit_cool_time_day in item_id:{},now item_suit_cool_time_day is 7'.format(item_id))
            sys.exit()

        if item_data['item_suit_order_limit']:
            order_setting[item_id]['item_suit_order_limit'] = min(
                item_data['item_suit_order_limit'])
        else:
            order_setting[item_id]['item_suit_order_limit'] = 1
            logging.warning(
                'lost setting:item_suit_order_limit in item_id:{},now item_suit_order_limit is 1'.format(item_id))
            sys.exit()

        if item_data['item_suit_level_limit_min']:
            order_setting[item_id]['item_suit_level_limit_min'] = max(
                item_data['item_suit_level_limit_min'])
        else:
            logging.critical(
                'lost setting:item_suit_level_limit_min in item_id:{}'.format(item_id))
            sys.exit()

        if item_data['item_suit_level_limit_max']:
            order_setting[item_id]['item_suit_level_limit_max'] = min(
                item_data['item_suit_level_limit_max'])
        else:
            logging.critical(
                'lost setting:item_suit_level_limit_max in item_id:{}'.format(item_id))
            sys.exit()

    return order_setting


def main():
    shop_setting_csv_path = os.path.join(
        csv_directory, 'free_shop_order_setting.csv')
    temp = get_free_shop_order_setting(shop_setting_csv_path)

    Ticket_Info, Warning_Log = forums_crawler.Get_Forums_Ticket()
    print('======================')
    print('Ticket_Info:{}, Warning_Log:{}'.format(Ticket_Info, Warning_Log))

    # # print(temp)
    # for a, b in temp.items():
    #     print(a)
    #     print(b)

    pass


if __name__ == "__main__":
    main()
