import requests
import re
import csv
from bs4 import BeautifulSoup
import os
import configparser
import sys
import logging
from typing import List, Dict, TypedDict, Tuple
import enum
import inspect
import datetime
import csv_tools
from utils.utils import get_now_time
from utils.logger import setup_logger

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

HENTAIVERSE_URL = 'https://hentaiverse.org'


def check_folder_path_exists(folder_Path: os.path):
    if not os.path.exists(folder_Path):
        os.makedirs(folder_Path)
        logging.warning(f"資料夾 '{folder_Path}' 已建立。")


equip_type_mapping = {
    'Axe': 'Axe',
    'Club': 'Club',
    'Rapier': 'Rapier',
    'Shortsword': 'Shortsword',
    'Wakizashi': 'Wakizashi',
    'Estoc': 'Estoc',
    'Longsword': 'Longsword',
    'Mace': 'Mace',
    'Katana': 'Katana',
    'Oak': 'Oak',
    'Redwood': 'Redwood',
    'Willow': 'Willow',
    'Katalox': 'Katalox',
    'Buckler': 'Buckler',
    'Kite': 'Kite',
    'Force': 'Force',
    'Cotton': 'Cotton',
    'Phase': 'Phase',
    'Leather': 'Leather',
    'Shade': 'Shade',
    'Plate': 'Plate',
    'Power': 'Power'
}


def Mapping_Equip_Type(Equip_Name):
    """
    輸入Equip_Name輸出Equip_Type
    """
    for key, value in equip_type_mapping.items():
        if key in Equip_Name:
            return value
    return None


class EquipCategory(enum.Enum):
    ONE_HANDED = "1H"
    TWO_HANDED = "2H"
    STAFF = "staff"
    SHIELD = "shield"
    ARMOR_CLOTH = "acloth"
    ARMOR_LIGHT = "alight"
    ARMOR_HEAVY = "aheavy"


# Equip_Salvage_URL_MAP = {
#     EquipCategory.ONE_HANDED: "https://hentaiverse.org/?s=Forge&ss=sa&filter=1handed",
#     EquipCategory.TWO_HANDED: "https://hentaiverse.org/?s=Forge&ss=sa&filter=2handed",
#     EquipCategory.STAFF: "https://hentaiverse.org/?s=Forge&ss=sa&filter=staff",
#     EquipCategory.SHIELD: "https://hentaiverse.org/?s=Forge&ss=sa&filter=shield",
#     EquipCategory.ARMOR_CLOTH: "https://hentaiverse.org/?s=Forge&ss=sa&filter=acloth",
#     EquipCategory.ARMOR_LIGHT: "https://hentaiverse.org/?s=Forge&ss=sa&filter=alight",
#     EquipCategory.ARMOR_HEAVY: "https://hentaiverse.org/?s=Forge&ss=sa&filter=aheavy",
# }
Equip_Salvage_URL_MAP = {
    EquipCategory.ONE_HANDED: HENTAIVERSE_URL+"/?s=Forge&ss=sa&filter=1handed",
    EquipCategory.TWO_HANDED: HENTAIVERSE_URL+"/?s=Forge&ss=sa&filter=2handed",
    EquipCategory.STAFF: HENTAIVERSE_URL+"/?s=Forge&ss=sa&filter=staff",
    EquipCategory.SHIELD: HENTAIVERSE_URL+"/?s=Forge&ss=sa&filter=shield",
    EquipCategory.ARMOR_CLOTH: HENTAIVERSE_URL+"/?s=Forge&ss=sa&filter=acloth",
    EquipCategory.ARMOR_LIGHT: HENTAIVERSE_URL+"/?s=Forge&ss=sa&filter=alight",
    EquipCategory.ARMOR_HEAVY: HENTAIVERSE_URL+"/?s=Forge&ss=sa&filter=aheavy",
}


class Equip_Status_List(enum.Enum):
    Tradeable = 'Tradeable'
    Soulbound = 'Soulbound'


