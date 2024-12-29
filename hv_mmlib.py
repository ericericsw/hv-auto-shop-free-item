import requests
import configparser
import os
import csv
import re
import logging

# 創建 ConfigParser 對象
config = configparser.ConfigParser()
# 讀取配置文件
config.read('config.ini')

current_directory = os.path.dirname(os.path.abspath(__file__))
csv_folder_path = os.path.join(current_directory, 'csv')
log_folder_path = os.path.join(current_directory, 'log')


def check_folder_path_exists(folder_Path: os.path):
    if not os.path.exists(folder_Path):
        os.makedirs(folder_Path)
        logging.warning(f"資料夾 '{folder_Path}' 已建立。")


check_folder_path_exists(log_folder_path)
check_folder_path_exists(csv_folder_path)


# 設定 logging
Log_Mode = config.get('Log', 'Log_Mode')
Log_Format = '%(asctime)s | %(filename)s | %(funcName)s | %(levelname)s:%(message)s'
log_file_path = os.path.join(
    current_directory, 'log', 'hv_mmlib.log')
logging.basicConfig(level=getattr(logging, Log_Mode.upper()),
                    format=Log_Format,
                    handlers=[logging.FileHandler(log_file_path, 'a', 'utf-8'),
                              logging.StreamHandler()])

item_dict = {
    # Restoratives
    'health draught': 11191,
    'health potion': 11195,
    'health elixir': 11199,
    'mana draught': 11291,
    'mana potion': 11295,
    'mana elixir': 11299,
    'spirit draught': 11391,
    'spirit potion': 11395,
    'spirit elixir': 11399,
    'last elixir': 11501,
    # infusion
    'infusion of flames': 12101,
    'infusion of frost': 12201,
    'infusion of lightning': 12301,
    'infusion of storms': 12401,
    'infusion of divinity': 12501,
    'infusion of darkness': 12601,
    # scroll
    'scroll of swiftness': 13101,
    'scroll of protection': 13111,
    'scroll of avatar': 13199,
    'scroll of absorption': 13201,
    'scroll of shadows': 13211,
    'scroll of life': 13221,
    'scroll of gods': 13299,
    # Special
    'flower vase': 19111,
    'bubble-gum': 19131,
    # Trophy
    'manBearPig tail': 30016,
    'holy hand hrenade of antioch': 30017,
    "mithra's flower": 30018,
    'dalek voicebox': 30019,
    'lock of blue hair': 30020,
    'bunny-girl costume': 30021,
    'hinamatsuri doll': 30022,
    'broken glasses': 30023,
    'sapling': 30030,
    'noodly appendage': 30032,
    # crystal
    'crystal of vigor': 50001,
    'crystal of finesse': 50002,
    'crystal of swiftness': 50003,
    'crystal of fortitude': 50004,
    'crystal of cunning': 50005,
    'crystal of knowledge': 50006,
    'crystal of flames': 50011,
    'crystal of frost': 50012,
    'crystal of lightning': 50013,
    'crystal of tempest': 50014,
    'crystal of devotion': 50015,
    'crystal of corruption': 50016,
    # Food
    'monster chow': 51001,
    'monster edibles': 51002,
    'monster cuisine': 51003,
    'happy pills': 51011,
    # Materials
    'low-grade cloth': 60001,
    'mid-grade cloth': 60002,
    'high-grade cloth': 60003,
    'low-grade leather': 60004,
    'mid-grade leather': 60005,
    'high-grade leather': 60006,
    'low-grade metals': 60007,  # why only metal is plural type?
    'mid-grade metals': 60008,
    'high-grade metals': 60009,
    'low-grade wood': 60010,
    'mid-grade wood': 60011,
    'high-grade wood': 60012,
    'scrap cloth': 60051,
    'scrap leather': 60052,
    'scrap metal': 60053,
    'scrap wood': 60054,
    'energy cell': 60071,
    'crystallized phazon': 60101,
    'shade fragment': 60102,
    'repurposed actuator': 60104,
    'defense matrix modulator': 60105,
    'binding of slaughter': 60201,
    'binding of balance': 60202,
    'binding of destruction': 60203,
    'binding of focus': 60204,
    'binding of protection': 60205,
    'binding of the fleet': 60206,
    'binding of the barrier': 60207,
    'binding of the nimble': 60208,
    'binding of the elementalist': 60209,
    'binding of the heaven-sent': 60210,
    'binding of the demon-fiend': 60211,
    'binding of the curse-weaver': 60212,
    'binding of the earth-walker': 60213,
    'binding of surtr': 60215,
    'binding of niflheim': 60216,
    'binding of mjolnir': 60217,
    'binding of freyr': 60218,
    'binding of heimdall': 60219,
    'binding of fenrir': 60220,
    'binding of dampening': 60221,
    'binding of stoneskin': 60222,
    'binding of deflection': 60223,
    'binding of the fire-eater': 60224,
    'binding of the frost-born': 60225,
    'binding of the thunder-child': 60226,
    'binding of the wind-waker': 60227,
    'binding of the thrice-blessed': 60228,
    'binding of the spirit-ward': 60229,
    'binding of the ox': 60230,
    'binding of the raccoon': 60231,
    'binding of the cheetah': 60232,
    'binding of the turtle': 60233,
    'binding of the fox': 60234,
    'binding of the owl': 60235,
    'binding of warding': 60236,
    'binding of negation': 60237,
    'binding of isaac': 60238,
    'binding of friendship': 60239,
    'legendary weapon core': 60402,
    'legendary staff core': 60412,
    'legendary armor core': 60422,
    'voidseeker shard': 61001,
    'aether shard': 61101,
    'featherweight shard': 61501,
    'amnesia shard': 65001,
    # figurine
    'twilight sparkle figurine': 70001,
    'rainbow dash figurine': 70002,
    'applejack figurine': 70003,
    'fluttershy figurine': 70004,
    'pinkie pie figurine': 70005,
    'rarity figurine': 70006,
    'trixie figurine': 70007,
    'princess celestia figurine': 70008,
    'princess luna figurine': 70009,
    'apple bloom figurine': 70010,
    'scootaloo figurine': 70011,
    'sweetie belle figurine': 70012,
    'big macintosh figurine': 70013,
    'spitfire figurine': 70014,
    'derpy hooves figurine': 70015,
    'lyra heartstrings figurine': 70016,
    'octavia figurine': 70017,
    'zecora figurine': 70018,
    'cheerilee figurine': 70019,
    'vinyl scratch figurine': 70020,
    'daring do figurine': 70021,
    'doctor whooves figurine': 70022,
    'berry punch figurine': 70023,
    'bon-Bon figurine': 70024,
    'fluffle puff figurine': 70025,
    'angel bunny figurine': 70101,
    'gummy figurine': 70102,
}
# 反轉字典
reversed_dict = {v: k for k, v in item_dict.items()}


