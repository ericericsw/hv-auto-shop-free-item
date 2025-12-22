import ast
import requests
import configparser
import os
import csv
import re
import datetime
import json
import sys
from typing import List, Dict, TypedDict, Optional, Tuple, Literal, Union
import csv_tools
from bs4 import BeautifulSoup
from lxml import etree
import time
import hv_equiplib
import inspect
import enum
from dataclasses import dataclass
import traceback
from pydantic import BaseModel, field_validator, HttpUrl
from utils.logger import setup_logger
from utils.utils import convert_to_iso, get_now_time

# 讀取 logger
logger = setup_logger(__name__)

if getattr(sys, 'frozen', False):
    # 如果是打包後的可執行文件
    current_directory = os.path.dirname(sys.executable)
else:
    # 如果是未打包的原始腳本
    current_directory = os.path.dirname(os.path.abspath(__file__))
# 創建 ConfigParser 對象
config = configparser.ConfigParser()
# 讀取配置文件
config_path = os.path.join(current_directory, 'config.ini')
config.read(config_path, encoding="utf-8")

csv_folder_path = os.path.join(current_directory, 'csv')
log_folder_path = os.path.join(current_directory, 'log')
json_folder_path = os.path.join(current_directory, 'json')


def check_folder_path_exists(folder_Path: os.path):
    if not os.path.exists(folder_Path):
        os.makedirs(folder_Path)
        logger.warning(f"資料夾 '{folder_Path}' 已建立。")


class CookieDict(BaseModel):
    ipb_member_id: str
    ipb_pass_hash: str
    ipb_session_id: str


class CookieKeys(enum.Enum):
    IPB_MEMBER_ID = 'ipb_member_id'
    IPB_PASS_HASH = 'ipb_pass_hash'
    IPB_SESSION_ID = 'ipb_session_id'


class ItemDict(BaseModel):
    item_name: str
    item_number: int


class TaskItem_to_dict(BaseModel):
    task_id: int
    user_id: str
    subject: str
    body_text: str
    data: List[ItemDict]
    status: str


class MM_Inbox_Data(BaseModel):
    mm_from: str
    subject: str
    sent_time: str
    mm_id: int
    done_read: bool


MM_INBOX_HEADER: List[str] = list(MM_Inbox_Data.__annotations__.keys())


class MM_Send_Mail_Data(BaseModel):
    mm_to: str
    subject: str
    sent_time: str
    read_time: str
    mm_id: int
    done_read: bool


MM_SEND_MAIL_HEADER: List[str] = list(MM_Send_Mail_Data.__annotations__.keys())


class MM_Inbox_List(enum.StrEnum):
    mm_from = 'mm_from'
    subject = 'subject'
    sent_time = 'sent_time'
    mm_id = 'mm_id'
    done_read = 'done_read'


class MM_Send_Mail_List(enum.StrEnum):
    mm_to = 'mm_to'
    subject = 'subject'
    sent_time = 'sent_time'
    read_time = 'read_time'
    mm_id = 'mm_id'
    done_read = 'done_read'


class MM_Read_Send_Data(BaseModel):
    mm_No: int
    mm_from: str
    mm_to: str
    subject: str
    sent_time: str
    read_time: str
    mm_id: int
    body_id: str
    cod_switch: bool
    cod_value: int
    attached_number: int
    attached_list_preview: list
    attached_list_id: int
    done_take: bool
    done_retrun: bool

    @field_validator("attached_list_preview", mode="before")
    def parse_list(cls, v):
        if v in ("", None, "[]"):
            return []
        if isinstance(v, str):
            try:
                return ast.literal_eval(v)  # 安全地把字串轉成 Python list
            except Exception:
                return []  # 如果解析失敗，給空 list
        return v


MM_INFO_HEADER: list[str] = list(MM_Read_Send_Data.__annotations__.keys())


class MM_Read_Send_Attach_List_Data(BaseModel):
    id: int
    attached_item1: str
    attached_item2: str
    attached_item3: str
    attached_item4: str
    attached_item5: str
    attached_item6: str
    attached_item7: str
    attached_item8: str
    attached_item9: str
    attached_item10: str


MM_ATTACH_LIST_HEADER: list[str] = list(
    MM_Read_Send_Attach_List_Data.__annotations__.keys())


class Read_Or_Send(enum.Enum):
    READ: str = 'read'
    SEND: str = 'send'


class MM_Or_List(enum.Enum):
    MM: str = 'mm'
    LIST: str = 'list'


class Lock_Or_Unlock(enum.Enum):
    LOCK: int = 1
    UNLOCK: int = 0


# 定義輸出的單個項目結構
class ParsedGameItem(BaseModel):
    # tag 限制只能是這四種字串之一
    tag: Literal['equip', 'Credits', 'Hath', 'item']
    name: str
    # value 可以是 int (數量) 或 HttpUrl (網址)
    # 這裡使用 Union[int, HttpUrl] 讓 Pydantic 知道這兩種都合法
    value: Union[int, HttpUrl]


class ParsedResultList(BaseModel):
    items: List[ParsedGameItem]


MAX_READ_PAGE = 0
HENTAIVERSE_URL = 'https://hentaiverse.org'
# HENTAIVERSE_URL = 'https://hvtl.e-hentai.org/'
mm_inbox_file_path = os.path.join(csv_folder_path, 'mm_inbox.csv')
mm_read_info_file_path = os.path.join(csv_folder_path, 'mm_read_info.csv')
mm_read_attach_list_file_path = os.path.join(
    csv_folder_path, 'mm_read_attach_list.csv')
mm_send_list_path = os.path.join(csv_folder_path, 'mm_send_list.csv')
mm_send_info_file_path = os.path.join(csv_folder_path, 'mm_send_info.csv')
mm_send_attach_list_file_path = os.path.join(
    csv_folder_path, 'mm_send_attach_list.csv')


def load_item_dict(csv_file_path):
    item_dict = {}
    with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            item_dict[row['item_name']] = int(row['item_id'])
    return item_dict


item_list_csv_path = os.path.join(csv_folder_path, 'item_list.csv')
item_dict = load_item_dict(item_list_csv_path)
# 反轉字典
reversed_dict = {v: k for k, v in item_dict.items()}


class TaskItem:
    def __init__(self, task_id: int, user_id: str, subject: str, body_text: str, data: List[ItemDict], status: str = 'Pending'):
        self.task_id: int = task_id
        self.user_id: str = user_id
        self.subject: str = subject
        self.body_text: str = body_text
        self.data: List[ItemDict] = data
        self.status: str = status

    def to_dict(self) -> TaskItem_to_dict:
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "subject": self.subject,
            "body_text": self.body_text,
            "data": self.data,
            "status": self.status
        }

    def complete(self):
        self.status: str = 'Finish'


def get_datetime_now_isoformat():
    """
    無時區、精度為秒
    """
    return datetime.datetime.now().isoformat(timespec='seconds')


def get_cookie() -> CookieDict:

    cookies = {}
    ipb_member_uid_value = config.get('Account', 'HV_Free_Shop_UID')
    ipb_pass_hash_value = config.get('Account', 'ipb_pass_hash')
    ipb_session_id_value = config.get('Account', 'ipb_session_id')

    cookies = {
        CookieKeys.IPB_MEMBER_ID.value: ipb_member_uid_value,
        CookieKeys.IPB_PASS_HASH.value: ipb_pass_hash_value,
        CookieKeys.IPB_SESSION_ID.value: ipb_session_id_value
    }

    return cookies


