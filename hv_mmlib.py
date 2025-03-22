import requests
import configparser
import os
import csv
import re
import logging
import datetime
import json
import sys
from typing import List, Dict, TypedDict
import csv_tools
from bs4 import BeautifulSoup
from lxml import etree
import time
import hv_equiplib
import inspect
import enum


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
        logging.warning(f"資料夾 '{folder_Path}' 已建立。")


# 設定 logging
Log_Mode = config.get('Log', 'Log_Mode')
Log_Format = '%(asctime)s | %(filename)s | %(funcName)s | %(levelname)s:%(message)s'
log_file_path = os.path.join(
    current_directory, 'log', 'hv_mmlib.log')
logging.basicConfig(level=getattr(logging, Log_Mode.upper()),
                    format=Log_Format,
                    handlers=[logging.FileHandler(log_file_path, 'a', 'utf-8'),
                              logging.StreamHandler()])


class CookieDict(TypedDict):
    ipb_member_id: str
    ipb_pass_hash: str
    ipb_session_id: str


class CookieKeys(enum.Enum):
    IPB_MEMBER_ID = 'ipb_member_id'
    IPB_PASS_HASH = 'ipb_pass_hash'
    IPB_SESSION_ID = 'ipb_session_id'


class ItemDict(TypedDict):
    item_name: str
    item_number: int


class TaskItem_to_dict(TypedDict):
    task_id: int
    user_id: str
    subject: str
    body_text: str
    data: List[ItemDict]
    status: str


class MM_Inbox_Data(TypedDict):
    mm_from: str
    subject: str
    sent_time: str
    mm_id: int


class MM_Read_Send_Data(TypedDict):
    mm_No: int
    mm_from: str
    mm_to: str
    subject: int
    sent_time: str
    read_time: str
    mm_id: int
    body_id: str
    cod_switch: bool
    cod_value: int
    attached_number: int
    attached_list_preview: list
    attached_list_id: int


class MM_Read_Send_Attach_List_Data(TypedDict):
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


class Read_Or_Send(enum.Enum):
    READ: str = 'read'
    SEND: str = 'send'


class MM_Or_List(enum.Enum):
    MM: str = 'mm'
    LIST: str = 'list'


class Lock_Or_Unlock(enum.Enum):
    LOCK: int = 1
    UNLOCK: int = 0


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


def get_isoformat():
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


def get_item_inventory() -> List:
    """
    取得當前道具清單與數量
    """

    url = 'https://hentaiverse.org/?s=Character&ss=it'
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
                logging.critical('can not found item table')
                return False

        else:
            logging.error('{} Fail. code:get_item_inventory text:{}'.format(
                response.status_code, response.text))
            return False

    else:
        logging.error('The account is in battle')
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
        logging.critical("No mid parameter found in the URL")
        return 0