def get_cookie():

    cookies = {}
    ipb_member_id_value = config.get('Account', 'ericeric91_UID')
    ipb_pass_hash_value = config.get('Account', 'ericeric91_ipb_pass_hash')
    ipb_session_id_value = config.get('Account', 'ericeric91_ipb_session_id')

    cookies = {
        'ipb_member_id': ipb_member_id_value,
        'ipb_pass_hash': ipb_pass_hash_value,
        'ipb_session_id': ipb_session_id_value
    }

    return cookies


class mm_write():
    def __init__(self, cookies: dict):
        self.mm_write_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=new'
        self.cookies = cookies
        # 進行 GET 請求並附加 cookie
        response = requests.get(self.mm_write_url, cookies=self.cookies)
        # 使用正則表達式提取 mmtoken
        self.mmtoken = re.search(
            r'<input type="hidden" name="mmtoken" value="(.*?)" />', response.text).group(1)
        logging.info('get mm_token:{}'.format(self.mmtoken))

    def attach_add_item(self, item_id: str, item_number: int):
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
            logging.info(
                'attach_add_item {}*{} success'.format(item_number, reversed_dict[item_id]))
            return True
        else:
            logging.warning('attach_add_item fail. code:{},text:{}'.format(
                response.status_code, response.text))
            return False
        # else:
        #     logging.critical('item_id {} does not exist'.format(item_id))
        #     return False

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
                logging.info('sent to {} success'.format(rcpt))
                return True
            else:
                logging.warning('send fail. code:{},text:{}'.format(
                    response.status_code, response.text))
                return False

    def discard(self):
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
            logging.info('mm discard')
            return True
        else:
            logging.warning('discard fail. code:{},text:{}'.format(
                response.status_code, response.text))
            return False


def check_item_list(item_list):
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


def send_mm_with_item(item_list: list, user_id: str, subject: str, body_text: str):
    """
    檢查item_list後發出MM
    """
    mm_start = mm_write(get_cookie())
    send_item_list = check_item_list(item_list)

    try:
        if mm_start.discard():
            counter: int = 0
            item_list_number: int = len(send_item_list)
            rcpt: str = user_id
            subject_text: str = subject
            body_text: str = body_text

            for send_item in send_item_list:
                if counter == 10:
                    mm_start.send(rcpt, subject_text, body_text)
                    counter = 0
                mm_start.attach_add_item(
                    item_dict[send_item['item_name'].lower()], send_item['item_number'])
                counter += 1
                item_list_number -= 1
                if item_list_number == 0:
                    mm_start.send(rcpt, subject_text, body_text)

            mm_start.discard()
            logging.info('MM has been sent to {},sent item_list:{}'.format(
                rcpt, send_item_list))
            logging.warning('MM has been sent to {}'.format(rcpt))

            return True
    except ValueError as e:
        logging.critical('setting value issye')
        logging.critical(e)
        return False


# ! 跳行方法仍不知道
# 跳行是'%0D%0A'
