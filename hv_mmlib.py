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
    mm_url: str


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


def get_cookie() -> CookieDict:

    cookies = {}
    ipb_member_uid_value = config.get('Account', 'HV_Free_Shop_UID')
    ipb_pass_hash_value = config.get('Account', 'ipb_pass_hash')
    ipb_session_id_value = config.get('Account', 'ipb_session_id')

    cookies = {
        'ipb_member_id': ipb_member_uid_value,
        'ipb_pass_hash': ipb_pass_hash_value,
        'ipb_session_id': ipb_session_id_value
    }

    return cookies


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
    check_battle_status = not (
        battle_token_exists or battle_new_exists)

    return check_battle_status


def add_inbox_mm_info(mm_inbox_data: List[MM_Inbox_Data]):
    """
    追加 inbox 資訊
    """

    try:
        mm_inbox_file_path = os.path.join(csv_folder_path, 'mm_inbox.csv')
        header = ['mm_from', 'subject', 'sent_time', 'mm_url']
        csv_tools.check_csv_exists(mm_inbox_file_path, header)

        # 讀取已存在的 mm_url
        existing_urls = set()
        try:
            with open(mm_inbox_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                headers = reader.fieldnames
                for row in reader:
                    existing_urls.add(row['mm_url'])
        except FileNotFoundError:
            pass

        # 過濾出尚未加入的資料
        new_data = [row for row in mm_inbox_data if row['mm_url']
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


class MoogleMail():
    def __init__(self, cookies: Dict[str, str]):
        self.mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm'
        self.mm_write_url = self.mm_url + '&filter=new'
        self.mm_inbox_url = self.mm_url + '&filter=inbox'
        # self.mm_write_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=new'
        self.cookies = cookies
        self.mmtoken = None

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
                                    # print(f"URL: {mm_url}")
                                    # from_ = columns[0].text.strip()
                                    # subject = columns[1].text.strip()
                                    # sent = columns[2].text.strip()
                                    # read = columns[3].text.strip()
                                    # print(f"From: {from_}, Subject: {
                                    #       subject}, Sent: {sent}, Read: {read},url: {mm_url}")

                                    mm_info: MM_Inbox_Data = {
                                        'mm_from': columns[0].text.strip(),
                                        'subject': columns[1].text.strip(),
                                        'sent_time': columns[2].text.strip(),
                                        'mm_url': mm_url
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

    def read_mm(self, mm_url: str):
        """
        輸入 mm_url 來讀取內容資料

        TODO 還沒做回傳與整理，裝備部分可以跟 hv_equiplib 串
        """
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
                print("mm_to:{}".format(mm_to))
                print("mm_from:{}".format(mm_from))
                print("subject:{}".format(subject))

                # 提取 MM body
                textarea_element = mmail_left.find('textarea')
                # print(textarea_element.get_text())
                bodytext = textarea_element.get_text()
                print('=============↓↓↓↓↓===body==↓↓↓↓↓=================')
                print(bodytext)
                print('=============↑↑↑↑↑===body==↑↑↑↑↑=================')

                # 提取 MM 右半邊資料
                mmail_right = soup.find('div', id="mmail_right")

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
                    print("抽取到的 attach_count:", attach_count_numbers)

                    # 抽取附件清單
                    attach_list = soup.select(
                        '#mmail_attachlist > div > div:first-child')
                    attach_items = [item.get_text() for item in attach_list]
                    print("抽取到的 attach_items:", attach_items)

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
                        # print(f"Item {key}:")
                        equip_url_part1 = key
                        # print(value['t'])
                        equip_name = value['t']
                        equip_url_part2 = value['k']
                        # print(value['k'])
                        print('equip_name:{}'.format(equip_name))
                        print('equip_url_part1:{}'.format(equip_url_part1))
                        print('equip_url_part2:{}'.format(equip_url_part2))
                        # print(equip_url_part2)
                        equip_url = 'https://hentaiverse.org/equip/{}/{}'.format(
                            equip_url_part1, equip_url_part2)
                        print('equip_url:{}'.format(equip_url))
                        print('---------------------------')
                    # https://hentaiverse.org/equip/300495653/798b293a94

                # mmail_attachpanes = mmail_right('mmail_attachpanes')
                # mmail_attachcount = mmail_attachlist.find('mmail_attachcount')
                # print(mmail_attachlist)
                # print(mmail_attachcount)
                # print(mmail_attachpanes)

                # for tr in trs:
                #     tr_element = soup.find('tr')
                #     # print(tr_element)
                #     tds = tr.find('td')
                #     for td in tds:
                #         print(td)
                #         input_element = td.find_all('input')
                #         print(input_element)
                # print(tds)

                # tr_element = soup.find(
                #     'tr', onclick="document.location='https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=2990465'")
                # # print(tr_element)
                # tds = tr_element.find_all('td')
                # mm_from = tds[0].text.strip()
                # subject = tds[1].text.strip()
                # sent_time = tds[2].text.strip()
                # read_time = tds[3].text.strip()
                # print('mm_from:{}'.format(mm_from))
                # print('subject:{}'.format(subject))
                # print('sent_time:{}'.format(sent_time))
                # print('read_time:{}'.format(read_time))

                # # 逐層選擇元素
                # # csp_div = soup.find('div', id='mmail_left')
                # csp_div = soup.find('form', id='mailform')
                # # csp_div = soup.find('div', id='mmail_outerlist')
                # if csp_div:
                #     print(csp_div.prettify())
                # mainpane_div = csp_div.find('div', id='mainpane')
                # print(mainpane_div)
                # csp = soup.find_all(id='mmail_left', recursive=True)
                # print(csp)
                # for cs in csp:
                #     print(cs.get_text())
                # if csp:
                #     table = csp.find(id='mainpane')
                #     print(table)
                #     if table:
                #         tbody = table.find('tbody')
                #         if tbody:
                #             # nth-child(1) 對應到索引 0
                #             tr = tbody.find_all('tr')[0]
                #             if tr:
                #                 # nth-child(2) 對應到索引 1
                #                 td = tr.find_all('td')[1]
                #                 if td:
                #                     input_element = td.find(
                #                         'input', {'type': 'text'})
                #                     print("抓取到的元素:", input_element)
                # element2 = soup.select(
                #     '#mmail_left > #mainpane')

                # # 打印結果
                # print("element", element)
                # print("element2", element2)
                # print("csp:", csp)
                # print("mm_to:", mm_to)
                # print("mm_from:", mm_from)
                # print("subject:", subject)
                # print("body_text:", body_text)
                # print("number_of_attached:", number_of_attached)
                # print("attached_list:", attached_list)

                return True

            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.error('__init__ fail. code:{}'.format(
                response.status_code))
            return False

    def take_mm(self, mm_url: str) -> bool:
        """
        輸入 mm_url 來收下 MM

        TODO take 紀錄要做

        """

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

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6,zh-CN;q=0.5",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        }

        data = {
            "mmtoken": self.mmtoken,
            "action": 'attach_remove',
            "action_value": 0,
        }

        response = requests.post(mm_url, headers=headers,
                                 data=data, cookies=self.cookies)

        if response.status_code == 200:
            if check_battle_status(response):
                logging.warning('Take MM:{} Success'.format(mm_url))
                return True
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.error('take mm fail. code:{}'.format(
                response.status_code))
            return False

    def return_mm(self, mm_url: str) -> bool:
        """
        輸入 mm_url 退回 MM
        """

    def write_new(self) -> bool:
        """
        新MM撰寫初始化，獲取mmtoken
        """
        # 進行 GET 請求並附加 cookie
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
            logging.error('write_new fail. code:{}'.format(
                response.status_code))
            return False

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

        if response.status_code == 200:
            if check_battle_status(response):
                logging.warning(
                    'attach_add_item {}*{} success'.format(item_number, reversed_dict[item_id]))
                return True
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.warning(
                'attach_add_item fail. code:'.format(response.status_code))
            logging.warning(response.text)
            return False

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
        if response.status_code == 200:
            if check_battle_status(response):
                logging.warning(
                    'attach_add_credits {}*credits success'.format(credits_number))
                return True
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.warning(
                'attach_add_credits fail. code:'.format(response.status_code))
            return False

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
        if response.status_code == 200:
            if check_battle_status(response):
                logging.warning(
                    'attach_add_hath {}*hath success'.format(hath_number))
                return True
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.error(
                'attach_add_hath fail. code:'.format(response.status_code))
            return False

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
            if response.status_code == 200:
                if check_battle_status(response):
                    logging.warning('sent to {} success'.format(rcpt))
                    return True
                else:
                    logging.error('The account is in battle')
                    return False
            else:
                logging.error(
                    'send fail. code:{}'.format(response.status_code))
                return False

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
        if response.status_code == 200:
            if check_battle_status(response):
                logging.info('mm discard')
                return True
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.error(
                'discard fail. code:{}'.format(response.status_code))
            return False


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
            writer.writerow([task.task_id, datetime.datetime.now(
            ).isoformat(), '', 'task_{}.json'.format(task.task_id)])

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
                    row['end_time'] = datetime.datetime.now().isoformat()
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