class Equip_Salvage_List_Data(TypedDict):
    id: int
    Datetime: datetime.datetime
    Equip_Category: str
    Equip_Type: str
    Equip_ID: str
    Equip_Name: str
    Equip_URL: str
    Equip_Level: str
    IW_Status: str
    Upgrades_Status: str
    Salvage_Materials: str


EQUIP_SALVAGE_LIST_HEADER: list[str] = list(
    Equip_Salvage_List_Data.__annotations__.keys())


class CookieDict(TypedDict):
    ipb_member_id: str
    ipb_pass_hash: str
    ipb_session_id: str


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


def get_equip_id(equip_url):
    try:
        equip_id = equip_url.split("/")[4]
        return equip_id
    except:
        print('error get_equip_id')


def Get_Equip_Level_0_90(soup):
    try:
        # 找到包含Level的<div>標籤，然後獲取其文字內容
        level_text = soup.text.split('Level')[1].strip()
        Equip_Level = level_text.split()[0]
        return Equip_Level
    except:
        return None


def Get_Equip_Category_0_90(soup):

    # 找到包含裝備類型的元素
    equip_Category_element = soup.find('div', class_='eq et')

    if equip_Category_element:
        # 從元素中取得裝備類型文本
        equip_Category = equip_Category_element.find(
            'div').text.strip().split()[0]
    else:
        equip_Category_element = soup.find('div', class_='eq es')
        equip_Category = equip_Category_element.find(
            'div').text.strip().split()[0]

    return equip_Category


def Get_Equip_Category_0_91(soup):

    # 找到包含裝備類型的元素
    equip_Category_element = soup.find('div', class_='eq')

    if equip_Category_element:
        # 從元素中取得裝備類型文本
        equip_Category = equip_Category_element.find(
            'div').text.strip().split()[0]
    else:
        equip_Category_element = soup.find('div', class_='eq')
        equip_Category = equip_Category_element.find(
            'div').text.strip().split()[0]

    return equip_Category


def Get_Equip_Status_Tradable_0_90(soup):
    try:
        # 定位目標信息
        tradeable_span = soup.find('div', id='equip_extended').find(
            'span', string=lambda text: text and ('Tradeable' in text or 'Untradeable' in text))

        if tradeable_span:
            tradeable_status = tradeable_span.text
            return tradeable_status
    except:
        return None


def Get_Equip_Status_0_91(soup) -> Equip_Status_List:

    eqt_div = soup.find("div", class_="eqt")
    if not eqt_div:
        return {"tier": [], "status": None}

    # 取得文字內容
    eqt_text = eqt_div.get_text(strip=True)

    # 擷取 Soulbound 或 Tradeable
    status_match = re.search(r"(Soulbound|Tradeable)", eqt_text)
    status = status_match.group(1) if status_match else None
    if status == 'Soulbound':
        status = Equip_Status_List.Soulbound
    elif status == 'Tradeable':
        status = Equip_Status_List.Tradeable
    return status


def Get_Equip_Status_IW_0_91(soup) -> str:
    # 找到 class="eqt" 的 div
    eqt_div = soup.find("div", class_="eqt")
    if not eqt_div:
        return {"tier": [], "status": None}

    # 取得文字內容
    eqt_text = eqt_div.get_text(strip=True)

    # 擷取 Tier 數字
    match = re.search(r"Tier\s+([\d\s/]+)", eqt_text)
    tier_numbers = [int(num) for num in match.group(1).split(
        "/") if num.strip().isdigit()] if match else []

    return tier_numbers


def Get_Equip_Status_Upgrades_0_90(soup):
    upgrades_and_enchantments_div = soup.find(
        'div', string='Upgrades and Enchantments')

    if upgrades_and_enchantments_div:
        enchantments_span = upgrades_and_enchantments_div.find_next(
            'span', id='eu')

        if enchantments_span:
            enchantments_text = enchantments_span.text.replace(
                '   ', '、')  # 使用 replace 替換掉空行
            return enchantments_text
        else:
            enchantments_text = 'None'
            return enchantments_text
    else:
        print("Upgrades and Enchantments section not found.")


