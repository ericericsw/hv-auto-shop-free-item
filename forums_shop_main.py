# import libary
import env_initialization
import csv_tools
import hv_mmlib
import forums_crawler
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
import traceback
from typing import List, Dict, TypedDict
from collections import defaultdict
from dataclasses import dataclass
from forums_lib import Forums_Code
import hv_mmlib
# endregion

# 指定時區
timezone = pytz.timezone('Asia/Taipei')

# 取得當前目錄
if getattr(sys, 'frozen', False):
    # 如果是打包後的可執行文件
    current_directory = os.path.dirname(sys.executable)
else:
    # 如果是未打包的原始腳本
    current_directory = os.path.dirname(os.path.abspath(__file__))
csv_directory = os.path.join(current_directory, 'csv')


# Load configparser
config = configparser.ConfigParser()
config_path = os.path.join(current_directory, 'config.ini')
config.read(config_path, encoding="utf-8")

# 設置日誌
Log_Mode = config.get('Log', 'Log_Mode')
Log_Format = '%(asctime)s | %(filename)s | %(funcName)s | %(levelname)s:%(message)s'
log_file_path = os.path.join(
    current_directory, 'log', 'forums_shop_main.log')
logging.basicConfig(level=getattr(logging, Log_Mode.upper()),
                    format=Log_Format,
                    handlers=[logging.FileHandler(log_file_path, 'a', 'utf-8'),
                              logging.StreamHandler()])


# 讀取店家資訊
HV_Free_Shop_ID = config.get('Account', 'HV_Free_Shop_ID')
HV_Free_Shop_UID = config.get('Account', 'HV_Free_Shop_UID')
Shop_Check_Interval = config.getint('Shop', 'Check_Interval')
Shop_Test_Mode = config.getboolean('Shop', 'Test_Mode')
Run_Once_Mode = config.getboolean('Shop', 'Run_Once_Mode')


@dataclass
class Ticket_Info(Dict):
    order_suit: str
    post_number: int
    User_ID: str
    User_UID: str
    User_Level: int
    Ticket_No: int


@dataclass
class Warning_Log(Dict):
    post_number: int
    Post_ID: int
    User_ID: str
    User_UID: str
    Input_Error_Type: str


class ItemDict(TypedDict):
    item_name: str
    item_number: int


class SuitInfo(TypedDict):
    item_info: List[ItemDict]
    item_suit_cool_time_day: int
    item_suit_order_limit: int
    item_suit_level_limit_min: int
    item_suit_level_limit_max: int


def check_folder_path_exists(folder_Path: os.path):
    if not os.path.exists(folder_Path):
        os.makedirs(folder_Path)
        logging.warning('created {} folder'.format(folder_Path))


