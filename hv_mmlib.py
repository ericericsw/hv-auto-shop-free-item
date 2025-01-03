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
import time


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


def get_cookie() -> Dict[str, str]:

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


class MoogleMail():
    def __init__(self, cookies: Dict[str, str]):
        self.mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm'
        self.mm_write_url = self.mm_url + '&filter=new'
        self.mm_inbox_url = self.mm_url + '&filter=inbox'
        # self.mm_write_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=new'
        self.cookies = cookies
        self.mmtoken = None

    def check_status(self):
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
            logging.error('__init__ fail. code:{}'.format(
                response.status_code))
            return False

    def inbox_check(self):
        """
        檢查inbox並取得inbox列表資訊(單封MM的URL、From、Subject、SentTime、ReadTime)
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
                    if table:
                        # mail_list = table.find('tbody')
                        mail_list = table
                        if mail_list:
                            rows = mail_list.find_all('tr')
                            for row in rows:
                                onclick_attr = row.get('onclick')
                                if onclick_attr:
                                    url = re.search(
                                        r"document\.location='(.*?)'", onclick_attr).group(1)
                                    print(f"URL: {url}")

                                columns = row.find_all('td')
                                if columns:
                                    from_ = columns[0].text.strip()
                                    subject = columns[1].text.strip()
                                    sent = columns[2].text.strip()
                                    read = columns[3].text.strip()
                                    print(f"From: {from_}, Subject: {
                                          subject}, Sent: {sent}, Read: {read}")
                        else:
                            print("No tbody found in the table.")
                    else:
                        print("No table with id 'mmail_list' found.")
                else:
                    print("No div with id 'mmail_outerlist' found.")

                return True
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.error('__init__ fail. code:{}'.format(
                response.status_code))
            return False

    def write_new(self):
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
            logging.error('__init__ fail. code:{}'.format(
                response.status_code))
            return False

    def attach_add_item(self, item_id: int, item_number: int):
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
                logging.info(
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

    def attach_add_credits(self, credits_number: int):
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
                logging.info(
                    'attach_add_credits {}*credits success'.format(credits_number))
                return True
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.warning(
                'attach_add_credits fail. code:'.format(response.status_code))
            return False

    def attach_add_hath(self, hath_number: int):
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
                logging.info(
                    'attach_add_hath {}*hath success'.format(hath_number))
                return True
            else:
                logging.error('The account is in battle')
                return False
        else:
            logging.warning(
                'attach_add_hath fail. code:'.format(response.status_code))
            return False

    def send(self, rcpt: str, subject: str, body: str):
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
                    logging.info('sent to {} success'.format(rcpt))
                    return True
                else:
                    logging.error('The account is in battle')
                    return False
            else:
                logging.warning(
                    'send fail. code:{}'.format(response.status_code))
                return False

    def discard(self):
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
            logging.warning(
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


def add_mm_task(item_list: List[ItemDict], user_id: str, subject: str, body_text: str):
    """
    檢查item_list後，將發送訊息轉換為task進行儲存
    """
    send_item_list = check_item_list(item_list)
    taskmanager = TaskManager()
    temp_data = {
        "user_id": user_id,
        "subject": subject,
        "body_text": body_text,
        "data": send_item_list}
    taskmanager.create_tasks(temp_data)


def check_pending_mm() -> bool:
    """
    有pending的MM則回應true
    """
    task_manager_csv_path = os.path.join(csv_folder_path, 'task_manager.csv')
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


def send_mm_with_item():
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

        except ValueError as e:
            logging.critical('setting value issye')
            logging.critical(e)


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


# ! 跳行方法仍不知道
# 跳行是'%0D%0A'