def Get_Equip_Status_IW_0_90(soup):
    IW_div = soup.find(
        'div', string='Upgrades and Enchantments')

    if IW_div:
        IW_span = IW_div.find_next(
            'span', id='ep')

        if IW_span:
            IW_text = IW_span.text.replace(
                '   ', '、')  # 使用 replace 替換掉空行
            return IW_text
        else:
            IW_text = 'None'
            return IW_text
    else:
        print("IW section not found.")


def Get_Equip_Status_Owner(soup):
    current_owner_element = soup.find(
        string=lambda string: string and 'Current Owner:' in string)

    if current_owner_element:
        # 獲取包含 "Current Owner:" 的元素之後的第一個 a 元素
        a_element = current_owner_element.find_next('a')

        if a_element:
            user_id = a_element.text
            urer_url = a_element['href']
            urer_uid = re.search(
                r'https://forums\.e-hentai\.org/index\.php\?showuser=(\d+)', urer_url).group(1)
            return user_id, urer_uid
        else:
            print("未找到 'Current Owner:' 後的 a 元素")
    else:
        print("未找到包含 'Current Owner:' 的元素")


def Get_Equip_Status_Name_0_90(soup) -> str:
    Name_div = soup.select('div.fc4.fac.fcb > div')
    result = ' '.join(div.get_text() for div in Name_div)

    # print('Name_div:', Name_div)
    # print('result:', result)
    return result


def Get_Equip_Status_Name_0_91(soup) -> str:
    equip_div = soup.find('div', class_='showequip')

    # 裝備名稱在 'showequip' div 下的第一個 div
    equip_name_tag = equip_div.find('div')
    equip_name = equip_name_tag.text.strip() if equip_name_tag else "未找到裝備名稱"

    return equip_name


def Get_Equip_Status_Soulbound_0_90(soup):
    try:
        target_span = soup.select_one(
            '#equip_extended > div.eq.es > div:nth-child(1) > span')
        result = target_span.get_text()
        # print('target_span:', result)
        return result
    except:
        return None


def Get_Equip_Status_ALL_0_90(Equip_URL):

    # 發送帶有 Cookie 的請求
    response = requests.get(Equip_URL, cookies=get_cookie())

    if response.status_code == 200:
        # 獲取網頁內容
        html_content = response.text
    else:
        print(f"Request failed. Status code: {response.status_code}")

    # 使用Beautiful Soup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    user_id, user_uid = Get_Equip_Status_Owner(soup)

    Equip_Level = Get_Equip_Level_0_90(soup)
    Equip_Category = Get_Equip_Category_0_90(soup)
    Equip_Status_Tradable = Get_Equip_Status_Tradable_0_90(soup)
    Equip_Status_IW = Get_Equip_Status_IW_0_90(soup)
    Equip_Status_Upgrades = Get_Equip_Status_Upgrades_0_90(soup)
    Equip_Name = Get_Equip_Status_Name_0_90(soup)
    Equip_Status_Soulbound = Get_Equip_Status_Soulbound_0_90(soup)

    if Equip_Status_Soulbound:
        Equip_Level = Equip_Status_Soulbound
        Equip_Status_Tradable = Equip_Status_Soulbound

    return Equip_Name, Equip_Level, Equip_Category, Equip_Status_Tradable, Equip_Status_IW, Equip_Status_Upgrades, user_id, user_uid


def Get_Equip_Winner_0_91(soup) -> Tuple[str, str]:
    """
    output: sername, user_id
    """
    target_a = soup.find("a", {"target": "_forums"})

    # 取得文字與 href
    username = target_a.get_text(strip=True)
    profile_link = target_a.get("href")

    match = re.search(r"showuser=(\d+)", profile_link)
    if match:
        user_id = match.group(1)
    else:
        print("未找到 User ID")
        user_id = None

    return username, user_id


def Get_Equip_Status_Soulbound_0_91(soup):
    try:
        target_span = soup.select_one(
            '#equip_extended > div.eq.es > div:nth-child(1) > span')
        result = target_span.get_text()
        # print('target_span:', result)
        return result
    except:
        return None