def parse_attach_data(data_obj: MM_Read_Send_Attach_List_Data) -> List[ParsedGameItem]:
    """
    解析 MM_Read_Send_Attach_List_Data 物件，並回傳驗證過的 Pydantic 模型列表
    """
    parsed_results = []

    # 步驟 1: 提取所有非空欄位
    raw_item_strings = []
    for i in range(1, 11):
        attr_name = f'attached_item{i}'
        val = getattr(data_obj, attr_name, '')
        if val:
            raw_item_strings.append(str(val))

    # 步驟 2: 解析邏輯
    for item_str in raw_item_strings:

        # 暫存變數，稍後用來建立 ParsedGameItem
        tag = None
        name = None
        value = None

        # --- 規則 1: 裝備 (Equip) ---
        equip_match = re.search(r"^(.*?)\((https?://[^)]+)\)$", item_str)
        if equip_match:
            tag = 'equip'
            name = equip_match.group(1).strip()
            value = equip_match.group(2)  # 這裡是網址 (str)

        # --- 規則 2: Credits ---
        elif 'Credits' in item_str:
            tag = 'Credits'
            name = 'Credits'
            num_part = re.sub(r"[^\d]", "", item_str)
            value = int(num_part) if num_part else 0  # 這裡是數量 (int)

        # --- 規則 3: Hath ---
        elif 'Hath' in item_str:
            tag = 'Hath'
            name = 'Hath'
            num_part = re.sub(r"[^\d]", "", item_str)
            value = int(num_part) if num_part else 0  # 這裡是數量 (int)

        # --- 規則 4: 一般道具 (Item) ---
        else:
            tag = 'item'
            item_match = re.search(r"^(\d+)x?\s+(.*)", item_str)
            if item_match:
                name = item_match.group(2).strip()
                value = int(item_match.group(1))  # 這裡是數量 (int)
            else:
                name = item_str
                value = 1

        # 建立 Pydantic 物件並加入列表
        if tag:
            item_model = ParsedGameItem(tag=tag, name=name, value=value)
            parsed_results.append(item_model)

    return parsed_results


def get_item_inventory() -> Dict[str, int]:
    """
    取得當前道具清單與數量
    """

    # url = 'https://hentaiverse.org/?s=Character&ss=it'
    url = HENTAIVERSE_URL+'/?s=Character&ss=it'
    response = requests.get(url, cookies=get_cookie())

    if check_battle_status(response):
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # 找到特定的table
            item_table = soup.find('table', class_='nosel itemlist')

            if item_table:
                # 擷取並處理表格內容
                items_text = item_table.text

                # 使用正則表達式擷取項目名稱和數字
                item_list = {}
                matches = re.findall(r'([A-Za-z\s\-]+)(\d+)', items_text)
                for match in matches:
                    item_name = match[0].strip().lower()  # 統一使用小寫 item name
                    item_count = int(match[1])
                    item_list[item_name] = item_count

                return item_list

            else:
                logger.critical('can not found item table')
                return False

        else:
            logger.error('{} Fail. code:get_item_inventory text:{}'.format(
                response.status_code, response.text))
            return False

    else:
        logger.error('The account is in battle')
        return False


def check_battle_status(response):
    """
    檢查是否在戰鬥狀態，不在戰鬥中回應true，在戰鬥中回應false
    """
    html_content = response.text
    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # 將 HTML 轉換為字符串
    html_str = str(soup)

    # 使用正則表達式檢查是否存在指定的變量
    battle_token_exists = bool(
        re.search(r'var battle_token', html_str))
    battle_new_exists = bool(
        re.search(r'var battle = new Battle\(\)', html_str))

    # 若在戰鬥中則 check_battle_status 為 False
    battle_status = not (
        battle_token_exists or battle_new_exists)

    return battle_status


def get_mm_id(mm_url: str) -> int:
    """
    抽取MM id
    https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=<MM id>
    """
    # 使用正则表达式提取 mid 参数的值
    match = re.search(r'mid=(\d+)', mm_url)
    if match:
        mm_id = match.group(1)
        return mm_id
    else:
        logger.critical("No mid parameter found in the URL")
        return 0