def get_item_list() -> List:
    item_list = []
    item_list_csv_path = os.path.join(csv_directory, 'item_list.csv')
    with open(item_list_csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            item_list.append(row['item_name'])
    return item_list


def get_free_shop_order_setting(file_path: os.path) -> Dict[str, SuitInfo]:
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


def warning_log_processing(warning_log: List[Warning_Log]):
    """
    記錄錯誤的ticket資訊
    """
    if warning_log:
        logging.info('warning_log:{}'.format(warning_log))
        logging.warning('Have New Tick')
        for warning_log_data in warning_log:
            # post_number = warning_log_data['post_number']
            # Post_ID = warning_log_data['Post_ID']
            # User_ID = warning_log_data['User_ID']
            # User_UID = warning_log_data['User_UID']
            # Input_Error_Type = warning_log_data['Input_Error_Type']
            post_number = warning_log_data.post_number
            Post_ID = warning_log_data.Post_ID
            User_ID = warning_log_data.User_ID
            User_UID = warning_log_data.User_UID
            Input_Error_Type = warning_log_data.Input_Error_Type
            csv_tools.Add_Error_Ticket_Log(
                post_number, Post_ID, User_ID, User_UID, Input_Error_Type)

            # TODO 還沒做靠 request 做 post edit 的功能

    else:
        logging.info('No Error Tick')


def ticket_info_processing(shop_order_setting: Dict[str, SuitInfo], ticket_info: List[Ticket_Info]):
    """
    ticket 處理的子程式
    輸入變數:
        shop_order_setting:從get_free_shop_order_setting()取得的設定dict
        ticket_info:從forums_crawler.Get_Forums_Ticket()取得的list

    """
    if ticket_info:
        logging.info('ticket_info:{}'.format(ticket_info))
        logging.warning('Have New Tick')

        # 進行task建立
        for ticket_info_data in ticket_info:
            order_suit = ticket_info_data.order_suit
            post_number = ticket_info_data.post_number
            user_id = ticket_info_data.User_ID
            user_uid = ticket_info_data.User_UID
            user_level = ticket_info_data.User_Level
            ticket_no = ticket_info_data.Ticket_No
            # order_suit = ticket_info_data['order_suit']
            # post_number = ticket_info_data['post_number']
            # user_id = ticket_info_data['User_ID']
            # user_uid = ticket_info_data['User_UID']
            # user_level = ticket_info_data['User_Level']
            # ticket_no = ticket_info_data['Ticket_No']

            subject_text = "{}'s Free Shop Ticket {}".format(
                HV_Free_Shop_ID, ticket_no)
            body_text = "Hello {}, Your supplies have arrived".format(user_id)
            if not Shop_Test_Mode:
                hv_mmlib.add_mm_task(
                    shop_order_setting[order_suit]['item_info'], user_id, subject_text, body_text)
        # 開始發送MM
        hv_mmlib.send_mm_with_item()

        # csv_tools.Tag_In_MM_Ticket(ticket_no)

    else:
        logging.info('No New Tick')


def check_item_thresholds(current_thresholds: Dict[str, int], now_holding_item: Dict[str, int]) -> bool:
    for item, count in current_thresholds.items():
        if item in now_holding_item and int(count) < int(now_holding_item[item]):
            logging.error(
                f'item {item} count is {now_holding_item[item]}, is less then thresholds {count}')
            return False
    return True


def get_item_threshold() -> Dict[str, int]:
    item_retention_threshold_file_path = os.path.join(
        current_directory, 'csv', 'item_retention_threshold.csv')

    try:
        # 開啟 CSV 檔案
        with open(item_retention_threshold_file_path, newline='', encoding='utf-8') as csvfile:
            # 建立 CSV 讀取器
            csv_reader = csv.DictReader(csvfile)

            item_list = {}

            # 遍歷每一行
            for row in csv_reader:
                item_name = row['item_name'].lower()
                item_count = row['item_count']
                item_list[item_name] = int(item_count)

        return item_list

    except FileNotFoundError:
        logging.critical(
            f"Error: File {item_retention_threshold_file_path} not found.")
    except Exception as e:
        logging.critical(f"An error occurred: {e}")


def generate_order_info_post_text(shop_order_setting: Dict[str, SuitInfo]):
    bot_order_info_file_path = os.path.join(
        current_directory, 'post_draft', 'bot_order_info.txt')

    def write_list_item(file, content):
        file.write(Forums_Code.LIST_ITEM.value)
        file.write(content)
        file.write(Forums_Code.NEWLINE.value)

    def write_order_info(file, details):
        cool_time = 'Infinity' if details['item_suit_cool_time_day'] == 0 else details['item_suit_cool_time_day']
        write_list_item(file, f"Re-request interval (Days): {cool_time}")
        write_list_item(
            file, f"Order request limit: {details['item_suit_order_limit']}")
        write_list_item(
            file, f"Level Limit: {details['item_suit_level_limit_min']} ~ {details['item_suit_level_limit_max']}")
        write_list_item(file, "Items:")
        file.write(Forums_Code.ORDERED_LIST_START.value)
        for item in details['item_info']:
            write_list_item(
                file, f"    {item['item_name']}: {item['item_number']}")
        file.write(Forums_Code.ORDERED_LIST_END.value)

    with open(bot_order_info_file_path, 'w') as file:
        for suit, details in shop_order_setting.items():
            file.write(f"Suit Name: {suit}")
            file.write(Forums_Code.UNORDERED_LIST_START.value)
            file.write(Forums_Code.NEWLINE.value)
            write_order_info(file, details)
            file.write(Forums_Code.ORDERED_LIST_END.value)
            file.write(Forums_Code.NEWLINE.value)


def main():

    logging.warning('Free Shop is initialization')

    shop_setting_csv_path = os.path.join(
        csv_directory, 'free_shop_order_setting.csv')
    shop_order_setting = get_free_shop_order_setting(shop_setting_csv_path)
    generate_order_info_post_text(shop_order_setting)

    check_transaction = csv_tools.Check_Transaction()

    loop_switch = True

    while (loop_switch):
        try:

            # 上一次完整檢查有結束則執行
            if check_transaction.Check():

                # 檢查開始的備份
                check_transaction.Backup()
                # 檢查開始標記
                check_transaction.Start()

                item_threshold = get_item_threshold()
                item_inventory = hv_mmlib.get_item_inventory()
                if check_item_thresholds(item_threshold, item_inventory):

                    # 爬取論壇 post 資訊
                    ticket_info, warning_log = forums_crawler.Get_Forums_Ticket()

                    if ticket_info:
                        ticket_info_processing(shop_order_setting, ticket_info)
                    if warning_log:
                        warning_log_processing(warning_log)
                    if hv_mmlib.check_pending_mm():
                        hv_mmlib.send_mm_with_item()

                    # 檢查結束標記
                    check_transaction.End()
                    if Run_Once_Mode:
                        loop_switch = False
                    else:
                        # 休息180秒
                        logging.warning('Waiting {}sec'.format(
                            (Shop_Check_Interval-20)))
                        time.sleep((Shop_Check_Interval-20))
                        logging.warning('Will be check in 20sec')
                        time.sleep(20)
                        logging.warning('Check Start')

            # 上次檢查異常中止，進行 Rollback
            else:
                # 進行 Rollback
                check_transaction.Rollback()

                # 關閉狀態
                check_transaction.End()

                logging.critical(
                    'Rollback End,Waiting Check Loop Start,Wait 300sec')

                # Rollback 後等待 300 秒
                time.sleep(300)

        except Exception as e:
            # 在這裡處理異常，並印出完整的錯誤訊息
            traceback.print_exc()
            # 在這裡處理異常，並印出錯誤訊息
            error_message = "遇到錯誤：{}".format(e)
            logging.critical(error_message)

            # 等待 300 秒
            time.sleep(300)


if __name__ == "__main__":
    # main()
    pass
    # os.system("pause")

    shop_setting_csv_path = os.path.join(
        csv_directory, 'free_shop_order_setting.csv')
    shop_order_setting = get_free_shop_order_setting(shop_setting_csv_path)
    generate_order_info_post_text(shop_order_setting)
    # print(shop_order_setting)

    # for suit, details in shop_order_setting.items():
    #     print(f"Suit Name: {suit}")
    #     cool_time = 'Infinity' if details['item_suit_cool_time_day'] == 0 else details['item_suit_cool_time_day']
    #     print(f"  Re-request interval (Days): {cool_time}")
    #     print(f"  Order request limit: {details['item_suit_order_limit']}")
    #     print(
    #         f"  Level Limit: {details['item_suit_level_limit_min']} ~ {details['item_suit_level_limit_max']}")
    #     print("  Items:")
    #     for item in details['item_info']:
    #         print(f"    - {item['item_name']}: {item['item_number']}")
    #     print()