def Get_Equip_Level_0_91(soup):

    # 裝備名稱 (第一個 <a> 標籤)
    name_tag = soup.find("a")
    name = name_tag.get_text(strip=True) if name_tag else None

    # 找到 class="eqt" 的 div
    eqt_div = soup.find("div", class_="eqt")
    eqt_text = eqt_div.get_text(strip=True) if eqt_div else ""

    # 擷取 Level 數字
    level_match = re.search(r"Level\s+(\d+)", eqt_text)
    level = int(level_match.group(1)) if level_match else None

    return level


def Get_Equip_Drop_time_0_91(soup):

    # Dropped by & Current Owner & 日期
    info_div = soup.find("div", style=re.compile("border-top"))
    drop_date = None

    if info_div:
        p_tags = info_div.find_all("p")
        if len(p_tags) >= 1:
            # Dropped by 誰 for 誰 on 日期
            dropped_text = p_tags[0].get_text(strip=True)
            # 擷取日期
            date_match = re.search(r"on\s+(\d{4}-\d{2}-\d{2})", dropped_text)
            drop_date = date_match.group(1) if date_match else None
            if date_match:
                # 轉換成 ISO 格式
                drop_date_iso = datetime.datetime.strptime(
                    date_match.group(1), "%Y-%m-%d").isoformat() + "Z"

    return drop_date_iso


def Get_Equip_Condition_0_91(soup):

    # Condition
    condition_div = soup.find("div", class_="eqr")
    condition_text = condition_div.get_text(
        strip=True) if condition_div else ""
    condition_match = re.search(r"Condition:\s*(\d+)%", condition_text)
    condition = int(condition_match.group(1)) if condition_match else None

    return condition


def Get_Equip_Status_ALL_0_91(Equip_URL):

    # 發送帶有 Cookie 的請求
    response = requests.get(Equip_URL, cookies=get_cookie())

    if response.status_code == 200:
        # 獲取網頁內容
        html_content = response.text
    else:
        print(f"Request failed. Status code: {response.status_code}")

    # 使用Beautiful Soup解析HTML
    # print(html_content)
    soup = BeautifulSoup(html_content, 'html.parser')

    user_id, user_uid = Get_Equip_Status_Owner(soup)

    Equip_Name = Get_Equip_Status_Name_0_91(soup)

    Equip_Category = Get_Equip_Category_0_91(soup)
    Equip_Status = Get_Equip_Status_0_91(soup)
    Equip_Winner_Username, Equip_Winner_UID = Get_Equip_Winner_0_91(soup)
    Equip_Drop_time = Get_Equip_Drop_time_0_91(soup)
    Equip_Condition = Get_Equip_Condition_0_91(soup)
    Equip_Status_Upgrades = None

    if Equip_Status == Equip_Status_List.Soulbound:
        Equip_Level = 0
        Equip_Status_Upgrades = Get_Equip_Status_IW_0_91(soup)
    elif Equip_Status == Equip_Status_List.Tradeable:
        Equip_Level = Get_Equip_Level_0_91(soup)
    else:
        logger.warning(f'Do not have Equip_Status')
        pass

    return Equip_Name, Equip_Level, Equip_Category, Equip_Condition, Equip_Status, Equip_Status_Upgrades, user_id, user_uid, Equip_Winner_Username, Equip_Winner_UID, Equip_Drop_time