def get_mm_send_time(mm_id: int) -> str:
    """
    從 mm_inbox.csv 取得 send_time

    """

    sent_time = None
    with open(mm_inbox_file_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['mm_id'] == str(mm_id):
                sent_time = row['sent_time']
                break
    return sent_time


def get_mm_read_send_max_id(read_or_send: Read_Or_Send, mm_or_list: MM_Or_List) -> int:
    """
    從 mm_read_info.csv、mm_send_info.csv、mm_read_list.csv、mm_send_list.csv 得取當前最大 id 值

    input:
        read_or_send:read or send
        mm_or_list:mm or list

    """
    if read_or_send == Read_Or_Send.READ:
        if mm_or_list == MM_Or_List.LIST:
            mm_file_path = mm_read_attach_list_file_path
            header = MM_ATTACH_LIST_HEADER
        elif mm_or_list == MM_Or_List.MM:
            mm_file_path = mm_read_info_file_path
            header = MM_INFO_HEADER
    elif read_or_send == Read_Or_Send.SEND:
        if mm_or_list == MM_Or_List.LIST:
            mm_file_path = mm_send_attach_list_file_path
            header = MM_ATTACH_LIST_HEADER
        elif mm_or_list == MM_Or_List.MM:
            mm_file_path = mm_send_info_file_path
            header = MM_INFO_HEADER

    # 進行檔案存在檢查
    csv_tools.check_csv_exists(mm_file_path, header)

    if mm_file_path:
        max_id = 0
        with open(mm_file_path, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if mm_or_list == MM_Or_List.LIST:
                    current_id = int(row['id'])
                elif mm_or_list == MM_Or_List.MM:
                    current_id = int(row['mm_No'])
                if max_id is None or current_id > max_id:
                    max_id = current_id
        return max_id
    else:
        logger('read_or_send input error,read_or_send:{},mm_or_list:{}'.format(
            read_or_send, mm_or_list))


def add_read_send_mm_body(body_id: int, read_or_send: Read_Or_Send, body_text: str) -> bool:
    """
    寫入 body 資訊

    """
    if read_or_send == Read_Or_Send.READ:
        mm_body_file_path = os.path.join(
            csv_folder_path, 'body', 'read', '{}.txt'.format(body_id))
    elif read_or_send == Read_Or_Send.SEND:
        mm_body_file_path = os.path.join(
            csv_folder_path, 'body', 'send', '{}.txt'.format(body_id))
    else:
        logger.critical(
            'read_or_send input error,read_or_send:{}'.format(read_or_send))
        return False

    # 對檔案的上一層資料夾確認
    check_folder_path_exists(os.path.abspath(
        os.path.join(mm_body_file_path, '..')))

    try:
        with open(mm_body_file_path, mode='w', encoding='utf-8') as file:
            file.write(body_text)
        return True

    except Exception as e:
        logger.critical('Error: {}'.format(e))
        return False


def add_read_send_mm_attach_list(read_or_send: Read_Or_Send, mm_read_send_attach_list_data: List[MM_Read_Send_Attach_List_Data]) -> bool:
    """
    追加 read、send 資訊

    input:
        read_or_send:輸入read或是send，決定模式
        mm_read_send_attach_list_data:read與send格式共用
    """

    if read_or_send == Read_Or_Send.READ:
        mm_file_path = mm_read_attach_list_file_path
    elif read_or_send == Read_Or_Send.SEND:
        mm_file_path = mm_send_attach_list_file_path
    else:
        logger.critical('read_or_send input error')
        return False

    csv_tools.check_csv_exists(mm_file_path, MM_ATTACH_LIST_HEADER)

    # try:
    #     with open(mm_file_path, 'r', newline='', encoding='utf-8') as csvfile:
    #         reader = csv.DictReader(csvfile)
    #         headers = reader.fieldnames
    # except FileNotFoundError:
    #     pass

    # 确保 mm_read_send_attach_list_data 是一个包含字典的列表
    if isinstance(mm_read_send_attach_list_data, dict):
        mm_read_send_attach_list_data = [mm_read_send_attach_list_data]

    # 寫入新資料到 CSV 檔案
    with open(mm_file_path, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=MM_ATTACH_LIST_HEADER)
        writer.writerows(mm_read_send_attach_list_data)
    return True


def add_send_mm_info_read_time(mm_id, read_time) -> bool:
    """
    補上 read time
    """
    csv_tools.check_csv_exists(mm_send_info_file_path, MM_INFO_HEADER)

    # 讀取並轉成 BaseModel
    rows = []
    with open(mm_send_list_path, mode="r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        for row in reader:
            # 建立 BaseModel 物件
            data = MM_Send_Mail_Data(**row)
            # 注意：CSV 讀進來的 int/bool 會是字串，要轉型
            data.mm_id = int(data.mm_id)
            data.done_read = data.done_read.lower() in ["true", "1", "yes"]

            # 如果符合目標 mm_id，更新 sent_time
            if data.mm_id == mm_id:
                data.sent_time = (data.sent_time + ";" +
                                  read_time) if data.sent_time else read_time
            # 存回 dict，準備寫回 CSV
            rows.append(data.dict())

    # 覆蓋寫回 CSV
    with open(mm_send_list_path, mode="w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"已更新 mm_id={mm_id} 的 sent_time")

    return True


def add_read_send_mm_info(read_or_send: Read_Or_Send, mm_read_send_data: List[MM_Read_Send_Data]) -> bool:
    """
    追加 read、send 資訊

    input:
        read_or_send:輸入read或是send，決定模式
        mm_read_send_data:read與send格式共用
    """

    if read_or_send == Read_Or_Send.READ:
        mm_file_path = mm_read_info_file_path
    elif read_or_send == Read_Or_Send.SEND:
        mm_file_path = mm_send_info_file_path
    else:
        logger.critical('read_or_send input error')
        return False

    csv_tools.check_csv_exists(mm_file_path, MM_INFO_HEADER)

    # 讀取已存在的 mm_id
    existing_mm_id = set()
    try:
        with open(mm_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            headers = reader.fieldnames
            for row in reader:
                existing_mm_id.add(row['mm_id'])
    except FileNotFoundError:
        pass

    # 檢查是否有寫入過
    data_mm_id = mm_read_send_data['mm_id']
    if str(data_mm_id) not in existing_mm_id:
        # 确保 mm_read_send_data 是一个包含字典的列表
        if isinstance(mm_read_send_data, dict):
            mm_read_send_data = [mm_read_send_data]

        # 寫入新資料到 CSV 檔案
        with open(mm_file_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writerows(mm_read_send_data)
        return True
    return False


def add_inbox_mm_info(mm_inbox_data: List[MM_Inbox_Data]):
    """
    追加 inbox 資訊
    """
    try:
        header = MM_INBOX_HEADER
        csv_tools.check_csv_exists(mm_inbox_file_path, header)

        # 讀取已存在的 mm_id
        existing_urls = set()
        try:
            with open(mm_inbox_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                headers = reader.fieldnames
                for row in reader:
                    existing_urls.add(row[MM_Inbox_List.mm_id])
        except FileNotFoundError:
            pass
        # 過濾出尚未加入的資料
        new_data = [row for row in mm_inbox_data if row[MM_Inbox_List.mm_id]
                    not in existing_urls]
        # ? 反轉 list
        # ? 因為 inbox_check 的 for 是從最後一筆資料往前問
        new_data = new_data[::-1]

        # 寫入新資料到 CSV 檔案
        with open(mm_inbox_file_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)

            writer.writerows(new_data)
        return True

    except Exception as e:
        logger.critical('Error: {}'.format(e))
        return False


def get_mm_read_info_all() -> List[MM_Read_Send_Data]:
    """
    讀取 mm_read_info.csv 並回傳 List[MM_Read_Send_Data]
    """

    result: list[MM_Read_Send_Data] = []

    if not os.path.exists(mm_read_info_file_path):
        return result

    try:
        with open(mm_read_info_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # 建立 BaseModel 物件
                model = MM_Read_Send_Data(**row)
                # model = MM_Read_Send_Data(
                #     mm_No=row.get('mm_No', ''),
                #     mm_from=row.get('mm_from', ''),
                #     mm_to=row.get('mm_to', ''),
                #     subject=row.get('subject', ''),
                #     sent_time=row.get('sent_time', ''),
                #     read_time=row.get('read_time', ''),
                #     mm_id=row.get('mm_id', ''),
                #     body_id=row.get('body_id', ''),
                #     cod_switch=row.get('cod_switch', ''),
                #     cod_value=row.get('cod_value', ''),
                #     attached_number=row.get('attached_number', ''),
                #     attached_list_preview=row.get('attached_list_preview', ''),
                #     attached_list_id=row.get('attached_list_id', ''),
                #     done_take=row.get('done_take', ''),
                # )

                result.append(model)
    except Exception as e:
        logger.critical(f"Error reading inbox CSV: {e}")

    return result


def get_mm_send_list_info_all() -> List[MM_Send_Mail_Data]:
    """
    讀取 mm_send_info.csv 並回傳 List[MM_Send_Mail_Data]

    :return: 說明
    :rtype: List[MM_Send_Mail_Data]
    """

    result: list[MM_Send_Mail_Data] = []

    if not os.path.exists(mm_send_list_path):
        return result

    try:
        with open(mm_send_list_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # 建立 BaseModel 物件
                model = MM_Send_Mail_Data(**row)

                result.append(model)
    except Exception as e:
        logger.critical(f"Error reading inbox CSV: {e}")

    return result


def save_mm_send_list_all(data_list: List[dict]) -> bool:
    """
    將完整的資料列表覆蓋寫回 CSV (清除舊檔，寫入新檔)
    """
    try:
        if not data_list:
            return False

        header = MM_SEND_MAIL_HEADER

        # 使用 'w' 模式，這會清空舊檔案內容並寫入新的完整資料
        with open(mm_send_list_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=header)
            writer.writeheader()
            writer.writerows(data_list)

        logger.info(
            f"Successfully overwritten CSV with {len(data_list)} unique records.")
        return True
    except Exception as e:
        logger.critical(f"Error saving send list CSV: {e}")
        return False


def get_mm_info_read_or_send(read_or_send: Read_Or_Send, mm_id: int) -> Tuple[bool, MM_Read_Send_Data, MM_Read_Send_Attach_List_Data]:
    """
    查詢 MM info 與 attach

    :param read_or_send: 指定查詢的是 read 或 send MM
    :type read_or_send: Read_Or_Send
    :param mm_id: mm_id
    :type mm_id: int
    """

    if read_or_send == Read_Or_Send.READ:
        info_file_path = mm_read_info_file_path
        attach_list_file_path = mm_read_attach_list_file_path
    elif read_or_send == Read_Or_Send.SEND:
        info_file_path = mm_send_info_file_path
        attach_list_file_path = mm_send_attach_list_file_path
    else:
        logger.critical(f'input error')

    try:
        target_mm: MM_Read_Send_Data
        target_attach: MM_Read_Send_Attach_List_Data

        with open(info_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # 建立 BaseModel 物件
                mm_info = MM_Read_Send_Data(**row)
                if str(mm_info.mm_id) == str(mm_id):
                    target_mm = mm_info

        mm_body_id = target_mm.body_id

        with open(attach_list_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # 建立 BaseModel 物件
                mm_attach = MM_Read_Send_Attach_List_Data(**row)
                if str(mm_attach.id) == str(mm_body_id):
                    target_attach = mm_attach

        return True, target_mm, target_attach

    except Exception as e:
        print("遇到錯誤：", e)
        print("完整錯誤追蹤：")
        print(traceback.format_exc())
        return False, None, None


def get_mm_inbox_all() -> List[MM_Inbox_Data]:
    """
    讀取 mm_inbox.csv 並回傳 List[MM_Inbox_Data]
    """

    result: list[MM_Inbox_Data] = []

    if not os.path.exists(mm_inbox_file_path):
        return result

    try:
        with open(mm_inbox_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # 建立 BaseModel 物件
                model = MM_Inbox_Data(**row)
                # model = MM_Inbox_Data(
                #     mm_No=row.get('mm_No', ''),
                #     mm_from=row.get('mm_from', ''),
                #     mm_to=row.get('mm_to', ''),
                #     subject=row.get('subject', ''),
                #     sent_time=row.get('sent_time', ''),
                #     read_time=row.get('read_time', ''),
                #     mm_id=row.get('mm_id', ''),
                #     body_id=row.get('body_id', ''),
                #     cod_switch=row.get('cod_switch', ''),
                #     cod_value=row.get('cod_value', ''),
                #     attached_number=row.get('attached_number', ''),
                #     attached_list_preview=row.get('attached_list_preview', ''),
                #     attached_list_id=row.get('attached_list_id', ''),
                #     done_take=row.get('done_take', ''),
                # )

                result.append(model)
    except Exception as e:
        logger.critical(f"Error reading inbox CSV: {e}")

    return result


def get_mm_read_info_by_mm_id(mm_id: int) -> Optional[MM_Inbox_Data]:
    """
    讀取 mm_inbox.csv 並根據 mm id 篩選後，回傳 MM_Inbox_Data
    """

    result = get_mm_read_info_all()
    for item in result:
        if int(item.mm_id) == int(mm_id):
            return item
    logger.warning(f'can not find mm info,mm_id:{mm_id}')
    return None


def update_done_take(mm_id: int) -> bool:
    fieldnames = list(MM_Read_Send_Data.model_fields.keys())

    if not os.path.exists(mm_read_info_file_path):
        return False

    try:
        # 讀取所有資料
        data = get_mm_read_info_all()

        # 更新指定 mm_id
        updated = False
        for item in data:
            if item.mm_id == mm_id:
                item.done_take = True
                updated = True
                break

        # 回存 CSV
        if updated:
            with open(mm_read_info_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for item in data:
                    writer.writerow(item.model_dump())
        logger.info(f'read mm_id:{mm_id}')
        return updated

    except Exception as e:
        print(f"Error updating done_read: {e}")
        return False


def update_done_retrun(mm_id: int) -> bool:
    """
    退回後並標記 done_retrun，主要用於對方寄 COD
    """

    fieldnames = list(MM_Read_Send_Data.model_fields.keys())

    if not os.path.exists(mm_read_info_file_path):
        return False

    try:
        # 讀取所有資料
        data = get_mm_read_info_all()

        # 更新指定 mm_id
        updated = False
        for item in data:
            if item.mm_id == mm_id:
                item.done_retrun = True
                updated = True
                break

        # 回存 CSV
        if updated:
            with open(mm_read_info_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for item in data:
                    writer.writerow(item.model_dump())
        logger.info(f'read mm_id:{mm_id}')
        return updated

    except Exception as e:
        print(f"Error updating done_read: {e}")
        return False


def read_send_mm_info_unread() -> List[MM_Inbox_Data]:
    """
    讀取 mm_send_list.csv，僅回傳 done_read == False 的資料
    """
    all_data = get_mm_send_list_info_all()
    unread_data = [
        row for row in all_data if not row.done_read]
    return unread_data


def get_send_mm_info_read_time_never() -> List[int]:
    """
    讀取 mm_send_list.csv，僅回傳 read_time 為 Never 的順序值
    """
    number_list = []
    all_data = get_mm_send_list_info_all()
    # 把 list 反轉
    all_data.reverse()
    number = 1
    for data in all_data:
        if data.read_time == 'Never':
            number_list.append(number)
        number += 1
    return number_list


def read_inbox_mm_info_unread() -> List[MM_Inbox_Data]:
    """
    讀取 mm_inbox.csv，僅回傳 done_read == False 的資料
    """
    all_data = get_mm_inbox_all()
    unread_data = [row for row in all_data if not row.done_read]
    return unread_data


def update_done_read(mm_id: int, read_or_send: Read_Or_Send) -> bool:
    """
    根據 mm_id 將 mm_inbox.csv 中的 done_read 改為 True
    """
    if read_or_send == Read_Or_Send.READ:
        fieldnames = list(MM_Inbox_Data.model_fields.keys())
        update_file_path = mm_inbox_file_path
    elif read_or_send == Read_Or_Send.SEND:
        fieldnames = list(MM_Send_Mail_Data.model_fields.keys())
        update_file_path = mm_send_list_path

    if not os.path.exists(update_file_path):
        return False

    try:
        # 讀取所有資料
        if read_or_send == Read_Or_Send.READ:
            data = get_mm_inbox_all()
        elif read_or_send == Read_Or_Send.SEND:
            data = get_mm_send_list_info_all()

        # 更新指定 mm_id
        updated = False
        for item in data:
            if item.mm_id == mm_id:
                item.done_read = True
                updated = True
                break

        # 回存 CSV
        if updated:
            with open(update_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for item in data:
                    writer.writerow(item.model_dump())
        logger.info(f'read mm_id:{mm_id}')
        return updated

    except Exception as e:
        print(f"Error updating done_read: {e}")
        return False


def check_after_post(response: requests, frame_name: str, mm_id: int = None) -> bool:

    # mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=' + mm_id
    if mm_id is not None:
        # mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=' + mm_id
        mm_url = HENTAIVERSE_URL+'/?s=Bazaar&ss=mm&filter=inbox&mid=' + mm_id
    else:
        # mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox'
        mm_url = HENTAIVERSE_URL + '/?s=Bazaar&ss=mm&filter=inbox'

    if response.status_code == 200:
        if check_battle_status(response):
            logger.info('{}:{} Success'.format(frame_name, mm_url))
            return True
        else:
            logger.error('The account is in battle')
            return False
    else:
        logger.error('{} Fail. code:{} text:{}'.format(
            frame_name, response.status_code, response.text))
        return False


def check_mm_cod_status(soup: BeautifulSoup) -> tuple[bool, int]:
    cod_switch: bool = False
    cod_value: int = 0

    mmail_currentcod = soup.find('div', id='mmail_currentcod')
    if mmail_currentcod:
        fc4_fac_fcb = mmail_currentcod.find(
            'div', class_='fc4 fac fcb')
        if fc4_fac_fcb:
            mmail_attachinfo = fc4_fac_fcb.find('div')
            if mmail_attachinfo:
                mmail_attachinfo_text = mmail_attachinfo.text
                # print(mmail_attachinfo_text)
                cod_switch = True
                # 使用 regex 提取 CoD 值
                cod_match = re.search(
                    r'\d+', mmail_attachinfo_text)
                if cod_match:
                    value = int(cod_match.group())
                    # print(value)
                    cod_value = value

    return cod_switch, cod_value


class MoogleMail():
    def __init__(self):
        # self.mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm'
        self.mm_url = HENTAIVERSE_URL+'/?s=Bazaar&ss=mm'
        self.mm_write_url = self.mm_url + '&filter=new'
        self.mm_inbox_url = self.mm_url + '&filter=inbox'
        self.mm_send_mail_url = self.mm_url + '&filter=sent'
        self.cookies: CookieDict = get_cookie()
        self.mmtoken = None
        self.simple_token = None
        self.user_uid = config.get('Account', 'HV_Free_Shop_UID')

    def check_status(self) -> bool:
        """
        戰鬥狀態檢查，沒在戰鬥中則回應true，戰鬥中回應false
        """
        # 進行 GET 請求並附加 cookie
        response = requests.get(self.mm_url, cookies=self.cookies)

        if response.status_code == 200:
            # 檢查是否在戰鬥狀態
            if check_battle_status(response):
                # logger.info('The account not in battle')
                return True
            else:
                logger.error('The account is in battle')
                return False
        else:
            logger.error('check_status fail. code:{}'.format(
                response.status_code))
            return False

    def inbox_check(self) -> tuple[bool, Optional[List[MM_Inbox_Data]]]:
        """
        檢查inbox並取得inbox列表資訊(單封MM的URL、From、Subject、SentTime、ReadTime)
        並將新的MM資訊記錄在 mm_inbox.csv 中

        return:
            檢查成功會回應 true，失敗則 false

        """
        try:

            # 進行 GET 請求並附加 cookie
            response = requests.get(self.mm_inbox_url, cookies=self.cookies)

            if response.status_code == 200:
                # 檢查是否在戰鬥狀態
                if check_battle_status(response):
                    # logger.info('The account not in battle')

                    soup = BeautifulSoup(response.text, 'html.parser')
                    outer_div = soup.find('div', id='mmail_outerlist')
                    if outer_div:
                        table = outer_div.find('table', id='mmail_list')
                        # 找到所有 <div> 標籤
                        divs = table.find_all('div')
                        # 將 ResultSet 轉換為字串
                        divs_str = ''.join(str(div) for div in divs)
                        # 檢查字串中是否包含特定子字串
                        No_New_MM_text = "<div>No New Mail</div>"
                        if not No_New_MM_text in divs_str:
                            # mail_list = table.find('tbody')
                            mail_list = table
                            if mail_list:
                                rows = mail_list.find_all('tr')
                                mm_inbox_list = []
                                for row in rows:
                                    onclick_attr = row.get('onclick')
                                    columns = row.find_all('td')
                                    if onclick_attr and columns:
                                        mm_url = re.search(
                                            r"document\.location='(.*?)'", onclick_attr).group(1)

                                        # 時間格式轉換
                                        raw_sent_time = columns[2].text.strip()

                                        iso_sent_time = convert_to_iso(
                                            raw_sent_time)

                                        mm_info: MM_Inbox_Data = {
                                            MM_Inbox_List.mm_from: columns[0].text.strip(),
                                            MM_Inbox_List.subject: columns[1].text.strip(),
                                            MM_Inbox_List.sent_time: iso_sent_time,
                                            MM_Inbox_List.mm_id: get_mm_id(mm_url),
                                            MM_Inbox_List.done_read: False
                                        }
                                        mm_inbox_list.append(mm_info)

                                if add_inbox_mm_info(mm_inbox_list):
                                    return True, mm_inbox_list
                                else:
                                    logger.critical('add inbox mm info fail')
                                    return False, None
                            else:
                                print("No tbody found in the table.")
                        else:
                            logger.info("No New Mail.")
                            return False, None
                    else:
                        logger.critical(
                            "No div with id 'mmail_outerlist' found.")
                        return False, None
                else:
                    logger.error('The account is in battle')
                    return False, None
            else:
                logger.error('inbox_check fail. code:{}'.format(
                    response.status_code))
                return False, None
        except Exception as e:
            print("遇到錯誤：", e)
            print("完整錯誤追蹤：")
            print(traceback.format_exc())

    def read_mm(self, mm_id: str, read_or_send: Read_Or_Send) -> bool:
        """
        輸入 mm_id 來讀取內容資料
        read_or_send 為選擇是 read 還是 send

        TODO 還沒做回傳與整理，裝備部分可以跟 hv_equiplib 串
        TODO 空白信件與attach關係處理
        """
        cod_switch: bool = False
        cod_value: int = 0

        # mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=' + \
        #     str(mm_id)
        mm_url = HENTAIVERSE_URL+'/?s=Bazaar&ss=mm&filter=inbox&mid=' + \
            str(mm_id)
        equip_dict = {}

        response = requests.get(mm_url, cookies=self.cookies)
        # print(response.text)
        if response.status_code == 200:
            # 檢查是否在戰鬥狀態
            if check_battle_status(response):
                # logger.info('The account not in battle')
                soup = BeautifulSoup(response.text, 'html.parser')
                # print(soup.prettify())

                # 提取 MM 左半邊資料
                mmail_left = soup.find('div', id="mmail_left")
                # 提取 MM to,from,subject 資訊
                trs = mmail_left.find_all('tr')
                temp_list = []
                # 因元素結構問題，透過 for 迴圈取出並暫存在 list 中
                for tr in trs:
                    td = tr.find_all('td')
                    input_element = td[1].find('input')
                    temp_list.append(input_element.get('value'))
                mm_to = temp_list[0]
                mm_from = temp_list[1]
                subject = temp_list[2]

                # 提取 MM body
                textarea_element = mmail_left.find('textarea')
                bodytext = textarea_element.get_text()

                # 提取 MM 右半邊資料
                mmail_right = soup.find('div', id="mmail_right")

                cod_switch, cod_value = check_mm_cod_status(soup)

                # 提取附件資訊
                mmail_attachpanes = mmail_right.find(
                    'div', id='mmail_attachpanes')
                mmail_attachinfo = mmail_attachpanes.find(
                    'div', id='mmail_attachinfo')

                # 確認有無附件資訊
                """
                解析
                <div id="mmail_attachinfo">
                </div>
                裡面的資料
                """
                if mmail_attachinfo.get_text(strip=True):
                    # 提取 2 / 10 items attached
                    attach_count = mmail_attachinfo.select_one(
                        '#mmail_attachcount .fc4.fac.fcb div').get_text()
                    # 提取 2 / 10
                    attach_count_numbers = ' '.join(attach_count.split()[:3])
                    attach_count_numbers_match = re.search(
                        r'^\d+', attach_count_numbers)
                    if attach_count_numbers_match:
                        attach_number = int(attach_count_numbers_match.group())

                    # 抽取附件清單
                    attach_list = soup.select(
                        '#mmail_attachlist > div > div:first-child')
                    attach_items = [item.get_text() for item in attach_list]
                else:
                    # 沒有附件時人工填 0
                    attach_number = 0
                    attach_items = []

                # 提取 裝備資訊
                script = mmail_right.find('script', type="text/javascript")
                if script:
                    # 以 string 方式抽取元素內容，提取 JSON 字串
                    json_str = script.string.split('var dynjs_eqstore = ')[
                        1].rstrip('; \n')
                    # 解析 JSON 資料
                    data = json.loads(json_str)
                    # 解析每個項目的 HTML 內容
                    for key, value in data.items():
                        html_content = value['d']
                        soup = BeautifulSoup(html_content, 'html.parser')
                        equip_url_part1 = key
                        equip_name = value['t']
                        equip_url_part2 = value['k']
                        # equip_url = 'https://hentaiverse.org/equip/{}/{}'.format(
                        #     equip_url_part1, equip_url_part2)
                        equip_url = HENTAIVERSE_URL+'/equip/{}/{}'.format(
                            equip_url_part1, equip_url_part2)
                        equip_item = {equip_url: equip_name}
                        equip_dict.update(equip_item)

                attached_list_id = get_mm_read_send_max_id(
                    read_or_send, MM_Or_List.LIST)+1
                mm_No = get_mm_read_send_max_id(
                    read_or_send, MM_Or_List.MM)+1

                if read_or_send == Read_Or_Send.READ:
                    read_time = get_now_time()
                elif read_or_send == Read_Or_Send.SEND:
                    read_time = None

                mm_read_data: MM_Read_Send_Data = {
                    'mm_No': mm_No,
                    'mm_from': mm_from,
                    'mm_to': mm_to,
                    'subject': subject,
                    'sent_time': get_mm_send_time(mm_id),
                    'read_time': read_time,
                    'mm_id': int(mm_id),
                    'body_id': mm_No,
                    'cod_switch': cod_switch,
                    'cod_value': cod_value,
                    'attached_number': attach_number,
                    'attached_list_preview': attach_items,
                    'attached_list_id': attached_list_id,
                    'done_take': False,
                    'done_retrun': False
                }

                # attach dict 建立
                # 加入 id
                attached_list_data: MM_Read_Send_Attach_List_Data = {
                    'id': attached_list_id}
                # 動態創建dict
                for i, item in enumerate(attach_items, start=1):
                    attached_list_data[f'attached_item{i}'] = item
                # 填充剩餘的值為None
                for i in range(len(attach_items) + 1, 11):
                    attached_list_data[f'attached_item{i}'] = None

                # 通過 equip_name 比對並更新 attached_list_data
                for key, value in attached_list_data.items():
                    if key.startswith('attached_item') and value in equip_dict.values():
                        # 找到對應的 equip_url
                        equip_url = next(
                            url for url, name in equip_dict.items() if name == value)
                        key_value = '{}({})'.format(equip_name, equip_url)
                        attached_list_data[key] = key_value
                        del equip_dict[equip_url]

                # TODO 之後要追加整串的檢查機制，避免死在中間某個斷點
                if add_read_send_mm_info(read_or_send, mm_read_data):
                    add_read_send_mm_body(mm_No, read_or_send, bodytext)
                    add_read_send_mm_attach_list(
                        read_or_send, attached_list_data)
                return True

            else:
                logger.error('The account is in battle')
                return False
        else:
            logger.error('__init__ fail. code:{}'.format(
                response.status_code))
            return False

    def send_check(self, select_page: int = 0, max_read_page: int = MAX_READ_PAGE):
        """
        讀取已發出的 MM 資訊
        :param select_page: 
            - 0: 自動模式，從第0頁開始，遇到舊信或達到 max_read_page 停止。
            - >0: 指定頁數模式，只讀取該頁並更新資料，讀完即停止。
        """
        try:
            # 1. 載入現有資料 (List[Object])
            raw_objects = get_mm_send_list_info_all()

            # 2. 轉換為 Map (Dictionary) 作為主要操作對象
            # Key: mm_id, Value: 資料字典 (Dict)
            data_map = {}
            for obj in raw_objects:
                # 轉成 Dict
                item_dict = {}
                if hasattr(obj, 'dict'):
                    item_dict = obj.dict()
                elif hasattr(obj, 'model_dump'):
                    item_dict = obj.model_dump()
                else:
                    item_dict = obj.__dict__
                # *** 強制將 ID 轉為字串 (避免 String/Int 導致的重複) ***
                str_id = str(item_dict[MM_Send_Mail_List.mm_id])

                # 確保 ID 欄位本身也是字串格式
                item_dict[MM_Send_Mail_List.mm_id] = str_id

                # 放入 Map (如果 CSV 原本就有重複，這裡會自動去重，只留最後一筆)
                data_map[str_id] = item_dict

            has_changes = False
            page = select_page
            stop_paging = False

            # 判斷模式
            is_specified_page_mode = (select_page != 0)

            while not stop_paging:
                logger.info(f"Scanning Send MM Page: {page}")
                current_url = f"{self.mm_send_mail_url}&page={page}"

                response = requests.get(current_url, cookies=self.cookies)

                if response.status_code != 200:
                    logger.error(
                        f'inbox_check fail. code:{response.status_code}')
                    return False

                if not check_battle_status(response):
                    logger.error('The account is in battle')
                    return False

                # logger.info('The account not in battle')
                soup = BeautifulSoup(response.text, 'html.parser')
                outer_div = soup.find('div', id='mmail_outerlist')

                if not outer_div:
                    logger.critical("No div with id 'mmail_outerlist' found.")
                    return False

                table = outer_div.find('table', id='mmail_list')
                divs = table.find_all('div')
                divs_str = ''.join(str(div) for div in divs)

                # 檢查 No New Mail
                if "<div>No New Mail</div>" in divs_str:
                    logger.info("No more mails found (End of list).")
                    break

                rows = table.find_all('tr')

                for row in rows:
                    onclick_attr = row.get('onclick')
                    columns = row.find_all('td')

                    if onclick_attr and columns:
                        mm_url = re.search(
                            r"document\.location='(.*?)'", onclick_attr).group(1)
                        current_mm_id = str(get_mm_id(mm_url))

                        # 時間轉換
                        raw_sent_time = columns[2].text.strip()
                        raw_read_time = columns[3].text.strip()
                        iso_sent_time = convert_to_iso(raw_sent_time)
                        iso_read_time = convert_to_iso(raw_read_time)

                        new_mm_info = {
                            MM_Send_Mail_List.mm_to: columns[0].text.strip(),
                            MM_Send_Mail_List.subject: columns[1].text.strip(),
                            MM_Send_Mail_List.sent_time: iso_sent_time,
                            MM_Send_Mail_List.read_time: iso_read_time,
                            MM_Send_Mail_List.mm_id: current_mm_id,
                            MM_Send_Mail_List.done_read: False
                        }

                        if current_mm_id in data_map:
                            # --- [舊資料更新邏輯] ---
                            existing_record = data_map[current_mm_id]
                            # 比對 read_time
                            if existing_record[MM_Send_Mail_List.read_time] != iso_read_time:
                                logger.info(
                                    f"Updating read_time for ID: {current_mm_id}")
                                # 直接覆蓋，確保是最新的
                                data_map[current_mm_id] = new_mm_info
                                has_changes = True

                            # 自動模式：遇到舊資料就停止
                            # if not is_specified_page_mode:
                            #     logger.info(
                            #         f"Found existing ID: {current_mm_id}. Stopping pagination.")
                            #     stop_paging = True
                            #     break
                        else:
                            # --- [新資料新增邏輯] ---
                            data_map[current_mm_id] = new_mm_info
                            has_changes = True

                # --- [翻頁控制] ---
                if stop_paging:
                    break

                # 指定頁數模式：讀完這一頁就強制結束
                if is_specified_page_mode:
                    logger.info(
                        f"Finished scanning specified page {select_page}.")
                    break

                # 自動模式：檢查最大頁數
                if page >= max_read_page:
                    stop_paging = True
                    break

                page += 1
                time.sleep(0.2)

            # 3. 儲存資料
            if has_changes:
                # 將 Map 轉回 List
                final_data_list = list(data_map.values())

                # *** 排序修正 ***
                # key: 依照 sent_time 排序
                # reverse=False (預設): 升序 (小->大)，即 舊->新，新的在最下面
                final_data_list.sort(
                    key=lambda x: x[MM_Send_Mail_List.sent_time], reverse=False)
                if save_mm_send_list_all(final_data_list):
                    return True
                else:
                    return False
            else:
                logger.info("No data changed.")
                return True

        except Exception as e:
            print("遇到錯誤：", e)
            print("完整錯誤追蹤：")
            print(traceback.format_exc())
            return False

    def read_send_mm(self):
        """
        讀取send並讀取還沒讀取的send MM

        """

        try:
            self.send_check()
            unread_mm_list = read_send_mm_info_unread()
            for mm_list in unread_mm_list:
                mm_id = mm_list.mm_id
                if self.read_mm(mm_id, Read_Or_Send.SEND):
                    update_done_read(mm_id, Read_Or_Send.SEND)
            read_time_never_list = get_send_mm_info_read_time_never()

            # 檢查還未讀取的
            for read_time_never in read_time_never_list:
                read_page = read_time_never // 20
                if read_page > 0:
                    self.send_check(read_page)

        except Exception as e:
            print("遇到錯誤：", e)
            print("完整錯誤追蹤：")
            print(traceback.format_exc())

    def read_inbox_mm(self):
        """
        讀取inbox並讀取還沒讀取的inbox MM

        """

        try:
            self.inbox_check()
            unread_mm_list = read_inbox_mm_info_unread()
            for mm_list in unread_mm_list:
                mm_id = mm_list.mm_id
                if self.read_mm(mm_id, Read_Or_Send.READ):
                    update_done_read(mm_id, Read_Or_Send.READ)

            return unread_mm_list

        except Exception as e:
            print("遇到錯誤：", e)
            print("完整錯誤追蹤：")
            print(traceback.format_exc())

    def take_mm_by_mm_id(self, mm_id: str) -> bool:
        """
        輸入 mm_id 來收下 MM

        TODO take 紀錄要做

        """

        # mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=' + \
        #     str(mm_id)
        mm_url = HENTAIVERSE_URL+'/?s=Bazaar&ss=mm&filter=inbox&mid=' + \
            str(mm_id)

        response = requests.get(mm_url, cookies=self.cookies)

        if response.status_code == 200:
            # 檢查是否在戰鬥狀態
            if check_battle_status(response):
                # 使用正則表達式提取 mmtoken
                self.mmtoken = re.search(
                    r'<input type="hidden" name="mmtoken" value="(.*?)" />', response.text).group(1)
                # logger.info('get mm_token:{}'.format(self.mmtoken))
            else:
                logger.error('The account is in battle')
                return False
        else:
            logger.error('take mm fail. code:{}'.format(
                response.status_code))
            return False

        payload = {
            "mmtoken": self.mmtoken,
            "action": 'attach_remove',
            "action_value": 0,
        }

        response = requests.post(mm_url, data=payload, cookies=self.cookies)
        logger.info(f'take mm_id:{mm_id}')

        return check_after_post(response,  inspect.currentframe().f_code.co_name, mm_url)

    def take_mm_all_not_cod_and_return_cod_mm(self) -> bool:
        """
        順序取所有不是 CoD 的 MM，並退回帶 CoD 的 MM
        """
        read_mm_list = get_mm_read_info_all()
        for read_mm in read_mm_list:
            if read_mm.cod_switch == False and read_mm.done_take == False:
                self.take_mm_by_mm_id(read_mm.mm_id)
                update_done_take(read_mm.mm_id)
            elif read_mm.cod_switch == True:
                self.return_or_recall_mm(read_mm.mm_id)
                update_done_retrun(read_mm.mm_id)

    def return_or_recall_mm(self, mm_id: str) -> bool:
        """
        輸入 mm_id 做 return 或 recall
        PS:實際上共用

        """
        # mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=' + \
        #     str(mm_id)
        mm_url = HENTAIVERSE_URL+'/?s=Bazaar&ss=mm&filter=inbox&mid=' + \
            str(mm_id)

        MoogleMail.get_mm_token(self)

        payload = {
            "mmtoken": self.mmtoken,
            "action": 'return_message',
            "action_value": 0,
        }

        response = requests.post(mm_url, data=payload, cookies=self.cookies)
        logger.warning(f'mm_id:{mm_id}')

        return check_after_post(response, inspect.currentframe().f_code.co_name, mm_url)

# TODO
    def del_inbox_mm_info():
        pass

    def equip_lock_or_unlock(self, lock_or_unlock: Lock_Or_Unlock, equip_id: int):
        """
        解除或鎖定裝備狀態
        """
        # url = "https://hentaiverse.org/json"
        url = HENTAIVERSE_URL+"/json"

        MoogleMail.get_simple_token(self)

        data = {
            "type": "simple",
            "method": "lockequip",
            "uid": self.user_uid,
            "token": self.simple_token,
            "eid": equip_id,
            "lock": lock_or_unlock.value
        }

        response = requests.post(url, cookies=self.cookies, json=data)

        if check_after_post(response, inspect.currentframe().f_code.co_name):
            # 檢查 response.text 是否包含特定的 JSON 回應
            expected_response = '{{"eid":{},"locked":{}}}'.format(
                equip_id, lock_or_unlock.value)
            if lock_or_unlock == Lock_Or_Unlock.LOCK:
                lock_or_unlock_string = 'lock'
            elif lock_or_unlock == Lock_Or_Unlock.UNLOCK:
                lock_or_unlock_string = 'unlock'

            if response.text == expected_response:
                logger.info('equip_lock_or_unlock succeed:{} {}'.format(
                    lock_or_unlock_string, equip_id))
            else:
                logger.warning('equip_lock_or_unlock fail:{} {}'.format(
                    lock_or_unlock_string, equip_id))

            return True

        else:
            return False

    def get_simple_token(self) -> bool:
        response = requests.get(self.mm_write_url, cookies=self.cookies)
        if response.status_code == 200:
            # 檢查是否在戰鬥狀態
            if check_battle_status(response):
                # 使用正則表達式提取 mmtoken
                self.simple_token = re.search(
                    r'var simple_token = "([^"]+)";', response.text).group(1)
                logger.info('get simple_token:{}'.format(self.simple_token))
                return True
            else:
                logger.error('The account is in battle')
                return False
        else:
            logger.error('get_simple_token fail code:{}'.format(
                response.status_code))
            return False

    def get_mm_token(self) -> bool:
        response = requests.get(self.mm_write_url, cookies=self.cookies)
        if response.status_code == 200:
            # 檢查是否在戰鬥狀態
            if check_battle_status(response):
                # 使用正則表達式提取 mmtoken
                self.mmtoken = re.search(
                    r'<input type="hidden" name="mmtoken" value="(.*?)" />', response.text).group(1)
                logger.info('get mm_token:{}'.format(self.mmtoken))
                return True
            else:
                logger.error('The account is in battle')
                return False
        else:
            logger.error('get_mm_token fail code:{}'.format(
                response.status_code))
            return False

    def write_new(self) -> bool:
        """
        新MM撰寫初始化，獲取mmtoken
        """
        # 先丟掉原本的信件內容
        if not MoogleMail.discard(self):
            logger.error('write_new fail')
            return False
        # 取得 token
        elif not MoogleMail.get_mm_token(self):
            logger.error('write_new fail')
            return False
        else:
            return True

    def set_cod(self, CoD_value: int) -> bool:
        payload = {
            'mmtoken': self.mmtoken,
            'action': 'attach_cod',
            'action_value': CoD_value,
            'select_item': 0,
            'select_count': 0,
            'select_pane': 0,
            'message_to_name': '',
            'message_subject': '',
            'message_body': ''
        }

        response = requests.post(
            self.mm_write_url, data=payload, cookies=self.cookies)

        return check_after_post(response,  inspect.currentframe().f_code.co_name)

    def attach_add_item(self, item_id: int, item_number: int) -> bool:
        payload = {
            'mmtoken': self.mmtoken,
            'action': 'attach_add',
            'action_value': '0',
            'select_item': item_id,
            'select_count': item_number,
            'select_pane': 'item',
            'message_to_name': '',
            'message_subject': '',
            'message_body': ''
        }
        response = requests.post(
            self.mm_write_url, data=payload, cookies=self.cookies)

        return check_after_post(response, inspect.currentframe().f_code.co_name)

    def attach_add_credits(self, credits_number: int) -> bool:
        payload = {
            'mmtoken': self.mmtoken,
            'action': 'attach_add',
            'action_value': '0',
            'select_item': '0',
            'select_count': credits_number,
            'select_pane': 'credits',
            'message_to_name': '',
            'message_subject': '',
            'message_body': ''
        }
        response = requests.post(
            self.mm_write_url, data=payload, cookies=self.cookies)

        return check_after_post(response, inspect.currentframe().f_code.co_name)

    def attach_add_hath(self, hath_number: int) -> bool:
        payload = {
            'mmtoken': self.mmtoken,
            'action': 'attach_add',
            'action_value': '0',
            'select_item': '0',
            'select_count': hath_number,
            'select_pane': 'hath',
            'message_to_name': '',
            'message_subject': '',
            'message_body': ''
        }
        response = requests.post(
            self.mm_write_url, data=payload, cookies=self.cookies)

        return check_after_post(response, inspect.currentframe().f_code.co_name)

    def send(self, rcpt: str, subject: str, body: str) -> bool:
        if rcpt is None:
            logger.critical('rcpt is None')
        elif subject is None:
            logger.critical('subject is None')
        else:
            payload = {
                'mmtoken': self.mmtoken,
                'action': 'send',
                'action_value': '0',
                'select_item': '0',
                'select_count': '0',
                'select_pane': '0',
                'message_to_name': rcpt,
                'message_subject': subject,
                'message_body': body
            }
            response = requests.post(
                self.mm_write_url, data=payload, cookies=self.cookies)

            return check_after_post(response, inspect.currentframe().f_code.co_name)

    def discard(self) -> bool:
        """
        相write new的內容通通清掉
        """
        payload = {
            'mmtoken': self.mmtoken,
            'action': 'discard',
            'action_value': '0',
            'select_item': '0',
            'select_count': '0',
            'select_pane': '0',
            'message_to_name': '',
            'message_subject': '',
            'message_body': ''
        }
        response = requests.post(
            self.mm_write_url, data=payload, cookies=self.cookies)

        return check_after_post(response, inspect.currentframe().f_code.co_name)


def check_item_list(item_list: List[ItemDict]) -> List[ItemDict]:
    """
    檢查是否有不在item list上的item，假如有錯誤則略過
    """
    send_item_list = []
    for item_unit in item_list:
        # 將 item_name 和 item_dict 的鍵都轉換為小寫進行比較
        if not item_unit['item_name'].lower() in (key.lower() for key in item_dict.keys()):
            logger.error('the item:{} is not in item list, will ignore this item'.format(
                item_unit['item_name']))
        else:
            send_item_list.append(item_unit)

    return send_item_list


def add_mm_task(item_list: List[ItemDict], user_id: str, subject: str, body_text: str) -> bool:
    """
    檢查item_list後，將發送訊息轉換為task進行儲存
    """
    try:
        send_item_list = check_item_list(item_list)
        taskmanager = TaskManager()
        temp_data = {
            "user_id": user_id,
            "subject": subject,
            "body_text": body_text,
            "data": send_item_list}
        taskmanager.create_tasks(temp_data)

        return True
    except ValueError as e:
        logger.critical('add mm task error:{}'.format(e))
        return False


def check_pending_mm() -> bool:
    """
    有pending的MM則回應true
    """
    task_manager_csv_path = os.path.join(csv_folder_path, 'task_manager.csv')
    headers = ['SN', 'creat_time', 'end_time', 'json_data_name']
    csv_tools.check_csv_exists(task_manager_csv_path, headers)
    incomplete_tasks = 0
    with open(task_manager_csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if not row['end_time']:
                incomplete_tasks += 1
    if incomplete_tasks == 0:
        return False
    else:
        return True


def send_mm_with_item() -> bool:
    """
    發送task的MM
    """
    taskmanager = TaskManager()
    pending_tasks = taskmanager.list_pending_tasks()
    task_ids = [task.task_id for task in pending_tasks]

    for task_id in task_ids:

        mm_lib = MoogleMail(get_cookie())
        task_data = taskmanager.get_task(task_id).to_dict()

        try:
            # 檢查是不是在戰鬥中
            if not mm_lib.check_status():
                logger.error('The account is in battle')
                return False

            elif mm_lib.write_new():
                mm_lib.discard()
                rcpt: str = task_data['user_id']
                subject_text: str = task_data['subject']
                body_text: str = task_data['body_text']

                for send_item in task_data['data']:
                    if not mm_lib.attach_add_item(
                            item_dict[send_item['item_name'].lower()], send_item['item_number']):
                        break
                    time.sleep(0.5)
                if mm_lib.send(rcpt, subject_text, body_text):
                    taskmanager.complete_task(task_id)
                time.sleep(1)

                return True

        except ValueError as e:
            logger.critical('setting value issye')
            logger.critical(e)

            return False


class TaskManager:
    def __init__(self):
        self.task_manager_csv_path = os.path.join(
            csv_folder_path, 'task_manager.csv')
        headers = ['SN', 'creat_time', 'end_time', 'json_data_name']
        csv_tools.check_csv_exists(self.task_manager_csv_path, headers)
        self.tasks = self.load_tasks()

    def load_tasks(self) -> List[TaskItem]:
        tasks = []
        try:
            with open(self.task_manager_csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # task_id = int(row['SN'])
                    task_json_file_path = os.path.join(
                        json_folder_path, row['json_data_name'])
                    with open(task_json_file_path, 'r', encoding='utf-8') as json_file:
                        task_data = json.load(json_file)
                        task = TaskItem(**task_data)
                        tasks.append(task)
        except FileNotFoundError as e:
            logger.error('FileNotFoundError:{}'.format(e))
        return tasks

    def save_task_to_csv(self, task: TaskItem):
        """
        建立新task資料到csv檔案
        """
        with open(self.task_manager_csv_path, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([task.task_id, get_datetime_now_isoformat(), '',
                            'task_{}.json'.format(task.task_id)])

    def save_task_to_json(self, task: TaskItem):
        """
        建立新item資訊的json
        """
        json_file_path = os.path.join(
            json_folder_path, 'task_{}.json'.format(task.task_id))
        with open(json_file_path, 'w', encoding='utf-8') as file:
            json.dump(task.to_dict(), file, ensure_ascii=False, indent=4)

    def update_task_in_csv(self, task: TaskItem):
        rows = []
        headers = []
        with open(self.task_manager_csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            headers = reader.fieldnames
            for row in reader:
                if int(row['SN']) == task.task_id:
                    row['end_time'] = get_datetime_now_isoformat()
                rows.append(row)

        with open(self.task_manager_csv_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    def create_tasks(self, tasks_info: List[ItemDict]):
        """
        建立task，且會以10筆為單位進行task切割
        """
        last_sn = 0
        if self.tasks:
            last_sn = self.tasks[-1].task_id

        # Split tasks_info into chunks of 10 items each
        for i in range(0, len(tasks_info['data']), 10):
            chunk = tasks_info['data'][i:i + 10]
            task_id = last_sn + 1
            last_sn += 1
            task = TaskItem(task_id, tasks_info['user_id'],
                            tasks_info['subject'], tasks_info['body_text'], chunk)
            self.tasks.append(task)
            self.save_task_to_csv(task)
            self.save_task_to_json(task)

    def complete_task(self, task_id: int):
        for task in self.tasks:
            if task.task_id == task_id:
                task.status = 'Finish'
                break
        self.save_task_to_json(task)
        self.update_task_in_csv(task)

    def list_pending_tasks(self):
        return [task for task in self.tasks if task.status == 'Pending']

    def get_task(self, task_id: int):
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