def get_mm_send_time(mm_id: int) -> str:
    """
    從 mm_inbox.csv 取得 send_time

    """
    mm_inbox_file_path = os.path.join(csv_folder_path, 'mm_inbox.csv')

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
    從 mm_read.csv、mm_send.csv、mm_read_list.csv、mm_send_list.csv 得取當前最大 id 值

    input:
        read_or_send:read or send
        mm_or_list:mm or list

    """
    if read_or_send == Read_Or_Send.READ:
        if mm_or_list == MM_Or_List.LIST:
            mm_file_path = os.path.join(
                csv_folder_path, 'mm_read_attach_list.csv')
        elif mm_or_list == MM_Or_List.MM:
            mm_file_path = os.path.join(
                csv_folder_path, 'mm_read.csv')

    elif read_or_send == Read_Or_Send.SEND:
        if mm_or_list == MM_Or_List.LIST:
            mm_file_path = os.path.join(
                csv_folder_path, 'mm_send_attach_list.csv')
        elif mm_or_list == MM_Or_List.MM:
            mm_file_path = os.path.join(
                csv_folder_path, 'mm_send.csv')

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
        logging('read_or_send input error,read_or_send:{},mm_or_list:{}'.format(
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
        logging.critical(
            'read_or_send input error,read_or_send:{}'.format(read_or_send))
        return False

    try:
        with open(mm_body_file_path, mode='w', encoding='utf-8') as file:
            file.write(body_text)
        return True

    except Exception as e:
        logging.critical('Error: {}'.format(e))
        return False


def add_read_send_mm_attach_list(read_or_send: Read_Or_Send, mm_read_send_attach_list_data: List[MM_Read_Send_Attach_List_Data]) -> bool:
    """
    追加 read、send 資訊

    input:
        read_or_send:輸入read或是send，決定模式
        mm_read_send_attach_list_data:read與send格式共用
    """

    if read_or_send == Read_Or_Send.READ:
        mm_file_path = os.path.join(csv_folder_path, 'mm_read_attach_list.csv')
    elif read_or_send == Read_Or_Send.SEND:
        mm_file_path = os.path.join(csv_folder_path, 'mm_send_attach_list.csv')
    else:
        logging.critical('read_or_send input error')
        return False

    header = ['id', 'attached_item1', 'attached_item2', 'attached_item3', 'attached_item4', 'attached_item5',
              'attached_item6', 'attached_item7', 'attached_item8', 'attached_item9', 'attached_item10']
    csv_tools.check_csv_exists(mm_file_path, header)

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
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writerows(mm_read_send_attach_list_data)
    return True


def add_read_send_mm_info(read_or_send: Read_Or_Send, mm_read_send_data: List[MM_Read_Send_Data]) -> bool:
    """
    追加 read、send 資訊

    input:
        read_or_send:輸入read或是send，決定模式
        mm_read_send_data:read與send格式共用
    """

    if read_or_send == Read_Or_Send.READ:
        mm_file_path = os.path.join(csv_folder_path, 'mm_read.csv')
    elif read_or_send == Read_Or_Send.SEND:
        mm_file_path = os.path.join(csv_folder_path, 'mm_send.csv')
    else:
        logging.critical('read_or_send input error')
        return False

    header = ['mm_No', 'mm_from', 'subject', 'sent_time', 'read_time', 'mm_id',
              'body', 'cod_switch', 'cod_value', 'attached_number', 'attached_list']
    csv_tools.check_csv_exists(mm_file_path, header)

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
        mm_inbox_file_path = os.path.join(csv_folder_path, 'mm_inbox.csv')
        header = ['mm_from', 'subject', 'sent_time', 'mm_id']
        csv_tools.check_csv_exists(mm_inbox_file_path, header)

        # 讀取已存在的 mm_id
        existing_urls = set()
        try:
            with open(mm_inbox_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                headers = reader.fieldnames
                for row in reader:
                    existing_urls.add(row['mm_id'])
        except FileNotFoundError:
            pass

        # 過濾出尚未加入的資料
        new_data = [row for row in mm_inbox_data if row['mm_id']
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
        logging.critical('Error: {}'.format(e))
        return False


def check_after_post(response: requests, frame_name: str, mm_id: int = None) -> bool:

    # mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=' + mm_id
    if mm_id is not None:
        mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=' + mm_id
    else:
        mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox'

    if response.status_code == 200:
        if check_battle_status(response):
            logging.warning('{}:{} Success'.format(frame_name, mm_url))
            return True
        else:
            logging.error('The account is in battle')
            return False
    else:
        logging.error('{} Fail. code:{} text:{}'.format(
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
    def __init__(self, cookies: Dict[str, str]):
        self.mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm'
        self.mm_write_url = self.mm_url + '&filter=new'
        self.mm_inbox_url = self.mm_url + '&filter=inbox'
        self.cookies = cookies
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
                logging.info('The account not in battle')
                return True
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.error('check_status fail. code:{}'.format(
                response.status_code))
            return False

    def inbox_check(self) -> bool:
        """
        檢查inbox並取得inbox列表資訊(單封MM的URL、From、Subject、SentTime、ReadTime)
        並將新的MM資訊記錄在 mm_inbox.csv 中

        return:
            檢查成功會回應 true，失敗則 false

        TODO 只做到顯示，還沒做完
        """
        # 進行 GET 請求並附加 cookie
        response = requests.get(self.mm_inbox_url, cookies=self.cookies)

        if response.status_code == 200:
            # 檢查是否在戰鬥狀態
            if check_battle_status(response):
                logging.info('The account not in battle')

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

                                    mm_info: MM_Inbox_Data = {
                                        'mm_from': columns[0].text.strip(),
                                        'subject': columns[1].text.strip(),
                                        'sent_time': columns[2].text.strip(),
                                        'mm_id': get_mm_id(mm_url)
                                    }
                                    mm_inbox_list.append(mm_info)

                            if add_inbox_mm_info(mm_inbox_list):
                                return True
                            else:
                                logging.critical('add inbox mm info fail')
                                return False
                        else:
                            print("No tbody found in the table.")
                    else:
                        logging.info("No New Mail.")
                        return True
                else:
                    logging.critical("No div with id 'mmail_outerlist' found.")
                    return False
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.error('inbox_check fail. code:{}'.format(
                response.status_code))
            return False

    def read_mm(self, mm_id: str) -> bool:
        """
        輸入 mm_id 來讀取內容資料

        TODO 還沒做回傳與整理，裝備部分可以跟 hv_equiplib 串
        TODO 空白信件與attach關係處理
        """
        cod_switch: bool = False
        cod_value: int = 0

        mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=' + \
            str(mm_id)
        equip_dict = {}

        response = requests.get(mm_url, cookies=self.cookies)
        # print(response.text)
        if response.status_code == 200:
            # 檢查是否在戰鬥狀態
            if check_battle_status(response):
                logging.info('The account not in battle')
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
                if mmail_attachinfo:
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
                        equip_url = 'https://hentaiverse.org/equip/{}/{}'.format(
                            equip_url_part1, equip_url_part2)
                        equip_item = {equip_url: equip_name}
                        equip_dict.update(equip_item)

                attached_list_id = get_mm_read_send_max_id('read', 'list')+1
                mm_No = get_mm_read_send_max_id('read', 'mm')+1

                mm_read_data: MM_Read_Send_Data = {
                    'mm_No': mm_No,
                    'mm_from': mm_from,
                    'mm_to': mm_to,
                    'subject': subject,
                    'sent_time': get_mm_send_time(mm_id),
                    'read_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'mm_id': int(mm_id),
                    'body_id': mm_No,
                    'cod_switch': cod_switch,
                    'cod_value': cod_value,
                    'attached_number': attach_number,
                    'attached_list_preview': attach_items,
                    'attached_list_id': attached_list_id
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
                if add_read_send_mm_info('read', mm_read_data):
                    add_read_send_mm_body(mm_No, 'read', bodytext)
                    add_read_send_mm_attach_list('read', attached_list_data)

                return True

            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.error('__init__ fail. code:{}'.format(
                response.status_code))
            return False

    def take_mm(self, mm_id: str) -> bool:
        """
        輸入 mm_id 來收下 MM

        TODO take 紀錄要做

        """

        mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=' + \
            str(mm_id)

        response = requests.get(mm_url, cookies=self.cookies)

        if response.status_code == 200:
            # 檢查是否在戰鬥狀態
            if check_battle_status(response):
                # 使用正則表達式提取 mmtoken
                self.mmtoken = re.search(
                    r'<input type="hidden" name="mmtoken" value="(.*?)" />', response.text).group(1)
                logging.info('get mm_token:{}'.format(self.mmtoken))
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.error('take mm fail. code:{}'.format(
                response.status_code))
            return False

        payload = {
            "mmtoken": self.mmtoken,
            "action": 'attach_remove',
            "action_value": 0,
        }

        response = requests.post(mm_url, data=payload, cookies=self.cookies)

        return check_after_post(response,  inspect.currentframe().f_code.co_name, mm_url)

    def return_or_recall_mm(self, mm_id: str) -> bool:
        """
        輸入 mm_id 做 return 或 recall
        PS:實際上共用

        TODO 執行前要先做內容存檔
        """
        mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=' + \
            str(mm_id)

        MoogleMail.get_mm_token(self)

        payload = {
            "mmtoken": self.mmtoken,
            "action": 'return_message',
            "action_value": 0,
        }

        response = requests.post(mm_url, data=payload, cookies=self.cookies)

        return check_after_post(response, inspect.currentframe().f_code.co_name, mm_url)

# TODO
    def del_inbox_mm_info():
        pass

    def check_send_mm():
        pass

# TODO

    def equip_lock_or_unlock(self, lock_or_unlock: Lock_Or_Unlock, equip_id: int):
        """
        解除或鎖定裝備狀態
        """
        url = "https://hentaiverse.org/json"

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
                logging.info('equip_lock_or_unlock succeed:{} {}'.format(
                    lock_or_unlock_string, equip_id))
            else:
                logging.warning('equip_lock_or_unlock fail:{} {}'.format(
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
                logging.info('get simple_token:{}'.format(self.simple_token))
                return True
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.error('get_simple_token fail code:{}'.format(
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
                logging.info('get mm_token:{}'.format(self.mmtoken))
                return True
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.error('get_mm_token fail code:{}'.format(
                response.status_code))
            return False

    def write_new(self) -> bool:
        """
        新MM撰寫初始化，獲取mmtoken
        """
        # 先丟掉原本的信件內容
        if not MoogleMail.discard(self):
            logging.error('write_new fail')
            return False
        # 取得 token
        elif not MoogleMail.get_mm_token(self):
            logging.error('write_new fail')
            return False
        else:
            return True

        # # 進行 GET 請求並附加 cookie
        # response = requests.get(self.mm_write_url, cookies=self.cookies)
        # if response.status_code == 200:
        #     # 檢查是否在戰鬥狀態
        #     if check_battle_status(response):
        #         # 使用正則表達式提取 mmtoken
        #         self.mmtoken = re.search(
        #             r'<input type="hidden" name="mmtoken" value="(.*?)" />', response.text).group(1)
        #         logging.info('get mm_token:{}'.format(self.mmtoken))
        #         return True
        #     else:
        #         logging.error('The account is in battle')
        #         return False
        # else:
        #     logging.error('write_new fail. code:{}'.format(
        #         response.status_code))
        #     return False

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
            logging.critical('rcpt is None')
        elif subject is None:
            logging.critical('subject is None')
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
            logging.error('the item:{} is not in item list, will ignore this item'.format(
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
        logging.critical('add mm task error:{}'.format(e))
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
                logging.error('The account is in battle')
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
            logging.critical('setting value issye')
            logging.critical(e)

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
            logging.error('FileNotFoundError:{}'.format(e))
        return tasks

    def save_task_to_csv(self, task: TaskItem):
        """
        建立新task資料到csv檔案
        """
        with open(self.task_manager_csv_path, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([task.task_id, get_isoformat(), '',
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
                    row['end_time'] = get_isoformat()
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