def get_salvage_log_max_id() -> int:
    """
    從 salvage_log.csv 得取當前最大 id 值
    """
    # 進行檔案存在檢查
    salvage_log_file_path = os.path.join(
        csv_folder_path, 'salvage_log.csv',)
    csv_tools.check_csv_exists(
        salvage_log_file_path, EQUIP_SALVAGE_LIST_HEADER)

    if salvage_log_file_path:
        max_id = 0
        with open(salvage_log_file_path, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                current_id = int(row['id'])
                if max_id is None or current_id > max_id:
                    max_id = current_id
        return max_id
    # else:
        # logging('read_or_send input error,read_or_send:{},mm_or_list:{}'.format(
        #     read_or_send, mm_or_list))


class EquipForge:
    def __init__(self):
        # self.mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm'
        self.mm_url = HENTAIVERSE_URL+'/?s=Bazaar&ss=mm'
        self.mm_write_url = self.mm_url + '&filter=new'
        self.mm_inbox_url = self.mm_url + '&filter=inbox'
        self.cookies: CookieDict = get_cookie()
        self.mmtoken = None
        self.simple_token = None
        self.user_uid = config.get('Account', 'HV_Free_Shop_UID')

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

    def equip_salvage(self, equip_category: EquipCategory, equip_url: str):
        """
        拆解裝備
        """

        url = Equip_Salvage_URL_MAP[equip_category]

        EquipForge.get_simple_token(self)

        equip_id = get_equip_id(equip_url)

        data = {
            "select_item": equip_id,
        }

        # headers = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0",
        #     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        #     "Accept-Language": "zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3",
        #     "Content-Type": "application/x-www-form-urlencoded",
        #     "Upgrade-Insecure-Requests": "1",
        #     "Sec-Fetch-Dest": "document",
        #     "Sec-Fetch-Mode": "navigate",
        #     "Sec-Fetch-Site": "same-origin",
        #     "Sec-Fetch-User": "?1",
        #     "Priority": "u=0, i",
        #     "Pragma": "no-cache",
        #     "Cache-Control": "no-cache"
        # }
        Equip_Name, Equip_Level, Equip_Category, Equip_Status_Tradable, Equip_Status_IW, Equip_Status_Upgrades, user_id, user_uid = Get_Equip_Status_ALL_0_90(
            equip_url)

        # response = requests.post(url, headers=headers,
        #                          cookies=self.cookies, data=data)
        response = requests.post(url,
                                 cookies=self.cookies, data=data)
        if check_after_post(response, inspect.currentframe().f_code.co_name):
            soup = BeautifulSoup(response.text, 'html.parser')
            messagebox_outer = soup.find('div', id="messagebox_outer")
            messagebox_inner = messagebox_outer.find(
                'div', id="messagebox_inner")
            salvage_text = messagebox_inner.get_text(strip=True)

            if salvage_text == 'Item not found.':
                logging.error('mabye equip-id or equip-type error')
                return False
            elif salvage_text == 'Cannot salvage locked or equipped items':
                logging.error('Cannot salvage locked or equipped items')
            else:
                salvage_log_file_path = os.path.join(
                    csv_folder_path, 'salvage_log.csv',)
                csv_tools.check_csv_exists(
                    salvage_log_file_path, EQUIP_SALVAGE_LIST_HEADER)
                print(salvage_text)
                # 取得當前最大ID
                max_id = get_salvage_log_max_id()

                salvage_item_info = {
                    'id': max_id+1,
                    'Datetime': get_now_time(),
                    'Equip_Category': Equip_Category,
                    'Equip_Type': Mapping_Equip_Type(Equip_Name),
                    'Equip_ID': equip_id,
                    'Equip_Name': Equip_Name,
                    'Equip_URL': equip_url,
                    'Equip_Level': Equip_Level,
                    'IW_Status': Equip_Status_IW,
                    'Upgrades_Status': Equip_Status_Upgrades,
                    'Salvage_Materials': salvage_text
                }

                with open(salvage_log_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(
                        csvfile, fieldnames=EQUIP_SALVAGE_LIST_HEADER)
                    writer.writerows([salvage_item_info])

                return True

        else:
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


def check_after_post(response: requests, frame_name: str, mm_id: int = None) -> bool:

    # mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=' + mm_id
    if mm_id is not None:
        # mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox&mid=' + mm_id
        mm_url = HENTAIVERSE_URL+'/?s=Bazaar&ss=mm&filter=inbox&mid=' + mm_id
    else:
        # mm_url = 'https://hentaiverse.org/?s=Bazaar&ss=mm&filter=inbox'
        mm_url = HENTAIVERSE_URL+'/?s=Bazaar&ss=mm&filter=inbox'

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
