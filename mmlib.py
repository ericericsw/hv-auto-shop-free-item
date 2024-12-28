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
Log_Format = '%(asctime)s %(filename)s %(levelname)s:%(message)s'  # 日誌格式
log_file_path = os.path.join(
    current_directory, 'log', 'mm.log')
logging.basicConfig(level=getattr(logging, Log_Mode.upper()),
                    format=Log_Format,
                    handlers=[logging.FileHandler(log_file_path, 'a', 'utf-8'),
                              logging.StreamHandler()])

item_dict = {
    # Restoratives
    'health drauth': 11191,
    'health potion': 11195,
    'health elixir': 11199,
    'mana drauth': 11291,
    'mana potion': 11295,
    'mana elixir': 11299,
    'spirit drauth': 11391,
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
    'ManBearPig Tail': 30016,
    'Holy Hand Grenade of Antioch': 30017,
    "Mithra's Flower": 30018,
    'Dalek Voicebox': 30019,
    'Lock of Blue Hair': 30020,
    'Bunny-Girl Costume': 30021,
    'Hinamatsuri Doll': 30022,
    'Broken Glasses': 30023,
    'Sapling': 30030,
    'Noodly Appendage': 30032,
    # Crystal
    'Crystal of Vigor': 50001,
    'Crystal of Finesse': 50002,
    'Crystal of Swiftness': 50003,
    'Crystal of Fortitude': 50004,
    'Crystal of Cunning': 50005,
    'Crystal of Knowledge': 50006,
    'Crystal of Flames': 50011,
    'Crystal of Frost': 50012,
    'Crystal of Lightning': 50013,
    'Crystal of Tempest': 50014,
    'Crystal of Devotion': 50015,
    'Crystal of Corruption': 50016,
    # Food
    'Monster Chow': 51001,
    'Monster Edibles': 51002,
    'Monster Cuisine': 51003,
    'Happy Pills': 51011,
    # Materials
    'Low-Grade Cloth': 60001,
    'Mid-Grade Cloth': 60002,
    'High-Grade Cloth': 60003,
    'Low-Grade Leather': 60004,
    'Mid-Grade Leather': 60005,
    'High-Grade Leather': 60006,
    'Low-Grade Metals': 60007,
    'Mid-Grade Metals': 60008,
    'High-Grade Metals': 60009,
    'Low-Grade Wood': 60010,
    'Mid-Grade Wood': 60011,
    'High-Grade Wood': 60012,
    'Scrap Cloth': 60051,
    'Scrap Leather': 60052,
    'Scrap Metal': 60053,
    'Scrap Wood': 60054,
    'Energy Cell': 60071,
    'Crystallized Phazon': 60101,
    'Shade Fragment': 60102,
    'Repurposed Actuator': 60104,
    'Defense Matrix Modulator': 60105,
    'Binding of Slaughter': 60201,
    'Binding of Balance': 60202,
    'Binding of Destruction': 60203,
    'Binding of Focus': 60204,
    'Binding of Protection': 60205,
    'Binding of the Fleet': 60206,
    'Binding of the Barrier': 60207,
    'Binding of the Nimble': 60208,
    'Binding of the Elementalist': 60209,
    'Binding of the Heaven-sent': 60210,
    'Binding of the Demon-fiend': 60211,
    'Binding of the Curse-weaver': 60212,
    'Binding of the Earth-walker': 60213,
    'Binding of Surtr': 60215,
    'Binding of Niflheim': 60216,
    'Binding of Mjolnir': 60217,
    'Binding of Freyr': 60218,
    'Binding of Heimdall': 60219,
    'Binding of Fenrir': 60220,
    'Binding of Dampening': 60221,
    'Binding of Stoneskin': 60222,
    'Binding of Deflection': 60223,
    'Binding of the Fire-eater': 60224,
    'Binding of the Frost-born': 60225,
    'Binding of the Thunder-child': 60226,
    'Binding of the Wind-waker': 60227,
    'Binding of the Thrice-blessed': 60228,
    'Binding of the Spirit-ward': 60229,
    'Binding of the Ox': 60230,
    'Binding of the Raccoon': 60231,
    'Binding of the Cheetah': 60232,
    'Binding of the Turtle': 60233,
    'Binding of the Fox': 60234,
    'Binding of the Owl': 60235,
    'Binding of Warding': 60236,
    'Binding of Negation': 60237,
    'Binding of Isaac': 60238,
    'Binding of Friendship': 60239,
    'Legendary Weapon Core': 60402,
    'Legendary Staff Core': 60412,
    'Legendary Armor Core': 60422,
    'Voidseeker Shard': 61001,
    'Aether Shard': 61101,
    'Featherweight Shard': 61501,
    'Amnesia Shard': 65001,
    # Figurine
    'Twilight Sparkle Figurine': 70001,
    'Rainbow Dash Figurine': 70002,
    'Applejack Figurine': 70003,
    'Fluttershy Figurine': 70004,
    'Pinkie Pie Figurine': 70005,
    'Rarity Figurine': 70006,
    'Trixie Figurine': 70007,
    'Princess Celestia Figurine': 70008,
    'Princess Luna Figurine': 70009,
    'Apple Bloom Figurine': 70010,
    'Scootaloo Figurine': 70011,
    'Sweetie Belle Figurine': 70012,
    'Big Macintosh Figurine': 70013,
    'Spitfire Figurine': 70014,
    'Derpy Hooves Figurine': 70015,
    'Lyra Heartstrings Figurine': 70016,
    'Octavia Figurine': 70017,
    'Zecora Figurine': 70018,
    'Cheerilee Figurine': 70019,
    'Vinyl Scratch Figurine': 70020,
    'Daring Do Figurine': 70021,
    'Doctor Whooves Figurine': 70022,
    'Berry Punch Figurine': 70023,
    'Bon-Bon Figurine': 70024,
    'Fluffle Puff Figurine': 70025,
    'Angel Bunny Figurine': 70101,
    'Gummy Figurine': 70102,
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

# ! 跳行方法仍不知道
# 跳行是'%0D%0A'


def main():
    cookies = get_cookie()
    mm_start = mm_write(cookies)
    if mm_start.discard():
        attach_item_list = [{
            'item_name': 'health drauth',
            'item_number': 10
        }, {
            'item_name': 'mana drauth',
            'item_number': 10
        }]

        counter: int = 0
        item_list_number: int = len(attach_item_list)
        rcpt: str = 'VVFGV'
        subject_text: str = '123'
        body_text: str = '456%0D%0A789'

        for attach_item in attach_item_list:
            if counter == 10:
                mm_start.send(rcpt, subject_text, body_text)
                counter = 0
            mm_start.attach_add_item(
                item_dict[attach_item['item_name']], attach_item['item_number'])
            counter += 1
            item_list_number -= 1
            if item_list_number == 0:
                mm_start.send(rcpt, subject_text, body_text)
        # mm_start.attach_add_item(item_dict['health drauth'], 10)
        # mm_start.send('VVFGV', '123', '456%0D%0A789')
        mm_start.discard()
        print('done')

    # mmstart.attach_add_item(item_dict['health drauth'], 10)
    # mmstart.send('VVFGV', '123', '456%0D%0A789')
    # mmstart.discard()

    # # 目標網址
    # url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=new'

    # # 進行 GET 請求並附加 cookie
    # response = requests.get(url, cookies=cookies)

    # # 顯示返回的內容
    # # print(response.text)

    # # 取得回應內容
    # html_content = response.text

    # # 使用正則表達式提取 mmtoken
    # mmtoken_match = re.search(
    #     r'<input type="hidden" name="mmtoken" value="(.*?)" />', html_content)

    # if mmtoken_match:
    #     mmtoken = mmtoken_match.group(1)
    #     print(f'mmtoken: {mmtoken}')
    # else:
    #     print('mmtoken not found')

    # payload = {
    #     'mmtoken': mmtoken,          # 你剛剛提取到的 mmtoken
    #     'action': 'attach_add',
    #     'action_value': '0',
    #     'select_item': '11291',
    #     'select_count': '1',
    #     'select_pane': 'item',
    #     'message_to_name': '',
    #     'message_subject': '',
    #     'message_body': ''
    # }

    # response = requests.post(url, data=payload, cookies=cookies)
    # print(response.text)


if __name__ == "__main__":
    main()
    print('')
